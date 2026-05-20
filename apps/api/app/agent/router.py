"""Rule-based lightweight service router."""

from app.constants import SERVICE_CATEGORY_KEYWORDS as _CAT

_RULES: list[tuple[list[str], list[str], float, str]] = [
    (
        _CAT["safety"] + ["caution"],
        ["crosswalk", "road", "street", "intersection", "횡단보도", "도로", "교차로"],
        0.9,
        "safety_alert",
    ),
    (
        ["read label"] + _CAT["label"],
        [],
        0.88,
        "label_reader",
    ),
    (
        _CAT["device"] + ["turn on", "turn off", "device", "켜줘", "꺼줘", "멈춰"],
        [],
        0.85,
        "device_control",
    ),
    (
        _CAT["navigation"] + ["navigation", "go to", "how do i get"],
        [],
        0.82,
        "navigation",
    ),
    (
        _CAT["context_memory"],
        [],
        0.85,
        "context_memory",
    ),
    (
        _CAT["scene"],
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
    # Keep default below router_confidence_threshold so unmatched/ambiguous queries
    # can take the LLM fallback path instead of being forced to scene_assistant.
    best_service = "scene_assistant"
    best_confidence = 0.30

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
