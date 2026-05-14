from fastapi import APIRouter

from app.memory import graph_store

router = APIRouter()


@router.get("/summary")
async def get_context_summary():
    """Return a brief summary of current stored context state."""
    return {
        "graph_node_count": graph_store.graph_size(),
        "graph_edge_count": graph_store.edge_size(),
    }
