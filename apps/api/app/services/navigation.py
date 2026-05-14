"""NavigationAssistant service."""

from app.groq_client import call_vlm
from app.schemas.agent import ActionResult
from app.schemas.context import ContextRequest


async def run(
    ctx: ContextRequest,
    image_b64_list: list[str],
    graph_context: str,
    request_id: str,
) -> tuple[str, bool, ActionResult | None]:
    gps_info = ""
    if ctx.gps:
        gps_info = (
            f"Current location: {ctx.gps.place_name or 'unknown'} "
            f"({ctx.gps.latitude:.4f}, {ctx.gps.longitude:.4f}), "
            f"location type: {ctx.gps.location_type or 'unspecified'}"
        )

    prompt = (
        "You are a navigation assistant for smart glasses. "
        "Give brief, practical guidance in 2-3 sentences based on the user's request.\n\n"
        f"{gps_info}\n"
        f"Previous context: {graph_context or 'none'}\n"
        f"User request: {ctx.user_request}"
    )

    response = await call_vlm(prompt, image_b64=image_b64_list[0] if image_b64_list else None)
    return response, True, None
