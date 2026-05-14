"""Temporal Scene Graph using NetworkX.

Nodes: Scene, Object, Location, Device, UserIntent, Action, Risk, Time
Edges encode relationships between nodes across requests.
"""

import uuid
from datetime import datetime

import networkx as nx

from app.schemas.context import ContextRequest

_graph: nx.DiGraph = nx.DiGraph()


def add_scene(request_id: str, ctx: ContextRequest, service_name: str) -> str:
    scene_id = f"scene:{request_id}"
    _graph.add_node(scene_id, type="Scene", timestamp=datetime.utcnow().isoformat(),
                    user_request=ctx.user_request, service=service_name)

    if ctx.gps:
        loc_id = f"loc:{ctx.gps.latitude:.4f},{ctx.gps.longitude:.4f}"
        _graph.add_node(loc_id, type="Location", place_name=ctx.gps.place_name,
                        location_type=ctx.gps.location_type)
        _graph.add_edge(scene_id, loc_id, rel="scene_at_location")

    intent_id = f"intent:{uuid.uuid4().hex[:8]}"
    _graph.add_node(intent_id, type="UserIntent", text=ctx.user_request)
    _graph.add_edge(scene_id, intent_id, rel="user_requested")

    for dev in ctx.nearby_devices:
        dev_id = f"device:{dev.device_id}"
        _graph.add_node(dev_id, type="Device", name=dev.name, device_type=dev.type)
        _graph.add_edge(scene_id, dev_id, rel="scene_contains_device")

    # Chain to previous scene if exists
    scene_nodes = [n for n, d in _graph.nodes(data=True) if d.get("type") == "Scene" and n != scene_id]
    if scene_nodes:
        prev = scene_nodes[-1]
        _graph.add_edge(prev, scene_id, rel="scene_before_scene")

    return scene_id


def get_all_nodes() -> list[dict]:
    return [{"id": n, **d} for n, d in _graph.nodes(data=True)]


def get_all_edges() -> list[dict]:
    return [{"source": u, "target": v, **d} for u, v, d in _graph.edges(data=True)]


def find_scenes_by_keyword(keyword: str) -> list[dict]:
    results = []
    for node_id, data in _graph.nodes(data=True):
        if data.get("type") != "Scene":
            continue
        if keyword in data.get("user_request", "") or keyword in data.get("service", ""):
            results.append({"id": node_id, **data})
    return results


def graph_size() -> int:
    return _graph.number_of_nodes()
