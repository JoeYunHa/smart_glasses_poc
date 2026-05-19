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


_FAKE_TOKENS = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}


def _make_usage(prompt: str, image_b64: str | None) -> dict:
    """Build a usage dict that mirrors what the real call_vlm returns."""
    usage = dict(_FAKE_TOKENS)
    usage["prompt_bytes"] = len(prompt.encode("utf-8"))
    if image_b64:
        usage["image_bytes"] = len(image_b64.encode("utf-8"))
    return usage


@pytest.fixture(autouse=True)
def stub_vlm(monkeypatch):
    async def fake_call_vlm(
        prompt: str, image_b64: str | None = None, max_tokens: int = 512
    ) -> tuple[str, dict]:
        usage = _make_usage(prompt, image_b64)
        prompt_lower = prompt.lower()
        if "scene_assistant, navigation, device_control, safety_alert, context_memory, label_reader" in prompt_lower:
            if "label" in prompt_lower or "medicine" in prompt_lower or "dosage" in prompt_lower:
                return "label_reader", usage
            if "turn off" in prompt_lower or "light" in prompt_lower:
                return "device_control", usage
            if "safe" in prompt_lower or "cross" in prompt_lower:
                return "safety_alert", usage
            if "earlier" in prompt_lower or "cafe" in prompt_lower:
                return "context_memory", usage
            if "where" in prompt_lower or "route" in prompt_lower:
                return "navigation", usage
            return "scene_assistant", usage
        if "safety" in prompt_lower:
            return "Please slow down and check the surroundings carefully.", usage
        if "navigation" in prompt_lower:
            return "Head straight for one block and turn left.", usage
        if "memory" in prompt_lower:
            return "You previously looked at a cafe near city hall.", usage
        # Default: covers semantic prompts ("[Frame N]" format) and other unmatched cases
        return "There is a street scene with pedestrians nearby.", usage

    monkeypatch.setattr("app.llm_client.call_vlm", fake_call_vlm)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
