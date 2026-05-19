from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

from app.schemas.agent import ServiceType, LatencyBreakdown

FallbackReason = Literal["low_confidence", "vlm_timeout", "parse_error", "none"]
FailureType = Literal["routing_error", "vlm_error", "action_error", "none"]


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

    token_count: int = 0
    image_payload_bytes: int = 0
    cloud_called: bool = False
    fallback_reason: FallbackReason = "none"
    failure_type: FailureType = "none"
    response_text: str = ""
    response_preview: str = ""
    path_used: str = "unknown"
    quality_check_passed: bool = True
