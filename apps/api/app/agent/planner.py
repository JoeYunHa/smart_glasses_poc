"""Pipeline orchestrator."""

import asyncio
import time
import uuid

from app.agent import router as _router
from app.agent.pipeline_support import (
    build_latency,
    classify_failure,
    route_service,
    run_perception,
)
from app.agent.service_registry import get_service_runner
from app.config import settings
from app.evaluation import logger as eval_logger
from app.memory import graph_store, retrieval
from app.schemas.agent import AgentResponse, ServiceType
from app.schemas.context import AgentMode, ContextRequest
from app.schemas.log import EvaluationLog


_GRAPH_CONTEXT_MAX_CHARS = 500

_OBJ_HINTS  = ["car", "person", "sign", "crosswalk", "light", "screen", "door", "building",
               "medicine", "drug", "pill", "label", "package"]
_RISK_HINTS = ["danger", "hazard", "obstacle", "warning", "unsafe", "caution", "risk"]
_ACT_HINTS  = ["turn_on", "turn_off", "set_volume", "lock", "unlock", "play", "pause",
                "set_brightness", "set_temperature"]


def _extract_graph_metadata(
    service_name: str, response_text: str
) -> tuple[list[str], list[str], list[str]]:
    """Extract objects/actions/risks from VLM response text for graph storage.

    Risks are extracted for all services so navigation/scene responses mentioning
    hazards are captured in the graph (not only safety_alert).
    Actions are extracted for device_control only — other services don't trigger actions.
    """
    text = response_text.lower()
    objects = [h for h in _OBJ_HINTS if h in text]
    risks = [h for h in _RISK_HINTS if h in text]
    actions = [h for h in _ACT_HINTS if h in text] if service_name == "device_control" else []
    return objects, actions, risks


def _ms() -> int:
    return int(time.monotonic() * 1000)


