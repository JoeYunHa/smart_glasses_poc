import os
import tempfile

import cv2
import numpy as np


def _detect_suffix(data: bytes) -> str:
    if len(data) >= 12:
        if data[4:8] == b"ftyp":
            return ".mp4"
        if data[:4] == b"RIFF" and data[8:12] == b"AVI ":
            return ".avi"
    if data[:4] == b"\x1a\x45\xdf\xa3":
        return ".webm"
    return ".mp4"


def sample_frames(
    video_bytes: bytes, fps_target: int | None = 2
) -> tuple[list[np.ndarray], int]:
    """Extract frames at target fps.

    Returns (sampled_frames, total_frame_count) where total_frame_count is the
    number of frames in the video before fps-based subsampling.
    """
    suffix = _detect_suffix(video_bytes)
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(video_bytes)
        tmp_path = f.name
    try:
        cap = cv2.VideoCapture(tmp_path)
        video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        interval = 1 if not fps_target or fps_target <= 0 else max(1, int(video_fps / fps_target))
        frames: list[np.ndarray] = []
        total = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if total % interval == 0:
                frames.append(frame)
            total += 1
        cap.release()
        return frames, total
    finally:
        os.unlink(tmp_path)
