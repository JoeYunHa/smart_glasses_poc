import cv2
import numpy as np


def select_keyframes(frames: list[np.ndarray], max_keyframes: int = 8) -> list[np.ndarray]:
    """Select representative keyframes via inter-frame scene change score."""
    if not frames:
        return []
    if len(frames) <= max_keyframes:
        return frames

    scores: list[float] = [0.0]
    for i in range(1, len(frames)):
        prev = cv2.cvtColor(frames[i - 1], cv2.COLOR_BGR2GRAY)
        curr = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
        scores.append(float(cv2.absdiff(prev, curr).mean()))

    # Always keep first frame; fill rest with highest-scoring frames
    top_indices = sorted(
        range(1, len(frames)), key=lambda i: scores[i], reverse=True
    )[: max_keyframes - 1]
    selected = sorted([0] + top_indices)
    return [frames[i] for i in selected]
