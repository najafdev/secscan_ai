# SecScan AI core module
"""Unit tests for auto-fetching models across different AI providers."""

from unittest.mock import MagicMock, patch
import pytest

from ai_engine import (
    ModelProvider,
    ModelInfo,
    MODEL_CATALOG,
    DYNAMIC_MODEL_CATALOG,
    get_model_info,
    list_all_models,
    get_models_by_provider,
    register_dynamic_model,
    clear_dynamic_models,
    fetch_all_provider_models,
    normalize_provider,
    OpenAIProvider,
    AnthropicProvider,
    GoogleProvider,
    DeepSeekProvider,
    GLMProvider,
    OllamaProvider,
    OpenRouterProvider,
    NineBRouterProvider,
    CustomRouterProvider,
    LiteLLMProvider,
)


@pytest.fixture(autouse=True)
def clean_dynamic_catalog():
    """Ensure dynamic catalog is cleared before and after each test."""
    clear_dynamic_models()
    yield
    clear_dynamic_models()


def test_normalize_provider():
    """Verify normalize_provider handles various aliases and casings."""
    assert normalize_provider("openai") == ModelProvider.OPENAI
    assert normalize_provider("OpenAI") == ModelProvider.OPENAI
    assert normalize_provider("claude") == ModelProvider.ANTHROPIC
    assert normalize_provider("anthropic") == ModelProvider.ANTHROPIC
    assert normalize_provider("gemini") == ModelProvider.GOOGLE
    assert normalize_provider("google") == ModelProvider.GOOGLE
    assert normalize_provider("deepseek") == ModelProvider.DEEPSEEK
    assert normalize_provider("glm") == ModelProvider.GLM
    assert normalize_provider("zhipu") == ModelProvider.GLM
    assert normalize_provider("ollama") == ModelProvider.LOCAL
    assert normalize_provider("local") == ModelProvider.LOCAL
    assert normalize_provider("openrouter") == ModelProvider.OPENROUTER
    assert normalize_provider("9brouter") == ModelProvider.NINEBROUTER
    assert normalize_provider("custom_router") == ModelProvider.CUSTOM_ROUTER
    assert normalize_provider("custom") == ModelProvider.CUSTOM_ROUTER
    assert normalize_provider(ModelProvider.OPENAI) == ModelProvider.OPENAI
    assert normalize_provider("nonexistent-xyz") is None


def test_register_and_clear_dynamic_models():
    """Verify registering dynamic models and querying them."""
    model = ModelInfo(
        model_id="gpt-astra-dynamic-preview",
        provider=ModelProvider.OPENAI,
        display_name="GPT Astra Dynamic Preview",
        max_tokens=32768,
        supports_tools=True,
        context_window=256000,
    )
    register_dynamic_model(model)
    assert "gpt-astra-dynamic-preview" in DYNAMIC_MODEL_CATALOG
    assert get_model_info("gpt-astra-dynamic-preview") == model

    all_models = list_all_models()
    assert any(m.model_id == "gpt-astra-dynamic-preview" for m in all_models)

    openai_models = get_models_by_provider(ModelProvider.OPENAI)
    assert any(m.model_id == "gpt-astra-dynamic-preview" for m in openai_models)

    clear_dynamic_models()
    assert "gpt-astra-dynamic-preview" not in DYNAMIC_MODEL_CATALOG
    assert get_model_info("gpt-astra-dynamic-preview") is None


def test_openai_fetch_remote_models(monkeypatch):
    """Verify OpenAIProvider.fetch_remote_models fetches and parses models."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    prov = OpenAIProvider()

    mock_json = {
        "data": [
            {"id": "gpt-astra-live"},
            {"id": "gpt-6-astra-preview"},
            {"id": "o1-pro"},
        ]
    }
    with patch("ai_engine.providers._safe_http_get", return_value=mock_json):
        with patch.object(prov, "_get_client", side_effect=Exception("No SDK")):
            models = prov.fetch_remote_models()
            assert len(models) == 3
            ids = [m.model_id for m in models]
            assert "gpt-astra-live" in ids
            assert "gpt-6-astra-preview" in ids
            assert "o1-pro" in ids
            for m in models:
                assert m.provider == ModelProvider.OPENAI


def test_anthropic_fetch_remote_models(monkeypatch):
    """Verify AnthropicProvider.fetch_remote_models fetches and parses models."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    prov = AnthropicProvider()

    mock_json = {
        "data": [
            {"id": "claude-3-7-sonnet-latest", "display_name": "Claude 3.7 Sonnet Latest"},
            {"id": "claude-4-opus-preview", "display_name": "Claude 4 Opus Preview"},
        ]
    }
    with patch("ai_engine.providers._safe_http_get", return_value=mock_json):
        models = prov.fetch_remote_models()
        assert len(models) == 2
        assert models[0].model_id == "claude-3-7-sonnet-latest"
        assert models[0].provider == ModelProvider.ANTHROPIC
        assert models[0].display_name == "Claude 3.7 Sonnet Latest"


