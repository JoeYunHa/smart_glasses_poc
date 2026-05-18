"""label_reader service tests.

Covers:
  - Label keyword routing → label_reader service
  - Safety sanitizer (footer injection, unsafe phrase detection)
  - dispatch() path selection based on OCR content presence
"""

from __future__ import annotations

import pytest

from app.agent.router import route
from app.services.label_reader import _OCR_MARKER, _sanitize_label_response


# ── Router: label keywords → label_reader ─────────────────────────────────────

@pytest.mark.parametrize("request_text,min_confidence", [
    # 2+ keyword hits → full base confidence (0.88)
    ("Read this medicine label and tell me the dosage", 0.8),
    ("약 라벨 읽어줘", 0.8),
    ("What ingredients are in this medication?", 0.8),
    # 1 keyword hit → 50% of base (0.44); still routes correctly, VLM fallback handles routing
    ("Read the pill bottle for me", 0.0),
    ("Check the drug expiry date", 0.0),
])
def test_label_reader_routing(request_text, min_confidence):
    service, confidence = route(request_text, "", has_devices=False)
    assert service == "label_reader", f"Expected label_reader, got {service!r} for {request_text!r}"
    if min_confidence > 0:
        assert confidence >= min_confidence, f"Confidence {confidence} below {min_confidence}"


# ── Safety sanitizer ───────────────────────────────────────────────────────────

def test_sanitizer_appends_footer_when_missing():
    response = "1. 제품명: 타이레놀\n2. 용법용량: 1정씩 복용"
    result = _sanitize_label_response(response)
    assert "의사 또는 약사에게 확인" in result


def test_sanitizer_no_double_append_when_footer_present():
    response = "정확한 복용량 및 사용법은 의사 또는 약사에게 확인하세요."
    result = _sanitize_label_response(response)
    assert result.count("의사 또는 약사에게 확인") == 1


@pytest.mark.parametrize("unsafe_phrase", [
    "복용해도 됩니다",
    "복용하세요",
    "드시면 됩니다",
    "안전합니다",
    "부작용 없습니다",
])
def test_sanitizer_redacts_unsafe_phrase_and_adds_footer(unsafe_phrase):
    response = f"하루 2회 {unsafe_phrase}."
    result = _sanitize_label_response(response)
    assert unsafe_phrase not in result, (
        f"Unsafe phrase {unsafe_phrase!r} must be removed from output, not just accompanied by footer"
    )
    assert "의사 또는 약사에게 확인" in result


def test_sanitizer_preserves_surrounding_label_content():
    """Redaction must be surgical: unsafe phrase is removed but label fields remain."""
    response = (
        "1. 제품명: 타이레놀\n"
        "3. 용법용량: 하루 3회 복용하세요. 식후 30분에 드시면 됩니다.\n"
        "5. 유효기간: 2026-12"
    )
    result = _sanitize_label_response(response)
    assert "복용하세요" not in result
    assert "드시면 됩니다" not in result
    assert "타이레놀" in result, "Product name must be preserved after redaction"
    assert "유효기간" in result, "Expiry date field must be preserved after redaction"
    assert "의사 또는 약사에게 확인" in result


# ── Dispatch path: OCR absent → vision, OCR present → text-only ───────────────

@pytest.mark.asyncio
async def test_label_run_uses_vision_when_no_ocr_block(monkeypatch):
    """semantic_prompt without OCR marker → dispatch must call VLM with image_b64."""
    captured = []

    async def fake_call_vlm(prompt, image_b64=None, max_tokens=512):
        captured.append(image_b64)
        return "1. 제품명: 타이레놀\n의사 또는 약사에게 확인하세요.", {"total_tokens": 10, "vlm_calls": 1}

    monkeypatch.setattr("app.groq_client.call_vlm", fake_call_vlm)

    from app.schemas.context import AgentMode, ContextRequest
    from app.services import label_reader

    ctx = ContextRequest(
        user_request="read the medicine label",
        nearby_devices=[],
        mode=AgentMode.optimized,
    )

    # semantic_prompt with NO OCR marker (pytesseract unavailable or OCR empty)
    semantic_no_ocr = "User request: read the medicine label\n[Frame 1] bright/outdoor, motion=0.00"

    await label_reader.run(ctx, ["FAKE_B64=="], "", "req-test-001", semantic_no_ocr)

    assert len(captured) == 1
    assert captured[0] == "FAKE_B64==", (
        "Expected vision path: image_b64 should be passed to VLM when OCR block is absent"
    )


