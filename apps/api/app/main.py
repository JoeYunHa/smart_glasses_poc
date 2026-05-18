from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agent, context, graph, logs
from app.demo.seed import reset_demo_memory, seed_demo_memory
from app.evaluation.logger import clear_logs


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_demo_memory()
    yield


app = FastAPI(
    title="Smart Glasses Physical AI Agent",
    version="0.1.0",
    description=(
        "PoC API for a smart-glasses-style physical AI agent with perception, "
        "routing, action execution, and evaluation logging."
    ),
    lifespan=lifespan,
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


@app.post("/api/demo/reset", tags=["demo"])
async def demo_reset():
    """메모리 스토어 초기화 + 로그 삭제 + 데모 context 재시드. 매 시연 전 호출."""
    deleted = clear_logs()
    reset_demo_memory()
    return {"status": "ok", "deleted_log_records": deleted, "message": "Logs cleared and demo memory re-seeded."}