def test_google_fetch_remote_models(monkeypatch):
    """Verify GoogleProvider.fetch_remote_models parses gemini models."""
    monkeypatch.setenv("GOOGLE_API_KEY", "AIzaSyTest")
    prov = GoogleProvider()

    mock_json = {
        "models": [
            {
                "name": "models/gemini-2.0-flash-exp",
                "displayName": "Gemini 2.0 Flash Exp",
                "inputTokenLimit": 1048576,
                "outputTokenLimit": 8192,
            },
            {
                "name": "models/gemini-2.0-pro-exp",
                "displayName": "Gemini 2.0 Pro Exp",
                "inputTokenLimit": 2097152,
                "outputTokenLimit": 8192,
            },
        ]
    }
    with patch("ai_engine.providers._safe_http_get", return_value=mock_json):
        models = prov.fetch_remote_models()
        assert len(models) == 2
        assert models[0].model_id == "gemini-2.0-flash-exp"
        assert models[0].provider == ModelProvider.GOOGLE
        assert models[0].context_window == 1048576
        assert models[1].model_id == "gemini-2.0-pro-exp"


def test_deepseek_fetch_remote_models(monkeypatch):
    """Verify DeepSeekProvider.fetch_remote_models fetches models."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-ds-test")
    prov = DeepSeekProvider()

    mock_json = {
        "data": [
            {"id": "deepseek-chat"},
            {"id": "deepseek-reasoner"},
            {"id": "deepseek-v3"},
        ]
    }
    with patch("ai_engine.providers._safe_http_get", return_value=mock_json):
        with patch.object(prov, "_get_client", side_effect=Exception("No SDK")):
            models = prov.fetch_remote_models()
            assert len(models) == 3
            ids = [m.model_id for m in models]
            assert "deepseek-reasoner" in ids
            assert models[0].provider == ModelProvider.DEEPSEEK


def test_glm_fetch_remote_models(monkeypatch):
    """Verify GLMProvider.fetch_remote_models returns models."""
    monkeypatch.setenv("GLM_API_KEY", "glm-token-test")
    prov = GLMProvider()

    mock_json = {
        "data": [
            {"id": "glm-4-plus"},
            {"id": "glm-4-flash"},
        ]
    }
    with patch("ai_engine.providers._safe_http_get", return_value=mock_json):
        models = prov.fetch_remote_models()
        assert len(models) == 2
        assert models[0].model_id == "glm-4-plus"
        assert models[0].provider == ModelProvider.GLM


def test_openrouter_fetch_remote_models(monkeypatch):
    """Verify OpenRouterProvider.fetch_remote_models prefixes and registers."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    prov = OpenRouterProvider()

    mock_json = {
        "data": [
            {"id": "anthropic/claude-3.7-sonnet", "name": "Anthropic: Claude 3.7 Sonnet", "context_length": 200000},
            {"id": "openai/gpt-astra", "name": "OpenAI: GPT Astra", "context_length": 256000},
        ]
    }
    with patch("ai_engine.providers._safe_http_get", return_value=mock_json):
        models = prov.fetch_remote_models()
        assert len(models) == 2
        assert models[0].model_id == "openrouter/anthropic/claude-3.7-sonnet"
        assert models[0].provider == ModelProvider.OPENROUTER
        assert models[1].model_id == "openrouter/openai/gpt-astra"


def test_fetch_all_provider_models_integration():
    """Verify fetch_all_provider_models coordinates across providers and populates catalog."""
    mock_models_openai = [
        ModelInfo(
            model_id="dynamic-gpt-auto-1",
            provider=ModelProvider.OPENAI,
            display_name="Dynamic GPT 1",
            max_tokens=4096,
        )
    ]
    mock_models_claude = [
        ModelInfo(
            model_id="dynamic-claude-auto-1",
            provider=ModelProvider.ANTHROPIC,
            display_name="Dynamic Claude 1",
            max_tokens=4096,
        )
    ]

    with patch("ai_engine.providers.OpenAIProvider.fetch_remote_models", return_value=mock_models_openai), \
         patch("ai_engine.providers.AnthropicProvider.fetch_remote_models", return_value=mock_models_claude):

        discovered = fetch_all_provider_models(providers=["openai", "claude"], force_refresh=True)

        assert "openai" in discovered
        assert "anthropic" in discovered
        assert len(discovered["openai"]) == 1
        assert len(discovered["anthropic"]) == 1

        # Check that DYNAMIC_MODEL_CATALOG now has them
        assert "dynamic-gpt-auto-1" in DYNAMIC_MODEL_CATALOG
        assert "dynamic-claude-auto-1" in DYNAMIC_MODEL_CATALOG

        # Check get_model_info works
        info1 = get_model_info("dynamic-gpt-auto-1")
        assert info1 is not None
        assert info1.display_name == "Dynamic GPT 1"

        info2 = get_model_info("dynamic-claude-auto-1")
        assert info2 is not None
        assert info2.display_name == "Dynamic Claude 1"
