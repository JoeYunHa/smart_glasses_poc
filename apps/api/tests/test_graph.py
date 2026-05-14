"""Graph endpoint integration tests."""

from __future__ import annotations

import json


def test_get_graph_nodes_empty_on_fresh_start(client):
    res = client.get("/api/graph/nodes")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


def test_query_graph_keyword(client):
    res = client.get("/api/graph/query", params={"keyword": "cafe"})
    assert res.status_code == 200
    data = res.json()
    assert "results" in data
    assert isinstance(data["results"], list)


def test_graph_nodes_populated_after_agent_run(client, base_context):
    client.post(
        "/api/agent/run",
        data={"context_json": json.dumps(base_context)},
    )
    res = client.get("/api/graph/nodes")
    assert res.status_code == 200
    data = res.json()
    assert len(data["nodes"]) > 0


def test_graph_size(client):
    res = client.get("/api/graph/size")
    assert res.status_code == 200
    data = res.json()
    assert "node_count" in data
    assert "edge_count" in data
