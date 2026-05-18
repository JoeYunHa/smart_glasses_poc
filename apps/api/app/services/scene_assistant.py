"""SceneAssistant service."""

from app.schemas.context import ContextRequest
from app.services.common import (
    ServiceRunResult,
    append_optional_context,
    dispatch,
    first_image_or_none,
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
    semantic_prompt: str = "",
) -> ServiceRunResult:
    if not image_b64_list and not semantic_prompt:
        return "No image was provided, so the scene cannot be described.", False, None, {}

    baseline_prompt = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
    baseline_prompt = append_optional_context(baseline_prompt, "Relevant prior context", graph_context)

    return await dispatch(semantic_prompt, baseline_prompt, first_image_or_none(image_b64_list))
