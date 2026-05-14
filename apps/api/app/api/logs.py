from fastapi import APIRouter, Query

from app.evaluation.logger import read_logs
from app.evaluation.metrics import aggregate

router = APIRouter()


@router.get("/")
async def get_logs(limit: int = Query(default=50, le=200)):
    """최근 평가 로그 목록을 반환한다."""
    return {"logs": read_logs(limit=limit)}


@router.get("/metrics")
async def get_metrics():
    """Baseline vs Optimized 성능 지표를 집계해 반환한다."""
    return aggregate()
