"""Safety policy and action guardrail.

Prevents hallucinated or dangerous actions from being executed.
Safety-alert responses must never assert definite safety.
"""

_BLOCKED_ACTIONS: set[str] = {"delete", "format", "shutdown", "emergency_call", "factory_reset"}

# Phrases that falsely guarantee safety — must be replaced
_DANGEROUS_PHRASES: list[tuple[str, str]] = [
    ("건너도 됩니다", "주의가 필요합니다. 직접 판단하세요"),
    ("안전합니다", "주의가 필요합니다. 직접 판단하세요"),
    ("괜찮습니다", "상황을 주의 깊게 확인하세요"),
    ("문제없습니다", "상황을 주의 깊게 확인하세요"),
]


def check_action_allowed(
    action: str,
    device_risk_level: str,
    requires_confirmation: bool,
) -> tuple[bool, str]:
    if action in _BLOCKED_ACTIONS:
        return False, f"'{action}' 액션은 시스템 정책으로 차단됩니다."
    if device_risk_level == "high" and requires_confirmation:
        return False, "고위험 기기입니다. 사용자 직접 확인이 필요합니다."
    return True, ""


def sanitize_safety_response(text: str) -> str:
    """Remove overconfident safety assurances from alert responses."""
    for dangerous, replacement in _DANGEROUS_PHRASES:
        text = text.replace(dangerous, replacement)
    return text
