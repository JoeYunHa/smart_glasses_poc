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
        # Put "off" before "on" and include Korean imperative forms to avoid
        # defaulting to supported_actions[0] on common requests like "불 꺼줘".
        (["turn off", "switch off", "power off", "stop", "꺼", "끄", "꺼줘", "꺼 줘"], "turn_off"),
        (["turn on", "switch on", "power on", "start", "켜", "켜줘", "켜 줘"], "turn_on"),
        (["volume", "louder", "quieter"], "set_volume"),
        (["brightness", "brighter", "dimmer"], "set_brightness"),
        (["play"], "play"),
        (["pause", "hold"], "pause"),
        # "unlock" must be checked before "lock" because it contains "lock".
        (["unlock", "open", "열어", "잠금 해제"], "unlock"),
        (["lock", "잠가", "잠궈", "잠금"], "lock"),
        (["temperature", "cooler", "warmer"], "set_temperature"),
        (["color"], "set_color"),
        (["mode"], "set_mode"),
        (["channel"], "change_channel"),
    ]
    for keywords, action in mapping:
        if action in supported_actions and any(kw in request_lower for kw in keywords):
            return action
    # Safer fallback for on/off capable devices: prefer turn_off over turn_on.
    if "turn_off" in supported_actions:
        return "turn_off"
    return supported_actions[0] if supported_actions else "turn_off"
