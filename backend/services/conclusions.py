"""One small gpt-oss call, reused by every model view (Phase 19). Turns a
model's numeric output into a single grounded, plain-language sentence with an
explicit confidence caveat — the same guardrail the chat assistant already
follows (services/rag.py): ground the sentence in the given summary, never
invent a number that isn't in it, and say so plainly if confidence is low.
"""

from services import llm

SYSTEM_PROMPT = """You turn one model's numeric output into a single plain-language \
conclusion sentence for a non-technical reader.

Rules:
- Exactly one sentence, plain language, no jargon.
- Use only the numbers/facts given below — never invent a figure that isn't present.
- End with a short confidence caveat in parentheses, matching the confidence level given.
- If confidence is low, say so plainly rather than asserting the conclusion."""


def conclude(summary: str, confidence: str) -> str:
    """summary: a short factual description of what the model computed.
    confidence: "high" | "medium" | "low" (or a similar short label)."""
    try:
        response = llm.chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Model output: {summary}\nConfidence: {confidence}"},
            ]
        )
        text = (response.message.content or "").strip()
        return text or _fallback(summary, confidence)
    except Exception:
        return _fallback(summary, confidence)


def _fallback(summary: str, confidence: str) -> str:
    return f"{summary} ({confidence} confidence — plain-language summary unavailable, gpt-oss unreachable)"
