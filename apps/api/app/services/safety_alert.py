"""SafetyAlert service with optimized text-first strategy and robust fallback."""

from __future__ import annotations

import base64
import re

import cv2
import numpy as np

from app.agent.policy import sanitize_safety_response
from app.llm_client import call_vlm
from app.schemas.context import ContextRequest
from app.services.common import ServiceRunResult, append_optional_context, first_image_or_none, merge_usage

_SYSTEM_PROMPT = (
    "You are a real-time pedestrian safety assistant in smart glasses.\n\n"
    "Analyze in this order:\n"
    "1. Pedestrian signal state/color.\n"
    "2. Vehicle signal state/color.\n"
    "3. Approaching vehicles near crosswalk.\n"
    "4. Crosswalk visibility and obstacles.\n"
    "5. Other hazards (bicycle, wet floor, blind spots, construction).\n\n"
    "Strict rules:\n"
    "- If evidence is insufficient, write '판독 불가' for that item.\n"
    "- Do not invent hazards or colors that are not supported by the provided evidence.\n"
    "- In text-only semantic mode, treat CV feature text as the only evidence source.\n\n"
    "End with one Korean recommendation only:\n"
    "- 대기하세요.\n"
    "- 주의하며 진행하세요.\n"
    "- 건너기 전 주변을 직접 확인하세요.\n\n"
    "Never guarantee safety. Keep response concise and in Korean."
)


def _is_safety_response_complete(response: str) -> bool:
    """Partial-success quality gate.

    Accept when at least 2 core fields are present to avoid over-rejecting
    usable outputs in hard frames.  Responses where ≥4 of the 5 fields are
    unreadable are rejected as too sparse — they indicate the text-only
    source lacked enough visual information and should trigger an image retry.
    """
    text = response.lower()
    # Reject degenerate responses where nearly all fields are unreadable.
    unreadable_count = len(re.findall(r"판독\s*불가", text))
    if unreadable_count >= 4:
        return False
    has_ped = ("보행" in text) or ("도보" in text) or ("pedestrian" in text)
    has_vehicle_signal = (("차량" in text) and ("신호" in text)) or ("traffic light" in text)
    # "vehicle" alone is excluded: it also appears in "vehicle signal" (field 2), causing false
    # positives. Use "접근"/"approach" or section-3 header as reliable field-3 markers.
    has_approaching_vehicle = (
        ("접근" in text)
        or ("approach" in text)
        or bool(re.search(r"(^|\n)\s*3[\.\):\-]\s*", text))
    )
    core_hits = sum([has_ped, has_vehicle_signal, has_approaching_vehicle])
    has_recommendation = any(k in text for k in ("대기", "주의", "직접 확인", "wait", "caution"))
    return core_hits >= 2 and has_recommendation


def _strip_prior_context_from_semantic(semantic_prompt: str) -> str:
    marker = "\n\nPrior context:"
    if marker in semantic_prompt:
        return semantic_prompt.split(marker, 1)[0].strip()
    return semantic_prompt


