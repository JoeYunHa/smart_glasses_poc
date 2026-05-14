from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.schemas.context import ContextRequest
from app.services import (
    context_memory,
    device_control,
    navigation,
    safety_alert,
    scene_assistant,
)
from app.services.common import ServiceRunResult

ServiceRunner = Callable[
    [ContextRequest, list[str], str, str],
    Awaitable[ServiceRunResult],
]

SERVICE_RUNNERS: dict[str, ServiceRunner] = {
    "safety_alert": safety_alert.run,
    "device_control": device_control.run,
    "navigation": navigation.run,
    "context_memory": context_memory.run,
    "scene_assistant": scene_assistant.run,
}


def get_service_runner(service_name: str) -> ServiceRunner:
    return SERVICE_RUNNERS.get(service_name, scene_assistant.run)


def known_service_names() -> tuple[str, ...]:
    return tuple(SERVICE_RUNNERS.keys())
