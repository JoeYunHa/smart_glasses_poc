import cv2
import numpy as np

_SCENE_W = 0.6
_QUERY_W = 0.4

_KEYWORD_HINTS: dict[str, list[str]] = {
    "safety":     ["safe", "cross", "danger", "traffic", "obstacle", "warning", "hazard"],
    "navigation": ["where", "route", "direction", "go", "navigate", "get to"],
    "device":     ["turn", "switch", "volume", "brightness", "play", "pause", "control"],
}


def _query_relevance_score(frame: np.ndarray, user_request: str) -> float:
    """Estimate frame relevance to user_request via brightness heuristic. No VLM required."""
    if not user_request:
        return 0.0
    req = user_request.lower()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    brightness = float(gray.mean())
    score = 0.0
    for category, keywords in _KEYWORD_HINTS.items():
        if any(kw in req for kw in keywords):
            if category in ("safety", "navigation") and brightness > 100:
                score += 0.3   # outdoor / bright frames
            elif category == "device" and brightness < 120:
                score += 0.3   # indoor / dim frames
    return min(score, 1.0)



def select_keyframes(
    frames: list[np.ndarray],
    max_keyframes: int = 8,
    user_request: str = "",
) -> list[np.ndarray]:
    """Select keyframes via scene-change score (0.6) + query relevance score (0.4)."""
    if not frames:
        return []
    if len(frames) <= max_keyframes:
        return frames

    scores: list[float] = []
    for i in range(len(frames)):
        # Frame 0 has no predecessor, so scene_score is 0; query relevance still applies.
        if i == 0:
            scene_score = 0.0
        else:
            prev = cv2.cvtColor(frames[i - 1], cv2.COLOR_BGR2GRAY)
            curr = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            scene_score = float(cv2.absdiff(prev, curr).mean())
        q_score = _query_relevance_score(frames[i], user_request) * 255.0
        scores.append(_SCENE_W * scene_score + _QUERY_W * q_score)

    top_indices = sorted(range(len(frames)), key=lambda i: scores[i], reverse=True)[:max_keyframes]
    selected = sorted(top_indices)
    return [frames[i] for i in selected]
