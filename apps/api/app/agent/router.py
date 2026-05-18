"""Rule-based lightweight service router."""

_RULES: list[tuple[list[str], list[str], float, str]] = [
    (
        [
            "safe", "safety", "danger", "hazard", "cross", "traffic", "obstacle", "warning",
            # Korean
            "안전", "위험", "건너", "횡단", "교통", "장애물", "경고", "조심", "주의",
        ],
        ["crosswalk", "road", "street", "intersection", "횡단보도", "도로", "교차로"],
        0.9,
        "safety_alert",
    ),
    (
        [
            "read label", "label", "medicine", "drug", "pill", "medication",
            "ingredient", "dosage", "expiry", "prescription",
            # Korean
            "라벨", "약", "의약품", "성분", "복용", "유효기간", "읽어줘", "읽어",
            "알려줘", "처방", "용량", "용법",
        ],
        [],
        0.88,
        "label_reader",
    ),
    (
        [
            "turn on", "turn off", "switch", "volume", "brightness", "device", "control", "play", "pause",
            # Korean
            "켜", "꺼", "켜줘", "꺼줘", "볼륨", "밝기", "기기", "조명", "스피커", "에어컨", "틀어", "멈춰",
        ],
        [],
        0.85,
        "device_control",
    ),
    (
        [
            "where", "direction", "route", "navigate", "navigation", "go to", "how do i get",
            # Korean
            "어디", "길", "방향", "경로", "가려면", "가는", "내비", "위치",
        ],
        [],
        0.82,
        "navigation",
    ),
    (
        [
            "remember", "earlier", "before", "previous", "last time", "memory", "looked at",
            # Korean
            "기억", "아까", "전에", "이전", "봤던", "봤어", "기억해", "저번",
        ],
        [],
        0.85,
        "context_memory",
    ),
    (
        [
            "what do you see", "describe", "look", "scene", "image", "what is here", "show me",
            # Korean
            "뭐가", "뭐야", "무엇", "보여", "보이나", "설명", "장면", "어떤", "알려",
        ],
        [],
        0.7,
        "scene_assistant",
    ),
]


def route(
    user_request: str,
    location_type: str = "",
    has_devices: bool = False,
) -> tuple[str, float]:
    """Return (service_name, confidence)."""
    request_lower = user_request.lower()
    best_service = "scene_assistant"
    best_confidence = 0.25

    for keywords, loc_hints, base_conf, service in _RULES:
        matched = sum(1 for kw in keywords if kw in request_lower)
        if matched == 0:
            continue
        # 1 keyword match → 50 % of base confidence; 2+ → full base confidence
        conf = base_conf * min(matched, 2) / 2
        if loc_hints and location_type in loc_hints:
            conf = min(conf + 0.08, 0.99)
        if service == "device_control" and not has_devices:
            conf *= 0.4
        if conf > best_confidence:
            best_confidence = conf
            best_service = service

    return best_service, round(best_confidence, 3)
