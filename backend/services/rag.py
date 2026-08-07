"""Orchestrates one gpt-oss call fed by two retrieval paths:

- structured: model-invoked tools hit the seed "database" directly (services/tools.py)
- unstructured: cosine-similarity retrieval over embedded text chunks (services/embed.py)

Both are folded into the same conversation before the model answers, so there is
one call, not two separate pipelines bolted together after the fact.
"""

import json

from services import embed, llm, tools

SYSTEM_PROMPT = """You are the SAMUDRA research assistant, unifying ocean sensor, \
fisheries, and biodiversity/eDNA data for the Indian coast.

Rules:
- Answer ONLY using the provided background context, tool results, and station \
context below. Do not invent numbers, species, or advisories that are not present \
in that material.
- Prefer calling a tool when the question needs a specific number (catch tonnage, \
sensor reading, advisory status, species status) — tool results are ground truth, \
background context is supporting narrative.
- Do not add your own "Sources:" line — the application appends the actual sources \
used underneath your answer automatically.
- If the context does not contain enough information to answer, say so plainly \
instead of guessing.
- Keep answers concise (3-5 sentences) unless the user asks for more detail."""

MAX_TOOL_ROUNDS = 3


def _format_context_block(hits: list[tuple[dict, float]]) -> str:
    lines = []
    for chunk, score in hits:
        lines.append(f"[{chunk['id']}] {chunk['title']}: {chunk['text']} (source: {chunk['source']})")
    return "\n\n".join(lines)


def answer(message: str, station_context: dict | None = None, species_context: dict | None = None) -> dict:
    hits = embed.search(message, top_k=4)
    sources: list[str] = [f"doc:{c['id']} {c['title']}" for c, _ in hits]

    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append({"role": "system", "content": f"Relevant background context:\n{_format_context_block(hits)}"})
    if station_context:
        messages.append(
            {
                "role": "system",
                "content": f"The user currently has this station selected on the map — treat it as directly relevant even if not named in the question:\n{json.dumps(station_context)}",
            }
        )
    if species_context:
        messages.append(
            {
                "role": "system",
                "content": f"The user currently has this species selected in Movement Trends — treat it as directly relevant even if not named in the question:\n{json.dumps(species_context)}",
            }
        )
    messages.append({"role": "user", "content": message})

    for _ in range(MAX_TOOL_ROUNDS):
        response = llm.chat(messages, tools=tools.TOOL_SPECS)
        msg = response.message
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            return {"answer": msg.content or "", "sources": sources}

        for call in msg.tool_calls:
            result = tools.run_tool(call.function.name, dict(call.function.arguments))
            sources.append(f"tool:{call.function.name}({dict(call.function.arguments)})")
            messages.append(
                {"role": "tool", "tool_name": call.function.name, "content": json.dumps(result, default=str)}
            )

    # ran out of tool rounds — force a final answer with no more tool access
    final = llm.chat(messages)
    return {"answer": final.message.content or "", "sources": sources}
