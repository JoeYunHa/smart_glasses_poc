"""NavigationAssistant service."""

from app.schemas.context import ContextRequest
from app.services.common import (
    ServiceRunResult,
    append_optional_context,
    dispatch,
    first_image_or_none,
)

_SYSTEM_PROMPT = (
    "You are a navigation assistant for smart glasses. "
    "Give brief, practical guidance in 2-3 sentences based on the user's request."
)


async def run(
    ctx: ContextRequest,
    image_b64_list: list[str],
    graph_context: str,
    request_id: str,
    semantic_prompt: str = "",
) -> ServiceRunResult:
    gps_info = ""
    if ctx.gps:
        gps_info = (
            f"Current location: {ctx.gps.place_name or 'unknown'} "
            f"({ctx.gps.latitude:.4f}, {ctx.gps.longitude:.4f}), "
            f"location type: {ctx.gps.location_type or 'unspecified'}"
        )

    # Optimized: semantic prompt includes OCR (street signs) and scene brightness.
    # GPS is appended so the VLM can ground navigation guidance to the current location.
    nav_semantic = f"{semantic_prompt}\n\n{gps_info}" if (semantic_prompt and gps_info) else semantic_prompt

    baseline_prompt = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
    baseline_prompt = append_optional_context(baseline_prompt, "Current location", gps_info)
    baseline_prompt = append_optional_context(baseline_prompt, "Previous context", graph_context)

    return await dispatch(nav_semantic, baseline_prompt, first_image_or_none(image_b64_list))
