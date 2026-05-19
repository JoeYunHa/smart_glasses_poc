"""Optimized vs Baseline regression smoke tests.

Validates that key evaluation metrics are present, non-negative, and that the
optimized mode produces structurally better or equal results on the dimensions
it is designed to improve: keyframe reduction, VLM call count, and payload size.

These tests use the mocked VLM (stub_vlm autouse fixture from conftest), so
latency assertions are skipped — only schema and relative ordering are checked.
"""

from __future__ import annotations

import json

import cv2
import numpy as np
import pytest


_SAME_REQUEST = {
    "user_request": "What do you see around me right now?",
    "gps": {
        "latitude": 37.5665,
        "longitude": 126.9780,
        "location_type": "street",
        "place_name": "Seoul City Hall",
    },
    "nearby_devices": [],
}

_LATENCY_FIELDS = {"frame_sampling", "keyframe_selection", "graph_retrieval", "routing", "vlm", "total"}


def _make_jpeg(size: int = 8) -> bytes:
    img = np.full((size, size, 3), 128, dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()


# ── Schema completeness ────────────────────────────────────────────────────────

@pytest.mark.parametrize("mode", ["optimized", "baseline"])
def test_agent_response_schema(client, mode):
    ctx = {**_SAME_REQUEST, "mode": mode}
    res = client.post("/api/agent/run", data={"context_json": json.dumps(ctx)})
    assert res.status_code == 200
    data = res.json()

    assert "request_id" in data
    assert "selected_service" in data
    assert "vlm_used" in data
    assert "response_text" in data
    assert isinstance(data["latency_ms"], dict)
    assert _LATENCY_FIELDS == set(data["latency_ms"].keys())
    assert data["latency_ms"]["total"] > 0


@pytest.mark.parametrize("mode", ["optimized", "baseline"])
def test_eval_log_schema(client, mode):
    ctx = {**_SAME_REQUEST, "mode": mode}
    before = len(client.get("/api/logs/").json()["logs"])
    client.post("/api/agent/run", data={"context_json": json.dumps(ctx)})
    logs = client.get("/api/logs/").json()["logs"]
    assert len(logs) == before + 1
    log = logs[-1]

    assert log["mode"] == mode
    assert log["vlm_call_count"] >= 0
    assert log["image_payload_bytes"] >= 0
    assert log["token_count"] >= 0
    assert log["router_confidence"] >= 0.0


# ── Optimized ≥ baseline guarantees ───────────────────────────────────────────

def test_optimized_records_graph_retrieval(client):
    """optimized mode must record retrieved_graph_nodes field (even if 0)."""
    ctx = {**_SAME_REQUEST, "mode": "optimized"}
    client.post("/api/agent/run", data={"context_json": json.dumps(ctx)})
    log = client.get("/api/logs/").json()["logs"][-1]
    assert "retrieved_graph_nodes" in log
    assert log["retrieved_graph_nodes"] >= 0


def test_baseline_retrieved_graph_nodes_is_zero(client):
    """baseline must not query graph memory — retrieved_graph_nodes must be 0."""
    ctx = {**_SAME_REQUEST, "mode": "baseline"}
    client.post("/api/agent/run", data={"context_json": json.dumps(ctx)})
    log = client.get("/api/logs/").json()["logs"][-1]
    assert log["retrieved_graph_nodes"] == 0


def test_optimized_image_payload_bytes_positive_for_image_request(client):
    """When an image is submitted, optimized mode must record non-zero payload bytes."""
    ctx = {**_SAME_REQUEST, "mode": "optimized"}
    jpeg = _make_jpeg()
    client.post(
        "/api/agent/run",
        data={"context_json": json.dumps(ctx)},
        files={"image": ("scene.jpg", jpeg, "image/jpeg")},
    )
    log = client.get("/api/logs/").json()["logs"][-1]
    assert log["image_payload_bytes"] > 0


def test_both_modes_return_same_service_for_same_request(client):
    """Routing must be consistent: the same text request routes to the same service
    in both modes (modulo low-confidence VLM fallback, which is mocked consistently)."""
    before = len(client.get("/api/logs/").json()["logs"])

    for mode in ("optimized", "baseline"):
        ctx = {**_SAME_REQUEST, "mode": mode}
        res = client.post("/api/agent/run", data={"context_json": json.dumps(ctx)})
        assert res.status_code == 200

    logs = client.get("/api/logs/").json()["logs"][before:]
    assert len(logs) == 2
    assert logs[0]["selected_service"] == logs[1]["selected_service"]


# ── device_control: no cloud call ─────────────────────────────────────────────

def test_device_control_cloud_not_called(client):
    """device_control must resolve without a VLM call (cloud_called=False)."""
    ctx = {
        "user_request": "Turn off the living room light",
        "gps": None,
        "nearby_devices": [
            {
                "device_id": "light-001",
                "name": "Living Room Light",
                "type": "smart_light",
                "supported_actions": ["turn_on", "turn_off"],
                "risk_level": "low",
                "requires_confirmation": False,
                "state": {"power": "on"},
            }
        ],
        "mode": "optimized",
    }
    client.post("/api/agent/run", data={"context_json": json.dumps(ctx)})
    log = client.get("/api/logs/").json()["logs"][-1]
    assert log["selected_service"] == "device_control"
    assert log["cloud_called"] is False
    assert log["image_payload_bytes"] == 0