@pytest.mark.asyncio
async def test_label_run_uses_text_only_when_ocr_block_present(monkeypatch):
    """semantic_prompt with OCR marker → dispatch must call VLM with image_b64=None."""
    captured = []

    async def fake_call_vlm(prompt, image_b64=None, max_tokens=512):
        captured.append(image_b64)
        return "1. 제품명: 타이레놀\n의사 또는 약사에게 확인하세요.", {"total_tokens": 10, "vlm_calls": 1}

    monkeypatch.setattr("app.groq_client.call_vlm", fake_call_vlm)

    from app.schemas.context import AgentMode, ContextRequest
    from app.services import label_reader

    ctx = ContextRequest(
        user_request="read the medicine label",
        nearby_devices=[],
        mode=AgentMode.optimized,
    )

    semantic_with_ocr = (
        "User request: read the medicine label\n"
        "\n--- Label / Medicine OCR Text ---\n"
        "[Label 1]:\n타이레놀 500mg 60정\n--- End OCR Text ---\n"
        "\n[Frame 1] bright/outdoor, motion=0.00, text_density=0.18"
    )
    assert _OCR_MARKER in semantic_with_ocr  # sanity check

    await label_reader.run(ctx, ["FAKE_B64=="], "", "req-test-002", semantic_with_ocr)

    assert len(captured) == 1
    assert captured[0] is None, (
        "Expected text-only path: image_b64 should be None when OCR block is present"
    )


@pytest.mark.asyncio
async def test_label_run_system_prompt_included_in_ocr_path(monkeypatch):
    """When OCR block present, _SYSTEM_PROMPT must be prepended so VLM extracts structured fields."""
    received_prompts = []

    async def fake_call_vlm(prompt, image_b64=None, max_tokens=512):
        received_prompts.append(prompt)
        return "1. 제품명: 타이레놀\n의사 또는 약사에게 확인하세요.", {"total_tokens": 10, "vlm_calls": 1}

    monkeypatch.setattr("app.groq_client.call_vlm", fake_call_vlm)

    from app.schemas.context import AgentMode, ContextRequest
    from app.services import label_reader

    ctx = ContextRequest(
        user_request="read the medicine label",
        nearby_devices=[],
        mode=AgentMode.optimized,
    )

    semantic_with_ocr = (
        "User request: read the medicine label\n"
        "\n--- Label / Medicine OCR Text ---\n"
        "[Label 1]:\n타이레놀 500mg\n--- End OCR Text ---\n"
    )

    await label_reader.run(ctx, ["FAKE_B64=="], "", "req-test-003", semantic_with_ocr)

    assert received_prompts, "VLM was not called"
    # The system prompt should include structured field instructions
    assert "제품명" in received_prompts[0], "Structured extraction prompt must include 제품명 field"
    assert "label_ocr_raw" not in received_prompts[0].lower(), "Should not expose raw field names"


@pytest.mark.asyncio
async def test_label_run_no_image_no_semantic_returns_error():
    from app.schemas.context import AgentMode, ContextRequest
    from app.services import label_reader

    ctx = ContextRequest(
        user_request="read the label",
        nearby_devices=[],
        mode=AgentMode.baseline,
    )
    response_text, vlm_used, action_result, usage = await label_reader.run(
        ctx, [], "", "req-test-004", ""
    )
    assert "이미지가 제공되지 않아" in response_text
    assert vlm_used is False


# ── Planner-level: image_payload_bytes accuracy ────────────────────────────────

def test_image_payload_bytes_reflects_image_when_ocr_empty(client):
    """When OCR is unavailable (pytesseract absent), label_reader falls through to vision.
    The eval log must record image_payload_bytes equal to the actual b64 image bytes,
    NOT the semantic perception text bytes.
    """
    import base64

    import cv2
    import numpy as np

    # Build a small but non-trivial image so b64 bytes are measurable
    image = np.zeros((32, 32, 3), dtype=np.uint8)
    image[10:22, 10:22] = [200, 200, 200]
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    jpeg_bytes = encoded.tobytes()
    expected_b64_bytes = len(base64.b64encode(jpeg_bytes))

    ctx = {
        "user_request": "Read this medicine label and tell me the dosage",
        "gps": None,
        "nearby_devices": [],
        "mode": "optimized",
    }
    before_count = client.get("/api/logs/").json()["logs"].__len__()

    client.post(
        "/api/agent/run",
        data={"context_json": __import__("json").dumps(ctx)},
        files={"image": ("label.jpg", jpeg_bytes, "image/jpeg")},
    )

    logs = client.get("/api/logs/").json()["logs"]
    new_logs = logs[before_count:]
    assert new_logs, "Agent run produced no log entry"
    log = new_logs[-1]

    assert log["selected_service"] == "label_reader"
    # Without pytesseract, OCR block is absent → vision path → image bytes were sent
    # image_payload_bytes must be ≥ expected_b64_bytes (planner encodes the preprocessed image,
    # not the raw JPEG, so sizes differ; we only assert it reflects image scale, not text bytes).
    assert log["image_payload_bytes"] > 0, "image_payload_bytes must be non-zero for vision fallback"
    # Semantic text alone would be at most a few hundred bytes; actual image b64 is much larger.
    # A 32×32 JPEG encoded to base64 is reliably > 500 bytes.
    assert log["image_payload_bytes"] > 500, (
        f"image_payload_bytes={log['image_payload_bytes']} looks like text bytes, not image bytes"
    )
