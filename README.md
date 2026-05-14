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