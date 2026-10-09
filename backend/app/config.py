"""
Central application configuration.

Everything here can be overridden with environment variables or a `.env`
file placed in the `backend/` folder. Keeping all tunables in one place
makes the system easy to reconfigure for different free-tier LLM
providers without touching business logic.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    APP_NAME: str = "MedReport AI"
    ENV: str = "development"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # --- Storage ---
    DATABASE_URL: str = "sqlite:///./medreport.db"
    UPLOAD_DIR: str = "./storage/uploads"
    VECTOR_STORE_DIR: str = "./storage/vector_store"
    MAX_UPLOAD_MB: int = 15

    # --- LLM provider chain (OpenAI-compatible) ---
    # Instead of a single primary + fallback, requests try each configured
    # provider IN ORDER until one succeeds. Any provider left with an empty
    # api_key is automatically skipped.
    #
    # Two separate orders: English requests prioritize Groq (fastest, most
    # reliable, no billing-link bugs). Telugu requests prioritize Gemini
    # FIRST — Google invests specifically in Indian-language quality, and
    # Llama-family models (Groq/Cerebras) tend to produce stiffer, more
    # literal/bookish Telugu. Both orders fall through to the same pool of
    # providers if the first choice is unavailable.
    LLM_PROVIDER_ORDER_EN: str = "groq,mistral,gemini,openai"
    LLM_PROVIDER_ORDER_TE: str = "sarvam,gemini,groq,mistral,openai"
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_MAX_TOKENS: int = 2048  # Report Overview needs 11 sections — 900 was too low and
                                # caused valid responses to get cut off mid-generation,
                                # which looked like "AI unavailable" even though the call succeeded
    LLM_TEMPERATURE: float = 0.2

    # Groq — https://console.groq.com/keys (free, no credit card required)
    # llama-3.3-70b-versatile (the previous default here) was deprecated by
    # Groq on June 17, 2026 with an August 16, 2026 shutdown — already past.
    # Switched to openai/gpt-oss-120b, Groq's own recommended replacement.
    # Check https://console.groq.com/docs/models if this changes again.
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_API_KEY: str = ""

    # Cerebras — https://cloud.cerebras.ai (free, 1M tokens/day)
    # Cerebras retires models on short notice (llama-3.3-70b, our previous
    # default, was deprecated Feb 2026 and returns 404 now). If gpt-oss-120b
    # also 404s later, check the current catalog at
    # https://inference-docs.cerebras.ai/models/overview and override
    # CEREBRAS_MODEL below without needing a code change.
    CEREBRAS_BASE_URL: str = "https://api.cerebras.ai/v1"
    CEREBRAS_MODEL: str = "gpt-oss-120b"
    CEREBRAS_API_KEY: str = ""

    # Mistral — https://console.mistral.ai (free "Experiment" tier, 1B tokens/month)
    MISTRAL_BASE_URL: str = "https://api.mistral.ai/v1"
    MISTRAL_MODEL: str = "mistral-small-latest"
    MISTRAL_API_KEY: str = ""

    # OpenRouter — https://openrouter.ai/keys (aggregates many free models behind one key)
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "meta-llama/llama-3.3-70b-instruct:free"
    OPENROUTER_API_KEY: str = ""

    # Gemini — https://aistudio.google.com/apikey (see note above on current reliability)
    # Model name uses the "gemini-flash-latest" alias rather than a fixed version
    # string (e.g. "gemini-2.5-flash") because Google has been retiring Gemini
    # model generations extremely fast — 2.5 -> 3 -> 3.1 -> 3.5 -> 3.6 within a
    # few months — sometimes returning 404 for brand-new API keys even before
    # the official deprecation date. The "-latest" alias is Google's own
    # documented mechanism for this exact problem and tracks whatever the
    # current GA flash model is, so this shouldn't need updating every time
    # Google ships a new generation. If Gemini still 404s, check the current
    # model list at https://ai.google.dev/gemini-api/docs/models.
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    GEMINI_MODEL: str = "gemini-flash-latest"
    GEMINI_API_KEY: str = ""

    # Sarvam AI — https://dashboard.sarvam.ai (₹100-1,000 free signup credits,
    # pay-as-you-go after — NOT a perpetual daily/monthly-reset free tier like
    # the others, it's a fixed credit pool). Indian company building models
    # specifically for Indian languages (22 of them, including Telugu) rather
    # than as a side feature — routed FIRST for Telugu requests (see
    # LLM_PROVIDER_ORDER_TE above) since this is genuinely their specialty.
    # sarvam-30b (the previous default here) was deprecated Aug 2026 —
    # sarvam-105b is the current flagship model. Check
    # https://docs.sarvam.ai/api/getting-started/models if this 404s later.
    SARVAM_BASE_URL: str = "https://api.sarvam.ai/v1"
    SARVAM_MODEL: str = "sarvam-105b"
    SARVAM_API_KEY: str = ""

    # OpenAI — optional, OFF by default (empty key = skipped). Deliberately last
    # in both orders and NOT recommended as a primary choice: OpenAI's "free tier"
    # is really a one-time trial credit that expires, after which it requires
    # billing — this doesn't fit the free-tier-first approach used everywhere
    # else in this app. Included only as an opt-in extra if you want to add paid
    # quality/capacity on top of the free chain. https://platform.openai.com/api-keys
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_API_KEY: str = ""

    # --- RAG ---
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE_CHARS: int = 800
    CHUNK_OVERLAP_CHARS: int = 120
    RAG_TOP_K: int = 5

    # --- Extraction ---
    SPACY_MODEL: str = "en_core_web_sm"
    LOINC_LOCAL_PATH: str = "./data/loinc_subset.csv"

    # --- Translation ---
    SUPPORTED_LANGUAGES: list[str] = ["en", "te"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
