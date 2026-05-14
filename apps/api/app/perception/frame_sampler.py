import os
import tempfile

import cv2
import numpy as np


def sample_frames(video_bytes: bytes, fps_target: int = 2) -> list[np.ndarray]:
    """Extract frames from video bytes at target fps."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(video_bytes)
        tmp_path = f.name
    try:
        cap = cv2.VideoCapture(tmp_path)
        video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        interval = max(1, int(video_fps / fps_target))
        frames: list[np.ndarray] = []
        idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if idx % interval == 0:
                frames.append(frame)
            idx += 1
        cap.release()
        return frames
    finally:
        os.unlink(tmp_path)
