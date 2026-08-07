"""Regional-language support (Phase 23.b) — translates between English and
Hindi/Tamil/Malayalam via Google Translate's free web endpoint (deep-translator,
no API key/billing needed, consistent with this build's "no paid keys"
constraint elsewhere — see services/vessels.py, services/pollution.py).

Two directions, both routed through this one function:
  - incoming: a regional-language chat message translated to English before
    it reaches the RAG pipeline (the seed text chunks and gpt-oss context are
    all English)
  - outgoing: an English answer translated to the user's chosen language for
    display, on demand, per message — not part of the original gpt-oss call,
    so switching a past message's display language never re-runs the LLM
"""

from functools import lru_cache

from deep_translator import GoogleTranslator

SUPPORTED_LANGUAGES = {"en", "hi", "ta", "ml"}


@lru_cache(maxsize=512)
def _translate_cached(text: str, source: str, target: str) -> str:
    return GoogleTranslator(source=source, target=target).translate(text) or text


def translate(text: str, target_lang: str, source_lang: str = "auto") -> str:
    """Falls back to the original text if the translate call fails (network
    down, endpoint rate-limited) rather than surfacing an error — a message
    shown in the wrong language beats one that fails to display at all."""
    if not text.strip() or target_lang == source_lang:
        return text
    try:
        return _translate_cached(text, source_lang, target_lang)
    except Exception:
        return text
