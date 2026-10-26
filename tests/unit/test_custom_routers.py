# SecScan AI core module
"""Unit tests for new models (gpt-astra, etc.) and custom routing (openrouter, 9brouter, custom_router)."""

import os
from unittest.mock import MagicMock, patch
import pytest

from ai_engine import (
    ModelProvider,
    ModelInfo,
    MODEL_CATALOG,
    get_model_info,
    list_all_models,
    get_models_by_provider,
    get_available_providers,
    ProviderFactory,
    OpenRouterProvider,
    NineBRouterProvider,
    CustomRouterProvider,
    get_advanced_ai_engine,
)


def test_gpt_astra_and_new_models_in_catalog():
    """Verify that gpt-astra, gpt-6-astra and other requested models exist in catalog."""
    assert "gpt-astra" in MODEL_CATALOG
    assert "gpt-6-astra" in MODEL_CATALOG
    assert "claude-3.7-sonnet" in MODEL_CATALOG
    assert "gemini-2.0-flash" in MODEL_CATALOG
    assert "gemini-2.0-pro" in MODEL_CATALOG
    assert "deepseek-r1-zero" in MODEL_CATALOG
    assert "o1" in MODEL_CATALOG
    assert "o1-mini" in MODEL_CATALOG

    astra = MODEL_CATALOG["gpt-astra"]
    assert astra.provider == ModelProvider.OPENAI
    assert astra.display_name == "GPT Astra"
    assert astra.max_tokens == 32768
    assert astra.context_window == 256000
    assert astra.supports_tools is True

    astra6 = MODEL_CATALOG["gpt-6-astra"]
    assert astra6.provider == ModelProvider.OPENAI
    assert astra6.display_name == "GPT-6 Astra"


def test_custom_routes_in_catalog():
    """Verify pre-registered routes for OpenRouter, 9B Router, and Custom Router."""
    assert "openrouter/openai/gpt-astra" in MODEL_CATALOG
    assert "openrouter/anthropic/claude-3.7-sonnet" in MODEL_CATALOG
    assert "openrouter/deepseek/deepseek-r1" in MODEL_CATALOG
    assert "openrouter/meta-llama/llama-3.3-70b-instruct" in MODEL_CATALOG

    assert "9brouter/agent-router" in MODEL_CATALOG
    assert "9brouter/qwen2.5:9b" in MODEL_CATALOG
    assert "9brouter/gemma2:9b" in MODEL_CATALOG

    assert "custom_router/default" in MODEL_CATALOG

    router_9b = MODEL_CATALOG["9brouter/agent-router"]
    assert router_9b.provider == ModelProvider.NINEBROUTER
    assert "9B" in router_9b.display_name

    custom_r = MODEL_CATALOG["custom_router/default"]
    assert custom_r.provider == ModelProvider.CUSTOM_ROUTER


def test_dynamic_routing_prefixes():
    """Verify dynamic model resolution when using router prefixes."""
    # OpenRouter dynamic routing
    info_or = get_model_info("openrouter/mistralai/mistral-large")
    assert info_or is not None
    assert info_or.provider == ModelProvider.OPENROUTER
    assert info_or.model_id == "mistralai/mistral-large"

    # 9B Router dynamic routing
    info_9b = get_model_info("9brouter/custom-pentest-9b")
    assert info_9b is not None
    assert info_9b.provider == ModelProvider.NINEBROUTER
    assert info_9b.model_id == "custom-pentest-9b"

    # Custom router dynamic routing (custom_router/ or custom/)
    info_cust1 = get_model_info("custom_router/sec-gpt-large")
    assert info_cust1 is not None
    assert info_cust1.provider == ModelProvider.CUSTOM_ROUTER
    assert info_cust1.model_id == "sec-gpt-large"

    info_cust2 = get_model_info("custom/my-fine-tuned-model")
    assert info_cust2 is not None
    assert info_cust2.provider == ModelProvider.CUSTOM_ROUTER
    assert info_cust2.model_id == "my-fine-tuned-model"

    # Non-existent model without prefix still returns None
    assert get_model_info("unknown-model-xyz") is None


