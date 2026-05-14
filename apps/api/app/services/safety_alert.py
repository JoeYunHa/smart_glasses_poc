"""SafetyAlert service.

Calls VLM with a safety-focused prompt and sanitizes the response
so it never asserts definitive safety ("건너도 됩니다" is forbidden).
"""

from app.agent.policy import sanitize_safety_response
from app.groq_client import call_vlm
from app.schemas.agent import ActionResult, AgentResponse, LatencyBreakdown, ServiceType
from app.schemas.context import ContextRequest

_SYSTEM_PROMPT = (
    "당신은 스마트 안경의 안전 경보 모듈입니다. "
    "이미지와 상황을 분석하여 위험 요소를 설명하세요. "
    "절대로 '안전합니다', '건너도 됩니다' 같은 확정적 표현을 사용하지 마세요. "
    "항상 사용자가 직접 판단하도록 유도하세요. 한국어로 답하세요."
)


async def run(
    ctx: ContextRequest,
    image_b64_list: list[str],
    graph_context: str,
    request_id: str,
) -> tuple[str, bool, ActionResult | None]:
    """Return (response_text, vlm_used, action_result)."""
    if not image_b64_list:
        text = "이미지가 없어 안전 분석을 수행할 수 없습니다."
        return sanitize_safety_response(text), False, None

    prompt = f"{_SYSTEM_PROMPT}\n\n사용자 요청: {ctx.user_request}"
    if graph_context:
        prompt += f"\n\n참고 과거 context: {graph_context}"

    raw = await call_vlm(prompt, image_b64=image_b64_list[0])
    cleaned = sanitize_safety_response(raw)
    return cleaned, True, None
