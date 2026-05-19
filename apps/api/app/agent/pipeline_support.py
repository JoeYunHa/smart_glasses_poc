from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import cv2
import numpy as np

from app.agent import router as svc_router
from app.agent.service_registry import known_service_names
from app.config import settings
from app.constants import SERVICE_CATEGORY_KEYWORDS
from app.perception.frame_sampler import sample_frames
from app.perception.image_preprocessor import frame_to_b64, preprocess_image_bytes
from app.perception.keyframe_selector import select_keyframes
from app.schemas.agent import LatencyBreakdown
from app.schemas.context import AgentMode, ContextRequest

# Sourced from constants.py (single definition shared with keyframe_selector and router keywords).
_LABEL_KEYWORDS: frozenset[str] = frozenset(SERVICE_CATEGORY_KEYWORDS["label"])


def _is_label_request(user_request: str) -> bool:
    lower = user_request.lower()
    return any(kw in lower for kw in _LABEL_KEYWORDS)


@dataclass
class PerceptionResult:
    image_b64_list: list[str]
    original_frame_count: int
    selected_keyframe_count: int
    frame_sampling_ms: int
    keyframe_selection_ms: int
    semantic_prompt: str = ""       # text-only VLM prompt built from SemanticPayloads


@dataclass
class RoutingResult:
    service_name: str
    confidence: float
    vlm_used: bool
    vlm_call_count: int
    usage: dict
    fallback_reason: str


def run_perception(
    image_bytes: bytes | None,
    video_bytes: bytes | None,
    mode: AgentMode,
    now_ms: Callable[[], int],
    user_request: str = "",
) -> PerceptionResult:
    from app.perception.semantic_extractor import SemanticPayload, build_semantic_prompt, extract_semantic

    t0 = now_ms()
    keyframes: list[np.ndarray] = []
    original_frame_count = 0
    selected_keyframe_count = 0
    keyframe_selection_ms = 0

    if video_bytes:
        fps_target = 2 if mode == AgentMode.optimized else None
        frames = sample_frames(video_bytes, fps_target=fps_target)
        frame_sampling_ms = now_ms() - t0
        original_frame_count = len(frames)
        if mode == AgentMode.optimized:
            t_keyframes = now_ms()
            keyframes = select_keyframes(
                frames,
                max_keyframes=settings.max_keyframes,
                user_request=user_request,
            )
            keyframe_selection_ms = now_ms() - t_keyframes
        else:
            # Baseline: scene-change-only selection (no query-aware scoring).
            # fps_target=None above means all frames are sampled; this caps at max_keyframes.
            t_keyframes = now_ms()
            keyframes = select_keyframes(frames, max_keyframes=settings.max_keyframes)
            keyframe_selection_ms = now_ms() - t_keyframes
        selected_keyframe_count = len(keyframes)
        image_b64_list = [frame_to_b64(frame) for frame in keyframes]

        semantic_prompt = ""
        if mode == AgentMode.optimized and keyframes:
            extract_mode = "label" if _is_label_request(user_request) else "general"
            prev = None
            payloads: list[SemanticPayload] = []
            for frame in keyframes:
                payloads.append(extract_semantic(frame, prev, mode=extract_mode))
                prev = frame
            semantic_prompt = build_semantic_prompt(payloads, user_request)

        return PerceptionResult(
            image_b64_list=image_b64_list,
            original_frame_count=original_frame_count,
            selected_keyframe_count=selected_keyframe_count,
            frame_sampling_ms=frame_sampling_ms,
            keyframe_selection_ms=keyframe_selection_ms,
            semantic_prompt=semantic_prompt,
        )

    if image_bytes:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        frame_sampling_ms = now_ms() - t0

        semantic_prompt = ""
        if mode == AgentMode.optimized and img is not None:
            extract_mode = "label" if _is_label_request(user_request) else "general"
            payload = extract_semantic(img, mode=extract_mode)
            semantic_prompt = build_semantic_prompt([payload], user_request)

        return PerceptionResult(
            image_b64_list=[preprocess_image_bytes(image_bytes)],
            original_frame_count=1,
            selected_keyframe_count=1,
            frame_sampling_ms=frame_sampling_ms,
            keyframe_selection_ms=0,
            semantic_prompt=semantic_prompt,
        )

    frame_sampling_ms = now_ms() - t0
    return PerceptionResult(
        image_b64_list=[],
        original_frame_count=0,
        selected_keyframe_count=0,
        frame_sampling_ms=frame_sampling_ms,
        keyframe_selection_ms=0,
        semantic_prompt="",
    )


async def route_service(
    ctx: ContextRequest,
    now_ms: Callable[[], int],
) -> tuple[RoutingResult, int]:
    t0 = now_ms()
    location_type = ctx.gps.location_type if ctx.gps else ""
    has_devices = len(ctx.nearby_devices) > 0
    service_name, confidence = svc_router.route(ctx.user_request, location_type, has_devices)

    vlm_used = False
    vlm_call_count = 0
    usage: dict = {}
    fallback_reason = "none"
    if confidence < settings.router_confidence_threshold:
        from app.llm_client import call_vlm

        routing_prompt = (
            "Classify the user request below into exactly one of these smart glasses services:\n"
            "- safety_alert: crossing roads, traffic lights, physical hazards, obstacles\n"
            "- device_control: turning devices on/off, adjusting volume/brightness, IoT control\n"
            "- navigation: directions, finding places, routes, location queries\n"
            "- context_memory: recalling something seen/heard earlier, past scenes or places\n"
            "- label_reader: reading medicine labels, product packaging, ingredient lists\n"
            "- scene_assistant: describing the current scene, identifying objects or text\n\n"
            "Reply with only the service name, no explanation.\n\n"
            f"Request: {ctx.user_request}"
        )
        try:
            raw, usage = await call_vlm(routing_prompt, max_tokens=16)
            vlm_call_count = 1
            vlm_used = True
            matched = False
            for service in known_service_names():
                if service in raw.lower():
                    service_name = service
                    confidence = 0.6
                    matched = True
                    break
            fallback_reason = "low_confidence" if matched else "parse_error"
        except Exception:
            vlm_used = True
            vlm_call_count = 1
            fallback_reason = "vlm_timeout"

    return (
        RoutingResult(
            service_name=service_name,
            confidence=confidence,
            vlm_used=vlm_used,
            vlm_call_count=vlm_call_count,
            usage=usage,
            fallback_reason=fallback_reason,
        ),
        now_ms() - t0,
    )


def build_latency(
    perception: PerceptionResult,
    graph_retrieval_ms: int,
    routing_ms: int,
    vlm_ms: int,
    total_ms: int,
) -> LatencyBreakdown:
    return LatencyBreakdown(
        frame_sampling=perception.frame_sampling_ms,
        keyframe_selection=perception.keyframe_selection_ms,
        graph_retrieval=graph_retrieval_ms,
        routing=routing_ms,
        vlm=vlm_ms,
        total=total_ms,
    )


def classify_failure(service_name: str, action_success: bool | None, vlm_used: bool, response_text: str) -> str:
    if service_name not in known_service_names():
        return "routing_error"
    if action_success is False:
        return "action_error"
    if vlm_used and not response_text:
        return "vlm_error"
    return "none"
