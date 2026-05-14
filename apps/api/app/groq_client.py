from groq import Groq
from app.config import settings

_client: Groq | None = None


def get_groq_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


async def call_vlm(prompt: str, image_b64: str | None = None, max_tokens: int = 512) -> str:
    client = get_groq_client()
    content: list = []
    if image_b64:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
        })
    content.append({"type": "text", "text": prompt})

    model = settings.groq_model if image_b64 else settings.groq_text_model
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": content}],
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""
