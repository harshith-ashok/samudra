"""Embeds the RAG text corpus once at startup and keeps it as an in-memory numpy matrix.

Per CLAUDE.md: no hosted vector DB needed for a 2-day build — in-memory cosine
similarity over a small corpus is plenty.
"""

import numpy as np

from services import data, llm

_chunk_ids: list[str] = []
_matrix: np.ndarray | None = None


def build_index() -> None:
    global _chunk_ids, _matrix
    chunks = data.text_chunks()
    texts = [f"{c['title']}. {c['text']}" for c in chunks]
    vectors = llm.embed(texts)
    _matrix = np.array(vectors, dtype=np.float32)
    _matrix /= np.linalg.norm(_matrix, axis=1, keepdims=True)
    _chunk_ids = [c["id"] for c in chunks]


def is_ready() -> bool:
    return _matrix is not None


def search(query: str, top_k: int = 4) -> list[tuple[dict, float]]:
    if _matrix is None:
        build_index()
    query_vec = np.array(llm.embed([query])[0], dtype=np.float32)
    query_vec /= np.linalg.norm(query_vec)
    scores = _matrix @ query_vec
    top_idx = np.argsort(-scores)[:top_k]
    chunks_by_id = {c["id"]: c for c in data.text_chunks()}
    return [(chunks_by_id[_chunk_ids[i]], float(scores[i])) for i in top_idx]
