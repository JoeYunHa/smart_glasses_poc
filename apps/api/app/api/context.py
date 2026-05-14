from fastapi import APIRouter

from app.memory import graph_store

router = APIRouter()


@router.get("/graph-size")
async def get_graph_size():
    """현재 scene graph에 저장된 노드 수를 반환한다."""
    return {"node_count": graph_store.graph_size()}
