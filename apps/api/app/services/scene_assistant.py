"""SceneAssistant service."""

from app.schemas.context import ContextRequest
from app.services.common import (
    ServiceRunResult,
    append_optional_context,
    first_image_or_none,
    run_vlm_service,
)

_SYSTEM_PROMPT = (
    "You are a scene understanding assistant for smart glasses. "
    "Describe the visible scene in 2-3 concise sentences and answer the user's request directly."
)


async def run(
    ctx: ContextRequest,
    image_b64_list: list[str],
    graph_context: str,
    request_id: str,
) -> ServiceRunResult:
    if not image_b64_list:
        return "No image was provided, so the scene cannot be described.", False, None, {}

    prompt = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
    prompt = append_optional_context(prompt, "Relevant prior context", graph_context)
    return await run_vlm_service(prompt, image_b64=first_image_or_none(image_b64_list))
