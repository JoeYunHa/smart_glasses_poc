"""Rule-based lightweight service router.

Each rule is (keywords, location_type_hints, base_confidence, service_name).
If no rule fires above threshold, returns (scene_assistant, low_confidence)
so the planner falls back to VLM.
"""

_RULES: list[tuple[list[str], list[str], float, str]] = [
    (["위험", "조심", "건너", "차", "사고", "불", "화재", "위협"],
     ["crosswalk", "road", "street", "intersection"], 0.9, "safety_alert"),
    (["꺼줘", "켜줘", "틀어줘", "볼륨", "조명", "제어", "조절", "끄", "켜"],
     [], 0.85, "device_control"),
    (["길", "방향", "어디", "가려면", "지도", "경로", "안내"],
     [], 0.82, "navigation"),
    (["기억", "아까", "전에", "지난번", "저번", "봤던", "다시"],
     [], 0.85, "context_memory"),
    (["뭐야", "설명", "알려줘", "보여줘", "뭐가", "이게", "뭔"],
     [], 0.70, "scene_assistant"),
]


def route(
    user_request: str,
    location_type: str = "",
    has_devices: bool = False,
) -> tuple[str, float]:
    """Return (service_name, confidence)."""
    best_service = "scene_assistant"
    best_confidence = 0.25

    for keywords, loc_hints, base_conf, service in _RULES:
        matched = sum(1 for kw in keywords if kw in user_request)
        if matched == 0:
            continue
        conf = base_conf * (matched / len(keywords))
        if loc_hints and location_type in loc_hints:
            conf = min(conf + 0.08, 0.99)
        if service == "device_control" and not has_devices:
            conf *= 0.4
        if conf > best_confidence:
            best_confidence = conf
            best_service = service

    return best_service, round(best_confidence, 3)
