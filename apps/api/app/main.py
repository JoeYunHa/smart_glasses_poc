from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agent, context, graph, logs

app = FastAPI(
    title="Smart Glasses Physical AI Agent",
    version="0.1.0",
    description="PoC — 입력 → 전처리 → 판단 → 행동 → 로그 → 개선 파이프라인",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(context.router, prefix="/api/context", tags=["context"])
app.include_router(agent.router, prefix="/api/agent", tags=["agent"])
app.include_router(graph.router, prefix="/api/graph", tags=["graph"])
app.include_router(logs.router, prefix="/api/logs", tags=["logs"])


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "version": app.version}