def test_openrouter_custom_base_url(monkeypatch):
    """Verify OpenRouterProvider respects OPENROUTER_BASE_URL environment variable."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-or-key")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://custom.openrouter.proxy/v1")

    prov = OpenRouterProvider()
    assert prov.api_key == "test-or-key"
    assert prov.base_url == "https://custom.openrouter.proxy/v1"
    assert prov.is_available() is True
    assert prov.provider_name == "OpenRouter"


def test_nineb_router_provider(monkeypatch):
    """Verify NineBRouterProvider initialization, configuration, and availability."""
    monkeypatch.setenv("NINEBROUTER_BASE_URL", "http://router.internal:8000/v1")
    monkeypatch.setenv("NINEBROUTER_API_KEY", "secret-9b-key")

    prov = NineBRouterProvider()
    assert prov.base_url == "http://router.internal:8000/v1"
    assert prov.api_key == "secret-9b-key"
    assert prov.is_available() is True
    assert prov.provider_name == "9B Router"

    # Test execution with mocked requests
    with patch("ai_engine.providers.requests.post", create=True) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Dispatched to sqlmap tool and high-priority exploitation"}}]
        }
        mock_post.return_value = mock_resp

        # Ensure _HAS_OPENAI check falls back or uses mock
        with patch.object(prov, "_get_client", side_effect=Exception("Client error")):
            out = prov.chat_completion(
                model_id="agent-router-9b",
                messages=[{"role": "user", "content": "Analyze SQL injection on /login"}],
            )
            assert "sqlmap" in out


def test_custom_router_provider(monkeypatch):
    """Verify CustomRouterProvider handles arbitrary gateway endpoints."""
    monkeypatch.setenv("CUSTOM_ROUTER_BASE_URL", "https://ai-gateway.corp.net/v1")
    monkeypatch.setenv("CUSTOM_ROUTER_API_KEY", "corp-token-12345")

    prov = CustomRouterProvider()
    assert prov.base_url == "https://ai-gateway.corp.net/v1"
    assert prov.api_key == "corp-token-12345"
    assert prov.is_available() is True
    assert prov.provider_name == "Custom Router"

    with patch("ai_engine.providers.requests.post", create=True) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Custom router response from gateway"}}]
        }
        mock_post.return_value = mock_resp

        with patch.object(prov, "_get_client", side_effect=Exception("Client error")):
            out = prov.chat_completion(
                model_id="sec-gpt",
                messages=[{"role": "user", "content": "Hello"}],
            )
            assert out == "Custom router response from gateway"


def test_provider_factory_dynamic_routing_and_custom_route(monkeypatch):
    """Verify ProviderFactory resolves dynamic routes and accepts custom route override."""
    monkeypatch.setenv("NINEBROUTER_BASE_URL", "http://localhost:8000/v1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    # 1. Resolve gpt-astra
    prov, info = ProviderFactory.get_provider_for_model("gpt-astra")
    assert prov.provider_name == "OpenAI"
    assert info.model_id == "gpt-astra"

    # 2. Resolve openrouter dynamic model
    prov_or, info_or = ProviderFactory.get_provider_for_model("openrouter/deepseek/deepseek-r1")
    assert prov_or.provider_name == "OpenRouter"
    assert info_or.model_id == "deepseek/deepseek-r1"

    # 3. Resolve 9brouter dynamic model
    prov_9b, info_9b = ProviderFactory.get_provider_for_model("9brouter/agent-router")
    assert prov_9b.provider_name == "9B Router"
    assert info_9b.model_id == "agent-router-9b"

    # 4. Resolve with explicit custom_route URL override
    prov_cust, info_cust = ProviderFactory.get_provider_for_model(
        "custom/proprietary-sec-model",
        custom_route="http://10.10.10.50:9000/v1"
    )
    assert prov_cust.provider_name == "Custom Router"
    assert prov_cust.base_url == "http://10.10.10.50:9000/v1"
    assert info_cust.model_id == "proprietary-sec-model"


def test_advanced_ai_engine_custom_route_integration(monkeypatch):
    """Verify AdvancedAIEngine initializes with custom route."""
    monkeypatch.setenv("CUSTOM_ROUTER_BASE_URL", "http://localhost:8080/v1")
    engine = get_advanced_ai_engine(
        model_id="custom_router/default",
        custom_route="http://custom.gateway:5000/v1"
    )
    assert engine.custom_route == "http://custom.gateway:5000/v1"
    current = engine.get_current_model()
    assert current["custom_route"] == "http://custom.gateway:5000/v1"
    assert current["provider"] == "custom_router"
