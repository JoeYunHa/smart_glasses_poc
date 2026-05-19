import cv2
import numpy as np

from app.constants import SERVICE_CATEGORY_KEYWORDS

_SCENE_W = 0.6
_QUERY_W = 0.4
_SAFETY_SIGNAL_BONUS_W = 0.35

# Brightness thresholds per category (heuristic: outdoor → bright, indoor → dim).
# "label", "context_memory", "scene" have no bias — they appear in any lighting.
_CATEGORY_BRIGHTNESS: dict[str, tuple[float | None, float | None]] = {
    "safety":         (100.0, None),   # prefer bright (outdoor)
    "navigation":     (100.0, None),   # prefer bright (outdoor)
    "device":         (None,  120.0),  # prefer dim (indoor)
    "label":          (None,  None),   # no brightness bias
    "context_memory": (None,  None),   # no brightness bias
    "scene":          (None,  None),   # no brightness bias
}


def _query_relevance_score(frame: np.ndarray, user_request: str) -> float:
    """Estimate frame relevance to user_request via brightness heuristic.

    Maps the query category detected from SERVICE_CATEGORY_KEYWORDS to a
    brightness expectation (outdoor/bright for safety & navigation, indoor/dim
    for device control).  No VLM call required.
    """
    if not user_request:
        return 0.0
    req = user_request.lower()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    brightness = float(gray.mean())

    score = 0.0
    for category, keywords in SERVICE_CATEGORY_KEYWORDS.items():
        if not any(kw in req for kw in keywords):
            continue
        low_thresh, high_thresh = _CATEGORY_BRIGHTNESS[category]
        if low_thresh is not None and brightness > low_thresh:
            score += 0.3
        elif high_thresh is not None and brightness < high_thresh:
            score += 0.3
        elif low_thresh is None and high_thresh is None:
            score += 0.15
    return min(score, 1.0)


def _is_safety_query(user_request: str) -> bool:
    req = user_request.lower()
    safety_keywords = SERVICE_CATEGORY_KEYWORDS.get("safety", [])
    navigation_keywords = SERVICE_CATEGORY_KEYWORDS.get("navigation", [])
    return any(kw in req for kw in safety_keywords + navigation_keywords)


def _signal_visibility_score(frame: np.ndarray) -> float:
    """Estimate traffic-signal visibility from upper region visual cues.

    Uses color blob likelihood (red/yellow/green), sharpness, and contrast.
    Returns score in [0, 1].
    """
    h, w = frame.shape[:2]
    if h < 4 or w < 4:
        return 0.0

    # Signals usually appear in upper half/upper corners.
    roi = frame[: max(1, int(h * 0.62)), :]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # Color masks for typical signal colors.
    red1 = cv2.inRange(hsv, (0, 80, 70), (12, 255, 255))
    red2 = cv2.inRange(hsv, (165, 80, 70), (179, 255, 255))
    yellow = cv2.inRange(hsv, (18, 70, 80), (40, 255, 255))
    green = cv2.inRange(hsv, (40, 60, 60), (95, 255, 255))
    color_mask = cv2.bitwise_or(cv2.bitwise_or(cv2.bitwise_or(red1, red2), yellow), green)

    # Small bright blobs are more signal-like than large color regions.
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(color_mask, connectivity=8)
    small_blob_score = 0.0
    roi_area = float(roi.shape[0] * roi.shape[1])
    for idx in range(1, num_labels):
        area = float(stats[idx, cv2.CC_STAT_AREA])
        if 6.0 <= area <= max(25.0, roi_area * 0.02):
            small_blob_score += 1.0
    small_blob_score = min(small_blob_score / 6.0, 1.0)

    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    sharpness_score = min(lap_var / 250.0, 1.0)
    contrast_score = min(float(gray.std()) / 64.0, 1.0)

    # Penalize very dark frames where signal reading is likely unstable.
    brightness = float(gray.mean())
    dark_penalty = 0.25 if brightness < 45.0 else 0.0

    score = (0.55 * small_blob_score) + (0.25 * sharpness_score) + (0.20 * contrast_score) - dark_penalty
    return float(max(0.0, min(score, 1.0)))


def signal_visibility_score(frame: np.ndarray) -> float:
    """Public wrapper for safety-frame ranking."""
    return _signal_visibility_score(frame)


def select_keyframes(
    frames: list[np.ndarray],
    max_keyframes: int = 8,
    user_request: str = "",
) -> list[np.ndarray]:
    """Select keyframes with temporal coverage + query-relevance scoring.

    Divides the video into max_keyframes equal segments and picks the
    highest-scoring frame within each segment, guaranteeing one representative
    frame per temporal interval regardless of where scene changes cluster.
    Score = scene-change score (0.6) + query relevance score (0.4).
    """
    if not frames:
        return []
    if len(frames) <= max_keyframes:
        return frames

    scores: list[float] = []
    safety_query = _is_safety_query(user_request)
    for i in range(len(frames)):
        if i == 0:
            scene_score = 0.0
        else:
            prev = cv2.cvtColor(frames[i - 1], cv2.COLOR_BGR2GRAY)
            curr = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            scene_score = float(cv2.absdiff(prev, curr).mean())
        q_score = _query_relevance_score(frames[i], user_request) * 255.0
        score = (_SCENE_W * scene_score) + (_QUERY_W * q_score)
        if safety_query:
            score += _signal_visibility_score(frames[i]) * 255.0 * _SAFETY_SIGNAL_BONUS_W
        scores.append(score)

    # Temporal coverage: pick best-scoring frame from each equal-width segment.
    segment_size = len(frames) / max_keyframes
    selected: list[int] = []
    for seg in range(max_keyframes):
        start = int(seg * segment_size)
        end = min(int((seg + 1) * segment_size), len(frames))
        best_idx = max(range(start, end), key=lambda i: scores[i])
        selected.append(best_idx)
    return [frames[i] for i in selected]
