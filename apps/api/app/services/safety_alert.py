"""SafetyAlert service."""

from app.agent.policy import sanitize_safety_response
from app.schemas.context import ContextRequest
from app.services.common import (
    ServiceRunResult,
    append_optional_context,
    dispatch,
    first_image_or_none,
)

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
    semantic_prompt: str = "",
) -> ServiceRunResult:
    if not image_b64_list and not semantic_prompt:
        text = "No image was provided, so a safety assessment cannot be performed."
        return sanitize_safety_response(text), False, None, {}

    baseline_prompt = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
    baseline_prompt = append_optional_context(baseline_prompt, "Reference context", graph_context)

    return await dispatch(
        semantic_prompt, baseline_prompt, first_image_or_none(image_b64_list),
        postprocess=sanitize_safety_response,
    )
