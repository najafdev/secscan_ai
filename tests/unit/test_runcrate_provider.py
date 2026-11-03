# HACKNOVA core module
"""Unit tests for the Runcrate provider."""

from unittest import mock

from ai_engine.model_registry import (
    MODEL_CATALOG,
    ModelProvider,
    get_model_info,
    normalize_provider,
)
from ai_engine.providers import ProviderFactory, RuncrateProvider


def test_runcrate_in_model_provider_enum():
    """Runcrate must be a member of the ModelProvider enum."""
    assert ModelProvider.RUNCRATE.value == "runcrate"
    assert normalize_provider("runcrate") is ModelProvider.RUNCRATE


def test_runcrate_catalog_entries():
    """Registered Runcrate models keep their exact upstream model ids."""
    entry = MODEL_CATALOG["deepseek-ai/DeepSeek-V4.1-Flash"]
    assert entry.provider is ModelProvider.RUNCRATE
    assert entry.model_id == "deepseek-ai/DeepSeek-V4.1-Flash"
    assert entry.context_window == 1_048_576
    assert MODEL_CATALOG["openai/gpt-oss-120b"].provider is ModelProvider.RUNCRATE


def test_runcrate_prefix_resolves_dynamic_model():
    """runcrate/<model> routes any Runcrate model without the prefix."""
    info = get_model_info("runcrate/Qwen/Qwen3.6-35B-A3B")
    assert info.provider is ModelProvider.RUNCRATE
    assert info.model_id == "Qwen/Qwen3.6-35B-A3B"


def test_provider_factory_resolves_runcrate(monkeypatch):
    """ProviderFactory returns a RuncrateProvider for Runcrate models."""
    monkeypatch.setenv("RUNCRATE_API_KEY", "test-key")
    ProviderFactory._providers.pop(ModelProvider.RUNCRATE, None)

    provider, info = ProviderFactory.get_provider_for_model("zai-org/GLM-5.3")
    assert isinstance(provider, RuncrateProvider)
    assert provider.provider_name == "Runcrate"
    assert info.model_id == "zai-org/GLM-5.3"
    ProviderFactory._providers.pop(ModelProvider.RUNCRATE, None)


def test_provider_override_routes_unknown_model(monkeypatch):
    """SECSCAN_AI_PROVIDER=runcrate dispatches an uncataloged model to Runcrate."""
    monkeypatch.setenv("SECSCAN_AI_PROVIDER", "runcrate")
    monkeypatch.delenv("SECSCAN_AI_CUSTOM_ROUTE", raising=False)
    monkeypatch.delenv("CUSTOM_ROUTER_BASE_URL", raising=False)

    provider, info = ProviderFactory.get_provider_for_model(
        "Qwen/Qwen3.6-35B-A3B", api_key="k"
    )
    assert isinstance(provider, RuncrateProvider)
    assert info.provider is ModelProvider.RUNCRATE


def test_defaults_and_env(monkeypatch):
    """Key and base URL come from the environment, with the public endpoint as default."""
    monkeypatch.delenv("RUNCRATE_API_KEY", raising=False)
    monkeypatch.delenv("RUNCRATE_BASE_URL", raising=False)
    prov = RuncrateProvider()
    assert prov.is_available() is False
    assert prov.base_url == "https://api.runcrate.ai/v1"

    monkeypatch.setenv("RUNCRATE_API_KEY", "rc_test")
    monkeypatch.setenv("RUNCRATE_BASE_URL", "http://localhost:9000/v1")
    prov = RuncrateProvider()
    assert prov.is_available() is True
    assert prov.base_url == "http://localhost:9000/v1"


def test_chat_completion_strips_route_prefix(monkeypatch):
    """chat_completion sends the bare model id to the OpenAI-compatible client."""
    prov = RuncrateProvider(api_key="rc_test")
    fake_client = mock.MagicMock()
    fake_client.chat.completions.create.return_value.choices = [
        mock.MagicMock(message=mock.MagicMock(content="ok"))
    ]
    prov._client = fake_client

    assert (
        prov.chat_completion(
            "runcrate/deepseek-ai/DeepSeek-V4.1-Flash",
            [{"role": "user", "content": "hi"}],
            max_tokens=300,
        )
        == "ok"
    )
    kwargs = fake_client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "deepseek-ai/DeepSeek-V4.1-Flash"
    assert kwargs["max_tokens"] == 300


def test_fetch_remote_models_parses_catalog(monkeypatch):
    """/models entries become Runcrate ModelInfo objects with their context length."""
    payload = {"data": [{"id": "zai-org/GLM-5.3-Flash", "context_length": 1048576}]}
    with mock.patch("ai_engine.providers._safe_http_get", return_value=payload) as get:
        models = RuncrateProvider(api_key="rc_test").fetch_remote_models()

    assert get.call_args.args[0] == "https://api.runcrate.ai/v1/models"
    assert get.call_args.kwargs["headers"]["Authorization"] == "Bearer rc_test"
    assert [m.model_id for m in models] == ["zai-org/GLM-5.3-Flash"]
    assert models[0].provider is ModelProvider.RUNCRATE
    assert models[0].context_window == 1048576


def test_fetch_remote_models_without_key_skips_request():
    """No key means no network call and no models."""
    with mock.patch("ai_engine.providers._safe_http_get") as get:
        assert RuncrateProvider(api_key="").fetch_remote_models() == []
    get.assert_not_called()
