"""Qdrant vector store with fastembed embeddings and in-memory fallback.

Embedding strategy:
  Primary  — fastembed `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
             (384-dim, ONNX Runtime).  No PyTorch dependency; suitable for CPU demo
             environments.  Supports Korean + English.  Loaded lazily on first call.
  Fallback — char-frequency pseudo-embedding (384-dim) when fastembed is not installed.
             Keeps the pipeline runnable in minimal environments.

Qdrant collection is created with size=384.  If an existing collection has a
different vector size (e.g. the legacy 64-dim demo store), it is dropped and
recreated automatically — persistent data from the old schema is discarded.
"""

from __future__ import annotations

import hashlib
import logging

from app.config import settings

logger = logging.getLogger(__name__)

_EMBEDDING_DIM = 384
_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# ---------------------------------------------------------------------------
# Encoder — lazy-loaded fastembed model (ONNX, no PyTorch)
# ---------------------------------------------------------------------------
_encoder: object = None   # TextEmbedding instance, False (unavailable), or None (unloaded)


def _get_encoder():
    global _encoder
    if _encoder is None:
        try:
            from fastembed import TextEmbedding  # type: ignore
            _encoder = TextEmbedding(model_name=_MODEL_NAME)
            logger.info("Loaded fastembed encoder: %s (ONNX, dim=%d)", _MODEL_NAME, _EMBEDDING_DIM)
        except Exception as exc:
            logger.warning(
                "fastembed unavailable (%s) — using char-frequency fallback", exc
            )
            _encoder = False  # sentinel: unavailable, don't retry
    return _encoder if _encoder is not False else None


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def _encode(text: str) -> list[float]:
    """Return a normalized 384-dim embedding for *text*."""
    encoder = _get_encoder()
    if encoder is not None:
        # fastembed.TextEmbedding.embed() returns a generator of numpy arrays
        vec = next(iter(encoder.embed([text])))
        return vec.tolist()
    # Char-frequency fallback: 384-dim, L2-normalized
    vec = [0.0] * _EMBEDDING_DIM
    for ch in text:
        vec[ord(ch) % _EMBEDDING_DIM] += 1.0
    norm = (sum(v ** 2 for v in vec) ** 0.5) or 1.0
    return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = (sum(x ** 2 for x in a) ** 0.5) or 1e-9
    nb = (sum(x ** 2 for x in b) ** 0.5) or 1e-9
    return dot / (na * nb)


# ---------------------------------------------------------------------------
# In-memory fallback store
# ---------------------------------------------------------------------------
_memory_store: list[tuple[list[float], str]] = []


# ---------------------------------------------------------------------------
# Qdrant client (optional)
# ---------------------------------------------------------------------------
_qdrant = None

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams

    _qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=2)
    _qdrant.get_collections()  # connectivity check

    # Recreate collection if vector size has changed (e.g. legacy 64-dim → 384-dim).
    _existing = {c.name for c in _qdrant.get_collections().collections}
    if settings.qdrant_collection in _existing:
        info = _qdrant.get_collection(settings.qdrant_collection)
        existing_size = info.config.params.vectors.size  # type: ignore[union-attr]
        if existing_size != _EMBEDDING_DIM:
            logger.warning(
                "Qdrant collection '%s' has size=%d but expected %d — recreating.",
                settings.qdrant_collection, existing_size, _EMBEDDING_DIM,
            )
            _qdrant.delete_collection(settings.qdrant_collection)
            _existing.discard(settings.qdrant_collection)

    if settings.qdrant_collection not in _existing:
        _qdrant.create_collection(
            settings.qdrant_collection,
            vectors_config=VectorParams(size=_EMBEDDING_DIM, distance=Distance.COSINE),
        )
    logger.info("Qdrant connected — using persistent vector store (dim=%d)", _EMBEDDING_DIM)

except Exception as e:
    logger.warning("Qdrant unavailable (%s) — using in-memory fallback", e)
    _qdrant = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def upsert(text: str, payload: dict | None = None) -> None:
    global _qdrant
    vec = _encode(text)
    if _qdrant is not None:
        try:
            from qdrant_client.models import PointStruct

            point_id = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            _qdrant.upsert(
                collection_name=settings.qdrant_collection,
                points=[PointStruct(id=point_id, vector=vec, payload={"text": text, **(payload or {})})],
            )
            return
        except Exception as exc:
            logger.warning("Qdrant upsert failed (%s) — falling back to in-memory store", exc)
            _qdrant = None
            _memory_store.append((vec, text))
    else:
        _memory_store.append((vec, text))


def search(query: str, top_k: int = 5) -> list[str]:
    global _qdrant
    vec = _encode(query)
    if _qdrant is not None:
        try:
            result = _qdrant.query_points(
                collection_name=settings.qdrant_collection,
                query=vec,
                limit=top_k,
            )
            return [h.payload.get("text", "") for h in result.points if h.payload]
        except Exception as exc:
            logger.warning("Qdrant search failed (%s) — falling back to in-memory store", exc)
            _qdrant = None
            scored = sorted(_memory_store, key=lambda item: _cosine(vec, item[0]), reverse=True)
            return [text for _, text in scored[:top_k]]
    else:
        scored = sorted(_memory_store, key=lambda item: _cosine(vec, item[0]), reverse=True)
        return [text for _, text in scored[:top_k]]


def reset_memory_store() -> None:
    _memory_store.clear()
