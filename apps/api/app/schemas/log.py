from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.agent import ServiceType, LatencyBreakdown


class EvaluationLog(BaseModel):
    request_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    mode: str
    selected_service: ServiceType
    router_confidence: float
    original_frame_count: int = 0
    selected_keyframe_count: int = 0
    vlm_call_count: int = 0
    retrieved_graph_nodes: int = 0
    latency_ms: LatencyBreakdown = Field(default_factory=LatencyBreakdown)
    action_result: str = "skipped"
    user_request: str = ""
