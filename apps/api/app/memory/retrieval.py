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
    """Return context hits with explicit source breakdown.

    Uses quota-based merge: reserves up to 2 slots for graph hits so they are
    never crowded out when vector search fills the full top_k quota.
    """
    vector_results = vector_store.search(query, top_k=top_k)
    graph_results = graph_store.find_subgraph_by_query(query, max_hops=2, max_results=3)
    graph_quota = min(len(graph_results), 2)
    vector_quota = max(0, top_k - graph_quota)
    combined = vector_results[:vector_quota] + graph_results[:graph_quota]
    return RetrievalResult(
        combined=combined,
        vector_hits=vector_results[:top_k],
        graph_hits=graph_results[:top_k],
    )


