"""ContextMemory service.

Retrieves past scenes from GraphRAG (NetworkX + vector store)
to answer temporal queries like "아까 본 카페".
"""

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
        return "관련 과거 기억이 없습니다. 더 많은 장면을 탐색한 뒤 다시 시도하세요.", False, None

    memory_text = "\n".join(f"- {s}" for s in similar)
    prompt = (
        "당신은 스마트 안경의 기억 검색 모듈입니다. "
        "아래 과거 기억을 바탕으로 사용자의 질문에 답하세요. "
        "한국어로 2-3문장으로 답하세요.\n\n"
        f"과거 기억:\n{memory_text}\n\n"
        f"사용자 질문: {ctx.user_request}"
    )

    response = await call_vlm(prompt, image_b64=None)
    return response, True, None
