"""Agent run endpoint integration tests."""

from __future__ import annotations

import json

import cv2
import numpy as np


def test_run_agent_text_only(client, base_context):
    res = client.post(
        "/api/agent/run",
        data={"context_json": json.dumps(base_context)},
    )
    assert res.status_code == 200
    data = res.json()
    assert "request_id" in data
    assert "selected_service" in data
    assert "response_text" in data
    assert isinstance(data["latency_ms"], dict)
    assert data["latency_ms"]["total"] > 0


def test_run_agent_returns_valid_service(client, base_context):
    valid_services = {
        "scene_assistant", "navigation", "device_control",
        "safety_alert", "context_memory", "label_reader", "unknown",
    }
    res = client.post(
        "/api/agent/run",
        data={"context_json": json.dumps(base_context)},
    )
    assert res.status_code == 200
    assert res.json()["selected_service"] in valid_services


def test_run_agent_device_control(client, device_context):
    res = client.post(
        "/api/agent/run",
        data={"context_json": json.dumps(device_context)},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["selected_service"] == "device_control"
    assert data["action_result"] is not None


def test_run_agent_baseline_mode(client):
    ctx = {
        "user_request": "Where am I right now?",
        "gps": {"latitude": 37.5, "longitude": 127.0, "location_type": "street", "place_name": "Test Street"},
        "nearby_devices": [],
        "mode": "baseline",
    }
    res = client.post(
        "/api/agent/run",
        data={"context_json": json.dumps(ctx)},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "baseline"


def test_run_agent_with_image(client, base_context):
    image = np.full((4, 4, 3), 255, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    minimal_jpeg = encoded.tobytes()
    res = client.post(
        "/api/agent/run",
        data={"context_json": json.dumps(base_context)},
        files={"image": ("test.jpg", minimal_jpeg, "image/jpeg")},
    )
    assert res.status_code == 200
    assert "response_text" in res.json()
