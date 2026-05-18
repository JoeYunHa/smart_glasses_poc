"""Rule-based lightweight service router."""

_RULES: list[tuple[list[str], list[str], float, str]] = [
    (
        ["safe", "safety", "danger", "hazard", "cross", "traffic", "obstacle", "warning"],
        ["crosswalk", "road", "street", "intersection"],
        0.9,
        "safety_alert",
    ),
    (
        [
            "read label", "label", "medicine", "drug", "pill", "medication",
            "ingredient", "dosage", "expiry", "prescription",
            "라벨", "약", "의약품", "성분", "복용", "유효기간", "읽어줘", "읽어",
        ],
        [],
        0.88,
        "label_reader",
    ),
    (
        ["turn on", "turn off", "switch", "volume", "brightness", "device", "control", "play", "pause"],
        [],
        0.85,
        "device_control",
    ),
    (
        ["where", "direction", "route", "navigate", "navigation", "go to", "how do i get"],
        [],
        0.82,
        "navigation",
    ),
    (
        ["remember", "earlier", "before", "previous", "last time", "memory", "looked at"],
        [],
        0.85,
        "context_memory",
    ),
    (
        ["what do you see", "describe", "look", "scene", "image", "what is here", "show me"],
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
