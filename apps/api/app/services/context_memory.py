"""ContextMemory service."""

from app.groq_client import call_vlm
from app.memory import retrieval
from app.schemas.agent import ActionResult
from app.schemas.context import ContextRequest


async def run(
    ctx: ContextRequest,
    image_b64_list: list[str],
    graph_context: str,
    request_id: str,
) -> tuple[str, bool, ActionResult | None]:
    similar = retrieval.find_similar(ctx.user_request, top_k=5)

    if not similar:
        return "No relevant prior memory was found for this request.", False, None

    memory_text = "\n".join(f"- {s}" for s in similar)
    prompt = (
        "You are a memory retrieval assistant for smart glasses. "
        "Use the past context below to answer the user's question in 2-3 concise sentences.\n\n"
        f"Past context:\n{memory_text}\n\n"
        f"User request: {ctx.user_request}"
    )

    response = await call_vlm(prompt, image_b64=None)
    return response, True, None
