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
    if graph_context:
        memory_text = graph_context
    else:
        retrieval_result = retrieve_context(ctx.user_request, top_k=5)
        similar = retrieval_result.combined
        if not similar:
            return "No relevant prior memory was found for this request.", False, None, {}
        memory_text = "\n".join(f"- {s}" for s in similar)

    prompt = (
        "You are a memory retrieval assistant for smart glasses. "
        "Use the past context below to answer the user's question in 2-3 concise sentences.\n\n"
        f"Past context:\n{memory_text}\n\n"
        f"User request: {ctx.user_request}"
    )

    return await run_vlm_service(prompt, image_b64=None)
