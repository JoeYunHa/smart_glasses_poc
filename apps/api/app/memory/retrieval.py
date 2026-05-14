"""Combined graph + vector context retrieval."""

from app.memory import graph_store, vector_store


def store_context(request_id: str, user_request: str, service_name: str, summary: str) -> None:
    """Persist context text in vector store for future retrieval."""
    text = f"[{service_name}] {user_request} :: {summary}"
    vector_store.upsert(text, payload={"request_id": request_id, "service": service_name})


def find_similar(query: str, top_k: int = 5) -> list[str]:
    """Return semantically similar past context strings."""
    vector_results = vector_store.search(query, top_k=top_k)
    graph_results = [
        f"[graph] {n['service']}: {n['user_request']}"
        for n in graph_store.find_scenes_by_keyword(query[:6])[:3]
    ]
    combined = vector_results + graph_results
    return combined[:top_k]
