"""
Free translation utility using deep-translator (Google Translate backend, no API key).

NOTE on how translation actually works in this app:
- AI-generated content (explanations, summaries, chat, flashcards) is generated
  DIRECTLY in the target language by the LLM (see explanation/explanation_engine.py
  and rag/chat_engine.py) — natural Telugu, not machine-translated — so this module
  is NOT used in that path.
- The app's static UI (nav, buttons, labels) is translated via a pre-built cached
  dictionary in frontend/src/i18n/, so no runtime translation call happens there
  either.
- This module remains as a general-purpose utility and backs
  scripts/generate_ui_translations.py, which helps draft new UI dictionary entries
  when the interface is extended.
"""
import logging

from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

_LANG_CODE_MAP = {"en": "en", "te": "te"}


def translate_text(text: str, target_language: str) -> str:
    if target_language == "en" or not text.strip():
        return text
    code = _LANG_CODE_MAP.get(target_language)
    if not code:
        return text
    try:
        return GoogleTranslator(source="en", target=code).translate(text)
    except Exception as e:  # noqa: BLE001
        logger.warning("Translation to '%s' failed, falling back to English: %s", target_language, e)
        return text


def translate_dict(data: dict, target_language: str) -> dict:
    """Translates every string value in a flat dict, preserving keys."""
    if target_language == "en":
        return data
    return {k: translate_text(v, target_language) if isinstance(v, str) else v for k, v in data.items()}
