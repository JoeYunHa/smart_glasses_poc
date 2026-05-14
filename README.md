# Smart Glasses Physical AI Agent PoC

## 1. Objective

This PoC demonstrates a smart-glasses-style Physical AI Agent that receives image/video, GPS, and nearby-device context, then routes the request to an appropriate service and returns voice/action outputs.

## 2. PoC Scope

### Implemented

- Image/video input
- GPS mock input
- Nearby device mock input
- Lightweight service routing
- GraphRAG-style context memory
- Mock action executor
- Latency and VLM call logging

### Not Implemented

- Real smart glasses hardware integration
- Real IoT device integration
- Real-time continuous video streaming
- Production-level authentication
- Safety-critical autonomous decision-making

## 3. Tech Stack

### Frontend

- React
- Vite
- TypeScript

### Backend

- Python
- FastAPI
- OpenCV
- NetworkX
- Qdrant

## 4. Services

1. Scene Assistant
2. Navigation Assistant
3. Device Control Agent
4. Safety Alert
5. Context Memory Agent

## 5. Optimization Strategy

- Keyframe selection
- Semantic compression
- GraphRAG-based context reuse
- Lightweight router
- LLM/VLM fallback
- Latency and call-count logging

## 6. How to Run

### Frontend

```bash
pnpm run dev:web
```

### Structure

Root monorepo
├─ React + Vite frontend
├─ FastAPI backend
├─ data mock
├─ docs
└─ README + demo scenarios

### Backend
apps/api/
├─ app/
│  ├─ main.py
│  ├─ api/
│  │  ├─ context.py
│  │  ├─ agent.py
│  │  ├─ graph.py
│  │  └─ logs.py
│  ├─ schemas/
│  │  ├─ context.py
│  │  ├─ agent.py
│  │  └─ log.py
│  ├─ perception/
│  │  ├─ frame_sampler.py
│  │  ├─ keyframe_selector.py
│  │  └─ image_preprocessor.py
│  ├─ agent/
│  │  ├─ router.py
│  │  ├─ policy.py
│  │  └─ planner.py
│  ├─ services/
│  │  ├─ scene_assistant.py
│  │  ├─ navigation.py
│  │  ├─ device_control.py
│  │  ├─ safety_alert.py
│  │  └─ context_memory.py
│  ├─ memory/
│  │  ├─ graph_store.py
│  │  ├─ vector_store.py
│  │  └─ retrieval.py
│  ├─ actions/
│  │  ├─ executor.py
│  │  └─ device_registry.py
│  └─ evaluation/
│     ├─ logger.py
│     └─ metrics.py
├─ tests/
├─ pyproject.toml
└─ README.md

### Frontend
apps/web/src/
├─ api/
│  └─ agentApi.ts
├─ components/
│  ├─ InputPanel.tsx
│  ├─ AgentDecisionPanel.tsx
│  ├─ OutputPanel.tsx
│  ├─ PerformancePanel.tsx
│  └─ GraphContextPanel.tsx
├─ pages/
│  └─ PocDashboard.tsx
├─ types/
│  └─ agent.ts
├─ App.tsx
└─ main.tsx
