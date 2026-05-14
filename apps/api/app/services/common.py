from __future__ import annotations

from collections.abc import Callable

from app.schemas.agent import ActionResult

ServiceRunResult = tuple[str, bool, ActionResult | None, dict]


def append_optional_context(prompt: str, label: str, context: str) -> str:
    if not context:
        return prompt
    return f"{prompt}\n\n{label}: {context}"


def first_image_or_none(image_b64_list: list[str]) -> str | None:
    return image_b64_list[0] if image_b64_list else None


async def run_vlm_service(
    prompt: str,
    image_b64: str | None = None,
    postprocess: Callable[[str], str] | None = None,
) -> ServiceRunResult:
    from app.groq_client import call_vlm

    response, usage = await call_vlm(prompt, image_b64=image_b64)
    if postprocess is not None:
        response = postprocess(response)
    return response, True, None, usage
