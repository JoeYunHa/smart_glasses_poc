"""Temporal Scene Graph using NetworkX.

Nodes: Scene, Object, Location, Device, UserIntent, Action, Risk, Time
Edges encode relationships between nodes across requests.
"""

from datetime import datetime

import networkx as nx

from app.schemas.context import ContextRequest

_graph: nx.DiGraph = nx.DiGraph()


def _ensure_node(node_id: str, **attrs: object) -> None:
    """Add node only if it does not already exist (deduplication helper)."""
    if not _graph.has_node(node_id):
        _graph.add_node(node_id, **attrs)


def add_scene(
    request_id: str,
    ctx: ContextRequest,
    service_name: str,
    objects: list[str] | None = None,
    actions: list[str] | None = None,
    risks: list[str] | None = None,
) -> str:
    scene_id = f"scene:{request_id}"
    _graph.add_node(scene_id, type="Scene", timestamp=datetime.utcnow().isoformat(),
                    user_request=ctx.user_request, service=service_name)

    time_bucket = datetime.utcnow().isoformat()[:16]
    time_id = f"time:{time_bucket}"
    _ensure_node(time_id, type="Time", bucket=time_bucket)
    _graph.add_edge(scene_id, time_id, rel="scene_at_time")

    if ctx.gps:
        loc_id = f"loc:{ctx.gps.latitude:.4f},{ctx.gps.longitude:.4f}"
        _ensure_node(loc_id, type="Location", place_name=ctx.gps.place_name,
                     location_type=ctx.gps.location_type)
        _graph.add_edge(scene_id, loc_id, rel="scene_at_location")

    intent_id = f"intent:{scene_id}"
    _ensure_node(intent_id, type="UserIntent", text=ctx.user_request)
    _graph.add_edge(scene_id, intent_id, rel="user_requested")

    for dev in ctx.nearby_devices:
        dev_id = f"device:{dev.device_id}"
        _ensure_node(dev_id, type="Device", name=dev.name, device_type=dev.type)
        _graph.add_edge(scene_id, dev_id, rel="scene_contains_device")

    for obj in (objects or []):
        obj_id = f"object:{obj.lower().replace(' ', '_')}"
        _ensure_node(obj_id, type="Object", name=obj)
        _graph.add_edge(scene_id, obj_id, rel="scene_contains_object")

    for act in (actions or []):
        act_id = f"action:{act.lower().replace(' ', '_')}"
        _ensure_node(act_id, type="Action", description=act)
        _graph.add_edge(scene_id, act_id, rel="scene_triggered_action")

    for risk in (risks or []):
        risk_id = f"risk:{risk.lower().replace(' ', '_')}"
        _ensure_node(risk_id, type="Risk", category=risk)
        _graph.add_edge(scene_id, risk_id, rel="scene_identified_risk")

    scene_nodes = [n for n, d in _graph.nodes(data=True)
                   if d.get("type") == "Scene" and n != scene_id]
    if scene_nodes:
        prev = max(scene_nodes, key=lambda n: _graph.nodes[n].get("timestamp", ""))
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


def find_subgraph_by_query(
    query: str,
    max_hops: int = 2,
    max_results: int = 5,
) -> list[str]:
    """Score Scene nodes by keyword overlap, then BFS-expand to collect rich context."""
    query_words = set(query.lower().split())

    scored: list[tuple[int, str, dict]] = []
    for node_id, data in _graph.nodes(data=True):
        if data.get("type") != "Scene":
            continue
        node_text = (data.get("user_request", "") + " " + data.get("service", "")).lower()
        overlap = len(query_words & set(node_text.split()))
        if overlap > 0:
            scored.append((overlap, node_id, data))
    scored.sort(key=lambda x: -x[0])

    results: list[str] = []
    for _, scene_id, scene_data in scored[:max_results]:
        neighbors: dict[str, dict] = {}
        frontier: set[str] = {scene_id}
        for _ in range(max_hops):
            next_f: set[str] = set()
            for n in frontier:
                # Traverse both directions: successors (attributes) and predecessors (temporal links)
                adjacent = set(_graph.successors(n)) | set(_graph.predecessors(n))
                for nb in adjacent:
                    if nb not in neighbors and nb != scene_id:
                        neighbors[nb] = dict(_graph.nodes[nb])
                        next_f.add(nb)
            frontier = next_f

        objs   = [d["name"]        for d in neighbors.values() if d.get("type") == "Object"]
        acts   = [d["description"] for d in neighbors.values() if d.get("type") == "Action"]
        risks  = [d["category"]    for d in neighbors.values() if d.get("type") == "Risk"]
        loc    = next((d.get("place_name", "") for d in neighbors.values()
                       if d.get("type") == "Location"), "")

        ctx_str = f"[{scene_data.get('service')}] {scene_data.get('user_request', '')}"
        if loc:   ctx_str += f" at {loc}"
        if objs:  ctx_str += f" | objects: {', '.join(objs)}"
        if risks: ctx_str += f" | risks: {', '.join(risks)}"
        if acts:  ctx_str += f" | actions: {', '.join(acts)}"
        results.append(ctx_str)

    return results


def graph_size() -> int:
    return _graph.number_of_nodes()


def edge_size() -> int:
    return _graph.number_of_edges()


def reset_graph() -> None:
    _graph.clear()
