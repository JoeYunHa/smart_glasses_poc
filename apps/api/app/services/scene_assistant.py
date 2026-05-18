"""SceneAssistant service."""

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

    if not image_b64 and not semantic_prompt:
        return "No image was provided, so the scene cannot be described.", False, None, {}

    # scene_assistant always sends the image regardless of mode.
    # semantic_prompt (brightness/color/motion stats) cannot substitute for the
    # actual image in a scene description task — CV features alone do not carry
    # object-level information needed to answer "what do I see?".
    # graph_context (prior scene knowledge) is appended when available.
    # The optimized benefit here comes from keyframe selection, not semantic reduction.
    prompt = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
    prompt = append_optional_context(prompt, "Relevant prior context", graph_context)
    return await run_vlm_service(prompt, image_b64=image_b64)
