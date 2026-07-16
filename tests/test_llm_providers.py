"""
Тест реестра LLM-провайдеров.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import llm  # noqa: E402
from app.llm import (  # noqa: E402
    PROVIDERS, list_providers, _resolve_config,
    get_active_provider, get_model, reset_client,
)


def test_all_providers_registered():
    expected = {"glm", "deepseek", "qwen", "openai", "gemini", "minimax", "mimo"}
    actual = set(PROVIDERS.keys())
    assert expected == actual, f"Провайдеры: ожидаем {expected}, есть {actual}"
    print(f"✅ PROVIDERS содержит: {sorted(PROVIDERS.keys())}")


def test_providers_have_required_fields():
    for pid, cfg in PROVIDERS.items():
        assert cfg.name, f"{pid}: пустое имя"
        assert cfg.base_url.startswith("http"), f"{pid}: base_url не похож на URL — {cfg.base_url}"
        assert cfg.default_model, f"{pid}: пустая дефолтная модель"
    print(f"✅ У всех провайдеров есть name/base_url/default_model ({len(PROVIDERS)} шт.)")


def test_list_providers():
    plist = list_providers()
    assert len(plist) == len(PROVIDERS)
    for p in plist:
        assert {"id", "name", "default_model", "base_url", "notes"} <= set(p.keys())
    print(f"✅ list_providers: {len(plist)} провайдеров с полным набором полей")


def test_provider_selection():
    """Через LLM_PROVIDER выбирается нужный base_url и модель."""
    for pid, cfg in PROVIDERS.items():
        os.environ["LLM_PROVIDER"] = pid
        os.environ.pop("LLM_MODEL", None)  # сброс, чтобы взять дефолт
        reset_client()
        resolved = _resolve_config()
        assert resolved.base_url == cfg.base_url, f"{pid}: base_url {resolved.base_url} != {cfg.base_url}"
        assert get_active_provider() == pid
        # get_model() без env LLM_MODEL → должен вернуть default
        os.environ.pop("LLM_MODEL", None)
        assert get_model() == cfg.default_model, f"{pid}: model {get_model()} != {cfg.default_model}"
    print(f"✅ Все {len(PROVIDERS)} провайдеров резолвятся корректно")


def test_model_override():
    """LLM_MODEL переопределяет дефолт."""
    os.environ["LLM_PROVIDER"] = "qwen"
    os.environ["LLM_MODEL"] = "qwen-max"
    reset_client()
    assert get_model() == "qwen-max"
    # Если сбросить LLM_MODEL — должен вернуться дефолт
    os.environ.pop("LLM_MODEL", None)
    assert get_model() == "qwen-plus"
    print("✅ LLM_MODEL переопределяет дефолт провайдера")


def test_custom_provider():
    """LLM_PROVIDER=custom использует LLM_BASE_URL и LLM_MODEL из env."""
    os.environ["LLM_PROVIDER"] = "custom"
    os.environ["LLM_BASE_URL"] = "https://my-proxy.example.com/v1"
    os.environ["LLM_MODEL"] = "my-custom-model"
    reset_client()
    cfg = _resolve_config()
    assert cfg.base_url == "https://my-proxy.example.com/v1"
    assert get_model() == "my-custom-model"
    print("✅ LLM_PROVIDER=custom берёт base_url/model из env")


def test_unknown_provider_raises():
    os.environ["LLM_PROVIDER"] = "nonexistent"
    reset_client()
    try:
        _resolve_config()
    except RuntimeError as e:
        assert "Неизвестный LLM_PROVIDER" in str(e)
        assert "nonexistent" in str(e)
        print(f"✅ Неизвестный провайдер → RuntimeError: {e}")
    else:
        raise AssertionError("Должен был выкинуть RuntimeError")


def test_client_creation_is_compatible_with_pinned_httpx(monkeypatch):
    import asyncio
    from app.llm import get_client
    monkeypatch.setenv("LLM_PROVIDER", "qwen")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_TRUST_ENV", "false")
    reset_client()
    client = get_client()
    assert client is not None
    asyncio.run(client.close())
    reset_client()


def main():
    test_all_providers_registered()
    test_providers_have_required_fields()
    test_list_providers()
    test_provider_selection()
    test_model_override()
    test_custom_provider()
    test_unknown_provider_raises()
    print("\n🎉 Все проверки LLM-провайдеров прошли.")


if __name__ == "__main__":
    main()
