# SecScan AI core module
"""Unit tests for the multi-provider AI model registry and client factory."""

import os
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
)

def test_model_catalog_completeness():
    """Verify that key requested models exist in the catalog."""
    assert "gpt-5" in MODEL_CATALOG
    assert "gpt-5.6" in MODEL_CATALOG
    assert "claude-sonnet-5" in MODEL_CATALOG
    assert "claude-opus-4.8" in MODEL_CATALOG
    assert "gemini-3.5-flash" in MODEL_CATALOG
    assert "gemini-3.1-pro" in MODEL_CATALOG
    assert "deepseek-r1" in MODEL_CATALOG
    assert "glm-5.2" in MODEL_CATALOG
    
    gpt5 = MODEL_CATALOG["gpt-5"]
    assert gpt5.provider == ModelProvider.OPENAI
    assert gpt5.context_window == 200000
    assert gpt5.max_tokens == 16384
    assert gpt5.supports_tools is True

def test_helper_functions():
    """Verify that metadata query helpers return correct values."""
    openai_models = get_models_by_provider(ModelProvider.OPENAI)
    assert len(openai_models) >= 6
    assert all(m.provider == ModelProvider.OPENAI for m in openai_models)
    
    info = get_model_info("claude-opus-4.8")
    assert info is not None
    assert info.display_name == "Claude Opus 4.8"
    
    non_existent = get_model_info("non-existent-model")
    assert non_existent is None
    
    all_models = list_all_models()
    assert len(all_models) >= 25

def test_provider_factory_availability(monkeypatch):
    """Verify ProviderFactory is_available behavior with environment variables."""
    # Temporarily remove keys
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    
    # We resolve from env in __init__, so we instantiate fresh subclasses to verify
    from ai_engine.providers import OpenAIProvider, AnthropicProvider
    
    openai_prov = OpenAIProvider()
    assert openai_prov.is_available() is False
    
    # Set keys and verify
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-openai")
    openai_prov_with_key = OpenAIProvider()
    assert openai_prov_with_key.is_available() is True
    
    anthropic_prov = AnthropicProvider()
    assert anthropic_prov.is_available() is False
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-anthropic")
    anthropic_prov_with_key = AnthropicProvider()
    assert anthropic_prov_with_key.is_available() is True

def test_get_provider_for_model(monkeypatch):
    """Verify ProviderFactory.get_provider_for_model returns correct mapping."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    provider, info = ProviderFactory.get_provider_for_model("gemini-3.5-flash")
    assert provider.provider_name == "Google"
    assert info.model_id == "gemini-3.5-flash"
