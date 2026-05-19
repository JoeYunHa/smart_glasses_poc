from __future__ import annotations

import base64
from collections.abc import Callable

import cv2
import numpy as np

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
    response_quality_checker: Callable[[str], bool] | None = None,
) -> ServiceRunResult:
    from app.llm_client import call_vlm

    response, usage = await call_vlm(prompt, image_b64=image_b64)
    if postprocess is not None:
        response = postprocess(response)
    usage["vlm_calls"] = 1
    usage["image_sent"] = 1 if image_b64 is not None else 0
    usage["path_used"] = "vision_direct"
    usage["quality_check_passed"] = (
        True if response_quality_checker is None else response_quality_checker(response)
    )
    return response, True, None, usage


_MIN_SEMANTIC_CHARS = 50


def _build_focus_crop_candidates_b64(image_b64: str) -> list[str]:
    """Build multiple upper-band ROI candidates for selective fallback.

    Tries left/center/right crops over the top area so signal locations with
    different camera framing can be covered without immediately sending the
    full image.
    """
    try:
        raw = base64.b64decode(image_b64)
        arr = np.frombuffer(raw, np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            return []
        h, w = bgr.shape[:2]
        y2 = max(1, int(h * 0.65))
        x_points = [
            (0, int(w * 0.55)),
            (int(w * 0.2), int(w * 0.8)),
            (int(w * 0.45), w),
        ]
        results: list[str] = []
        for x1, x2 in x_points:
            x1 = max(0, min(w - 1, x1))
            x2 = max(x1 + 1, min(w, x2))
            crop = bgr[:y2, x1:x2]
            ok, encoded = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ok:
                results.append(base64.b64encode(encoded.tobytes()).decode("utf-8"))
        return results
    except Exception:
        return []


async def run_semantic_service(
    semantic_prompt: str,
    fallback_image_b64: str | None = None,
    postprocess: Callable[[str], str] | None = None,
    response_quality_checker: Callable[[str], bool] | None = None,
    fallback_vision_prompt: str | None = None,
) -> ServiceRunResult:
    """Send text-only semantic prompt to VLM.

    Falls back to a vision call only when the response is substantively empty
    (< 10 non-whitespace chars). Usage from both calls is merged so token
    counts remain accurate. vlm_calls in the returned usage dict reflects the
    actual number of cloud calls made (1 normally, 2 when fallback fires).

    Thin semantic prompts (< _MIN_SEMANTIC_CHARS) skip the text-only attempt
    and go directly to vision to avoid a guaranteed wasted first call.
    """
    from app.llm_client import call_vlm

    if len(semantic_prompt.strip()) < _MIN_SEMANTIC_CHARS and fallback_image_b64:
        vision_prompt = fallback_vision_prompt or (
            "Describe the scene shown in the image and answer the user's request.\n\n"
            + semantic_prompt
        )
        response, usage = await call_vlm(vision_prompt, image_b64=fallback_image_b64)
        if postprocess is not None:
            response = postprocess(response)
        usage["vlm_calls"] = 1
        usage["image_sent"] = 1
        usage["path_used"] = "vision_direct_short_semantic"
        usage["quality_check_passed"] = (
            True if response_quality_checker is None else response_quality_checker(response)
        )
        return response, True, None, usage

    response, usage = await call_vlm(semantic_prompt, image_b64=None)
    vlm_calls = 1
    image_sent = 0
    path_used = "text_only"
    low_content = len(response.strip()) < 10
    low_quality = (
        response_quality_checker is not None
        and not response_quality_checker(response)
    )
    if (low_content or low_quality) and fallback_image_b64:
        # Selective reinforcement: first try compact ROI crops.
        focus_crops = _build_focus_crop_candidates_b64(fallback_image_b64)
        fallback_usage = {}
        roi_attempted = False
        for idx, focus_crop_b64 in enumerate(focus_crops):
            roi_attempted = True
            focused_prompt = (
                "Focus on traffic signals/signage and nearby vehicles in this ROI.\n\n"
                + semantic_prompt
            )
            focused_response, focused_usage = await call_vlm(
                focused_prompt, image_b64=focus_crop_b64
            )
            vlm_calls += 1
            image_sent = 1
            fallback_usage = merge_usage(fallback_usage, focused_usage)
            focused_ok = (
                len(focused_response.strip()) >= 10
                and (
                    response_quality_checker is None
                    or response_quality_checker(focused_response)
                )
            )
            if focused_ok:
                response = focused_response
                usage = merge_usage(usage, fallback_usage)
                if postprocess is not None:
                    response = postprocess(response)
                usage["vlm_calls"] = vlm_calls
                usage["image_sent"] = image_sent
                usage["path_used"] = f"roi_fallback_{idx + 1}"
                usage["quality_check_passed"] = True
                return response, True, None, usage

        vision_prompt = fallback_vision_prompt or (
            "Describe the scene shown in the image and answer the user's request.\n\n"
            + semantic_prompt
        )
        fallback_response, fallback_usage2 = await call_vlm(
            vision_prompt, image_b64=fallback_image_b64
        )
        fallback_ok = len(fallback_response.strip()) >= 10 and (
            response_quality_checker is None
            or response_quality_checker(fallback_response)
        )
        if fallback_ok:
            response = fallback_response
            path_used = "full_image_fallback"
        else:
            path_used = "text_only_failed_after_roi_full" if roi_attempted else "text_only_failed_after_full"
        fallback_usage = merge_usage(fallback_usage, fallback_usage2)
        usage = merge_usage(usage, fallback_usage)
        vlm_calls += 1
        image_sent = 1
    if postprocess is not None:
        response = postprocess(response)
    usage["vlm_calls"] = vlm_calls
    usage["image_sent"] = image_sent
    usage["path_used"] = path_used
    usage["quality_check_passed"] = (
        True if response_quality_checker is None else response_quality_checker(response)
    )
    return response, True, None, usage


async def dispatch(
    semantic_prompt: str,
    baseline_prompt: str,
    image_b64: str | None,
    postprocess: Callable[[str], str] | None = None,
    response_quality_checker: Callable[[str], bool] | None = None,
) -> ServiceRunResult:
    """Route to semantic (optimized) or vision (baseline) VLM path.

    Callers build both prompts unconditionally; this function selects the path
    based on whether semantic_prompt is non-empty (optimized mode).
    """
    if semantic_prompt:
        return await run_semantic_service(
            semantic_prompt,
            fallback_image_b64=image_b64,
            postprocess=postprocess,
            response_quality_checker=response_quality_checker,
            fallback_vision_prompt=baseline_prompt,
        )
    return await run_vlm_service(
        baseline_prompt,
        image_b64=image_b64,
        postprocess=postprocess,
        response_quality_checker=response_quality_checker,
    )
