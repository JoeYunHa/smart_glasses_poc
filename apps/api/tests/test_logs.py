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
        "avg_tokens", "avg_image_payload_bytes", "cloud_call_ratio",
        "fallback_distribution", "failure_distribution",
    }
    for mode_data in data["by_mode"].values():
        assert required.issubset(mode_data.keys())


def test_eval_log_extended_fields_populated(client, base_context):
    """token_count, cloud_called, fallback_reason이 로그에 기록되는지 검증."""
    client.post(
        "/api/agent/run",
        data={"context_json": json.dumps(base_context)},
    )
    logs = client.get("/api/logs/").json()["logs"]
    assert logs, "로그가 하나 이상 있어야 합니다"
    last = logs[-1]

    assert "token_count" in last
    assert "image_payload_bytes" in last
    assert "cloud_called" in last
    assert "fallback_reason" in last
    assert "failure_type" in last

    assert isinstance(last["token_count"], int)
    assert last["token_count"] >= 0
    assert last["cloud_called"] == (last["vlm_call_count"] > 0)
    assert last["fallback_reason"] in ("low_confidence", "parse_error", "vlm_timeout", "none")
    assert last["failure_type"] in ("routing_error", "vlm_error", "action_error", "none")
