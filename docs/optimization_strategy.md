# Optimization Strategy

Smart Glasses Agent PoC의 핵심 최적화 전략 3가지와 각 전략의 구현 방식, 성능 비교 포인트를 정리합니다.

---

## Strategy 01 — Query-aware Keyframe Selection

### 문제
영상 전체 프레임을 VLM에 전송하면 불필요한 토큰 비용과 지연이 발생한다.

### 구현
`perception/keyframe_selector.py`에서 두 점수를 결합해 keyframe을 선택한다.

| 점수 | 가중치 | 계산 방법 |
|---|---|---|
| Scene-change score | 0.6 | 인접 프레임 간 픽셀 차이 (`cv2.absdiff`) |
| Query relevance score | 0.4 | 요청 키워드 카테고리 × 밝기 휴리스틱 |

**Temporal coverage 보장**: 전체 구간을 `max_keyframes` 등분 후 각 구간에서 최고 점수 프레임을 1개씩 선택. 점수가 한 구간에 몰려도 전체 커버리지를 유지한다.

**카테고리 키워드 단일 정의**: `constants.SERVICE_CATEGORY_KEYWORDS`에서 키워드를 공유해 router와 keyframe_selector 간 드리프트를 방지한다.

### 측정 지표
- `original_frame_count` vs `selected_keyframe_count`
- `frame_reduction_ratio = 1 - selected / original`
- Baseline: scene-change-only, fps_target=None (전체 프레임)
- Optimized: query-aware + fps_target=2 (2fps 다운샘플)

---

## Strategy 02 — Semantic Perception Layer

### 문제
이미지 전체를 base64로 VLM에 전송하면 전송량이 크고, 단순 밝기/색상 판단도 VLM을 거쳐야 한다.

### 구현
`perception/semantic_extractor.py`에서 OpenCV로 특징을 추출해 텍스트 프롬프트로 변환한다.

| 추출 항목 | 방법 |
|---|---|
| Brightness | 그레이스케일 평균 |
| Motion level | 인접 프레임 픽셀 차 평균 |
| Dominant colors | HSV 범위 마스킹 (red/yellow/green/blue) |
| OCR text | pytesseract (미설치 시 생략) |

**dispatch() 헬퍼**: `semantic_prompt` 존재 시 text-only VLM 호출. 응답이 10자 미만이면 vision fallback 자동 발동. `semantic_prompt`가 50자 미만이면 첫 번째 호출 낭비를 방지하기 위해 직접 vision으로 단락.

**실제 전송 바이트 계산**: `call_vlm()`이 호출 시점 `prompt_bytes`와 `image_bytes`를 usage dict에 기록. Planner가 이를 합산해 `image_payload_bytes`를 정확히 측정한다.

### 측정 지표
- `image_payload_bytes` (실제 전송 바이트)
- `vlm_call_count` (semantic fallback 2회 포함 정확 집계)
- `cloud_called` (VLM 호출 여부)

---

## Strategy 03 — GraphRAG Context Memory

### 문제
매 요청마다 VLM이 과거 context를 모른다. "아까 본 카페"처럼 과거 장면을 참조하는 요청을 처리할 수 없다.

### 구현
두 저장소를 조합한 hybrid retrieval을 사용한다.

| 저장소 | 구현 | 역할 |
|---|---|---|
| NetworkX DiGraph | `memory/graph_store.py` | Temporal scene graph (Object/Action/Risk/Time 노드) |
| Qdrant + fastembed | `memory/vector_store.py` | 384-dim 다국어 임베딩 cosine 유사도 검색 |

**Quota-based merge**: vector 검색 결과가 graph hits를 밀어내지 않도록 graph에 최소 2슬롯을 예약한다.
```
graph_quota = min(len(graph_results), 2)
vector_quota = max(0, top_k - graph_quota)
combined = vector_results[:vector_quota] + graph_results[:graph_quota]
```

**동시성 보호**: `graph_store._lock (threading.RLock)`으로 `asyncio.to_thread` 기반 retrieval과 메인 루프의 write를 직렬화한다.

**device_control 최적화**: rule-based 라우터로 사전 판별 후 device_control이 확정되면 retrieval task를 아예 생성하지 않는다.

**graph_context 주입 위치**: Planner가 `semantic_prompt`에 1회만 주입. 서비스 레이어는 baseline prompt에만 별도 주입해 이중 주입을 방지한다.

### 측정 지표
- `retrieved_graph_nodes` (검색된 컨텍스트 노드 수)
- `graph_retrieval_ms` (retrieval 지연)
- Context Memory 시나리오: retrieval 없는 baseline vs. retrieval 있는 optimized 응답 품질 비교

---

## Baseline vs Optimized 비교 기준

| 항목 | Baseline | Optimized |
|---|---|---|
| FPS 다운샘플 | 없음 (전체 프레임) | 2fps |
| Keyframe 선택 | scene-change-only | query-aware + temporal coverage |
| 프롬프트 | raw image → vision VLM | semantic text → text VLM (vision fallback) |
| GraphRAG | 사용 안 함 | 사용 (vector + graph hybrid) |
| Memory 저장 | 사용 안 함 | optimized 요청만 저장 (오염 방지) |

---

## 알려진 한계 및 향후 개선 방향

| 항목 | 현재 상태 | 개선 방향 |
|---|---|---|
| Query relevance score | 밝기 휴리스틱 | frame-query embedding 유사도 (vector_store encoder 재사용) |
| OCR | pytesseract (미설치 시 생략) | 전용 OCR 마이크로서비스 |
| 전역 그래프 | 프로세스 공유 | 세션별 격리 + TTL 만료 |
| VLM provider | OpenAI (gpt-4o / gpt-4o-mini) | Edge 모델 hybrid 또는 on-device fallback |
