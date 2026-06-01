"""
LLM-клиент. Совместим с любым OpenAI-compat API:
- z.ai GLM 5.1
- DeepSeek
- OpenAI
- Gemini OpenAI-compat
"""
from __future__ import annotations
import os
from openai import AsyncOpenAI

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        base_url = os.getenv("LLM_BASE_URL", "https://api.z.ai/api/coding/paas/v4")
        api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            raise RuntimeError("LLM_API_KEY не задан. Заполни .env")
        _client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    return _client


def get_model() -> str:
    return os.getenv("LLM_MODEL", "glm-5.1")


def get_temperature() -> float:
    try:
        return float(os.getenv("LLM_TEMPERATURE", "0.4"))
    except ValueError:
        return 0.4


async def chat(messages: list[dict], *, temperature: float | None = None, max_tokens: int = 2500) -> str:
    """Синхронный вызов LLM, возвращает текст ответа."""
    client = get_client()
    response = await client.chat.completions.create(
        model=get_model(),
        messages=messages,
        temperature=temperature if temperature is not None else get_temperature(),
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""
