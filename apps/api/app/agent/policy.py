"""Safety policy, action guardrail, and shared response sanitization."""

import re

_BLOCKED_ACTIONS: set[str] = {"delete", "format", "shutdown", "emergency_call", "factory_reset"}

_DANGEROUS_PHRASES: list[tuple[str, str]] = [
    ("it is safe", "Use caution and make the final decision yourself."),
    ("you are safe", "Use caution and make the final decision yourself."),
    ("completely safe", "Check the situation carefully before acting."),
    ("no problem", "Check the situation carefully before acting."),
    # Korean overconfident phrases
    ("건너셔도 됩니다", "주변 상황을 직접 확인 후 판단하세요."),
    ("건너도 됩니다", "주변 상황을 직접 확인 후 판단하세요."),
    ("안전합니다", "주변 상황을 직접 확인 후 판단하세요."),
    ("문제없습니다", "주변 상황을 직접 확인 후 판단하세요."),
]


def check_action_allowed(
    action: str,
    device_risk_level: str,
    requires_confirmation: bool,
) -> tuple[bool, str]:
    if action in _BLOCKED_ACTIONS:
        return False, f"Action '{action}' is blocked by the safety policy."
    if device_risk_level == "high" and requires_confirmation:
        return False, "This is a high-risk device and requires direct user confirmation."
    return True, ""


def sanitize_response(
    text: str,
    replacements: list[tuple[str, str]],
    footer: str = "",
    footer_check: str = "",
) -> str:
    """Generic phrase-replacement sanitizer with optional footer enforcement.

    Performs exact string replacement (case-sensitive).  Use sanitize_safety_response
    when case-insensitive regex matching is required (e.g. English safety phrases).
    """
    for unsafe, safe in replacements:
        text = text.replace(unsafe, safe)
    if footer and footer_check and footer_check not in text:
        text = text.rstrip() + footer
    return text


def sanitize_safety_response(text: str) -> str:
    """Remove overconfident safety assurances and non-standard prefixes from alert responses."""
    sanitized = text
    for dangerous, replacement in _DANGEROUS_PHRASES:
        sanitized = re.sub(re.escape(dangerous), replacement, sanitized, flags=re.IGNORECASE)
    # Strip non-standard recommendation label prefixes the LLM sometimes adds.
    # e.g. "주요 추천: 대기하세요." → "대기하세요."
    sanitized = re.sub(r"주요\s*추천\s*[:：]\s*", "", sanitized)
    sanitized = re.sub(r"최종\s*추천\s*[:：]\s*", "", sanitized)
    sanitized = re.sub(r"(?<!\w)추천\s*[:：]\s*", "", sanitized)
    return sanitized
