"""Device capability registry.

Maps device type → allowed actions with risk metadata.
Used by the guardrail before any action is dispatched.
"""

from dataclasses import dataclass, field


@dataclass
class DeviceCapability:
    device_type: str
    supported_actions: list[str] = field(default_factory=list)
    risk_level: str = "low"
    requires_confirmation: bool = False


_REGISTRY: dict[str, DeviceCapability] = {
    "smart_light": DeviceCapability(
        device_type="smart_light",
        supported_actions=["turn_on", "turn_off", "set_brightness", "set_color"],
        risk_level="low",
    ),
    "speaker": DeviceCapability(
        device_type="speaker",
        supported_actions=["play", "pause", "set_volume", "stop"],
        risk_level="low",
    ),
    "tv": DeviceCapability(
        device_type="tv",
        supported_actions=["turn_on", "turn_off", "set_volume", "change_channel"],
        risk_level="low",
    ),
    "air_conditioner": DeviceCapability(
        device_type="air_conditioner",
        supported_actions=["turn_on", "turn_off", "set_temperature", "set_mode"],
        risk_level="medium",
    ),
    "door_lock": DeviceCapability(
        device_type="door_lock",
        supported_actions=["lock", "unlock"],
        risk_level="high",
        requires_confirmation=True,
    ),
}


def get_capability(device_type: str) -> DeviceCapability | None:
    return _REGISTRY.get(device_type)


def infer_action(user_request: str, supported_actions: list[str]) -> str:
    """Map Korean request keywords to a supported action name."""
    mapping: list[tuple[list[str], str]] = [
        (["켜", "켜줘", "on"], "turn_on"),
        (["꺼", "꺼줘", "off"], "turn_off"),
        (["볼륨", "소리"], "set_volume"),
        (["밝기"], "set_brightness"),
        (["틀어", "재생", "play"], "play"),
        (["일시정지", "멈춰"], "pause"),
        (["잠가", "잠금"], "lock"),
        (["열어", "열어줘"], "unlock"),
        (["온도", "temperature"], "set_temperature"),
    ]
    for keywords, action in mapping:
        if action in supported_actions and any(kw in user_request for kw in keywords):
            return action
    return supported_actions[0] if supported_actions else "turn_off"
