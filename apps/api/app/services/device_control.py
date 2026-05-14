"""DeviceControl service."""

from app.actions.executor import execute_device_action
from app.schemas.context import ContextRequest
from app.services.common import ServiceRunResult


async def run(
    ctx: ContextRequest,
    image_b64_list: list[str],
    graph_context: str,
    request_id: str,
) -> ServiceRunResult:
    if not ctx.nearby_devices:
        return "No controllable nearby devices were provided.", False, None, {}

    target = ctx.nearby_devices[0]
    request_lower = ctx.user_request.lower()
    for dev in ctx.nearby_devices:
        if dev.name.lower() in request_lower or dev.type.lower() in request_lower:
            target = dev
            break

    action_result = execute_device_action(target, ctx.user_request)

    if action_result.success:
        response = f"{target.name}: {action_result.action} completed."
    else:
        response = f"Device control failed: {action_result.message}"

    return response, False, action_result, {}
