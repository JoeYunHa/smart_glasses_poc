"""Aggregate evaluation metrics for Baseline vs Optimized comparison."""

from collections import defaultdict

from app.evaluation.logger import read_logs


def aggregate(limit: int = 200) -> dict:
    logs = read_logs(limit=limit)
    if not logs:
        return {"total": 0, "by_mode": {}}

    by_mode: dict[str, dict] = defaultdict(lambda: {
        "count": 0,
        "total_latency_ms": 0,
        "vlm_calls": 0,
        "frame_reduction_total": 0,
        "graph_nodes_retrieved": 0,
        "services": defaultdict(int),
    })

    for log in logs:
        mode = log.get("mode", "unknown")
        m = by_mode[mode]
        m["count"] += 1
        m["total_latency_ms"] += log.get("latency_ms", {}).get("total", 0)
        m["vlm_calls"] += log.get("vlm_call_count", 0)
        orig = log.get("original_frame_count", 0)
        sel = log.get("selected_keyframe_count", 0)
        if orig > 0:
            m["frame_reduction_total"] += (orig - sel) / orig
        m["graph_nodes_retrieved"] += log.get("retrieved_graph_nodes", 0)
        m["services"][log.get("selected_service", "unknown")] += 1

    result: dict = {"total": len(logs), "by_mode": {}}
    for mode, m in by_mode.items():
        n = m["count"] or 1
        result["by_mode"][mode] = {
            "count": m["count"],
            "avg_latency_ms": round(m["total_latency_ms"] / n),
            "avg_vlm_calls": round(m["vlm_calls"] / n, 2),
            "avg_frame_reduction_ratio": round(m["frame_reduction_total"] / n, 3),
            "avg_graph_nodes": round(m["graph_nodes_retrieved"] / n, 1),
            "service_distribution": dict(m["services"]),
        }
    return result
