from __future__ import annotations

from collections.abc import Callable

from app.schemas.agent import ActionResult

ServiceRunResult = tuple[str, bool, ActionResult | None, dict]


def merge_usage(*usages: dict) -> dict:
    """Sum token usage dicts from multiple VLM calls into one."""
    result: dict[str, int] = {}
    for u in usages:
        for k, v in u.items():
            result[k] = result.get(k, 0) + v
    return result


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
    usage["vlm_calls"] = 1
    usage["image_sent"] = 1 if image_b64 is not None else 0
    return response, True, None, usage


async def run_semantic_service(
    semantic_prompt: str,
    fallback_image_b64: str | None = None,
    postprocess: Callable[[str], str] | None = None,
) -> ServiceRunResult:
    """Send text-only semantic prompt to VLM.

    Falls back to a vision call only when the response is substantively empty
    (< 10 non-whitespace chars). Usage from both calls is merged so token
    counts remain accurate. vlm_calls in the returned usage dict reflects the
    actual number of cloud calls made (1 normally, 2 when fallback fires).
    """
    from app.groq_client import call_vlm

    response, usage = await call_vlm(semantic_prompt, image_b64=None)
    vlm_calls = 1
    image_sent = 0
    if len(response.strip()) < 10 and fallback_image_b64:
        vision_prompt = (
            "Describe the scene shown in the image and answer the user's request.\n\n"
            + semantic_prompt
        )
        fallback_response, fallback_usage = await call_vlm(vision_prompt, image_b64=fallback_image_b64)
        if len(fallback_response.strip()) >= 10:
            response = fallback_response
        usage = merge_usage(usage, fallback_usage)
        vlm_calls = 2
        image_sent = 1
    if postprocess is not None:
        response = postprocess(response)
    usage["vlm_calls"] = vlm_calls
    usage["image_sent"] = image_sent
    return response, True, None, usage


async def dispatch(
    semantic_prompt: str,
    baseline_prompt: str,
    image_b64: str | None,
    postprocess: Callable[[str], str] | None = None,
) -> ServiceRunResult:
    """Route to semantic (optimized) or vision (baseline) VLM path.

    Callers build both prompts unconditionally; this function selects the path
    based on whether semantic_prompt is non-empty (optimized mode).
    """
    if semantic_prompt:
        return await run_semantic_service(
            semantic_prompt, fallback_image_b64=image_b64, postprocess=postprocess
        )
    return await run_vlm_service(baseline_prompt, image_b64=image_b64, postprocess=postprocess)
