"""Demo seed data loader.

Pre-loads a realistic prior-visit scene into graph_store and vector_store so
Demo 3 (Context Memory) works immediately without first running Step 1 manually.

Call seed_demo_memory() once at API startup via the FastAPI lifespan hook.
Call reset_demo_memory() from the /api/demo/reset endpoint to wipe and re-seed.
"""

from app.memory import graph_store, retrieval, vector_store
from app.schemas.context import ContextRequest, GpsContext

_SEED_SCENES = [
    {
        "request_id": "seed-cafe-visit-001",
        "user_request": "이게 무슨 카페야? 간판 읽어줘",
        "service_name": "scene_assistant",
        "response_summary": "북촌 카페 간판 발견. '북촌커피' 라고 적혀 있음. 삼청동 골목 안쪽 위치.",
        "gps": GpsContext(
            latitude=37.5712,
            longitude=126.9823,
            location_type="street",
            place_name="삼청동 북촌커피 앞",
        ),
        "objects": ["sign", "building"],
        "actions": [],
        "risks": [],
    },
    {
        "request_id": "seed-cafe-visit-002",
        "user_request": "이 카페 영업시간이 어떻게 돼?",
        "service_name": "scene_assistant",
        "response_summary": "북촌커피 영업시간 09:00~21:00. 주말 동일. 삼청동 골목 입구 우측.",
        "gps": GpsContext(
            latitude=37.5712,
            longitude=126.9823,
            location_type="street",
            place_name="삼청동 북촌커피 앞",
        ),
        "objects": ["sign", "building"],
        "actions": [],
        "risks": [],
    },
]


def seed_demo_memory() -> None:
    """Inject seed scenes into graph and vector stores."""
    for scene in _SEED_SCENES:
        ctx = ContextRequest(
            user_request=scene["user_request"],
            gps=scene["gps"],
            nearby_devices=[],
            mode="optimized",  # type: ignore[arg-type]
        )
        graph_store.add_scene(
            scene["request_id"],
            ctx,
            scene["service_name"],
            objects=scene["objects"],
            actions=scene["actions"],
            risks=scene["risks"],
        )
        retrieval.store_context(
            scene["request_id"],
            scene["user_request"],
            scene["service_name"],
            scene["response_summary"],
        )


def reset_demo_memory() -> None:
    """Clear all in-memory graph/vector data and re-seed for a fresh demo run."""
    graph_store.reset_graph()
    vector_store.reset_memory_store()
    seed_demo_memory()
