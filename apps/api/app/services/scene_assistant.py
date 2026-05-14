"""SceneAssistant service.

Calls VLM to describe the visual scene in response to the user's question.
"""

from app.groq_client import call_vlm
from app.schemas.agent import ActionResult
from app.schemas.context import ContextRequest

_SYSTEM_PROMPT = (
    "당신은 스마트 안경의 장면 설명 모듈입니다. "
    "이미지를 보고 사용자의 질문에 간결하게 답하세요. "
    "한국어로 2-3문장으로 답하세요."
)


async def run(
    ctx: ContextRequest,
    image_b64_list: list[str],
    graph_context: str,
    request_id: str,
) -> tuple[str, bool, ActionResult | None]:
    if not image_b64_list:
        return "이미지가 없어 장면을 설명할 수 없습니다.", False, None

    prompt = f"{_SYSTEM_PROMPT}\n\n사용자 질문: {ctx.user_request}"
    if graph_context:
        prompt += f"\n\n과거 맥락: {graph_context}"

    response = await call_vlm(prompt, image_b64=image_b64_list[0])
    return response, True, None