async def run_pipeline(
    image_bytes: bytes | None,
    video_bytes: bytes | None,
    ctx: ContextRequest,
) -> AgentResponse:
    request_id = str(uuid.uuid4())
    t_start = _ms()

    # 1. Perception: frame sampling + keyframe selection + semantic extraction
    # Offloaded to a thread so OpenCV CPU work does not block the event loop.
    perception = await asyncio.to_thread(
        run_perception, image_bytes, video_bytes, ctx.mode, _ms, user_request=ctx.user_request
    )
    image_b64_list = perception.image_b64_list

    # 3+4. GraphRAG retrieval (optimized) runs concurrently with routing so its
    # wall-clock cost is hidden behind the routing step rather than added serially.
    graph_context = ""
    retrieved_nodes = 0
    graph_retrieval_ms = 0

    if ctx.mode == AgentMode.optimized:
        t_graph_start = _ms()
        # Fast rule-based pre-check (no VLM, no await) to skip retrieval task creation
        # for high-confidence device_control — avoids spinning up an unnecessary thread.
        location_type = ctx.gps.location_type if ctx.gps else ""
        has_devices = len(ctx.nearby_devices) > 0
        _pre_service, _pre_conf = _router.route(ctx.user_request, location_type, has_devices)
        skip_retrieval = (
            _pre_service == "device_control"
            and _pre_conf >= settings.router_confidence_threshold
        )

        if skip_retrieval:
            routing_result, routing_ms = await route_service(ctx, _ms)
            graph_retrieval_ms = _ms() - t_graph_start
        else:
            retrieval_task = asyncio.create_task(
                asyncio.to_thread(retrieval.retrieve_context, ctx.user_request)
            )
            routing_result, routing_ms = await route_service(ctx, _ms)
            retrieval_result = await retrieval_task
            graph_retrieval_ms = _ms() - t_graph_start
            # Guard against the rare case where VLM fallback changes routing to device_control.
            if routing_result.service_name != "device_control" and retrieval_result.combined:
                retrieved_nodes = len(retrieval_result.combined)
                raw_context = "; ".join(retrieval_result.combined)
                graph_context = raw_context[:_GRAPH_CONTEXT_MAX_CHARS]
    else:
        routing_result, routing_ms = await route_service(ctx, _ms)

    # Inject graph_context into semantic_prompt now that retrieval is done
    semantic_prompt = perception.semantic_prompt
    if semantic_prompt and graph_context:
        semantic_prompt = f"{semantic_prompt}\n\nPrior context: {graph_context}"
    service_name = routing_result.service_name
    confidence = routing_result.confidence

    # 5. Run selected service
    t3 = _ms()
    service_fn = get_service_runner(service_name)
    response_text, vlm_used_service, action_result, service_vlm_usage = await service_fn(
        ctx, image_b64_list, graph_context, request_id, semantic_prompt
    )
    vlm_ms = _ms() - t3
    vlm_used = routing_result.vlm_used or vlm_used_service

    total_ms = max(1, _ms() - t_start)
    latency = build_latency(perception, graph_retrieval_ms, routing_ms, vlm_ms, total_ms)

    # 6. Store in memory (optimized only — prevents baseline data from contaminating retrieval)
    if ctx.mode == AgentMode.optimized:
        objects, actions, risks = _extract_graph_metadata(service_name, response_text)
        graph_store.add_scene(request_id, ctx, service_name,
                              objects=objects, actions=actions, risks=risks)
        # context_memory responses are derived output, not new knowledge.
        # Storing them causes recursive contamination on subsequent retrievals.
        if service_name != "context_memory":
            retrieval.store_context(request_id, ctx.user_request, service_name, response_text[:120])

    # 7. Evaluation log
    token_count = (
        routing_result.usage.get("total_tokens", 0)
        + service_vlm_usage.get("total_tokens", 0)
    )
    # vlm_calls from service usage dict reflects actual calls (2 when semantic fallback fires)
    service_vlm_calls = service_vlm_usage.get("vlm_calls", 1 if vlm_used_service else 0)

    # image_payload_bytes: total bytes actually transmitted to the VLM.
    # call_vlm reports prompt_bytes and image_bytes per call; merge_usage sums them
    # across 1 or 2 calls (text-only + optional vision fallback), so the accumulated
    # value reflects the complete transmission including system prompts added by services.
    image_payload_bytes = (
        service_vlm_usage.get("prompt_bytes", 0)
        + service_vlm_usage.get("image_bytes", 0)
    )
    failure_type = classify_failure(
        service_name,
        action_result.success if action_result else None,
        vlm_used,
        response_text,
    )

    log = EvaluationLog(
        request_id=request_id,
        mode=ctx.mode.value,
        selected_service=ServiceType(service_name),
        router_confidence=confidence,
        original_frame_count=perception.original_frame_count,
        selected_keyframe_count=perception.selected_keyframe_count,
        vlm_call_count=routing_result.vlm_call_count + service_vlm_calls,
        retrieved_graph_nodes=retrieved_nodes,
        latency_ms=latency,
        action_result="success" if (action_result and action_result.success) else ("failed" if action_result else "skipped"),
        user_request=ctx.user_request,
        token_count=token_count,
        image_payload_bytes=image_payload_bytes,
        cloud_called=vlm_used,
        fallback_reason=routing_result.fallback_reason,
        failure_type=failure_type,
        response_text=response_text,
        response_preview=response_text[:300],
        path_used=str(service_vlm_usage.get("path_used", "unknown")),
        quality_check_passed=bool(service_vlm_usage.get("quality_check_passed", True)),
    )
    await eval_logger.write_log(log)

    return AgentResponse(
        request_id=request_id,
        selected_service=ServiceType(service_name),
        router_confidence=confidence,
        vlm_used=vlm_used,
        response_text=response_text,
        action_result=action_result,
        original_frame_count=perception.original_frame_count,
        selected_keyframe_count=perception.selected_keyframe_count,
        retrieved_graph_nodes=retrieved_nodes,
        latency_ms=latency,
        mode=ctx.mode.value,
    )
