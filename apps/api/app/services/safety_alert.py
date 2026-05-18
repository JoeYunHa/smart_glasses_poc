"""SafetyAlert service."""

from app.agent.policy import sanitize_safety_response
from app.schemas.context import ContextRequest
from app.services.common import (
    ServiceRunResult,
    append_optional_context,
    run_vlm_service,
)

_SYSTEM_PROMPT = (
    "You are a real-time safety assistant embedded in smart glasses for pedestrian use. "
    "Your output is spoken aloud to the user — be direct, specific, and free of filler phrases.\n\n"
    "Analyze the image and cover these points in order:\n"
    "1. Pedestrian signal: state (walk / don't walk / absent) and color.\n"
    "2. Vehicle traffic light: red / yellow / green. If none visible, state so.\n"
    "3. Vehicles: are any approaching the crosswalk? Estimate count and proximity.\n"
    "4. Crosswalk: clearly marked? Any obstacles on it?\n"
    "5. Other hazards: cyclists, wet surface, blind spots, construction.\n\n"
    "End with exactly one of these recommendations:\n"
    "- '대기하세요.' — signal is red or vehicles are approaching.\n"
    "- '주의하며 진행하세요.' — signal is green but caution is needed.\n"
    "- '건너기 전 주변을 직접 확인하세요.' — signal is ambiguous or absent.\n\n"
    "Rules: never say it is safe or guarantee safety. "
    "Keep the total response under 5 sentences. Respond in Korean."
)


async def run(
    ctx: ContextRequest,
    image_b64_list: list[str],
    graph_context: str,
    request_id: str,
    semantic_prompt: str = "",
) -> ServiceRunResult:
    image_b64 = image_b64_list[0] if image_b64_list else None

    if not image_b64:
        text = "No image was provided, so a safety assessment cannot be performed."
        return sanitize_safety_response(text), False, None, {}

    # Safety assessment always requires the actual image regardless of mode.
    # Semantic features (CV-extracted) are included as supplementary context only.
    prompt = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
    if semantic_prompt:
        # Include CV-extracted scene features to help the model focus
        prompt = append_optional_context(prompt, "Scene features (CV-extracted)", semantic_prompt)
    prompt = append_optional_context(prompt, "Reference context", graph_context)

    return await run_vlm_service(prompt, image_b64=image_b64, postprocess=sanitize_safety_response)
