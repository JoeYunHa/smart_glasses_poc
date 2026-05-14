from enum import Enum
from pydantic import BaseModel, Field


class ServiceType(str, Enum):
    scene_assistant = "scene_assistant"
    navigation = "navigation"
    device_control = "device_control"
    safety_alert = "safety_alert"
    context_memory = "context_memory"
    unknown = "unknown"


class LatencyBreakdown(BaseModel):
    frame_sampling: int = 0
    keyframe_selection: int = 0
    graph_retrieval: int = 0
    routing: int = 0
    vlm: int = 0
    total: int = 0


class ActionResult(BaseModel):
    device_id: str = ""
    action: str = ""
    success: bool = False
    message: str = ""


class AgentResponse(BaseModel):
    request_id: str
    selected_service: ServiceType
    router_confidence: float
    vlm_used: bool = False
    response_text: str
    action_result: ActionResult | None = None
    original_frame_count: int = 0
    selected_keyframe_count: int = 0
    retrieved_graph_nodes: int = 0
    latency_ms: LatencyBreakdown = Field(default_factory=LatencyBreakdown)
    mode: str = "optimized"
