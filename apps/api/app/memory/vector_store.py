"""Qdrant vector store with in-memory fallback.

If Qdrant is not reachable, falls back to a simple cosine-similarity
in-memory store so the pipeline never hard-fails during local dev.
"""

from __future__ import annotations

import hashlib
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory fallback
# ---------------------------------------------------------------------------
_memory_store: list[tuple[list[float], str]] = []


def _text_to_vector(text: str) -> list[float]:
    """Deterministic char-frequency pseudo-embedding (64-dim). Demo only."""
    vec = [0.0] * 64
    for ch in text:
        vec[ord(ch) % 64] += 1.0
    norm = (sum(v ** 2 for v in vec) ** 0.5) or 1.0
    return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = (sum(x ** 2 for x in a) ** 0.5) or 1e-9
    nb = (sum(x ** 2 for x in b) ** 0.5) or 1e-9
    return dot / (na * nb)


# ---------------------------------------------------------------------------
# Qdrant client (optional)
# ---------------------------------------------------------------------------
_qdrant = None

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams

    _qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=2)
    _qdrant.get_collections()  # connectivity check

    if not any(c.name == settings.qdrant_collection for c in _qdrant.get_collections().collections):
        _qdrant.create_collection(
            settings.qdrant_collection,
            vectors_config=VectorParams(size=64, distance=Distance.COSINE),
        )
    logger.info("Qdrant connected — using persistent vector store")
except Exception as e:
    logger.warning("Qdrant unavailable (%s) — using in-memory fallback", e)
    _qdrant = None


def upsert(text: str, payload: dict | None = None) -> None:
    vec = _text_to_vector(text)
    if _qdrant is not None:
        from qdrant_client.models import PointStruct
        point_id = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        _qdrant.upsert(
            collection_name=settings.qdrant_collection,
            points=[PointStruct(id=point_id, vector=vec, payload={"text": text, **(payload or {})})],
        )
    else:
        _memory_store.append((vec, text))


def search(query: str, top_k: int = 5) -> list[str]:
    vec = _text_to_vector(query)
    if _qdrant is not None:
        result = _qdrant.query_points(
            collection_name=settings.qdrant_collection,
            query=vec,
            limit=top_k,
        )
        return [h.payload.get("text", "") for h in result.points if h.payload]
    else:
        scored = sorted(_memory_store, key=lambda item: _cosine(vec, item[0]), reverse=True)
        return [text for _, text in scored[:top_k]]


def reset_memory_store() -> None:
    _memory_store.clear()
