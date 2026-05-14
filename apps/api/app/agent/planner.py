"""Pipeline orchestrator."""

import time
import uuid

import cv2
import numpy as np

from app.agent import router as svc_router
from app.config import settings
from app.evaluation import logger as eval_logger
from app.memory import graph_store, retrieval
from app.perception.frame_sampler import sample_frames
from app.perception.image_preprocessor import frame_to_b64, preprocess_image_bytes
from app.perception.keyframe_selector import select_keyframes
from app.schemas.agent import AgentResponse, LatencyBreakdown, ServiceType
from app.schemas.context import AgentMode, ContextRequest
from app.schemas.log import EvaluationLog
from app.services import context_memory, device_control, navigation, safety_alert, scene_assistant

_SERVICE_MAP = {
    "safety_alert": safety_alert.run,
    "device_control": device_control.run,
    "navigation": navigation.run,
    "context_memory": context_memory.run,
    "scene_assistant": scene_assistant.run,
}


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
    t0 = _ms()
    keyframes: list[np.ndarray] = []
    original_frame_count = 0
    selected_keyframe_count = 0
    keyframe_selection_ms = 0

    if video_bytes:
        fps_target = 2 if ctx.mode == AgentMode.optimized else None
        frames = sample_frames(video_bytes, fps_target=fps_target)
        frame_sampling_ms = _ms() - t0
        original_frame_count = len(frames)
        if ctx.mode == AgentMode.optimized:
            t_keyframes = _ms()
            keyframes = select_keyframes(frames, max_keyframes=settings.max_keyframes)
            keyframe_selection_ms = _ms() - t_keyframes
        else:
            keyframes = frames
        selected_keyframe_count = len(keyframes)
    elif image_bytes:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is not None:
            keyframes = [img]
        original_frame_count = 1
        selected_keyframe_count = 1
        frame_sampling_ms = _ms() - t0
    else:
        frame_sampling_ms = _ms() - t0

    # 2. Encode keyframes to base64
    if image_bytes and not video_bytes:
        image_b64_list = [preprocess_image_bytes(image_bytes)]
    else:
        image_b64_list = [frame_to_b64(f) for f in keyframes]

    # 3. GraphRAG retrieval (optimized only)
    t1 = _ms()
    graph_context = ""
    retrieved_nodes = 0
    if ctx.mode == AgentMode.optimized:
        similar = retrieval.find_similar(ctx.user_request)
        retrieved_nodes = len(similar)
        if similar:
            graph_context = "Relevant prior context: " + "; ".join(similar[:3])
    graph_retrieval_ms = _ms() - t1

    # 4. Route: rule-based; VLM fallback if confidence < threshold
    t2 = _ms()
    location_type = ctx.gps.location_type if ctx.gps else ""
    has_devices = len(ctx.nearby_devices) > 0
    service_name, confidence = svc_router.route(ctx.user_request, location_type, has_devices)

    vlm_used_routing = False
    routing_vlm_call_count = 0
    if confidence < settings.router_confidence_threshold:
        from app.groq_client import call_vlm

        routing_prompt = (
            "Classify the following request as exactly one of these services:\n"
            "scene_assistant, navigation, device_control, safety_alert, context_memory\n"
            "Return only the service name.\n\n"
            f"Request: {ctx.user_request}"
        )
        raw = await call_vlm(routing_prompt)
        routing_vlm_call_count = 1
        for svc in _SERVICE_MAP:
            if svc in raw.lower():
                service_name = svc
                confidence = 0.6
                break
        vlm_used_routing = True

    routing_ms = _ms() - t2

    # 5. Run selected service
    t3 = _ms()
    service_fn = _SERVICE_MAP.get(service_name, scene_assistant.run)
    response_text, vlm_used_service, action_result = await service_fn(
        ctx, image_b64_list, graph_context, request_id
    )
    vlm_ms = _ms() - t3
    vlm_used = vlm_used_routing or vlm_used_service

    total_ms = max(1, _ms() - t_start)
    latency = LatencyBreakdown(
        frame_sampling=frame_sampling_ms,
        keyframe_selection=keyframe_selection_ms,
        graph_retrieval=graph_retrieval_ms,
        routing=routing_ms,
        vlm=vlm_ms,
        total=total_ms,
    )

    # 6. Store in memory
    graph_store.add_scene(request_id, ctx, service_name)
    retrieval.store_context(request_id, ctx.user_request, service_name, response_text[:120])

    # 7. Evaluation log
    log = EvaluationLog(
        request_id=request_id,
        mode=ctx.mode.value,
        selected_service=ServiceType(service_name),
        router_confidence=confidence,
        original_frame_count=original_frame_count,
        selected_keyframe_count=selected_keyframe_count,
        vlm_call_count=routing_vlm_call_count + (1 if vlm_used_service else 0),
        retrieved_graph_nodes=retrieved_nodes,
        latency_ms=latency,
        action_result="success" if (action_result and action_result.success) else ("failed" if action_result else "skipped"),
        user_request=ctx.user_request,
    )
    await eval_logger.write_log(log)

    return AgentResponse(
        request_id=request_id,
        selected_service=ServiceType(service_name),
        router_confidence=confidence,
        vlm_used=vlm_used,
        response_text=response_text,
        action_result=action_result,
        original_frame_count=original_frame_count,
        selected_keyframe_count=selected_keyframe_count,
        retrieved_graph_nodes=retrieved_nodes,
        latency_ms=latency,
        mode=ctx.mode.value,
    )
