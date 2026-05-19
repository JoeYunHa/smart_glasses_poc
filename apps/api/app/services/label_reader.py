"""LabelReader service: OCR label extraction with safety guardrail."""

from app.agent.policy import sanitize_response
from app.schemas.context import ContextRequest
from app.services.common import (
    ServiceRunResult,
    append_optional_context,
    dispatch,
    first_image_or_none,
)

_SYSTEM_PROMPT = (
    "You are an OCR label extraction assistant for smart glasses. "
    "This is informational OCR extraction only, not diagnosis or prescribing.\n\n"
    "Extract only visible label text. If unreadable, write '확인 불가'. "
    "Output exactly 6 numbered lines in Korean:\n"
    "1. 제품명: <value>\n"
    "2. 주성분: <value>\n"
    "3. 복용법/용량: <value>\n"
    "4. 주의사항: <value>\n"
    "5. 유효기간: <value>\n"
    "6. 제조사: <value>\n\n"
    "Do not provide diagnosis/treatment recommendations; only extract visible text. "
    "Append this final sentence: "
    "'정확한 복용법과 사용법은 반드시 의사 또는 약사에게 확인하세요.'"
)

_UNSAFE_REPLACEMENTS: list[tuple[str, str]] = [
    ("복용해도 됩니다", "복용 전 반드시 전문가에게 확인하세요"),
    ("복용하세요", "복용 전 반드시 전문가에게 확인하세요"),
    ("드시면 됩니다", "복용 전 반드시 전문가에게 확인하세요"),
    ("드셔도 됩니다", "복용 전 반드시 전문가에게 확인하세요"),
    ("안전합니다", "안전성은 반드시 전문가에게 확인하세요"),
    ("부작용 없습니다", "부작용 여부는 반드시 전문가에게 확인하세요"),
]

_SAFETY_FOOTER = "\n\n정확한 복용법과 사용법은 반드시 의사 또는 약사에게 확인하세요."
_FOOTER_CHECK = "의사 또는 약사에게 확인"
_OCR_MARKER = "--- Label / Medicine OCR Text ---"
_REFUSAL_PHRASES = (
    "i'm sorry",
    "i’m sorry",
    "i cannot",
    "i can't",
    "can’t",
    "i can't help",
    "i cannot help",
    "can't help with that",
    "cannot help with that",
    "cannot assist",
    "can't assist",
    "요청을 도와드릴 수",
    "도와드릴 수 없",
    "처리할 수 없",
    "응답할 수 없",
)


def _build_refusal_fallback() -> str:
    return (
        "1. 제품명: 확인 불가\n"
        "2. 주성분: 확인 불가\n"
        "3. 복용법/용량: 확인 불가\n"
        "4. 주의사항: 확인 불가\n"
        "5. 유효기간: 확인 불가\n"
        "6. 제조사: 확인 불가"
        + _SAFETY_FOOTER
    )


def _sanitize_label_response(response: str) -> str:
    return sanitize_response(response, _UNSAFE_REPLACEMENTS, _SAFETY_FOOTER, _FOOTER_CHECK)


_OCR_END_MARKER = "--- End OCR Text ---"
_ROI_REFOCUS_HINT = "Focus on printed text, labels, and packaging information in this image region."


def _has_sufficient_ocr_content(semantic_prompt: str) -> bool:
    """Check whether OCR block is meaningful enough for text-only extraction.

    Inspects only the text between the OCR delimiters, not surrounding frame
    metadata — prevents a frame with rich scene info but sparse OCR from
    incorrectly locking into the text-only path.
    """
    if _OCR_MARKER not in semantic_prompt:
        return False
    ocr_section = semantic_prompt.split(_OCR_MARKER, 1)[1]
    if _OCR_END_MARKER in ocr_section:
        ocr_section = ocr_section.split(_OCR_END_MARKER, 1)[0]
    ocr_section = ocr_section.strip()
    meaningful = "".join(ch for ch in ocr_section if ch.isalnum())
    if len(meaningful) < 60:
        return False
    if ocr_section.lower().count("확인 불가") >= 3:
        return False
    return True


def _is_label_response_complete(response: str) -> bool:
    text = response.lower().strip()
    if not text:
        return False
    if any(p in text for p in _REFUSAL_PHRASES):
        return False
    if not all(key in text for key in ("1.", "2.", "3.", "4.", "5.", "6.")):
        return False
    # Reject low-value structured outputs where almost every field is unreadable.
    if text.count("확인 불가") >= 4:
        return False
    return True


async def run(
    ctx: ContextRequest,
    image_b64_list: list[str],
    graph_context: str,
    request_id: str,
    semantic_prompt: str = "",
) -> ServiceRunResult:
    if not image_b64_list and not semantic_prompt:
        msg = "이미지가 제공되지 않아 라벨을 읽을 수 없습니다." + _SAFETY_FOOTER
        return msg, False, None, {}

    baseline_prompt = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
    baseline_prompt = append_optional_context(baseline_prompt, "Prior context", graph_context)

    has_ocr = _has_sufficient_ocr_content(semantic_prompt)
    ocr_semantic_prompt = f"{_SYSTEM_PROMPT}\n\n{semantic_prompt}" if has_ocr else ""

    # When OCR data is present, suppress image fallback: _build_refusal_fallback() below
    # handles quality failures without a vision retry, preserving the text-only guarantee.
    fallback_image = None if has_ocr else first_image_or_none(image_b64_list)
    response, vlm_used, action_result, usage = await dispatch(
        ocr_semantic_prompt,
        baseline_prompt,
        fallback_image,
        postprocess=_sanitize_label_response,
        response_quality_checker=_is_label_response_complete,
        roi_refocus_hint=_ROI_REFOCUS_HINT,
    )
    if not _is_label_response_complete(response):
        response = _build_refusal_fallback()
        usage["quality_check_passed"] = False
    return response, vlm_used, action_result, usage
