"""ContextMemory service."""

import asyncio

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
    # Perform dedicated retrieval with a larger budget.  The planner-provided
    # graph_context is capped at 500 chars (auxiliary budget for perception services)
    # and is insufficient here where retrieved content IS the primary answer source.
    # asyncio.to_thread avoids blocking the event loop on fastembed + Qdrant I/O.
    retrieval_result = await asyncio.to_thread(retrieve_context, ctx.user_request, 8)
    similar = retrieval_result.combined
    if not similar:
        return "관련된 이전 기억을 찾지 못했습니다.", False, None, {"retrieved_nodes": 0}

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

    text, vlm_used, action, usage = await run_vlm_service(prompt, image_b64=None)
    usage["retrieved_nodes"] = len(similar)
    return text, vlm_used, action, usage
