import base64

import cv2
import numpy as np


def preprocess_image_bytes(image_bytes: bytes, max_size: int = 768) -> str:
    """Resize image and return base64 JPEG string."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes")
    h, w = img.shape[:2]
    if max(h, w) > max_size:
        scale = max_size / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))
    _, encoded = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(encoded.tobytes()).decode("utf-8")


def frame_to_b64(frame: np.ndarray, max_size: int | None = None, quality: int = 85) -> str:
    img = frame
    if max_size is not None:
        h, w = img.shape[:2]
        if max(h, w) > max_size:
            scale = max_size / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)))
    _, encoded = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(encoded.tobytes()).decode("utf-8")
