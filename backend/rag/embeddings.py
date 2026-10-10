"""Embeddings via hosted APIs (Mistral, Gemini) instead of a local model.

Why: a local model (PyTorch or ONNX) needs hundreds of MB of RAM, which exceeds
Render's free 512 MB tier and gets the server killed during the first upload.
Calling a hosted embeddings API keeps the server small and costs nothing on the
free tiers of these providers. Both expose OpenAI-compatible /embeddings endpoints,
so one client library covers them.

Vectors from different providers live in different spaces (and have different
sizes), so each report's index records which provider built it and queries are
always embedded with that same provider.
"""
import logging
import time

import numpy as np
from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_BATCH_SIZE = 16


def _is_real_key(key: str | None) -> bool:
    if not key:
        return False
    s = key.strip().lower()
    return not (not s or s.startswith("your_") or s.endswith("_here") or s in {"changeme", "xxx", "todo"})


def _provider_config(name: str) -> tuple[str, str, str] | None:
    """Return (base_url, api_key, model) for a provider, or None if unconfigured."""
    if name == "mistral" and _is_real_key(settings.MISTRAL_API_KEY):
        return settings.MISTRAL_BASE_URL, settings.MISTRAL_API_KEY, settings.MISTRAL_EMBED_MODEL
    if name == "gemini" and _is_real_key(settings.GEMINI_API_KEY):
        return settings.GEMINI_BASE_URL, settings.GEMINI_API_KEY, settings.GEMINI_EMBED_MODEL
    return None


def _embed_with(name: str, texts: list[str]) -> np.ndarray:
    cfg = _provider_config(name)
    if cfg is None:
        raise RuntimeError(f"embedding provider '{name}' is not configured")
    base_url, api_key, model = cfg
    client = OpenAI(base_url=base_url, api_key=api_key, timeout=40, max_retries=1)

    out: list[list[float]] = []
    for start in range(0, len(texts), _BATCH_SIZE):
        batch = texts[start:start + _BATCH_SIZE]
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                resp = client.embeddings.create(model=model, input=batch)
                out.extend(d.embedding for d in sorted(resp.data, key=lambda d: d.index))
                last_err = None
                break
            except Exception as e:  # rate limit / transient network error
                last_err = e
                time.sleep(1.5 * (attempt + 1))
        if last_err is not None:
            raise last_err

    vectors = np.asarray(out, dtype="float32")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def embed_texts(texts: list[str], providers: list[str] | None = None) -> tuple[np.ndarray, str]:
    """Embed texts with the first provider that works. Returns (L2-normalized vectors,
    name of the provider used)."""
    order = providers or [p.strip() for p in settings.EMBEDDING_PROVIDER_ORDER.split(",") if p.strip()]
    errors: list[str] = []
    for name in order:
        if _provider_config(name) is None:
            continue
        try:
            return _embed_with(name, texts), name
        except Exception as e:
            logger.warning("Embedding provider %s failed: %s", name, e)
            errors.append(f"{name}: {e}")
    raise RuntimeError("No embedding provider available. " + ("; ".join(errors) or "no API keys configured"))
