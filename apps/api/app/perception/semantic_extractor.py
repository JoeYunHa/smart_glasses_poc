"""Semantic perception layer — converts raw frames to structured SemanticPayload.

Optimized mode uses this to build a text-only prompt for VLM, reducing
image payload bytes and token cost compared to raw base64 transmission.

mode="label": activates enhanced OCR pipeline for medicine/product label reading.
  Applies adaptive thresholding, denoising, and upscaling before OCR, then
  surfaces label_ocr_raw in the semantic prompt as a prominent block.
  Reference: Video-RAG (NeurIPS 2025) — visually-aligned auxiliary text extraction;
             Intention-Aware Semantic Agent Communications for AI Glasses (2026)
             — text-task → OCR result transmission, not raw image.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

# Safety-relevant colors ordered by priority (red/yellow first)
_COLOR_RANGES: list[tuple[str, np.ndarray, np.ndarray]] = [
    ("red",    np.array([0,   100, 100]), np.array([10,  255, 255])),
    ("yellow", np.array([20,  100, 100]), np.array([35,  255, 255])),
    ("green",  np.array([40,  100, 100]), np.array([80,  255, 255])),
    ("blue",   np.array([100, 100, 100]), np.array([130, 255, 255])),
]

_OCR_AVAILABLE: bool | None = None  # lazily detected


@dataclass
class SemanticPayload:
    ocr_text: str = ""
    label_ocr_raw: str = ""           # enhanced OCR output (label mode only)
    text_density: float = 0.0         # ratio of text-pixel area; high → label image
    dominant_colors: list[str] = field(default_factory=list)
    scene_brightness: float = 0.0     # 0–1; > 0.5 → outdoor/bright
    motion_level: float = 0.0         # 0–1; inter-frame motion magnitude


def _check_ocr_available() -> bool:
    global _OCR_AVAILABLE
    if _OCR_AVAILABLE is None:
        try:
            import pytesseract  # type: ignore  # noqa: F401
            _OCR_AVAILABLE = True
        except Exception:
            _OCR_AVAILABLE = False
    return _OCR_AVAILABLE  # type: ignore[return-value]


def extract_label_ocr(frame: np.ndarray) -> tuple[str, float]:
    """Enhanced OCR for medicine/product label reading with OpenCV preprocessing.

    Pipeline: grayscale → upscale (if small) → adaptive threshold → denoise
    Tries PSM 6 (block text) and PSM 3 (auto) and keeps the longer result.
    Returns (ocr_text, text_density).
    text_density is the ratio of bright (text) pixels after thresholding.
    Falls back to ("", 0.0) when pytesseract is unavailable.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Upscale small images — medicine labels are often low-res captures
    h, w = gray.shape
    if h < 400 or w < 400:
        scale = max(400 / h, 400 / w)
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # Adaptive threshold handles uneven lighting (common in glasses camera)
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=15, C=8,
    )

    # Morphological close to remove small noise dots (3×3 provides actual denoising)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    denoised = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # text_density: fraction of dark (text) pixels after THRESH_BINARY.
    # Dark text on light background → text pixels == 0; background == 255.
    text_density = float(np.sum(denoised == 0)) / denoised.size

    if not _check_ocr_available():
        return "", text_density

    try:
        import pytesseract  # type: ignore

        # PSM 6: single uniform text block (ingredient lists, drug info tables)
        # PSM 3: fully automatic page segmentation (full label layout)
        cfg_block = "--psm 6 -l kor+eng"
        cfg_auto  = "--psm 3 -l kor+eng"
        text_block = pytesseract.image_to_string(denoised, config=cfg_block).strip()
        text_auto  = pytesseract.image_to_string(denoised, config=cfg_auto).strip()

        # Keep whichever mode extracted more content
        best = text_block if len(text_block) >= len(text_auto) else text_auto
        return best[:1000], text_density
    except Exception:
        return "", text_density


def extract_semantic(
    frame: np.ndarray,
    prev_frame: np.ndarray | None = None,
    mode: str = "general",
) -> SemanticPayload:
    """Extract lightweight semantic features from a single frame using OpenCV only.

    mode="general": standard brightness/motion/color + sparse OCR (--psm 11).
    mode="label"  : same general features + enhanced label OCR pipeline.
    """
    p = SemanticPayload()

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    p.scene_brightness = float(gray.mean()) / 255.0

    if prev_frame is not None:
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(gray, prev_gray)
        p.motion_level = float(diff.mean()) / 255.0

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    for name, lo, hi in _COLOR_RANGES:
        if cv2.inRange(hsv, lo, hi).mean() > 1.0:
            p.dominant_colors.append(name)

    if mode == "label":
        # Enhanced OCR pipeline: replaces the sparse --psm 11 call
        p.label_ocr_raw, p.text_density = extract_label_ocr(frame)
        p.ocr_text = p.label_ocr_raw[:200]
    else:
        if _check_ocr_available():
            try:
                import pytesseract  # type: ignore
                p.ocr_text = pytesseract.image_to_string(frame, config="--psm 11").strip()[:200]
            except Exception:
                pass

    return p


def build_semantic_prompt(
    payloads: list[SemanticPayload],
    user_request: str,
) -> str:
    """Compose a text-only VLM prompt from SemanticPayloads.

    Sends no image bytes — reduces cloud payload_bytes vs raw base64 transmission.
    Graph context is injected by the caller (planner.py) after retrieval completes.

    When any payload has label_ocr_raw set (label mode), the full OCR text is
    surfaced as a prominent block so label_reader.py can parse it without a
    vision call, achieving image_payload_bytes ≈ 0 for text-heavy tasks.
    """
    lines = [f"User request: {user_request}"]

    # Label OCR block — show full extracted text prominently
    label_texts = [p.label_ocr_raw for p in payloads if p.label_ocr_raw]
    if label_texts:
        lines.append("\n--- Label / Medicine OCR Text ---")
        for i, txt in enumerate(label_texts):
            lines.append(f"[Label {i + 1}]:\n{txt}")
        lines.append("--- End OCR Text ---\n")

    for i, p in enumerate(payloads):
        scene_label = "bright/outdoor" if p.scene_brightness > 0.5 else "dim/indoor"
        parts = [f"[Frame {i + 1}] {scene_label}, motion={p.motion_level:.2f}"]
        if p.dominant_colors:
            parts.append(f"colors={','.join(p.dominant_colors)}")
        if p.text_density > 0.1:
            parts.append(f"text_density={p.text_density:.2f}")
        # Show short ocr_text only when label_ocr_raw is not already shown above
        if p.ocr_text and not p.label_ocr_raw:
            parts.append(f'text="{p.ocr_text}"')
        lines.append(" | ".join(parts))

    return "\n".join(lines)