def _decode_b64_image(image_b64: str) -> np.ndarray | None:
    try:
        raw = base64.b64decode(image_b64)
        arr = np.frombuffer(raw, np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        return None


def _encode_jpeg_b64(frame: np.ndarray, max_size: int = 1400, quality: int = 95) -> str:
    h, w = frame.shape[:2]
    img = frame
    if max(h, w) > max_size:
        # Only downscale — upscaling small frames inflates payload without quality gain.
        scale = max_size / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    ok, enc = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise ValueError("Failed to encode high-res safety retry image")
    return base64.b64encode(enc.tobytes()).decode("utf-8")


def _color_masks(hsv: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "red": cv2.bitwise_or(
            cv2.inRange(hsv, (0, 95, 90), (12, 255, 255)),
            cv2.inRange(hsv, (165, 95, 90), (179, 255, 255)),
        ),
        "yellow": cv2.inRange(hsv, (18, 85, 95), (42, 255, 255)),
        "green": cv2.inRange(hsv, (40, 75, 75), (95, 255, 255)),
    }


def _contour_score(mask: np.ndarray) -> float:
    # Prefer compact circular blobs to suppress neon/board false positives.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    score = 0.0
    for c in contours:
        area = float(cv2.contourArea(c))
        if area < 8.0:
            continue
        peri = float(cv2.arcLength(c, True))
        if peri <= 0.0:
            continue
        circularity = float((4.0 * np.pi * area) / (peri * peri))
        if circularity < 0.35:
            continue
        score += area * min(1.0, max(0.0, circularity))
    return score


def _score_via_hough_circles(upper_roi: np.ndarray) -> dict[str, float] | None:
    """Detect circular signal lamps with Hough transform and score color within each circle.

    Returns per-color area-weighted scores when circles are found, or None when
    detection fails (caller should fall back to contour blob scoring).

    Scoring: for each detected circle, count HSV-matched pixels inside the circle
    mask, then weight by circle area.  Larger / more lit circles dominate.
    """
    h, w = upper_roi.shape[:2]
    max_r = max(8, min(h, w) // 5)
    if max_r <= 4:
        return None

    gray = cv2.cvtColor(upper_roi, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 1.5)
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=12,
        param1=60,   # Canny high threshold
        param2=22,   # accumulator threshold — lower catches small/dim lamps
        minRadius=4,
        maxRadius=max_r,
    )
    if circles is None:
        return None

    hsv = cv2.cvtColor(upper_roi, cv2.COLOR_BGR2HSV)
    scores: dict[str, float] = {"red": 0.0, "yellow": 0.0, "green": 0.0}

    for x, y, r in circles[0]:
        cx, cy, cr = int(round(x)), int(round(y)), int(round(r))
        x1 = max(0, cx - cr)
        x2 = min(w, cx + cr + 1)
        y1 = max(0, cy - cr)
        y2 = min(h, cy + cr + 1)
        roi_hsv = hsv[y1:y2, x1:x2]
        if roi_hsv.size == 0:
            continue

        # Circular pixel mask — avoids scoring rectangular corner background.
        circ_mask = np.zeros(roi_hsv.shape[:2], dtype=np.uint8)
        cv2.circle(circ_mask, (cx - x1, cy - y1), cr, 255, -1)
        area = float(np.sum(circ_mask > 0)) + 1e-6

        for color, cmask in _color_masks(roi_hsv).items():
            lit = float(np.sum(cv2.bitwise_and(cmask, circ_mask) > 0))
            # Area-weighted ratio: larger, more uniformly lit circles score higher.
            scores[color] = max(scores[color], (lit / area) * (np.pi * cr * cr))

    return scores


def _estimate_signal_scores(frame: np.ndarray) -> dict[str, float]:
    """Two-stage signal color scoring.

    Stage 1 (preferred): Hough Circle detection localizes circular signal lamps
    in the upper frame, then scores color only within each circle.  This avoids
    false positives from non-circular environmental colors (vegetation, cars).

    Stage 2 (fallback): if no circles are detected, falls back to the original
    contour blob approach across three overlapping horizontal ROI bands.
    """
    h, w = frame.shape[:2]
    if h < 8 or w < 8:
        return {"red": 0.0, "yellow": 0.0, "green": 0.0}

    upper = frame[: max(1, int(h * 0.58)), :]
    circle_scores = _score_via_hough_circles(upper)
    if circle_scores is not None:
        return circle_scores

    # Fallback: three overlapping ROI bands + contour blob scoring.
    rois = [
        upper,
        upper[:, int(w * 0.2) : int(w * 0.85)],
        upper[:, int(w * 0.45) :],
    ]
    scores = {"red": 0.0, "yellow": 0.0, "green": 0.0}
    for roi in rois:
        if roi.size == 0:
            continue
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        masks = _color_masks(hsv)
        for color, mask in masks.items():
            scores[color] = max(scores[color], _contour_score(mask))
    return scores


def _estimate_signal_color(frame: np.ndarray) -> tuple[str, float]:
    scores = _estimate_signal_scores(frame)
    best = max(scores, key=scores.get)
    total = float(sum(scores.values()))
    if total <= 0.0 or scores[best] < 30.0:
        return "unknown", 0.0
    conf = min(scores[best] / max(total, 1e-6), 1.0)
    return best, conf


def _extract_vehicle_color_from_text(response: str) -> str:
    text = response.lower()
    vehicle_keys = ("차량", "vehicle", "traffic light", "car signal")

    def _detect_color(scope: str) -> str:
        has_red = ("빨" in scope) or ("red" in scope)
        has_yellow = ("노" in scope) or ("황" in scope) or ("yellow" in scope) or ("amber" in scope)
        has_green = ("초록" in scope) or ("녹" in scope) or ("green" in scope)
        hits = [has_red, has_yellow, has_green]
        if sum(hits) != 1:
            return "unknown"
        if has_red:
            return "red"
        if has_yellow:
            return "yellow"
        return "green"

    lines = [ln.strip().lower() for ln in response.splitlines() if ln.strip()]
    candidates: list[str] = []

    # Strongest hint: section "2." is expected to be vehicle signal.
    for line in lines:
        if re.match(r"^\s*2[\.\):\-]\s*", line):
            candidates.append(line)

    # Secondary hint: explicit vehicle keywords.
    for line in lines:
        if any(k in line for k in vehicle_keys) and line not in candidates:
            candidates.append(line)

    for line in candidates:
        color = _detect_color(line)
        if color != "unknown":
            return color

    # Fallback: inspect a short window near the first vehicle keyword.
    first_idx = min((text.find(k) for k in vehicle_keys if k in text), default=-1)
    if first_idx >= 0:
        window = text[first_idx : first_idx + 80]
        color = _detect_color(window)
        if color != "unknown":
            return color

    return "unknown"


def _mentions_vehicle_signal(response: str) -> bool:
    text = response.lower()
    return bool(
        re.search(r"(^|\n)\s*2[\.\):\-]\s*", text)
        or ("차량" in text)
        or ("vehicle" in text)
        or ("traffic light" in text)
        or ("car signal" in text)
    )


def _extract_pedestrian_color_from_text(response: str) -> str:
    """Extract pedestrian signal color from section 1 of the safety response."""
    ped_keys = ("보행", "pedestrian", "도보")

    def _detect_color(scope: str) -> str:
        has_red = ("빨" in scope) or ("red" in scope) or ("적색" in scope) or ("붉" in scope)
        has_yellow = ("노" in scope) or ("황" in scope) or ("yellow" in scope) or ("amber" in scope)
        # 파란불 is a common Korean term for the pedestrian walk signal (green).
        has_green = ("초록" in scope) or ("녹" in scope) or ("green" in scope) or ("파란" in scope)
        hits = [has_red, has_yellow, has_green]
        if sum(hits) != 1:
            return "unknown"
        if has_red:
            return "red"
        if has_yellow:
            return "yellow"
        return "green"

    lines = [ln.strip().lower() for ln in response.splitlines() if ln.strip()]
    candidates: list[str] = []

    for line in lines:
        if re.match(r"^\s*1[\.\):\-]\s*", line):
            candidates.append(line)

    for line in lines:
        if any(k in line for k in ped_keys) and line not in candidates:
            candidates.append(line)

    for line in candidates:
        color = _detect_color(line)
        if color != "unknown":
            return color

    return "unknown"


def _is_color_conflict(response: str, image_b64: str | None, min_conf: float = 0.62) -> bool:
    if not image_b64:
        return False
    frame = _decode_b64_image(image_b64)
    if frame is None:
        return False
    cv_scores = _estimate_signal_scores(frame)
    cv_color, cv_conf = _estimate_signal_color(frame)
    text_color = _extract_vehicle_color_from_text(response)
    has_vehicle_section = _mentions_vehicle_signal(response)

    # Conservative gate: if vehicle section exists but text color is ambiguous,
    # do not trust it when CV has a strong signal estimate.
    if has_vehicle_section and text_color == "unknown" and cv_color != "unknown" and cv_conf >= 0.58:
        return True

    if text_color == "green":
        # Hard guard: if red evidence is comparable or stronger, do not trust green text-only.
        if cv_scores["red"] >= max(20.0, cv_scores["green"] * 0.9):
            return True

    # Pedestrian signal check: "green walk" while CV shows dominant red is a dangerous
    # hallucination (user walks into oncoming traffic).  Apply the same hard guard.
    ped_color = _extract_pedestrian_color_from_text(response)
    if ped_color == "green":
        if cv_scores["red"] >= max(20.0, cv_scores["green"] * 0.9):
            return True
    if cv_conf >= min_conf and cv_color != "unknown" and ped_color not in ("unknown", ""):
        if cv_color != ped_color:
            return True

    if cv_conf < min_conf or cv_color == "unknown" or text_color == "unknown":
        return False
    return cv_color != text_color


def _build_safety_fallback_response() -> str:
    return (
        "1. 보행자 신호: 판독 불가\n"
        "2. 차량 신호: 판독 불가\n"
        "3. 접근 차량: 판독 불가\n"
        "4. 횡단보도/장애물: 판독 불가\n"
        "5. 기타 위험요소: 판독 불가\n\n"
        "건너기 전 주변을 직접 확인하세요."
    )


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
    return (
        f"1. 보행자 신호: {ped}\n"
        f"2. 차량 신호: {color} 계열 감지(추정)\n"
        "3. 접근 차량: 판단 어려움(직접 확인 필요)\n"
        "4. 횡단보도/장애물: 판독 불가\n"
        "5. 기타 위험요소: 판독 불가\n\n"
        f"{rec}"
    )


async def _safety_retry_then_fallback(
    retry_prompt: str,
    image_b64: str | None,
    usage: dict,
    retry_path_name: str,
    fail_path_name: str,
) -> ServiceRunResult:
    """High-res single retry → CV-assisted fallback, shared by both safety paths."""
    if image_b64:
        hi_b64 = image_b64
        frame = _decode_b64_image(image_b64)
        if frame is not None:
            hi_b64 = _encode_jpeg_b64(frame, max_size=1400, quality=95)
        response2, usage2 = await call_vlm(retry_prompt, image_b64=hi_b64)
        merged = merge_usage(usage, usage2)
        response2 = sanitize_safety_response(response2)
        if _is_safety_response_complete(response2) and not _is_color_conflict(response2, hi_b64):
            merged["vlm_calls"] = 2
            merged["image_sent"] = 1
            merged["path_used"] = retry_path_name
            merged["quality_check_passed"] = True
            return response2, True, None, merged
        usage = merged

    fallback = sanitize_safety_response(_build_cv_assisted_fallback(image_b64))
    usage["vlm_calls"] = usage.get("vlm_calls", 1) + (1 if image_b64 else 0)
    usage["image_sent"] = 1 if image_b64 else 0
    usage["path_used"] = fail_path_name
    usage["quality_check_passed"] = _is_safety_response_complete(fallback)
    return fallback, True, None, usage


async def _run_optimized_safety(
    full_semantic: str,
    baseline_prompt: str,
    image_b64: str | None,
) -> ServiceRunResult:
    response1, usage1 = await call_vlm(full_semantic, image_b64=None)
    response1 = sanitize_safety_response(response1)
    if _is_safety_response_complete(response1) and not _is_color_conflict(response1, image_b64):
        usage1["vlm_calls"] = 1
        usage1["image_sent"] = 0
        usage1["path_used"] = "text_only"
        usage1["quality_check_passed"] = True
        return response1, True, None, usage1

    return await _safety_retry_then_fallback(
        baseline_prompt, image_b64, usage1,
        retry_path_name="full_image_retry_highres",
        fail_path_name="text_only_failed_highres_retry+cv_fallback",
    )


async def _run_baseline_safety(
    baseline_prompt: str,
    image_b64: str | None,
) -> ServiceRunResult:
    response1, usage1 = await call_vlm(baseline_prompt, image_b64=image_b64)
    response1 = sanitize_safety_response(response1)
    if _is_safety_response_complete(response1) and not _is_color_conflict(response1, image_b64):
        usage1["vlm_calls"] = 1
        usage1["image_sent"] = 1 if image_b64 else 0
        usage1["path_used"] = "vision_direct"
        usage1["quality_check_passed"] = True
        return response1, True, None, usage1

    return await _safety_retry_then_fallback(
        baseline_prompt, image_b64, usage1,
        retry_path_name="vision_direct_highres_retry",
        fail_path_name="vision_failed_highres_retry+cv_fallback",
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

    baseline_prompt = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
    baseline_prompt = append_optional_context(baseline_prompt, "Reference context", graph_context)

    if semantic_prompt:
        semantic_prompt = _strip_prior_context_from_semantic(semantic_prompt)
        full_semantic = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
        full_semantic = append_optional_context(full_semantic, "Scene features (CV-extracted)", semantic_prompt)
        return await _run_optimized_safety(full_semantic, baseline_prompt, image_b64)
    return await _run_baseline_safety(baseline_prompt, image_b64)
