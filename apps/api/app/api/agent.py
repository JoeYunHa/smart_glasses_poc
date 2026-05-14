import json

from fastapi import APIRouter, File, Form, UploadFile

from app.agent.planner import run_pipeline
from app.schemas.agent import AgentResponse
from app.schemas.context import ContextRequest

router = APIRouter()


@router.post("/run", response_model=AgentResponse)
async def run_agent(
    context_json: str = Form(...),
    image: UploadFile | None = File(default=None),
    video: UploadFile | None = File(default=None),
):
    """실행: 이미지/영상 + 컨텍스트 JSON → Agent 파이프라인 → AgentResponse."""
    ctx = ContextRequest(**json.loads(context_json))
    image_bytes = await image.read() if image else None
    video_bytes = await video.read() if video else None
    return await run_pipeline(image_bytes, video_bytes, ctx)
