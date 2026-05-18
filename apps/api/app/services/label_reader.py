"""LabelReader service — medicine and product label OCR + structured extraction.

Optimized path: semantic_prompt already contains the full label_ocr_raw block
  extracted by semantic_extractor.extract_label_ocr(). A text-only VLM call
  is sufficient → image_payload_bytes ≈ 0, faster text model call.

Baseline path: raw image → vision VLM call (comparison baseline).

Safety guardrail: _sanitize_label_response() ensures no definitive dosage
  confirmation is emitted, since incorrect medical information is especially
  dangerous for visually impaired users.
"""

from app.schemas.context import ContextRequest
from app.services.common import (
    ServiceRunResult,
    append_optional_context,
    dispatch,
    first_image_or_none,
)

_SYSTEM_PROMPT = (
    "You are a label reading assistant for smart glasses designed for visually impaired users.\n"
    "Read and summarize the key information from the medicine or product label.\n"
    "Respond in the following order:\n"
    "1. 제품명/약품명\n"
    "2. 주성분 또는 핵심 성분\n"
    "3. 용법·용량 (복용 방법 또는 사용 방법)\n"
    "4. 주의사항 (알러지, 부작용, 금기 등)\n"
    "5. 유효기간\n"
    "6. 제조사\n\n"
    "If a field is not visible or not present, state '확인 불가'.\n"
    "Keep each field to 1–2 sentences. Be concise and clear for audio delivery.\n"
    "IMPORTANT: Do not confirm specific dosage as medical advice. "
    "Always end with: '정확한 복용량 및 사용법은 의사 또는 약사에게 확인하세요.'"
)

# Unsafe phrase → safe replacement mapping.
# Definitive dosage confirmations are redacted at the phrase level so the
# surrounding label information (product name, ingredients, etc.) is preserved
# while removing the dangerous authoritative statement.
_UNSAFE_REPLACEMENTS: list[tuple[str, str]] = [
    ("복용해도 됩니다", "복용 전 반드시 전문가에게 확인하세요"),
    ("복용하세요", "복용 전 반드시 전문가에게 확인하세요"),
    ("드시면 됩니다", "복용 전 반드시 전문가에게 확인하세요"),
    ("안전합니다", "안전성은 반드시 전문가에게 확인하세요"),
    ("부작용 없습니다", "부작용 여부는 반드시 전문가에게 확인하세요"),
]

_SAFETY_FOOTER = "\n\n⚠️ 정확한 복용량 및 사용법은 반드시 의사 또는 약사에게 확인하세요."


def _sanitize_label_response(response: str) -> str:
    """Redact definitive dosage phrases and ensure safety footer is present.

    Each unsafe phrase is replaced inline with a safe alternative so the
    structured label output remains readable. The safety footer is appended
    if not already present.
    """
    for unsafe, safe in _UNSAFE_REPLACEMENTS:
        response = response.replace(unsafe, safe)
    if "의사 또는 약사에게 확인" not in response:
        response = response.rstrip() + _SAFETY_FOOTER
    return response


_OCR_MARKER = "--- Label / Medicine OCR Text ---"


async def run(
    ctx: ContextRequest,
    image_b64_list: list[str],
    graph_context: str,
    request_id: str,
    semantic_prompt: str = "",
) -> ServiceRunResult:
    """Run label reading service.

    Optimized: semantic_prompt must contain the OCR block (marked by _OCR_MARKER).
      We prepend _SYSTEM_PROMPT so the VLM receives structured extraction instructions
      alongside the OCR text — no raw image bytes sent to cloud.
    Baseline / OCR-empty: raw image sent to vision VLM with _SYSTEM_PROMPT.
    """
    if not image_b64_list and not semantic_prompt:
        msg = "이미지가 제공되지 않아 라벨을 읽을 수 없습니다." + _SAFETY_FOOTER
        return msg, False, None, {}

    baseline_prompt = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
    baseline_prompt = append_optional_context(baseline_prompt, "Prior context", graph_context)

    # Only use the semantic (text-only) path when actual OCR content is present.
    # If OCR failed or pytesseract is unavailable, label_ocr_raw is empty and
    # build_semantic_prompt() omits the OCR block → fall through to vision.
    has_ocr = _OCR_MARKER in semantic_prompt
    ocr_semantic_prompt = (
        f"{_SYSTEM_PROMPT}\n\n{semantic_prompt}" if has_ocr else ""
    )

    return await dispatch(
        ocr_semantic_prompt,
        baseline_prompt,
        first_image_or_none(image_b64_list),
        postprocess=_sanitize_label_response,
    )
