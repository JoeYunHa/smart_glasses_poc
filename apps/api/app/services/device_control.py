"""DeviceControl service.

Matches user intent to a nearby device, runs guardrail,
and dispatches mock action execution.
"""

from app.actions.executor import execute_device_action
from app.groq_client import call_vlm
from app.schemas.agent import ActionResult
from app.schemas.context import ContextRequest


async def run(
    ctx: ContextRequest,
    image_b64_list: list[str],
    graph_context: str,
    request_id: str,
) -> tuple[str, bool, ActionResult | None]:
    if not ctx.nearby_devices:
        return "근처에 제어 가능한 기기가 없습니다.", False, None

    # Simple heuristic: pick first device that matches request keywords
    target = ctx.nearby_devices[0]
    for dev in ctx.nearby_devices:
        if dev.name in ctx.user_request or dev.type in ctx.user_request:
            target = dev
            break

    action_result = execute_device_action(target, ctx.user_request)

    if action_result.success:
        response = f"{target.name}: {action_result.action} 완료했습니다."
    else:
        response = f"기기 제어 실패: {action_result.message}"

    return response, False, action_result
