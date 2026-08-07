"""Whisper-based speech-to-text for the NLQ search bar and AI Assistant mic
input.

Runs locally via faster-whisper (CTranslate2), not through Ollama — gpt-oss
doesn't do audio, so this is deliberately the one place a non-Ollama model is
used, same "one model, one job" principle as services/llm.py just applied to
a different job. faster-whisper decodes the browser's webm/opus recording
directly (via bundled PyAV/ffmpeg), no separate conversion step needed.

Uses the multilingual "small" model (not "base.en") so the same model
transcribes English, Hindi, Tamil, and Malayalam (Phase 23.b) — passing the
expected language explicitly (rather than relying on auto-detect) noticeably
improves accuracy for the Indic languages, and costs nothing for English.
"""

from functools import lru_cache
from io import BytesIO

from faster_whisper import WhisperModel

MODEL_SIZE = "small"  # multilingual — covers en/hi/ta/ml with one model
DEFAULT_LANGUAGE = "en"


@lru_cache
def _model() -> WhisperModel:
    return WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")


def transcribe(audio_bytes: bytes, language: str = DEFAULT_LANGUAGE) -> str:
    segments, _ = _model().transcribe(BytesIO(audio_bytes), language=language)
    return " ".join(segment.text.strip() for segment in segments).strip()


def warm() -> None:
    """Loads the model now, so the first real mic request isn't the one
    paying the (~0.5-60s depending on cache) load cost."""
    _model()
