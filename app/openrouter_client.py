# app/openrouter_client.py
from typing import Any, AsyncIterator, Tuple
from openai import AsyncOpenAI
from .settings import settings

# Инициализируем клиента OpenAI, но указываем base_url OpenRouter
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
    default_headers={
        **({"HTTP-Referer": settings.OPENROUTER_SITE_URL} if settings.OPENROUTER_SITE_URL else {}),
        **({"X-Title": settings.OPENROUTER_APP_NAME} if settings.OPENROUTER_APP_NAME else {}),
    },
    # при необходимости: timeout=60.0
)

async def create_chat_completion(
    messages: list[dict[str, Any]],
    model: str | None = None,
    **kwargs: Any,
) -> dict:
    """
    Неблокирующий вызов chat.completions (без стриминга).
    kwargs пробрасываются в openai (temperature, max_tokens и т.д.)
    """
    resp = await client.chat.completions.create(
        model=model or settings.OPENROUTER_MODEL,
        messages=messages,
        **kwargs,
    )
    # Преобразуем pydantic-объект в dict (у клиента есть .dict()/.model_dump())
    return resp.model_dump()

def extract_text(resp: dict) -> Tuple[str, str | None, str | None]:
    """
    Возвращает (content, model, finish_reason) из ответа OpenRouter (формат OpenAI-like).
    """
    choice = (resp.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    return (
        msg.get("content") or "",
        resp.get("model"),
        choice.get("finish_reason"),
    )

# --- Вариант со стримингом (если хочешь потоковую отдачу) ---

async def stream_chat_completion(
    messages: list[dict[str, Any]],
    model: str | None = None,
    **kwargs: Any,
) -> AsyncIterator[str]:
    stream = await client.chat.completions.create(
        model=model or settings.OPENROUTER_MODEL,
        messages=messages,
        stream=True,
        **kwargs,
    )
    async for event in stream:
        for c in event.choices:
            delta = getattr(c, "delta", None)
            if delta and getattr(delta, "content", None):
                yield delta.content