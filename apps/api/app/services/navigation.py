"""NavigationAssistant service."""

from app.schemas.context import ContextRequest
from app.services.common import (
    ServiceRunResult,
    append_optional_context,
    dispatch,
    first_image_or_none,
)

_SYSTEM_PROMPT = (
    "You are a navigation assistant embedded in smart glasses. "
    "Your guidance is delivered as voice output — use clear, directional language "
    "with landmarks or distances where possible (e.g., '앞으로 50미터', '오른쪽 건물 옆').\n\n"
    "If GPS location is provided, ground your guidance in the actual place name. "
    "If the destination is unclear or GPS is unavailable, ask one specific clarifying question. "
    "Do not speculate about routes you cannot confirm. "
    "Keep the total response under 3 sentences. Respond in Korean."
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

    # Optimized: prepend system instructions so both modes share the same prompt structure.
    # graph_context is already injected into semantic_prompt by planner — not added again.
    nav_semantic = ""
    if semantic_prompt:
        nav_semantic = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
        nav_semantic = append_optional_context(nav_semantic, "Scene features (CV-extracted)", semantic_prompt)
        if gps_info:
            nav_semantic = f"{nav_semantic}\n\n{gps_info}"

    # Baseline path has no semantic_prompt, so graph_context is injected here only.
    baseline_prompt = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
    baseline_prompt = append_optional_context(baseline_prompt, "Current location", gps_info)
    baseline_prompt = append_optional_context(baseline_prompt, "Previous context", graph_context)

    return await dispatch(nav_semantic, baseline_prompt, first_image_or_none(image_b64_list))
