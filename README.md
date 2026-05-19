# Smart Glasses Physical AI Agent PoC

스마트 안경형 Physical AI Agent의 핵심 파이프라인 구조를 검증하는 PoC입니다.
이미지/영상, GPS, 주변 기기 정보를 입력받아 Agent가 상황을 판단하고 적절한 서비스로 라우팅한 뒤,
voice 또는 action output을 생성합니다.

단순 VLM 호출 데모가 아니라 Keyframe Selection, Semantic Compression, GraphRAG Context Memory,
Lightweight Router, Action Guardrail, Latency Logging을 결합해
**기능 개선과 성능 개선 가능성을 측정 가능한 형태로 증명**하는 것이 목표입니다.

---

## 목차

1. [아키텍처](#아키텍처)
2. [서비스](#서비스)
3. [최적화 전략](#최적화-전략)
4. [기술 스택](#기술-스택)
5. [디렉토리 구조](#디렉토리-구조)
6. [실행 방법](#실행-방법)
7. [환경 변수](#환경-변수)
8. [API 엔드포인트](#api-엔드포인트)
9. [평가 지표](#평가-지표)
10. [PoC 범위](#poc-범위)

---

## 아키텍처

### 논리 계층

```
입력 계층        이미지/영상/GPS/주변 기기 (웹 UI에서 mock 입력)
     ↓
API 계층         FastAPI multipart 수신 → ContextRequest 파싱
     ↓
파이프라인 계층   planner.py — 전체 파이프라인 조율
     ↓
Perception 계층  frame_sampler → keyframe_selector → semantic_extractor
     ↓
Retrieval 계층   GraphRAG retrieval (optimized 모드, routing과 병렬 실행)
     ↓
Routing 계층     rule-based router + VLM fallback
     ↓
서비스 계층      6개 서비스 중 1개 실행
     ↓
Action 계층      device capability 검증 → mock 실행 (device_control만)
     ↓
Memory 계층      graph/vector 저장 (optimized 모드만)
     ↓
Evaluation 계층  per-request JSONL 로그 기록
     ↓
프론트엔드 계층  AgentDecisionPanel / OutputPanel / PerformancePanel / GraphContextPanel
```

### 핵심 파이프라인 흐름

```
요청 수신
  → run_perception()              # frame sampling + keyframe selection + semantic extraction
  → [optimized] asyncio.create_task(retrieve_context())  # routing과 병렬 실행
  → route_service()               # rule-based → VLM fallback
  → await retrieval_task          # graph_context 수집
  → graph_context → semantic_prompt 주입
  → service_fn()                  # 선택된 서비스 실행
  → [optimized] graph/vector 저장 (context_memory 응답은 제외)
  → EvaluationLog 기록
  → AgentResponse 반환
```

optimized 모드에서 GraphRAG retrieval과 routing이 `asyncio.create_task`로 동시에 실행되어
retrieval의 wall-clock 비용이 전체 latency에 추가되지 않습니다.

---

## 서비스

| 서비스 | 역할 | 입력 | 출력 |
|---|---|---|---|
| **Scene Assistant** | 장면 설명, 객체 인식 | Image/Video | Voice |
| **Navigation** | 위치 기반 길 안내 | GPS, Graph Memory | Voice |
| **Device Control** | 주변 기기 인식 및 제어 | Devices, Intent | Action |
| **Safety Alert** | 위험 감지 및 경고 | Image/Video, GPS | Voice Alert |
| **Context Memory** | 과거 장면/장소 기억 조회 | GraphRAG | Voice |
| **Label Reader** | 의약품/제품 라벨 OCR + 구조화 | Image (label) | Voice |

### 서비스 라우팅 confidence 기준

| 서비스 | 기본 confidence |
|---|---|
| safety_alert | 0.90 |
| label_reader | 0.88 |
| device_control | 0.85 |
| context_memory | 0.85 |
| navigation | 0.82 |
| scene_assistant | 0.70 (fallback) |

confidence < 0.35 시 VLM 분류 fallback 발동.

---

## 최적화 전략

### Strategy 01 — Query-aware Keyframe Selection

영상을 모두 처리하지 않고 의미 있는 프레임만 추출합니다.

- **frame sampling**: optimized 2fps / baseline 전 프레임
- **keyframe selection**: scene-change score(0.6) + query relevance score(0.4) 복합 scoring
  - safety/navigation 요청 → 밝은 프레임(야외) 선호
  - device_control 요청 → 어두운 프레임(실내) 선호
  - label_reader 요청 → 밝기 bias 없음
- VLM 호출 없이 OpenCV만으로 계산

측정 지표: `original_frame_count`, `selected_keyframe_count`, frame reduction ratio

### Strategy 02 — Semantic Perception Layer

raw 이미지 base64 대신 OpenCV 특징을 텍스트 프롬프트로 변환해 전송합니다.

`SemanticPayload` 필드:
- `scene_brightness` (0–1, 실내/야외 판별)
- `motion_level` (0–1, 프레임 간 diff)
- `dominant_colors` (red/yellow/green/blue HSV 마스크)
- `ocr_text` (pytesseract sparse OCR, 설치 시 활성화)
- `label_ocr_raw` (label 모드 전용 enhanced OCR)
- `text_density` (텍스트 픽셀 비율, label 판별)

Label Reader에서 OCR 텍스트가 추출되면 image_payload_bytes ≈ 0.
응답 길이 < 10자일 때 image_b64 포함 vision fallback 자동 발동.

### Strategy 03 — Full GraphRAG + Subgraph Retrieval

과거 context를 구조화된 메모리로 저장하고 재사용합니다.

**Graph (NetworkX)**
- 노드: Scene, Object, Location, Device, UserIntent, Action, Risk, Time
- 엣지: scene_contains_object, scene_at_location, device_supports_action, scene_before_scene(시간 연결)
- `_ensure_node()`로 중복 노드 방지
- BFS 양방향 탐색으로 시간 연결 검색

**Vector (Qdrant + fastembed)**
- `paraphrase-multilingual-MiniLM-L12-v2` (384-dim ONNX, 한국어+영어, PyTorch 불필요)
- Qdrant 연결 불가 시 in-memory cosine 유사도 fallback
- Qdrant collection dim 불일치 시 자동 재생성

context_memory 서비스 응답은 graph에 저장하지 않습니다 (recursive 오염 방지).

### image_payload_bytes 측정 로직

| 경로 | payload_bytes |
|---|---|
| semantic text-only (no fallback) | perception 텍스트 bytes |
| semantic + vision fallback (vlm_calls=2) | 텍스트 bytes + image_b64 bytes |
| baseline / OCR 없는 direct vision | image_b64 bytes |

---

## 기술 스택

### Backend (`apps/api`)

| 항목 | 내용 |
|---|---|
| 언어 | Python 3.11+ |
| 프레임워크 | FastAPI + uvicorn |
| VLM | `gpt-4o` (vision) via OpenAI |
| LLM | `gpt-4o-mini` (text-only) via OpenAI |
| 영상 처리 | OpenCV (`opencv-python`) |
| Scene Graph | NetworkX |
| Vector DB | Qdrant (로컬 Docker) |
| Embedding | fastembed `paraphrase-multilingual-MiniLM-L12-v2` (ONNX) |
| 설정 관리 | pydantic-settings |
| 개발 도구 | ruff, mypy, pytest, pytest-asyncio |

### Frontend (`apps/web`)

| 항목 | 내용 |
|---|---|
| 언어 | TypeScript 6 |
| 프레임워크 | React 19 + Vite 8 |
| UI | Tailwind CSS + shadcn/ui |
| TTS | Web Speech API (`useTTS` hook) |

### 패키지 매니저

- Frontend: pnpm (workspace)
- Backend: uv

---

## 디렉토리 구조

```
smart-glasses-agent-poc/
├── apps/
│   ├── api/                              # FastAPI 백엔드
│   │   └── app/
│   │       ├── main.py                   # FastAPI 앱, 라우터, lifespan
│   │       ├── config.py                 # pydantic-settings 환경변수
│   │       ├── constants.py              # SERVICE_CATEGORY_KEYWORDS (공유)
│   │       ├── llm_client.py             # OpenAI AsyncClient 어댑터 (VLM/LLM 분기)
│   │       ├── api/                      # REST 엔드포인트
│   │       │   ├── agent.py              # POST /api/agent/run
│   │       │   ├── graph.py              # GET /api/graph/*
│   │       │   ├── context.py            # GET /api/context/summary
│   │       │   └── logs.py               # GET /api/logs/metrics
│   │       ├── agent/                    # Agent 코어
│   │       │   ├── planner.py            # 파이프라인 오케스트레이터
│   │       │   ├── pipeline_support.py   # run_perception, route_service
│   │       │   ├── router.py             # rule-based router
│   │       │   ├── policy.py             # safety guardrail, sanitize 헬퍼
│   │       │   └── service_registry.py   # 6개 서비스 디스패처
│   │       ├── perception/               # 영상/이미지 전처리
│   │       │   ├── frame_sampler.py      # 영상 → fps 기반 프레임 추출
│   │       │   ├── keyframe_selector.py  # scene-change + query relevance 선택
│   │       │   ├── image_preprocessor.py # 리사이즈(512px), JPEG 압축, base64
│   │       │   └── semantic_extractor.py # SemanticPayload, build_semantic_prompt
│   │       ├── services/                 # 6개 서비스 모듈
│   │       │   ├── common.py             # dispatch, run_vlm_service, run_semantic_service
│   │       │   ├── scene_assistant.py
│   │       │   ├── navigation.py
│   │       │   ├── device_control.py
│   │       │   ├── safety_alert.py
│   │       │   ├── context_memory.py
│   │       │   └── label_reader.py       # 의약품/제품 라벨 OCR 특화
│   │       ├── memory/                   # GraphRAG / Context Memory
│   │       │   ├── graph_store.py        # NetworkX temporal scene graph
│   │       │   ├── vector_store.py       # fastembed + Qdrant
│   │       │   └── retrieval.py          # hybrid 검색 (graph + vector)
│   │       ├── actions/                  # 기기 제어
│   │       │   ├── device_registry.py    # 기기 capability 정의
│   │       │   └── executor.py           # mock action 실행 + policy 체크
│   │       ├── evaluation/               # 평가 로그
│   │       │   ├── logger.py             # per-request JSONL 기록
│   │       │   └── metrics.py            # baseline vs optimized 집계
│   │       ├── schemas/                  # Pydantic 스키마
│   │       │   ├── context.py            # ContextRequest, AgentMode
│   │       │   ├── agent.py              # AgentResponse, LatencyBreakdown
│   │       │   └── log.py                # EvaluationLog
│   │       └── demo/
│   │           └── seed.py               # 시동 시 데모 context 주입
│   └── web/                              # React 프론트엔드
│       └── src/
│           ├── api/agentApi.ts
│           ├── components/
│           │   ├── InputPanel.tsx         # 시나리오 선택, 모드 토글, 파일 업로드
│           │   ├── AgentDecisionPanel.tsx # 서비스 선택, confidence, latency trace
│           │   ├── OutputPanel.tsx        # 응답 텍스트, action 결과, TTS
│           │   ├── PerformancePanel.tsx   # payload/latency 비교 지표
│           │   └── GraphContextPanel.tsx  # GraphRAG 노드 목록
│           ├── pages/PocDashboard.tsx
│           ├── hooks/useTTS.ts            # Web Speech API TTS
│           └── types/agent.ts
├── data/
│   ├── logs/                             # eval.jsonl (요청별 평가 로그)
│   ├── mock_devices.json                 # 4개 기기 mock
│   ├── scenarios.json                    # 3개 시연 시나리오
│   ├── sample_images/
│   └── sample_videos/
├── docs/
│   ├── architecture.md
│   ├── demo_scenarios.md
│   ├── optimization_strategy.md
│   ├── product_brief.md
│   └── requirements_spec.md
├── package.json                          # pnpm 루트 스크립트
└── pnpm-workspace.yaml
```

---

## 실행 방법

### 사전 요구사항

- Python 3.11+
- Node.js + pnpm
- uv (`pip install uv`)
- Docker (Qdrant 실행용)
- OpenAI API 키 ([platform.openai.com](https://platform.openai.com))
- (선택) Tesseract OCR — Label Reader OCR 활성화용

### 1. 환경 변수 설정

프로젝트 루트 또는 `apps/api/` 디렉토리에 `.env` 파일을 생성합니다.

```env
OPENAI_API_KEY=sk-...
```

### 2. Qdrant 실행

```bash
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

Qdrant 없이도 동작합니다 (in-memory vector fallback 자동 사용).

### 3. 백엔드 실행

```bash
# 개발 모드 (hot reload)
pnpm run dev:api

# 프로덕션 모드
pnpm run start:api
```

백엔드 단독 실행:

```bash
cd apps/api
uv run fastapi dev app/main.py
```

서버 시작 시 `seed_demo_memory()`가 자동으로 데모 context를 주입합니다.

백엔드: `http://localhost:8000`
Swagger UI: `http://localhost:8000/docs`

### 4. 프론트엔드 실행

```bash
pnpm install
pnpm run dev:web
```

프론트엔드: `http://localhost:5173`

### 5. (선택) Tesseract OCR 설치

설치 시 Label Reader의 OCR 경로가 활성화됩니다.

```bash
# Ubuntu/Debian
apt install tesseract-ocr tesseract-ocr-kor

# macOS
brew install tesseract tesseract-lang
```

Windows: [공식 installer](https://github.com/UB-Mannheim/tesseract/wiki) 설치 후 PATH 추가.

미설치 시에도 vision fallback으로 정상 동작합니다.

---

## 환경 변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `OPENAI_API_KEY` | (필수) | OpenAI API 인증 키 |
| `OPENAI_VISION_MODEL` | `gpt-4o` | Vision 모델 |
| `OPENAI_TEXT_MODEL` | `gpt-4o-mini` | Text-only 모델 |
| `QDRANT_HOST` | `localhost` | Qdrant 호스트 |
| `QDRANT_PORT` | `6333` | Qdrant 포트 |
| `QDRANT_COLLECTION` | `scene_contexts` | 컬렉션 이름 |
| `ROUTER_CONFIDENCE_THRESHOLD` | `0.35` | VLM fallback 발동 임계값 |
| `MAX_KEYFRAMES` | `8` | 영상당 최대 keyframe 수 |
| `LOG_DIR` | `data/logs` | 평가 로그 디렉토리 |

`.env` 파일은 `apps/api/.env` 또는 프로젝트 루트 `.env` 모두 지원합니다.

---

## API 엔드포인트

### 핵심 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/api/agent/run` | Agent 파이프라인 실행 (multipart: image/video + context JSON) |
| `GET` | `/api/logs/metrics` | baseline vs optimized 집계 지표 조회 |
| `GET` | `/api/graph/nodes` | 저장된 graph 노드 목록 |
| `GET` | `/api/graph/query` | 쿼리 기반 subgraph 검색 |
| `GET` | `/api/graph/size` | graph 노드/엣지 수 |
| `GET` | `/api/context/summary` | graph 요약 |
| `GET` | `/api/logs/` | 전체 로그 조회 |
| `POST` | `/api/demo/reset` | 메모리 초기화 + 로그 삭제 + 데모 context 재주입 |
| `GET` | `/health` | 헬스 체크 |

### 요청 예시 (`/api/agent/run`)

```bash
curl -X POST http://localhost:8000/api/agent/run \
  -F 'context_json={"user_request":"지금 건너도 돼?","mode":"optimized","gps":{"location_type":"crosswalk","latitude":37.5,"longitude":127.0},"nearby_devices":[]}' \
  -F 'image=@crosswalk.jpg'
```

### 응답 필드

```json
{
  "request_id": "uuid",
  "selected_service": "safety_alert",
  "router_confidence": 0.9,
  "vlm_used": false,
  "response_text": "...",
  "action_result": null,
  "original_frame_count": 1,
  "selected_keyframe_count": 1,
  "retrieved_graph_nodes": 3,
  "latency_ms": {
    "frame_sampling": 12,
    "keyframe_selection": 0,
    "graph_retrieval": 28,
    "routing": 5,
    "vlm": 0,
    "total": 48
  },
  "mode": "optimized"
}
```

---

## 평가 지표

요청마다 `data/logs/eval.jsonl`에 기록됩니다.

| 지표 | 설명 |
|---|---|
| `original_frame_count` | 샘플링 전 전체 프레임 수 |
| `selected_keyframe_count` | keyframe selection 후 프레임 수 |
| `vlm_call_count` | 실제 VLM/LLM 호출 횟수 (semantic fallback 포함) |
| `retrieved_graph_nodes` | GraphRAG에서 검색된 노드 수 |
| `token_count` | routing + service 합산 토큰 수 |
| `image_payload_bytes` | 실제 클라우드로 전송된 payload bytes |
| `latency_ms` | 구간별 latency (frame_sampling / keyframe_selection / graph_retrieval / routing / vlm / total) |
| `cloud_called` | 외부 VLM API 호출 여부 |
| `fallback_reason` | none / low_confidence / parse_error / vlm_timeout |
| `failure_type` | none / routing_error / action_error / vlm_error |

### Baseline vs Optimized 비교

| 항목 | Baseline | Optimized |
|---|---|---|
| 프레임 처리 | 전 프레임 (fps 제한 없음) | 2fps + query-aware keyframe selection |
| VLM 입력 | raw image_b64 | semantic text prompt → vision fallback |
| Context Memory | 없음 | GraphRAG graph + vector retrieval |
| Memory 저장 | 없음 | graph/vector 저장 |
| 동시 실행 | 순차 routing | routing + retrieval 병렬 실행 |

---

## 시연 시나리오

### Demo 1 — Safety Alert

```
입력: 횡단보도 이미지 + GPS(road) + "지금 건너도 돼?"
포인트: 안전 확정 응답 차단, 보수적 안내 생성
```

### Demo 2 — Device Control

```
입력: 방 이미지 + nearby_devices(smart_light, speaker) + "저거 꺼줘"
포인트: capability 조회 → guardrail 체크 → mock 실행
```

### Demo 3 — Context Memory (GraphRAG)

```
Step 1: 카페 간판 이미지 + GPS → Scene graph 저장
Step 2: "아까 본 카페 쪽으로 가려면?" → graph 검색 → Navigation 라우팅
포인트: VLM 재호출 없이 graph memory로 응답
```

매 시연 전 `/api/demo/reset`을 호출하면 메모리와 로그가 초기화되고 데모 context가 재주입됩니다.

---

## PoC 범위

### 구현 완료

- 이미지/영상 업로드, GPS mock, 주변 기기 mock 입력
- 2fps frame sampling + query-aware keyframe selection (scene-change 0.6 + query relevance 0.4)
- OpenCV 기반 SemanticPayload 추출 (brightness / motion / color / OCR)
- 텍스트 전용 VLM 경로 + vision fallback 자동 발동
- Label Reader enhanced OCR (adaptive threshold + denoising + PSM 6/3 비교)
- rule-based router (한국어/영어 키워드) + VLM classification fallback
- 6개 서비스 (Scene Assistant / Navigation / Device Control / Safety Alert / Context Memory / Label Reader)
- Safety guardrail: 확정형 안전 표현 차단 (regex sanitizer)
- Action guardrail: device capability 조회 → risk check → mock 실행
- NetworkX temporal scene graph (Object/Action/Risk/Time 노드, BFS 양방향 탐색)
- fastembed 384-dim 다국어 embedding + Qdrant (in-memory fallback 포함)
- asyncio.create_task 병렬 retrieval + routing (optimized 모드)
- per-request JSONL 평가 로그 (6구간 latency breakdown)
- baseline vs optimized 집계 API
- 데모 리셋 엔드포인트 (`/api/demo/reset`)

### 의도적 제외 범위

- 실제 스마트 안경 하드웨어 및 센서 스트리밍
- 실제 IoT 기기 제어 프로토콜
- Edge-Cloud hybrid 분산 실행
- Embedding 기반 frame-query 유사도 keyframe selection
- 프로덕션 인증/인가 및 멀티 세션 격리
- OpenAI SDK 외 provider 지원 (현재 OpenAI AsyncClient 고정)
