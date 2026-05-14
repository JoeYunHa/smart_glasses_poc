"""Mock action executor."""

from app.actions.device_registry import get_capability, infer_action
from app.agent.policy import check_action_allowed
from app.schemas.agent import ActionResult
from app.schemas.context import DeviceInfo


def execute_device_action(device: DeviceInfo, user_request: str) -> ActionResult:
    cap = get_capability(device.type)
    if cap is None:
        return ActionResult(
            device_id=device.device_id,
            action="unknown",
            success=False,
            message=f"Unsupported device type: {device.type}.",
        )

    action = infer_action(user_request, cap.supported_actions)
    allowed, reason = check_action_allowed(action, cap.risk_level, cap.requires_confirmation)
    if not allowed:
        return ActionResult(
            device_id=device.device_id,
            action=action,
            success=False,
            message=reason,
        )

    return ActionResult(
        device_id=device.device_id,
        action=action,
        success=True,
        message=f"[MOCK] Executed '{action}' on {device.name}.",
    )
