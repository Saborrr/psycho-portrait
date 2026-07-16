"""
LLM-клиент. Совместим с любым OpenAI-compat API.

Провайдеры (все OpenAI-compat, в .env выбирается через LLM_PROVIDER):
  - mimo      — Xiaomi MiMo V2.5 Pro (Token Plan)
  - glm       — z.ai GLM 5.1
  - deepseek  — DeepSeek
  - qwen      — Alibaba Qwen через DashScope
  - openai    — ChatGPT / OpenAI
  - gemini    — Google Gemini OpenAI-compat endpoint
  - minimax   — MiniMax (Anthropic-compat, не OpenAI)
  - custom    — свои base_url / api_key / model

Выбор:
  LLM_PROVIDER=qwen          # выберет Qwen-эндпоинт и qwen-plus по дефолту
  LLM_MODEL=qwen-max         # переопределит модель внутри провайдера
  LLM_API_KEY=...            # обязателен
  LLM_BASE_URL=...           # опционально (если хочется свой endpoint)
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
import httpx
from openai import AsyncOpenAI


# === Реестр провайдеров ===

@dataclass
class ProviderConfig:
    name: str
    base_url: str
    default_model: str
    env_key: str = "LLM_API_KEY"
    extra_env: dict = field(default_factory=dict)  # доп. переменные окружения
    notes: str = ""


PROVIDERS: dict[str, ProviderConfig] = {
    "glm": ProviderConfig(
        name="z.ai GLM",
        base_url="https://api.z.ai/api/coding/paas/v4",
        default_model="glm-5.1",
        notes="Z.ai coding plan (Китай). Текущий основной.",
    ),
    "deepseek": ProviderConfig(
        name="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        default_model="deepseek-chat",
        notes="DeepSeek API. Дешёвый, сильный на коде и агенте.",
    ),
    "qwen": ProviderConfig(
        name="Alibaba Qwen (DashScope)",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        default_model="qwen-plus",
        notes=(
            "Qwen через DashScope OpenAI-compat. "
            "Модели: qwen-turbo / qwen-plus / qwen-max / qwen-long / qwen-coder-plus. "
            "API-ключ: Alibaba Cloud → DashScope."
        ),
    ),
    "openai": ProviderConfig(
        name="OpenAI / ChatGPT",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
        notes=(
            "OpenAI. Модели: gpt-4o-mini / gpt-4o / gpt-4.1 / gpt-5 / o3-mini и т.д. "
            "API-ключ: platform.openai.com → API keys."
        ),
    ),
    "gemini": ProviderConfig(
        name="Google Gemini (OpenAI-compat)",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        default_model="gemini-2.0-flash",
        notes="Gemini через OpenAI-compat эндпоинт. Бесплатный tier.",
    ),
    "minimax": ProviderConfig(
        name="MiniMax (OpenAI-compat)",
        base_url="https://api.minimax.io/v1",
        default_model="MiniMax-M3",
        notes=(
            "MiniMax M3 через OpenAI-compat эндпоинт. "
            "Мультимодал (vision), 1M контекст, дешёвый. "
            "Для китайских пользователей есть зеркало api.minimaxi.com/v1."
        ),
    ),
    "mimo": ProviderConfig(
        name="Xiaomi MiMo (Token Plan)",
        base_url="https://token-plan-sgp.xiaomimimo.com/v1",
        default_model="mimo-v2.5-pro",
        notes=(
            "Xiaomi MiMo V2.5 Pro через Token Plan. "
            "1M контекст, reasoning, дешёвый. "
            "Базовый URL зависит от региона: sgp / ams / cn. "
            "Документация: https://mimo.mi.com/docs/en-US/tokenplan/integration/openclaw"
        ),
    ),
}


def list_providers() -> list[dict]:
    """Для /api/llm/providers — список доступных провайдеров с дефолтами."""
    return [
        {
            "id": k,
            "name": v.name,
            "default_model": v.default_model,
            "base_url": v.base_url,
            "notes": v.notes,
        }
        for k, v in PROVIDERS.items()
    ]


# === Клиент ===

_client: AsyncOpenAI | None = None
_active_config: ProviderConfig | None = None


def _resolve_config() -> ProviderConfig:
    """Определить активного провайдера по env."""
    global _active_config
    provider_id = os.getenv("LLM_PROVIDER", "qwen").lower()
    if provider_id == "custom":
        # Свой base_url / model / api_key
        base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        default_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        cfg = ProviderConfig(name="Custom", base_url=base_url, default_model=default_model)
    elif provider_id in PROVIDERS:
        cfg = PROVIDERS[provider_id]
    else:
        raise RuntimeError(
            f"Неизвестный LLM_PROVIDER={provider_id!r}. "
            f"Доступные: {', '.join(list(PROVIDERS.keys()) + ['custom'])}"
        )
    _active_config = cfg
    return cfg


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        cfg = _resolve_config()
        api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            raise RuntimeError(
                f"LLM_API_KEY не задан. Провайдер: {cfg.name}. "
                f"Положи в .env ключ от {cfg.name}."
            )
        # base_url можно переопределить через env (для custom-эндпоинтов)
        base_url = os.getenv("LLM_BASE_URL", cfg.base_url)
        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
        trust_env = os.getenv("LLM_TRUST_ENV", "false").lower() in {"1", "true", "yes", "on"}
        _client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max(0, int(os.getenv("LLM_MAX_RETRIES", "2"))),
            http_client=httpx.AsyncClient(timeout=timeout, trust_env=trust_env),
        )
    return _client


def get_model() -> str:
    """Модель: либо LLM_MODEL из env, либо дефолт провайдера."""
    cfg = _resolve_config()
    return os.getenv("LLM_MODEL", cfg.default_model)


def get_active_provider() -> str:
    """ID текущего провайдера (для логов/UI)."""
    return os.getenv("LLM_PROVIDER", "qwen").lower()


def get_temperature() -> float:
    try:
        return float(os.getenv("LLM_TEMPERATURE", "0.4"))
    except ValueError:
        return 0.4


async def chat(messages: list[dict], *, temperature: float | None = None, max_tokens: int = 2500) -> str:
    """Асинхронный вызов LLM, возвращает текст ответа."""
    client = get_client()
    response = await client.chat.completions.create(
        model=get_model(),
        messages=messages,
        temperature=temperature if temperature is not None else get_temperature(),
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


def reset_client() -> None:
    """Сбросить кэшированный клиент (для тестов или после смены env)."""
    global _client, _active_config
    _client = None
    _active_config = None
