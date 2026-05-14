from fastapi import APIRouter, Query

from app.memory import graph_store

router = APIRouter()


@router.get("/nodes")
async def get_graph_nodes():
    """GraphRAG scene graph의 전체 노드 목록을 반환한다."""
    return {"nodes": graph_store.get_all_nodes(), "edges": graph_store.get_all_edges()}


@router.get("/query")
async def query_graph(keyword: str = Query(..., description="검색 키워드")):
    """키워드로 과거 scene을 검색한다."""
    results = graph_store.find_scenes_by_keyword(keyword)
    return {"results": results, "count": len(results)}
