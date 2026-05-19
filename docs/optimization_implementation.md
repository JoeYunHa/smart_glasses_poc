# 최적화 전략 구현 상세 문서

> Smart Glasses Physical AI Agent PoC에서 논문 기반 최적화 전략이 실제 코드에 어떻게 반영되었는지를 설명합니다.

---

## 목차

1. [전략 개요](#1-전략-개요)
2. [Strategy 01 — Query-aware Keyframe Selection](#2-strategy-01--query-aware-keyframe-selection)
3. [Strategy 02 — Semantic Perception Layer (Text-only VLM Path)](#3-strategy-02--semantic-perception-layer-text-only-vlm-path)
4. [Strategy 03 — GraphRAG Context Memory](#4-strategy-03--graphrag-context-memory)
5. [공통 설계 — Sanitize 헬퍼 & 평가 지표](#5-공통-설계--sanitize-헬퍼--평가-지표)
6. [Baseline vs Optimized 비교 흐름](#6-baseline-vs-optimized-비교-흐름)

---

## 1. 전략 개요

본 PoC는 세 가지 핵심 최적화 전략을 구현합니다. 각 전략은 특정 병목(frame 수, cloud payload, VLM 호출 횟수)을 줄이는 데 초점을 맞추며, Baseline 모드와 Optimized 모드를 동일 입력으로 비교 측정할 수 있도록 설계되었습니다.

| # | 전략 | 해결하는 병목 | 핵심 지표 |
|---|------|-------------|---------|
| 01 | Query-aware Keyframe Selection | 불필요한 프레임 전송 | `frame_reduction_ratio` |
| 02 | Semantic Perception Layer | cloud image payload 크기 | `image_payload_bytes` |
| 03 | GraphRAG Context Memory | 반복 VLM 호출 | `vlm_call_count`, `retrieved_graph_nodes` |

---

## 2. Strategy 01 — Query-aware Keyframe Selection

### 2.1 배경 및 목표

영상에서 모든 프레임을 VLM에 전달하면 토큰 비용과 네트워크 payload가 선형으로 증가합니다. 핵심 의미가 담긴 프레임만 선택해 VLM 입력 크기를 줄이는 것이 Strategy 01의 목표입니다.

참조 논문: *Video-RAG* (NeurIPS 2025) — visually-aligned auxiliary text extraction, *Intention-Aware Semantic Agent Communications* (2026) — intent-conditioned frame transmission.

### 2.2 구현 파일

```
apps/api/app/perception/keyframe_selector.py
apps/api/app/perception/frame_sampler.py
apps/api/app/constants.py
apps/api/app/agent/pipeline_support.py
```

### 2.3 알고리즘

```python
# keyframe_selector.py — 최종 점수 계산
score[i] = 0.6 * scene_score + 0.4 * q_score
```

**scene_score** (`_SCENE_W = 0.6`): 인접 프레임 간 픽셀 차이(cv2.absdiff)의 평균값. 씬 전환이 많을수록 높아집니다.

**q_score** (`_QUERY_W = 0.4`): 사용자 요청 키워드가 어떤 카테고리에 속하는지 판단한 뒤, 해당 카테고리의 밝기 기대값과 프레임 밝기를 비교해 relevance를 추정합니다.

```python
# constants.py — 공유 카테고리 키워드 (단일 정의 → divergence 방지)
SERVICE_CATEGORY_KEYWORDS = {
    "safety":     ["safe", "danger", "hazard", "cross", "traffic", ...],
    "navigation": ["where", "route", "direction", "navigate", ...],
    "device":     ["turn", "switch", "volume", "brightness", "play", ...],
    "label":      ["label", "medicine", "drug", "pill", "약", "복용", ...],
}

# keyframe_selector.py — 카테고리별 밝기 기대값
_CATEGORY_BRIGHTNESS = {
    "safety":     (100.0, None),   # 야외/밝은 환경 선호
    "navigation": (100.0, None),   # 야외/밝은 환경 선호
    "device":     (None,  120.0),  # 실내/어두운 환경 선호
    "label":      (None,  None),   # 밝기 bias 없음
}
```

### 2.4 Baseline vs Optimized 분기

```python
# pipeline_support.py — run_perception()
if mode == AgentMode.optimized:
    keyframes = select_keyframes(frames, max_keyframes=8, user_request=ctx.user_request)
    # → scene-change + query relevance 결합
else:
    keyframes = select_keyframes(frames, max_keyframes=8, user_request="")
    # → scene-change-only (query relevance 0점, 균등 간격 선택)
```

- **Optimized**: `user_request` 전달 → query relevance score가 살아있는 상태로 프레임 선택
- **Baseline**: `user_request=""` → q_score = 0.0, scene-change 기준만 사용

### 2.5 측정 지표

```json
{
  "original_frame_count": 180,
  "selected_keyframe_count": 6,
  "frame_reduction_ratio": 0.967
}
```

`frame_reduction_ratio = 1 - (selected / original)`. 값이 클수록 더 많은 프레임이 제거된 것입니다.

---

## 3. Strategy 02 — Semantic Perception Layer (Text-only VLM Path)

### 3.1 배경 및 목표

이미지를 base64로 VLM에 전달하면 수십~수백 KB의 payload가 cloud로 전송됩니다. OpenCV로 밝기·모션·색상·OCR을 먼저 추출해 텍스트 설명으로 변환한 뒤, VLM에는 이 텍스트만 전달하면 payload를 수 KB로 줄일 수 있습니다. 텍스트만으로 응답이 불충분할 때만 원본 이미지를 fallback으로 전송합니다.

참조 논문: *Intention-Aware Semantic Agent Communications for AI Glasses* (2026) — text-task → OCR/semantic transmission, not raw image; *Video-RAG* (NeurIPS 2025) — visually-aligned auxiliary text.

### 3.2 구현 파일

```
apps/api/app/perception/semantic_extractor.py   ← SemanticPayload 추출
apps/api/app/services/common.py                 ← dispatch() / run_semantic_service()
apps/api/app/services/scene_assistant.py        ← dispatch() 적용
apps/api/app/services/navigation.py             ← dispatch() 적용
apps/api/app/services/safety_alert.py           ← dispatch() 적용
apps/api/app/services/label_reader.py           ← OCR-path (text-only)
```

### 3.3 SemanticPayload 추출 (`semantic_extractor.py`)

```python
@dataclass
class SemanticPayload:
    ocr_text: str = ""
    label_ocr_raw: str = ""        # 라벨 모드 전용 고해상도 OCR
    text_density: float = 0.0      # 텍스트 픽셀 비율
    dominant_colors: list[str]     # HSV 기반 색상 감지 (red/yellow/green/blue)
    scene_brightness: float = 0.0  # 0–1, 0.5 초과 → 야외/밝음
    motion_level: float = 0.0      # 0–1, 프레임 간 픽셀 변화량
```

HSV 색상 감지는 고정 범위 루프로 구현됩니다:

```python
_COLOR_RANGES = [
    ("red",    np.array([0,   100, 100]), np.array([10,  255, 255])),
    ("yellow", np.array([20,  100, 100]), np.array([35,  255, 255])),
    ("green",  np.array([40,  100, 100]), np.array([80,  255, 255])),
    ("blue",   np.array([100, 100, 100]), np.array([130, 255, 255])),
]

for name, lo, hi in _COLOR_RANGES:
    if cv2.inRange(hsv, lo, hi).mean() > 1.0:   # 0.4% 이상 픽셀 해당 시
        p.dominant_colors.append(name)
```

신호등 판단에서 red/yellow/green이 텍스트로 추출되므로, 이 정보만으로 VLM이 안전 판단을 내릴 수 있습니다.

`build_semantic_prompt()` 는 SemanticPayload를 다음과 같은 텍스트로 변환합니다:

```
User request: 지금 건너도 돼?
[Frame 1] bright scene, motion=0.12 | colors=red,yellow
[Frame 2] bright scene, motion=0.45 | colors=green
```

### 3.4 dispatch() 헬퍼 (`common.py`)

모든 서비스가 동일한 패턴으로 optimized/baseline을 분기합니다:

```python
async def dispatch(
    semantic_prompt: str,
    baseline_prompt: str,
    image_b64: str | None,
    postprocess: Callable[[str], str] | None = None,
) -> ServiceRunResult:
    if semantic_prompt:
        return await run_semantic_service(
            semantic_prompt, fallback_image_b64=image_b64, postprocess=postprocess
        )
    return await run_vlm_service(baseline_prompt, image_b64=image_b64, postprocess=postprocess)
```

`run_semantic_service()`는 text-only VLM 호출 후, 응답이 10자 미만이면 vision fallback을 자동 발동합니다:

```python
async def run_semantic_service(semantic_prompt, fallback_image_b64, postprocess):
    response, usage = await call_vlm(semantic_prompt, image_b64=None)  # text-only
    vlm_calls = 1
    if len(response.strip()) < 10 and fallback_image_b64:
        vision_prompt = "Describe the scene...\n\n" + semantic_prompt
        fallback_response, fallback_usage = await call_vlm(vision_prompt, image_b64=fallback_image_b64)
        if len(fallback_response.strip()) >= 10:
            response = fallback_response
        usage = merge_usage(usage, fallback_usage)
        vlm_calls = 2                      # 실제 호출 횟수 정확 집계
        image_sent = 1
    usage["vlm_calls"] = vlm_calls
    usage["image_sent"] = image_sent
    return response, True, None, usage
```

### 3.5 서비스별 dispatch() 적용

#### scene_assistant.py

```python
full_semantic = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
full_semantic = append_optional_context(full_semantic, "Scene features (CV-extracted)", semantic_prompt)
full_semantic = append_optional_context(full_semantic, "Relevant prior context", graph_context)

baseline_prompt = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
baseline_prompt = append_optional_context(baseline_prompt, "Relevant prior context", graph_context)

return await dispatch(full_semantic, baseline_prompt, image_b64)
```

#### safety_alert.py

```python
full_semantic = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
full_semantic = append_optional_context(full_semantic, "Scene features (CV-extracted)", semantic_prompt)
full_semantic = append_optional_context(full_semantic, "Reference context", graph_context)

baseline_prompt = f"{_SYSTEM_PROMPT}\n\nUser request: {ctx.user_request}"
baseline_prompt = append_optional_context(baseline_prompt, "Reference context", graph_context)

return await dispatch(full_semantic, baseline_prompt, image_b64, postprocess=sanitize_safety_response)
```

`sanitize_safety_response`는 `postprocess` 인자로 전달되어 optimized/baseline 양쪽 경로 모두에 적용됩니다.

#### navigation.py

```python
nav_semantic = ""
if semantic_prompt:
    nav_semantic = f"{nav_semantic}\n\n{gps_info}"
    nav_semantic = append_optional_context(nav_semantic, "Previous context", graph_context)
```

이전에는 `graph_context`가 `baseline_prompt`에만 주입되고 optimized path에는 누락되는 버그가 있었습니다. 수정 후 양쪽 경로 모두에 GPS + graph_context가 주입됩니다.

#### label_reader.py

라벨 모드(OCR)에서는 `semantic_extractor`가 이미 텍스트를 추출했으므로 `dispatch()`가 text-only path를 선택합니다. pytesseract 미설치 환경에서는 OCR이 비어 있어 vision fallback으로 전환됩니다. 결과적으로 `image_payload_bytes ≈ 0` (텍스트 prompt만 전송)이 실현됩니다.

### 3.6 image_payload_bytes 실측 방법

```python
# planner.py
image_b64_bytes = sum(len(b64.encode()) for b64 in image_b64_list)
image_actually_sent = bool(service_vlm_usage.get("image_sent", 0))

if not image_actually_sent and perception.semantic_prompt:
    image_payload_bytes = perception_prompt_bytes      # 텍스트 prompt만 전송
elif image_actually_sent and service_vlm_calls == 2:
    image_payload_bytes = perception_prompt_bytes + image_b64_bytes  # fallback 발동
else:
    image_payload_bytes = image_b64_bytes              # baseline (raw 이미지 전송)
```

`image_sent` 플래그는 `common.py`의 usage dict에 서비스가 직접 기록하므로, planner가 이를 신뢰할 수 있습니다.

---

## 4. Strategy 03 — GraphRAG Context Memory

### 4.1 배경 및 목표

동일한 장소에서 반복 질의가 발생할 때 매번 VLM을 호출하는 것은 비효율적입니다. 이전 씬의 분석 결과를 Temporal Scene Graph(NetworkX)와 벡터 스토어(Qdrant)에 저장하고, 새 요청 시 관련 컨텍스트를 검색해 VLM 프롬프트에 주입합니다.

참조: *GraphRAG* (Microsoft, 2024) — community-aware graph retrieval; *Video-RAG* (NeurIPS 2025) — temporal graph augmented generation.

### 4.2 구현 파일

```
apps/api/app/memory/graph_store.py    ← Temporal Scene Graph (NetworkX)
apps/api/app/memory/vector_store.py   ← 벡터 임베딩 (fastembed + Qdrant)
apps/api/app/memory/retrieval.py      ← 그래프 + 벡터 통합 검색
apps/api/app/agent/planner.py         ← optimized 모드에서만 저장/조회
```

### 4.3 Temporal Scene Graph (`graph_store.py`)

노드 타입: `Scene`, `Object`, `Location`, `Device`, `UserIntent`, `Action`, `Risk`, `Time`

```python
# 노드 중복 제거 — 동일 노드 반복 추가 방지
def _ensure_node(node_id: str, **attrs) -> None:
    if not _graph.has_node(node_id):
        _graph.add_node(node_id, **attrs)
```

씬 간 시간 연결 엣지:

```python
# 이전 씬 → 현재 씬 순서 연결
prev = max(scene_nodes, key=lambda n: _graph.nodes[n].get("timestamp", ""))
_graph.add_edge(prev, scene_id, rel="scene_before_scene")
```

이 엣지 덕분에 "아까 봤던 카페"와 같은 시간 역방향 질의가 가능합니다.

BFS 탐색은 양방향(successor + predecessor)으로 수행됩니다:

```python
# find_subgraph_by_query() — max_hops BFS
adjacent = set(_graph.successors(n)) | set(_graph.predecessors(n))
```

predecessor 탐색을 포함하는 이유: `scene_before_scene` 엣지는 이전 씬 → 현재 씬 방향이므로, 과거 씬을 찾으려면 역방향(predecessor) 탐색이 필요합니다.

### 4.4 벡터 임베딩 (`vector_store.py`)

#### fastembed 선택 이유

| 항목 | sentence-transformers | fastembed |
|------|-----------------------|-----------|
| 런타임 | PyTorch (CPU 2GB+) | ONNX Runtime (100MB) |
| 한국어 지원 | 가능 | 가능 (동일 모델) |
| Lazy load | 별도 구현 필요 | 내장 |
| 데모 CPU 환경 | 느림 | 적합 |

사용 모델: `paraphrase-multilingual-MiniLM-L12-v2` (384-dim, ONNX)

```python
# vector_store.py — lazy load 패턴
_encoder: object = None   # None(미초기화) | TextEmbedding(로드됨) | False(실패)

def _get_encoder():
    global _encoder
    if _encoder is None:
        try:
            from fastembed import TextEmbedding
            _encoder = TextEmbedding(model_name=_MODEL_NAME)
        except Exception as exc:
            logger.warning("fastembed unavailable — using char-frequency fallback")
            _encoder = False
    return _encoder if _encoder is not False else None
```

fastembed 미설치 시 384-dim char-frequency fallback으로 자동 전환합니다.

#### Qdrant 차원 불일치 자동 복구

기존 64-dim 컬렉션이 존재할 경우 자동으로 삭제 후 384-dim으로 재생성합니다:

```python
if settings.qdrant_collection in _existing:
    info = _qdrant.get_collection(settings.qdrant_collection)
    existing_size = info.config.params.vectors.size
    if existing_size != _EMBEDDING_DIM:
        _qdrant.delete_collection(settings.qdrant_collection)
        _existing.discard(settings.qdrant_collection)
```

Qdrant 미연결 시 `_memory_store: list[tuple[list[float], str]]`에 fallback하고 코사인 유사도로 검색합니다.

### 4.5 통합 검색 (`retrieval.py`)

```python
def retrieve_context(query: str, top_k: int = 5) -> RetrievalResult:
    vector_results = vector_store.search(query, top_k=top_k)       # 의미 유사도
    graph_results  = graph_store.find_subgraph_by_query(query, max_hops=2, max_results=3)  # 구조 탐색
    combined = vector_results + graph_results
    return RetrievalResult(
        combined=combined[:top_k],
        vector_hits=vector_results[:top_k],
        graph_hits=graph_results[:top_k],
    )
```

`RetrievalResult`로 소스를 명시적으로 분리하여 향후 디버깅 및 소스별 가중치 조정이 가능합니다.

### 4.6 Optimized 모드에서만 저장/조회

```python
# planner.py
if ctx.mode == AgentMode.optimized:
    # GraphRAG 조회 (routing과 병렬 실행)
    retrieval_task = asyncio.create_task(
        asyncio.to_thread(retrieval.retrieve_context, ctx.user_request)
    )
    routing_result, routing_ms = await route_service(ctx, _ms)
    retrieval_result = await retrieval_task

    # 씬 저장 (context_memory 서비스 응답은 저장 제외 — recursive 오염 방지)
    if service_name != "context_memory":
        retrieval.store_context(request_id, ctx.user_request, service_name, response_text[:120])
```

**병렬 실행**: `retrieval_task`를 먼저 spawn하고 routing을 수행하므로, graph retrieval의 wall-clock 비용이 routing 뒤에 숨겨집니다. `graph_retrieval_ms`는 routing 시작부터 retrieval 완료까지의 실경과 시간을 기록합니다.

**context_memory 저장 제외**: context_memory 서비스가 graph에서 가져온 내용을 다시 graph에 저장하면, 다음 조회 시 "derived output"이 원본으로 취급되는 recursive 오염이 발생합니다. 이를 방지하기 위해 `context_memory` 응답은 저장에서 제외합니다.

**Baseline에서는 저장/조회 없음**: baseline 모드 요청이 graph에 쌓이면 optimized 모드의 검색 결과가 오염됩니다.

---

## 5. 공통 설계 — Sanitize 헬퍼 & 평가 지표

### 5.1 공통 Sanitize 헬퍼 (`policy.py`)

phrase replacement + footer enforcement 패턴을 여러 서비스가 각자 구현하는 중복을 제거합니다:

```python
# policy.py
def sanitize_response(
    text: str,
    replacements: list[tuple[str, str]],
    footer: str = "",
    footer_check: str = "",
) -> str:
    for unsafe, safe in replacements:
        text = text.replace(unsafe, safe)
    if footer and footer_check and footer_check not in text:
        text = text.rstrip() + footer
    return text
```

`label_reader.py`는 이 함수를 import해 재사용합니다:

```python
# label_reader.py
from app.agent.policy import sanitize_response

_SAFETY_FOOTER = "\n\n⚠️ 정확한 복용량 및 사용법은 반드시 의사 또는 약사에게 확인하세요."
_FOOTER_CHECK = "의사 또는 약사에게 확인"

def _sanitize_label_response(response: str) -> str:
    return sanitize_response(response, _UNSAFE_REPLACEMENTS, _SAFETY_FOOTER, _FOOTER_CHECK)
```

`safety_alert.py`의 `sanitize_safety_response()`는 regex 기반(대소문자 불변)으로 별도 유지합니다:

```python
def sanitize_safety_response(text: str) -> str:
    for dangerous, replacement in _DANGEROUS_PHRASES:
        text = re.sub(re.escape(dangerous), replacement, text, flags=re.IGNORECASE)
    return text
```

### 5.2 평가 지표 (`planner.py`, `logger.py`, `metrics.py`)

요청마다 아래 항목을 JSONL에 기록합니다:

```json
{
  "request_id": "uuid",
  "mode": "optimized",
  "selected_service": "safety_alert",
  "router_confidence": 0.84,
  "original_frame_count": 180,
  "selected_keyframe_count": 6,
  "vlm_call_count": 1,
  "retrieved_graph_nodes": 8,
  "token_count": 312,
  "image_payload_bytes": 2048,
  "cloud_called": true,
  "fallback_reason": null,
  "failure_type": null,
  "latency_ms": {
    "frame_sampling": 90,
    "graph_retrieval": 35,
    "routing": 20,
    "vlm": 1250,
    "total": 1410
  }
}
```

`vlm_call_count`는 semantic fallback이 발동된 경우 2로 기록됩니다. `image_payload_bytes`는 실제 VLM에 전달된 바이트를 서비스 usage dict의 `image_sent` 플래그를 기반으로 실측합니다.

---

## 6. Baseline vs Optimized 비교 흐름

```
입력 (이미지/영상 + user_request + GPS + devices)
           │
           ▼
    ┌─────────────┐
    │ frame_sampler│ → 영상 → 초당 N프레임 추출
    └─────────────┘
           │
    ┌──────┴──────┐
    │             │
Baseline      Optimized
    │             │
scene-change   scene-change +
only           query relevance
    │             │
    │        semantic_extractor
    │        brightness/motion/color/OCR
    │             │
    │        build_semantic_prompt()
    │        → text-only 입력 생성
    │             │
    │     ┌───────┴───────┐
    │     │ retrieval      │  (병렬)
    │     │ graph + vector │
    │     └───────────────┘
    │             │
    └──────┬──────┘
           │
       router.py
       rule-based → confidence ≥ threshold
                       (미달 시 LLM fallback)
           │
    ┌──────┴──────┐
    │             │
Baseline      Optimized
    │             │
run_vlm_service  dispatch()
(raw 이미지)    → run_semantic_service()
                  text-only VLM
                  (응답 <10자 → vision fallback)
                  postprocess=sanitize_*
           │
    ┌──────┴──────┐
    │             │
    │        graph_store.add_scene()
    │        vector_store.upsert()
    │        (optimized만)
           │
      EvaluationLog
      → JSONL 기록
           │
      AgentResponse
      (metrics 포함)
```

---

## 부록 — 파일별 역할 요약

| 파일 | 전략 | 역할 |
|------|------|------|
| `constants.py` | 01 | 키워드 카테고리 단일 정의 (router/keyframe 공유) |
| `keyframe_selector.py` | 01 | scene-change + query relevance 복합 점수 |
| `frame_sampler.py` | 01 | 영상 → 목표 FPS 프레임 추출 |
| `semantic_extractor.py` | 02 | OpenCV → SemanticPayload → text prompt |
| `common.py` | 02 | `dispatch()` / `run_semantic_service()` / `run_vlm_service()` |
| `scene_assistant.py` | 02 | dispatch() 적용 |
| `safety_alert.py` | 02 | dispatch() + sanitize_safety_response |
| `navigation.py` | 02 | dispatch() + GPS + graph_context 주입 |
| `label_reader.py` | 02 | OCR-path text-only, policy.sanitize_response() 재사용 |
| `graph_store.py` | 03 | NetworkX Temporal Scene Graph, BFS 양방향 탐색 |
| `vector_store.py` | 03 | fastembed 384-dim ONNX + Qdrant, fallback 내장 |
| `retrieval.py` | 03 | 벡터+그래프 통합 검색, RetrievalResult 소스 분리 |
| `policy.py` | 공통 | sanitize_response() 공통 헬퍼 |
| `planner.py` | 전체 | 파이프라인 오케스트레이터, 병렬 retrieval, 지표 측정 |
