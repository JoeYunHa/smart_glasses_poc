"""Combined graph + vector context retrieval."""

from dataclasses import dataclass, field

from app.memory import graph_store, vector_store


@dataclass
class RetrievalResult:
    combined: list[str]
    vector_hits: list[str] = field(default_factory=list)
    graph_hits: list[str] = field(default_factory=list)


def store_context(request_id: str, user_request: str, service_name: str, summary: str) -> None:
    """Persist context text in vector store for future retrieval."""
    text = f"[{service_name}] {user_request} :: {summary}"
    vector_store.upsert(text, payload={"request_id": request_id, "service": service_name})


def retrieve_context(query: str, top_k: int = 5) -> RetrievalResult:
    """Return context hits with explicit source breakdown."""
    vector_results = vector_store.search(query, top_k=top_k)
    graph_results = [
        f"[graph] {n['service']}: {n['user_request']}"
        for n in graph_store.find_scenes_by_keyword(query[:6])[:3]
    ]
    combined = vector_results + graph_results
    return RetrievalResult(
        combined=combined[:top_k],
        vector_hits=vector_results[:top_k],
        graph_hits=graph_results[:top_k],
    )


def find_similar(query: str, top_k: int = 5) -> list[str]:
    """Backward-compatible helper for existing callers."""
    return retrieve_context(query, top_k=top_k).combined
