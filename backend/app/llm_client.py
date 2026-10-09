"""
Multi-provider LLM client with automatic failover.

Rather than a single primary + fallback, this tries EVERY configured
provider in the order given by settings.LLM_PROVIDER_ORDER_EN or _TE
(English and Telugu use separate orders), skipping any
provider whose API key is empty. This means:

- If one provider is rate-limited, misconfigured, or down, the request
  transparently moves to the next one — the user never sees an error
  unless every single configured provider fails.
- Providers can be added, removed, or reordered entirely via .env, with
  zero code changes.
- All providers must be OpenAI-compatible chat-completion endpoints
  (Groq, Cerebras, Mistral, OpenRouter, Gemini, a local Ollama server,
  etc. all qualify).
"""
import logging
from dataclasses import dataclass

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMUnavailableError(Exception):
    """Raised only when every configured provider has failed."""


@dataclass
class ProviderConfig:
    name: str
    base_url: str
    model: str
    api_key: str
    # Extra fields merged into the OpenAI SDK's `extra_body` for this provider's
    # requests — needed for provider-specific quirks that aren't part of the
    # standard OpenAI request shape. Currently only Sarvam uses this: its models
    # have "thinking mode" on by default, and reasoning tokens count against
    # max_tokens, so without disabling it a small token budget can be entirely
    # consumed by invisible reasoning, leaving an empty reply.
    extra_body: dict | None = None


def _provider_registry() -> dict[str, ProviderConfig]:
    return {
        "groq": ProviderConfig("groq", settings.GROQ_BASE_URL, settings.GROQ_MODEL, settings.GROQ_API_KEY),
        "cerebras": ProviderConfig("cerebras", settings.CEREBRAS_BASE_URL, settings.CEREBRAS_MODEL, settings.CEREBRAS_API_KEY),
        "mistral": ProviderConfig("mistral", settings.MISTRAL_BASE_URL, settings.MISTRAL_MODEL, settings.MISTRAL_API_KEY),
        "openrouter": ProviderConfig("openrouter", settings.OPENROUTER_BASE_URL, settings.OPENROUTER_MODEL, settings.OPENROUTER_API_KEY),
        "gemini": ProviderConfig("gemini", settings.GEMINI_BASE_URL, settings.GEMINI_MODEL, settings.GEMINI_API_KEY),
        "sarvam": ProviderConfig(
            "sarvam", settings.SARVAM_BASE_URL, settings.SARVAM_MODEL, settings.SARVAM_API_KEY,
            extra_body={"reasoning_effort": None},  # disable thinking mode — see ProviderConfig docstring
        ),
        "openai": ProviderConfig("openai", settings.OPENAI_BASE_URL, settings.OPENAI_MODEL, settings.OPENAI_API_KEY),
    }


def _is_real_key(key: str) -> bool:
    """
    Filters out placeholder text left over from .env.example (e.g.
    "your_groq_key_here") so those providers are silently skipped instead of
    being attempted and failing with a confusing 401/400 error. Without this,
    copying .env.example to .env and only filling in 1-2 keys causes every
    OTHER provider to still be "configured" (non-empty string) and get tried
    and fail first, which is exactly what happened in testing: Groq, Mistral,
    OpenRouter, and Gemini all failed with "Invalid API Key" because their
    placeholder text was still present, not because real keys were wrong.
    """
    if not key:
        return False
    stripped = key.strip().lower()
    if not stripped:
        return False
    if stripped.startswith("your_") or stripped.endswith("_here") or stripped in {"changeme", "xxx", "todo"}:
        return False
    return True


def _ordered_providers(language: str = "en") -> list[ProviderConfig]:
    registry = _provider_registry()
    order_str = settings.LLM_PROVIDER_ORDER_TE if language == "te" else settings.LLM_PROVIDER_ORDER_EN
    order = [name.strip().lower() for name in order_str.split(",") if name.strip()]
    providers = [registry[name] for name in order if name in registry]
    # only providers with a real (non-placeholder) key are usable
    return [p for p in providers if _is_real_key(p.api_key)]


@retry(stop=stop_after_attempt(2), wait=wait_fixed(1), reraise=True)
def _call(provider: ProviderConfig, system_prompt: str, user_prompt: str) -> str:
    client = OpenAI(base_url=provider.base_url, api_key=provider.api_key, timeout=settings.LLM_TIMEOUT_SECONDS)
    kwargs = {}
    if provider.extra_body:
        kwargs["extra_body"] = provider.extra_body
    response = client.chat.completions.create(
        model=provider.model,
        max_tokens=settings.LLM_MAX_TOKENS,
        temperature=settings.LLM_TEMPERATURE,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        **kwargs,
    )
    return (response.choices[0].message.content or "").strip()


def generate(system_prompt: str, user_prompt: str, language: str = "en") -> str:
    """
    Tries each configured provider in order (English and Telugu use different
    orders — see settings.LLM_PROVIDER_ORDER_EN / _TE), returning the first
    successful response. Raises LLMUnavailableError only if every provider
    fails (or none are configured at all).
    """
    providers = _ordered_providers(language)
    if not providers:
        raise LLMUnavailableError(
            "No LLM provider is configured. Add at least one API key "
            "(GROQ_API_KEY, CEREBRAS_API_KEY, MISTRAL_API_KEY, OPENROUTER_API_KEY, "
            "GEMINI_API_KEY, SARVAM_API_KEY, or OPENAI_API_KEY) to your .env file."
        )

    last_error: Exception | None = None
    for provider in providers:
        try:
            result = _call(provider, system_prompt, user_prompt)
            if result:
                return result
        except Exception as e:  # noqa: BLE001
            logger.warning("Provider '%s' failed, trying next: %s", provider.name, e)
            last_error = e
            continue

    logger.error("All LLM providers failed. Last error: %s", last_error)
    raise LLMUnavailableError(
        "The AI explanation service is temporarily unavailable across all configured "
        "providers. Please try again shortly."
    ) from last_error
