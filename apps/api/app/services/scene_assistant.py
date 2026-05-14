"""SceneAssistant service."""

from app.groq_client import call_vlm
from app.schemas.agent import ActionResult
from app.schemas.context import ContextRequest

_SYSTEM_PROMPT = (
    "You are a scene understanding assistant for smart glasses. "
    "Describe the visible scene in 2-3 concise sentences and answer the user's request directly."
)


async def run(
    ctx: ContextRequest,
    image_b64_list: list[str],
    graph_context: str,
    request_id: str,
) -> tuple[str, bool, ActionResult | None]:
    if not image_b64_list:
        return "No image was provided, so the scene cannot be described.", False, None

    prompt = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
    if graph_context:
        prompt += f"\n\nRelevant prior context: {graph_context}"

    response = await call_vlm(prompt, image_b64=image_b64_list[0])
    return response, True, None
