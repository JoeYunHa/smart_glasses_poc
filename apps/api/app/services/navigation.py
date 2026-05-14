"""NavigationAssistant service.

Combines GPS context and past memory to provide navigation guidance.
Falls back to VLM if text-only context is insufficient.
"""

from app.groq_client import call_vlm
from app.schemas.agent import ActionResult
from app.schemas.context import ContextRequest


async def run(
    ctx: ContextRequest,
    image_b64_list: list[str],
    graph_context: str,
    request_id: str,
) -> tuple[str, bool, ActionResult | None]:
    gps_info = ""
    if ctx.gps:
        gps_info = (
            f"현재 위치: {ctx.gps.place_name or '알 수 없음'} "
            f"({ctx.gps.latitude:.4f}, {ctx.gps.longitude:.4f}), "
            f"장소 유형: {ctx.gps.location_type or '미분류'}"
        )

    prompt = (
        "당신은 스마트 안경의 길 안내 모듈입니다. "
        "사용자의 위치와 요청을 바탕으로 간결한 안내를 제공하세요. "
        "한국어로 2-3문장으로 답하세요.\n\n"
        f"{gps_info}\n"
        f"과거 기억: {graph_context or '없음'}\n"
        f"사용자 요청: {ctx.user_request}"
    )

    response = await call_vlm(prompt, image_b64=image_b64_list[0] if image_b64_list else None)
    return response, True, None
