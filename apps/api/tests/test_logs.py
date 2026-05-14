"""Logs and metrics endpoint integration tests."""

from __future__ import annotations

import json


def test_get_logs_returns_list(client):
    res = client.get("/api/logs/")
    assert res.status_code == 200
    data = res.json()
    assert "logs" in data
    assert isinstance(data["logs"], list)


def test_get_logs_limit_param(client):
    res = client.get("/api/logs/", params={"limit": 1})
    assert res.status_code == 200
    assert len(res.json()["logs"]) <= 1


def test_get_metrics_structure(client):
    res = client.get("/api/logs/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "by_mode" in data
    assert isinstance(data["by_mode"], dict)


def test_metrics_populated_after_run(client, base_context):
    before = client.get("/api/logs/metrics").json()["total"]

    client.post(
        "/api/agent/run",
        data={"context_json": json.dumps(base_context)},
    )

    after = client.get("/api/logs/metrics").json()["total"]
    assert after > before


def test_metrics_by_mode_has_correct_fields(client, base_context):
    client.post(
        "/api/agent/run",
        data={"context_json": json.dumps(base_context)},
    )
    data = client.get("/api/logs/metrics").json()
    required = {
        "count", "avg_latency_ms", "avg_vlm_calls",
        "avg_frame_reduction_ratio", "avg_graph_nodes", "service_distribution",
    }
    for mode_data in data["by_mode"].values():
        assert required.issubset(mode_data.keys())
