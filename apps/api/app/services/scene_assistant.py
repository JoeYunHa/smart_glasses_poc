"""SceneAssistant service.

To reduce mode divergence, both baseline and optimized now run vision-based
scene description on the current image. Optimized still benefits from upstream
keyframe/perception optimizations, but the final scene answer is grounded on
the same visual input as baseline.
"""

from app.schemas.context import ContextRequest
from app.services.common import (
    ServiceRunResult,
    append_optional_context,
    first_image_or_none,
    run_vlm_service,
)

_SYSTEM_PROMPT = (
    "You are a visual assistant embedded in smart glasses. "
    "Your output is read aloud to the user, so be concise, specific, and avoid filler phrases.\n\n"
    "Focus only on what is directly relevant to the user's request: "
    "objects, text, people, signage, spatial layout, or notable features. "
    "Prioritize information the user cannot easily perceive on their own. "
    "If the user asks a yes/no question, answer it first, then add one supporting detail. "
    "Do not list everything visible — pick the most important 2-3 elements. "
    "Keep the total response under 3 sentences. Respond in Korean."
)


async def run(
    ctx: ContextRequest,
    image_b64_list: list[str],
    graph_context: str,
    request_id: str,
    semantic_prompt: str = "",
) -> ServiceRunResult:
    image_b64 = first_image_or_none(image_b64_list)

    if not image_b64:
        return "No image was provided, so the scene cannot be described.", False, None, {}

    # Keep scene_assistant grounded on current visual evidence.
    # semantic_prompt is supplemental only (helps concise focus), not a text-only path.
    # Strip "Prior context:" injected by planner — graph history contaminates direct scene description.
    prompt = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
    if semantic_prompt:
        clean_semantic = semantic_prompt.split("\n\nPrior context:", 1)[0].strip()
        prompt = append_optional_context(prompt, "Scene features (CV-extracted)", clean_semantic)

    return await run_vlm_service(prompt, image_b64=image_b64)
