"""ContextMemory service."""

from app.memory.retrieval import retrieve_context
from app.schemas.context import ContextRequest
from app.services.common import ServiceRunResult, run_vlm_service


async def run(
    ctx: ContextRequest,
    image_b64_list: list[str],
    graph_context: str,
    request_id: str,
    semantic_prompt: str = "",
) -> ServiceRunResult:
    # Use planner's already-retrieved graph_context to avoid a duplicate retrieval call.
    # Only fall back to a fresh retrieval when graph_context is empty (e.g. baseline mode
    # or first request with no prior stored context).
    # Use planner's already-retrieved graph_context to avoid a duplicate retrieval call.
    # Only fall back to a fresh retrieval when graph_context is empty (e.g. baseline mode
    # or first request with no prior stored context).
    if graph_context:
        memory_text = graph_context
    else:
        retrieval_result = retrieve_context(ctx.user_request, top_k=5)
        similar = retrieval_result.combined
        if not similar:
            return "관련된 이전 기억을 찾지 못했습니다.", False, None, {}
        memory_text = "\n".join(f"- {s}" for s in similar)

    prompt = (
        "You are a memory assistant embedded in smart glasses. "
        "The user is asking about something they encountered earlier. "
        "Answer using only the past context provided — do not invent details not present in it. "
        "If the context is insufficient to answer, say so clearly in one sentence rather than guessing. "
        "Keep the total response under 3 sentences. Respond in Korean.\n\n"
        f"Past context:\n{memory_text}\n\n"
        f"User request: {ctx.user_request}"
    )

    return await run_vlm_service(prompt, image_b64=None)
