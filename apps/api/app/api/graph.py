from fastapi import APIRouter, Query

from app.memory import graph_store

router = APIRouter()


@router.get("/size")
async def get_graph_size():
    """Return current scene-graph node and edge counts."""
    return {
        "node_count": graph_store.graph_size(),
        "edge_count": graph_store.edge_size(),
    }


@router.get("/nodes")
async def get_graph_nodes():
    """Return all scene-graph nodes and edges."""
    return {"nodes": graph_store.get_all_nodes(), "edges": graph_store.get_all_edges()}


@router.get("/query")
async def query_graph(keyword: str = Query(..., description="Keyword to search scenes")):
    """Search stored scenes by keyword."""
    results = graph_store.find_scenes_by_keyword(keyword)
    return {"results": results, "count": len(results)}
