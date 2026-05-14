"""Pipeline orchestrator."""

import time
import uuid

from app.agent.pipeline_support import (
    build_latency,
    classify_failure,
    route_service,
    run_perception,
)
from app.agent.service_registry import get_service_runner
from app.evaluation import logger as eval_logger
from app.memory import graph_store, retrieval
from app.schemas.agent import AgentResponse, ServiceType
from app.schemas.context import AgentMode, ContextRequest
from app.schemas.log import EvaluationLog


def _ms() -> int:
    return int(time.monotonic() * 1000)


async def run_pipeline(
    image_bytes: bytes | None,
    video_bytes: bytes | None,
    ctx: ContextRequest,
) -> AgentResponse:
    request_id = str(uuid.uuid4())
    t_start = _ms()

    # 1. Perception: frame sampling + keyframe selection
    perception = run_perception(image_bytes, video_bytes, ctx.mode, _ms)
    image_b64_list = perception.image_b64_list

    # 3. GraphRAG retrieval (optimized only)
    t1 = _ms()
    graph_context = ""
    retrieved_nodes = 0
    if ctx.mode == AgentMode.optimized:
        retrieval_result = retrieval.retrieve_context(ctx.user_request)
        retrieved_nodes = len(retrieval_result.combined)
        if retrieval_result.combined:
            graph_context = "Relevant prior context: " + "; ".join(retrieval_result.combined[:3])
    graph_retrieval_ms = _ms() - t1

    # 4. Route: rule-based; VLM fallback if confidence < threshold
    routing_result, routing_ms = await route_service(ctx, _ms)
    service_name = routing_result.service_name
    confidence = routing_result.confidence

    # 5. Run selected service
    t3 = _ms()
    service_fn = get_service_runner(service_name)
    response_text, vlm_used_service, action_result, service_vlm_usage = await service_fn(
        ctx, image_b64_list, graph_context, request_id
    )
    vlm_ms = _ms() - t3
    vlm_used = routing_result.vlm_used or vlm_used_service

    total_ms = max(1, _ms() - t_start)
    latency = build_latency(perception, graph_retrieval_ms, routing_ms, vlm_ms, total_ms)

    # 6. Store in memory
    graph_store.add_scene(request_id, ctx, service_name)
    retrieval.store_context(request_id, ctx.user_request, service_name, response_text[:120])

    # 7. Evaluation log
    image_payload_bytes = sum(len(b64.encode()) for b64 in image_b64_list)
    cloud_called = routing_result.vlm_used or vlm_used_service
    token_count = (
        routing_result.usage.get("total_tokens", 0)
        + service_vlm_usage.get("total_tokens", 0)
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
        vlm_call_count=routing_result.vlm_call_count + (1 if vlm_used_service else 0),
        retrieved_graph_nodes=retrieved_nodes,
        latency_ms=latency,
        action_result="success" if (action_result and action_result.success) else ("failed" if action_result else "skipped"),
        user_request=ctx.user_request,
        token_count=token_count,
        image_payload_bytes=image_payload_bytes,
        cloud_called=cloud_called,
        fallback_reason=routing_result.fallback_reason,
        failure_type=failure_type,
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
