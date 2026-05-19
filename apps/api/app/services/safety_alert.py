"""SafetyAlert service.

Optimized mode keeps text-only first, then selective vision reinforcement.
This module adds stricter failure handling so low-quality outputs never surface
as final answers.
"""

import base64

import cv2
import numpy as np

from app.agent.policy import sanitize_safety_response
from app.schemas.context import ContextRequest
from app.services.common import (
    ServiceRunResult,
    append_optional_context,
    dispatch,
    first_image_or_none,
)

_SYSTEM_PROMPT = (
    "You are a real-time pedestrian safety assistant in smart glasses.\n\n"
    "Analyze in this order:\n"
    "1. Pedestrian signal state/color.\n"
    "2. Vehicle signal state/color.\n"
    "3. Approaching vehicles near crosswalk.\n"
    "4. Crosswalk visibility and obstacles.\n"
    "5. Other hazards (bicycle, wet floor, blind spots, construction).\n\n"
    "End with one Korean recommendation only:\n"
    "- 대기하세요.\n"
    "- 주의하며 진행하세요.\n"
    "- 건너기 전 주변을 직접 확인하세요.\n\n"
    "Never guarantee safety. Keep response concise and in Korean."
)


def _is_safety_response_complete(response: str) -> bool:
    text = response.lower()
    has_ped = ("보행" in text) or ("도보" in text) or ("pedestrian" in text)
    has_vehicle_signal = (("차량" in text) and ("신호" in text)) or ("traffic light" in text)
    has_approaching_vehicle = ("접근" in text) or ("approach" in text) or ("vehicle" in text)
    all_absent_pattern = (
        ("보행" in text or "도보" in text)
        and ("없" in text)
        and ("차량" in text and "신호" in text and "없" in text)
        and ("접근" in text and "없" in text)
    )
    return has_ped and has_vehicle_signal and has_approaching_vehicle and not all_absent_pattern


def _strip_prior_context_from_semantic(semantic_prompt: str) -> str:
    marker = "\n\nPrior context:"
    if marker in semantic_prompt:
        return semantic_prompt.split(marker, 1)[0].strip()
    return semantic_prompt


def _build_safety_fallback_response() -> str:
    return (
        "1. 보행자 신호: 판독 불가\n"
        "2. 차량 신호: 판독 불가\n"
        "3. 접근 차량: 판독 불가\n"
        "4. 횡단보도/장애물: 판독 불가\n"
        "5. 기타 위험요소: 판독 불가\n\n"
        "건너기 전 주변을 직접 확인하세요."
    )


def _decode_b64_image(image_b64: str) -> np.ndarray | None:
    try:
        raw = base64.b64decode(image_b64)
        arr = np.frombuffer(raw, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


def _estimate_signal_color(frame: np.ndarray) -> tuple[str, float]:
    """Estimate dominant traffic-signal color in upper region.

    Returns (color, confidence) where color is one of red/yellow/green/unknown.
    """
    h, w = frame.shape[:2]
    if h < 8 or w < 8:
        return "unknown", 0.0
    roi = frame[: max(1, int(h * 0.65)), :]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    masks = {
        "red": cv2.bitwise_or(
            cv2.inRange(hsv, (0, 90, 80), (12, 255, 255)),
            cv2.inRange(hsv, (165, 90, 80), (179, 255, 255)),
        ),
        "yellow": cv2.inRange(hsv, (18, 80, 90), (40, 255, 255)),
        "green": cv2.inRange(hsv, (40, 70, 70), (95, 255, 255)),
    }

    # Score only small/medium blobs (signal-like), ignore huge regions.
    roi_area = float(roi.shape[0] * roi.shape[1])
    scores: dict[str, float] = {"red": 0.0, "yellow": 0.0, "green": 0.0}
    for color, mask in masks.items():
        num_labels, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        score = 0.0
        for idx in range(1, num_labels):
            area = float(stats[idx, cv2.CC_STAT_AREA])
            if 6.0 <= area <= max(35.0, roi_area * 0.03):
                score += area
        scores[color] = score

    best_color = max(scores, key=scores.get)
    total = float(sum(scores.values()))
    if total <= 0.0:
        return "unknown", 0.0
    confidence = min(scores[best_color] / max(total, 1e-6), 1.0)
    if scores[best_color] < 20.0:
        return "unknown", confidence * 0.5
    return best_color, confidence


def _build_cv_assisted_fallback(image_b64: str | None) -> str:
    if not image_b64:
        return _build_safety_fallback_response()
    frame = _decode_b64_image(image_b64)
    if frame is None:
        return _build_safety_fallback_response()

    color, conf = _estimate_signal_color(frame)
    if color == "unknown" or conf < 0.52:
        return _build_safety_fallback_response()

    if color in ("red", "yellow"):
        rec = "대기하세요."
        ped = "빨간색 계열 추정(정지 권고)"
    else:
        rec = "주의하며 진행하세요."
        ped = "녹색 계열 추정(주변 확인 필요)"
    vehicle_sig = f"{color} 계열 감지(추정)"
    return (
        f"1. 보행자 신호: {ped}\n"
        f"2. 차량 신호: {vehicle_sig}\n"
        "3. 접근 차량: 판단 어려움(직접 확인 필요)\n"
        "4. 횡단보도/장애물: 판독 불가\n"
        "5. 기타 위험요소: 판독 불가\n\n"
        f"{rec}"
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
        text = "이미지가 없어 안전 판단을 수행할 수 없습니다.\n\n건너기 전 주변을 직접 확인하세요."
        return sanitize_safety_response(text), False, None, {}

    full_semantic = ""
    if semantic_prompt:
        # Keep optimized strategy while reducing context contamination.
        semantic_prompt = _strip_prior_context_from_semantic(semantic_prompt)
        full_semantic = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
        full_semantic = append_optional_context(
            full_semantic,
            "Scene features (CV-extracted)",
            semantic_prompt,
        )

    baseline_prompt = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
    baseline_prompt = append_optional_context(baseline_prompt, "Reference context", graph_context)

    response, vlm_used, action_result, usage = await dispatch(
        full_semantic,
        baseline_prompt,
        image_b64,
        postprocess=sanitize_safety_response,
        response_quality_checker=_is_safety_response_complete,
    )
    if not _is_safety_response_complete(response):
        cv_fallback = _build_cv_assisted_fallback(image_b64)
        response = sanitize_safety_response(cv_fallback)
        usage["quality_check_passed"] = _is_safety_response_complete(response)
        usage["path_used"] = f"{usage.get('path_used', 'unknown')}+cv_fallback"
    return response, vlm_used, action_result, usage
