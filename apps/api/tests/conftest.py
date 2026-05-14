"""Shared pytest fixtures for integration tests."""

from __future__ import annotations

import tempfile

import pytest
from fastapi.testclient import TestClient

from app import config
from app.evaluation import logger as eval_logger
from app.main import app
from app.memory import graph_store, vector_store


@pytest.fixture(scope="session")
def base_context() -> dict:
    return {
        "user_request": "What is happening around me right now?",
        "gps": {
            "latitude": 37.5665,
            "longitude": 126.9780,
            "location_type": "street",
            "place_name": "Seoul City Hall",
        },
        "nearby_devices": [],
        "mode": "optimized",
    }


@pytest.fixture(scope="session")
def device_context() -> dict:
    return {
        "user_request": "Turn off the light",
        "gps": {
            "latitude": 37.5665,
            "longitude": 126.9780,
            "location_type": "indoor",
            "place_name": "Office",
        },
        "nearby_devices": [
            {
                "device_id": "light-001",
                "name": "Living Room Light",
                "type": "smart_light",
                "supported_actions": ["turn_on", "turn_off", "set_brightness"],
                "risk_level": "low",
                "requires_confirmation": False,
                "state": {"power": "on", "brightness": 80},
            }
        ],
        "mode": "optimized",
    }


@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setattr(config.settings, "log_dir", tmpdir)
        eval_logger._log_path = None
        graph_store.reset_graph()
        vector_store.reset_memory_store()
        yield
        eval_logger._log_path = None
        graph_store.reset_graph()
        vector_store.reset_memory_store()


FAKE_USAGE = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}


@pytest.fixture(autouse=True)
def stub_vlm(monkeypatch):
    async def fake_call_vlm(
        prompt: str, image_b64: str | None = None, max_tokens: int = 512
    ) -> tuple[str, dict]:
        prompt_lower = prompt.lower()
        if "scene_assistant, navigation, device_control, safety_alert, context_memory" in prompt_lower:
            if "turn off" in prompt_lower or "light" in prompt_lower:
                return "device_control", FAKE_USAGE
            if "safe" in prompt_lower or "cross" in prompt_lower:
                return "safety_alert", FAKE_USAGE
            if "earlier" in prompt_lower or "cafe" in prompt_lower:
                return "context_memory", FAKE_USAGE
            if "where" in prompt_lower or "route" in prompt_lower:
                return "navigation", FAKE_USAGE
            return "scene_assistant", FAKE_USAGE
        if "safety" in prompt_lower:
            return "Please slow down and check the surroundings carefully.", FAKE_USAGE
        if "navigation" in prompt_lower:
            return "Head straight for one block and turn left.", FAKE_USAGE
        if "memory" in prompt_lower:
            return "You previously looked at a cafe near city hall.", FAKE_USAGE
            return "There is a street scene with pedestrians nearby.", FAKE_USAGE

    monkeypatch.setattr("app.groq_client.call_vlm", fake_call_vlm)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
