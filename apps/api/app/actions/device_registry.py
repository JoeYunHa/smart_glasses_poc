"""Device capability registry."""

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
    """Map user request keywords to a supported action name."""
    request_lower = user_request.lower()
    mapping: list[tuple[list[str], str]] = [
        (["turn on", "switch on", "start"], "turn_on"),
        (["turn off", "switch off", "stop"], "turn_off"),
        (["volume", "louder", "quieter"], "set_volume"),
        (["brightness", "brighter", "dimmer"], "set_brightness"),
        (["play"], "play"),
        (["pause", "hold"], "pause"),
        (["lock"], "lock"),
        (["unlock", "open"], "unlock"),
        (["temperature", "cooler", "warmer"], "set_temperature"),
        (["color"], "set_color"),
        (["mode"], "set_mode"),
        (["channel"], "change_channel"),
    ]
    for keywords, action in mapping:
        if action in supported_actions and any(kw in request_lower for kw in keywords):
            return action
    return supported_actions[0] if supported_actions else "turn_off"
