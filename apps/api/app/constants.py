"""Shared constants used across multiple modules.

SERVICE_CATEGORY_KEYWORDS: broad category keyword lists consumed by
  keyframe_selector._query_relevance_score() AND agent/router._RULES.
  Single source of truth — update here when adding services or keywords.

Mapping to brightness heuristic in keyframe_selector:
  "safety" + "navigation" → outdoor / bright frames preferred (brightness > 100)
  "device"                → indoor / dim frames preferred (brightness < 120)
  "label"                 → no brightness bias (label reading works in any lighting)
  "context_memory"/"scene" → no brightness bias
"""

SERVICE_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "safety": [
        "safe", "safety", "danger", "hazard", "cross", "traffic",
        "obstacle", "warning", "caution",
        # Korean
        "안전", "위험", "건너", "횡단", "교통", "장애물", "경고", "조심", "주의",
    ],
    "navigation": [
        "where", "route", "direction", "go", "navigate", "get to",
        # Korean
        "어디", "길", "방향", "경로", "가려면", "가는", "내비", "위치",
        "찾아", "안내", "데려다",  # 찾아줘 / 안내해줘 / 데려다줘
    ],
    "device": [
        "turn", "switch", "volume", "brightness", "play", "pause", "control",
        # Korean
        "켜", "꺼", "볼륨", "밝기", "기기", "조명", "스피커", "에어컨", "틀어",
    ],
    "label": [
        "label", "medicine", "drug", "pill", "medication",
        "ingredient", "dosage", "expiry", "prescription",
        # Korean
        "라벨", "약", "의약품", "성분", "복용", "유효기간", "읽어줘", "읽어",
        "처방", "용량", "용법",
        # NOTE: "알려줘" intentionally excluded — it is a generic request suffix ("tell me")
        # that appears in all service queries and causes context_memory queries to
        # misroute to label_reader.
    ],
    "context_memory": [
        "remember", "earlier", "before", "previous", "last time", "memory", "looked at",
        # Korean
        "기억", "아까", "전에", "이전", "봤던", "봤어", "기억해", "저번",
        "방금", "금방", "직전", "지난번", "아까전",  # 방금 본 거 / 금방 지나온 곳
    ],
    "scene": [
        "what do you see", "describe", "look", "scene", "image", "what is here", "show me",
        # Korean
        "뭐가", "뭐야", "무엇", "보여", "보이나", "설명", "장면", "어떤", "알려",
    ],
}
