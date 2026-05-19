"""Async OpenAI client for VLM and text model calls."""

from openai import AsyncOpenAI

from app.config import settings

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def call_vlm(prompt: str, image_b64: str | None = None, max_tokens: int = 512) -> tuple[str, dict]:
    client = get_client()
    content: list = []
    if image_b64:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
        })
    content.append({"type": "text", "text": prompt})

    model = settings.openai_vision_model if image_b64 else settings.openai_text_model
    resp = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": content}],
        max_tokens=max_tokens,
    )
    usage: dict = {}
    if resp.usage:
        usage = {
            "prompt_tokens": resp.usage.prompt_tokens,
            "completion_tokens": resp.usage.completion_tokens,
            "total_tokens": resp.usage.total_tokens,
        }
    # Track actual transmitted bytes so planner can report accurate image_payload_bytes.
    usage["prompt_bytes"] = len(prompt.encode("utf-8"))
    if image_b64:
        usage["image_bytes"] = len(image_b64.encode("utf-8"))
    return resp.choices[0].message.content or "", usage
