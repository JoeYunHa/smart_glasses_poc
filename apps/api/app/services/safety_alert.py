"""SafetyAlert service."""

from app.agent.policy import sanitize_safety_response
from app.groq_client import call_vlm
from app.schemas.agent import ActionResult
from app.schemas.context import ContextRequest

_SYSTEM_PROMPT = (
    "You are a safety assistant for smart glasses. "
    "Describe visible hazards and caution points. "
    "Never guarantee that a situation is safe, and ask the user to make the final decision."
)


async def run(
    ctx: ContextRequest,
    image_b64_list: list[str],
    graph_context: str,
    request_id: str,
) -> tuple[str, bool, ActionResult | None]:
    if not image_b64_list:
        text = "No image was provided, so a safety assessment cannot be performed."
        return sanitize_safety_response(text), False, None

    prompt = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
    if graph_context:
        prompt += f"\n\nReference context: {graph_context}"

    raw = await call_vlm(prompt, image_b64=image_b64_list[0])
    cleaned = sanitize_safety_response(raw)
    return cleaned, True, None
