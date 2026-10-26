# SecScan AI core module
"""Tests for the OrcaRouter Cyber Inference provider integration.

These tests cover the API-key credential seam, the capability-aware model
catalog, the terminal ``401`` transition, and the provider wiring.  Only fake
credentials are used; the single live test reads the operator's
``ORCAROUTER_API_KEY`` and skips when it is not present.
"""

import json
import logging
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_engine import orcarouter
from ai_engine.model_registry import (
    MODEL_CATALOG,
    ModelProvider,
    get_available_providers,
    get_model_info,
    get_models_by_provider,
    normalize_provider,
)
from ai_engine.providers import (
    OrcaRouterProvider,
    ProviderFactory,
    _PROVIDER_CLASS_MAP,
)

FAKE_KEY = "sk-orca-fake-test-credential-0001"
LIVE_MODEL = "orca/orcacyber-ultra-1.0"


def _catalog_payload():
    """A catalog fixture covering every capability family."""
    return {
        "data": [
            {
                "id": "deepseek/deepseek-v4-flash",
                "name": "DeepSeek V4 Flash",
                "context_length": 128000,
                "architecture": {"input_modalities": ["text"]},
                "supported_endpoint_types": ["openai", "openai-response"],
            },
            {
                "id": "deepseek/deepseek-v4.1-flash",
                "name": "DeepSeek V4.1 Flash",
                "context_length": 131072,
                "architecture": {"input_modalities": ["text", "image"]},
                "supported_endpoint_types": ["openai", "anthropic"],
            },
            {
                "id": "orca/orcacyber-ultra-1.0",
                "name": "OrcaCyber Ultra 1.0",
                "context_length": 200000,
                "architecture": {"input_modalities": ["text"]},
                "supported_endpoint_types": ["openai"],
                "cyber": True,
                "reasoning_efforts": ["low", "medium", "high"],
            },
            {
                "id": "openai/text-embedding-3-large",
                "name": "Text Embedding 3 Large",
                "supported_endpoint_types": ["embeddings"],
                "architecture": {"input_modalities": ["text"]},
            },
            {
                "id": "openai/gpt-image-2",
                "name": "GPT Image 2",
                "supported_endpoint_types": ["image-generation"],
                "architecture": {
                    "input_modalities": ["text"],
                    "output_modalities": ["image"],
                },
            },
            {
                "id": "google/veo-4",
                "name": "Veo 4",
                "supported_endpoint_types": ["openai-video"],
                "architecture": {"input_modalities": ["text"]},
            },
            {
                "id": "jina/jina-reranker-v3",
                "name": "Jina Reranker v3",
                "supported_endpoint_types": ["jina-rerank"],
                "architecture": {"input_modalities": ["text"]},
            },
            "not-a-record",
            {"name": "missing id"},
            {"id": "bad id with spaces"},
        ]
    }


def _fake_getter(status=200, payload=None):
    captured = {}

    def getter(url, headers, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        body = payload if payload is not None else _catalog_payload()
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode("utf-8")
        return status, body

    return getter, captured


# ---------------------------------------------------------------------------
# Registry and provider wiring
# ---------------------------------------------------------------------------


def test_orcarouter_is_a_named_registry_provider():
    assert ModelProvider.ORCAROUTER.value == "orcarouter"
    assert normalize_provider("OrcaRouter") is ModelProvider.ORCAROUTER
    assert normalize_provider("orca") is ModelProvider.ORCAROUTER
    assert _PROVIDER_CLASS_MAP[ModelProvider.ORCAROUTER] is OrcaRouterProvider

    meta = {p["id"]: p for p in get_available_providers()}
    entry = meta["orcarouter"]
    assert entry["name"] == "OrcaRouter Cyber Inference"
    assert entry["required_env_vars"] == ["ORCAROUTER_API_KEY"]

    models = get_models_by_provider(ModelProvider.ORCAROUTER)
    assert len(models) >= 9
    ids = {m.model_id for m in models}
    assert {
        "orca/orcacyber-ultra-1.0",
        "orca/orcacyber-zero-1.5",
        "orcarouter/fusion",
    } <= ids


def test_catalog_preserves_namespaced_model_ids_and_metadata():
    ultra = get_model_info("orca/orcacyber-ultra-1.0")
    assert ultra is not None and ultra.provider is ModelProvider.ORCAROUTER
    gpt = MODEL_CATALOG["openai/gpt-5.5"]
    assert gpt.model_id == "openai/gpt-5.5"
    assert gpt.reasoning_efforts == ("low", "medium", "high", "xhigh")


def test_provider_defaults_to_official_inference_origin(monkeypatch):
    monkeypatch.delenv("ORCAROUTER_BASE_URL", raising=False)
    monkeypatch.delenv("ORCA_API_BASE_URL", raising=False)
    monkeypatch.delenv("ORCA_BASE_URL", raising=False)
    provider = OrcaRouterProvider(api_key=FAKE_KEY)
    assert provider.base_url == "https://api.orcarouter.ai/v1"
    assert provider.provider_name == "OrcaRouter Cyber Inference"


def test_provider_honours_explicit_and_shared_base_overrides(monkeypatch):
    monkeypatch.setenv("ORCA_BASE_URL", "https://self-hosted.example")
    assert orcarouter.resolve_api_base() == "https://self-hosted.example"
    monkeypatch.setenv("ORCA_API_BASE_URL", "https://api.self-hosted.example/v1")
    assert orcarouter.resolve_api_base() == "https://api.self-hosted.example/v1"
    assert (
        orcarouter.resolve_api_base("https://explicit.example/v1")
        == "https://explicit.example/v1"
    )


def test_auth_origin_is_separate_from_inference_origin():
    assert orcarouter.AUTH_BASE == "https://www.orcarouter.ai"
    assert orcarouter.DEFAULT_API_BASE == "https://api.orcarouter.ai/v1"
    for path in ("ai_engine/orcarouter.py", "ai_engine/providers.py"):
        source = (ROOT / path).read_text(encoding="utf-8")
        assert "api.orcarouter.ai/v1/auth" not in source


def test_factory_dispatches_orcarouter_for_unknown_model(monkeypatch):
    monkeypatch.setenv("SECSCAN_AI_PROVIDER", "orcarouter")
    monkeypatch.setenv("ORCAROUTER_API_KEY", FAKE_KEY)
    monkeypatch.delenv("SECSCAN_AI_CUSTOM_ROUTE", raising=False)
    provider, info = ProviderFactory.get_provider_for_model("vendor/some-cyber-model")
    assert isinstance(provider, OrcaRouterProvider)
    assert info.provider is ModelProvider.ORCAROUTER
    assert info.model_id == "vendor/some-cyber-model"


# ---------------------------------------------------------------------------
# Credential seam
# ---------------------------------------------------------------------------


def test_credential_resolution_precedence(monkeypatch):
    store = orcarouter.CredentialStore(config_reader=lambda: "sk-orca-from-config-0002")
    monkeypatch.delenv(orcarouter.ENV_API_KEY, raising=False)
    assert store.resolve().source == "config"
    monkeypatch.setenv(orcarouter.ENV_API_KEY, "sk-orca-from-env-0003")
    assert store.resolve().source == "env"
    store.set_runtime_key("sk-orca-runtime-0004")
    assert store.resolve().source == "dashboard"
    assert store.resolve("sk-orca-explicit-0005").source == "argument"


def test_credential_set_update_clear_and_mask(monkeypatch):
    monkeypatch.delenv(orcarouter.ENV_API_KEY, raising=False)
    store = orcarouter.CredentialStore()
    assert store.status()["configured"] is False

    store.set_runtime_key(FAKE_KEY)
    status = store.status()
    assert status["configured"] is True
    assert status["masked"] == "sk-orca-…0001"
    assert FAKE_KEY not in json.dumps(status)
    assert status["generation"] == 1

    store.set_runtime_key("sk-orca-second-key-9999")
    assert store.status()["generation"] == 2
    assert store.status()["masked"].endswith("9999")

    store.clear()
    assert store.status()["configured"] is False
    assert store.status()["generation"] == 3


@pytest.mark.parametrize(
    "candidate",
    ["", "not-a-key", "sk-orca- short", "sk-orca-has space inside 000000"],
)
def test_malformed_api_keys_are_rejected(candidate):
    store = orcarouter.CredentialStore()
    with pytest.raises(ValueError):
        store.set_runtime_key(candidate)


def test_reauth_is_generation_safe(monkeypatch):
    monkeypatch.delenv(orcarouter.ENV_API_KEY, raising=False)
    store = orcarouter.CredentialStore()
    store.set_runtime_key(FAKE_KEY)
    stale_generation = store.generation

    store.set_runtime_key("sk-orca-fresh-key-7777")
    assert store.mark_needs_reauth(stale_generation) is False
    assert store.needs_reauth() is False

    assert store.mark_needs_reauth(store.generation) is True
    assert store.needs_reauth() is True

    store.set_runtime_key("sk-orca-newer-key-8888")
    assert store.needs_reauth() is False


def test_rejected_key_only_marks_the_active_credential(monkeypatch):
    monkeypatch.delenv(orcarouter.ENV_API_KEY, raising=False)
    store = orcarouter.CredentialStore()
    store.set_runtime_key(FAKE_KEY)
    assert store.mark_needs_reauth_for_key("sk-orca-other-key-1234") is False
    assert store.mark_needs_reauth_for_key(FAKE_KEY) is True


# ---------------------------------------------------------------------------
# Catalog parsing and capability filtering
# ---------------------------------------------------------------------------


def test_parse_catalog_rejects_bad_shapes():
    good = orcarouter.parse_catalog_item({"id": "vendor/model"})
    assert good is not None and good.model_id == "vendor/model"
    assert orcarouter.parse_catalog_item("nope") is None
    assert orcarouter.parse_catalog_item({"name": "no id"}) is None
    assert orcarouter.parse_catalog_item({"id": "bad id"}) is None
    assert orcarouter.parse_catalog_item({"id": ""}) is None


def test_chat_capability_excludes_non_chat_endpoint_families():
    models = [
        orcarouter.parse_catalog_item(item)
        for item in _catalog_payload()["data"]
        if isinstance(item, dict)
    ]
    kept = orcarouter.filter_catalog([m for m in models if m], "chat")
    ids = [m.model_id for m in kept]
    assert "deepseek/deepseek-v4-flash" in ids
    assert "deepseek/deepseek-v4.1-flash" in ids
    assert "openai/text-embedding-3-large" not in ids
    assert "openai/gpt-image-2" not in ids
    assert "google/veo-4" not in ids
    assert "jina/jina-reranker-v3" not in ids
    # Cyber-tier models sort first so the recommended default leads the list.
    assert ids[0] == "orca/orcacyber-ultra-1.0"


def test_multimodal_requirement_fails_closed():
    models = [
        orcarouter.parse_catalog_item(item)
        for item in _catalog_payload()["data"]
        if isinstance(item, dict)
    ]
    models = [m for m in models if m]
    kept = orcarouter.filter_catalog(
        models, "chat", required_input_modalities=["image"]
    )
    assert [m.model_id for m in kept] == ["deepseek/deepseek-v4.1-flash"]

    # A model that does not declare image input is never admitted.
    text_only = orcarouter.parse_catalog_item({"id": "vendor/text-only"})
    assert orcarouter.filter_catalog([text_only], "chat", ["image"]) == []


@pytest.mark.parametrize(
    "capability,expected",
    [
        ("embedding", ["openai/text-embedding-3-large"]),
        ("image", ["openai/gpt-image-2"]),
        ("video", ["google/veo-4"]),
        ("rerank", ["jina/jina-reranker-v3"]),
    ],
)
def test_non_chat_capabilities_use_strict_endpoint_matching(capability, expected):
    models = [
        m
        for m in (
            orcarouter.parse_catalog_item(item)
            for item in _catalog_payload()["data"]
            if isinstance(item, dict)
        )
        if m
    ]
    assert [
        m.model_id for m in orcarouter.filter_catalog(models, capability)
    ] == expected


def test_live_discovery_is_authoritative(monkeypatch):
    getter, captured = _fake_getter()
    result = orcarouter.discover_models(FAKE_KEY, http_get=getter)

    assert result.source == "live"
    assert result.degraded is False
    assert captured["url"] == "https://api.orcarouter.ai/v1/models?capability=chat"
    assert captured["headers"]["Authorization"] == f"Bearer {FAKE_KEY}"
    assert captured["timeout"] <= 10

    ids = {m.model_id for m in result.models}
    # Namespaced ids are kept verbatim, and seed-only entries are not mixed in.
    assert "orca/orcacyber-ultra-1.0" in ids
    assert "openai/gpt-5.5" not in ids


def test_live_discovery_respects_multimodal_requirement():
    getter, _ = _fake_getter()
    result = orcarouter.discover_models(
        FAKE_KEY, http_get=getter, required_input_modalities=["image"]
    )
    assert [m.model_id for m in result.models] == ["deepseek/deepseek-v4.1-flash"]


def test_missing_credentials_returns_labelled_seed():
    result = orcarouter.discover_models(None)
    assert result.degraded is True
    assert result.source == "fallback"
    assert result.reason == "missing_credentials"
    seed = {m.model_id: m for m in result.models}
    assert seed["openai/gpt-5.5"].reasoning_efforts == (
        "low",
        "medium",
        "high",
        "xhigh",
    )
    assert seed["orca/orcacyber-ultra-1.0"].cyber_tier is True


@pytest.mark.parametrize("status", [500, 502, 503])
def test_server_errors_degrade_to_seed(status):
    getter, _ = _fake_getter(status=status, payload=b"")
    result = orcarouter.discover_models(FAKE_KEY, http_get=getter)
    assert result.degraded is True
    assert result.source == "fallback"
    assert result.reason == f"http_{status}"
    assert any(m.model_id == "orca/orcacyber-ultra-1.0" for m in result.models)


def test_malformed_payload_degrades_to_seed():
    getter, _ = _fake_getter(payload=b"{not json")
    result = orcarouter.discover_models(FAKE_KEY, http_get=getter)
    assert result.degraded is True
    assert result.reason == "malformed_catalog"


def test_network_failure_degrades_to_seed():
    def boom(url, headers, timeout):
        raise OSError("connection reset")

    result = orcarouter.discover_models(FAKE_KEY, http_get=boom)
    assert result.degraded is True
    assert result.reason == "network_error"


def test_empty_filtered_catalog_degrades_to_seed():
    getter, _ = _fake_getter(
        payload={"data": [{"id": "x", "supported_endpoint_types": ["embeddings"]}]}
    )
    result = orcarouter.discover_models(FAKE_KEY, http_get=getter)
    assert result.degraded is True
    assert result.reason == "empty_catalog"


def test_unauthorised_catalog_raises_terminal_error():
    getter, _ = _fake_getter(status=401, payload=b"")
    with pytest.raises(orcarouter.OrcaRouterAuthError):
        orcarouter.discover_models(FAKE_KEY, http_get=getter)


def test_forbidden_catalog_does_not_invalidate_the_key():
    getter, _ = _fake_getter(status=403, payload=b"")
    result = orcarouter.discover_models(FAKE_KEY, http_get=getter)
    assert result.degraded is True
    assert result.reason == "forbidden"


# ---------------------------------------------------------------------------
# Provider call paths
# ---------------------------------------------------------------------------


def test_provider_fetch_remote_models_uses_live_catalog(monkeypatch):
    getter, _ = _fake_getter()
    monkeypatch.setattr(orcarouter, "_default_http_get", getter)
    monkeypatch.setattr(
        "ai_engine.providers.discover_models",
        lambda api_key, capability="chat", **kwargs: orcarouter.discover_models(
            api_key, capability=capability, http_get=getter
        ),
    )
    provider = OrcaRouterProvider(api_key=FAKE_KEY)
    models = provider.fetch_remote_models()
    assert models
    assert all(m.provider is ModelProvider.ORCAROUTER for m in models)
    assert {m.model_id for m in models} >= {"orca/orcacyber-ultra-1.0"}


def test_provider_chat_completion_success_path(monkeypatch):
    monkeypatch.setattr(
        "ai_engine.providers._safe_http_post_json",
        lambda url, headers, payload, timeout=60: (
            200,
            {"choices": [{"message": {"content": "routed"}}]},
        ),
    )
    provider = OrcaRouterProvider(api_key=FAKE_KEY)
    assert (
        provider.chat_completion(LIVE_MODEL, [{"role": "user", "content": "hi"}])
        == "routed"
    )


def test_provider_401_marks_exact_generation(monkeypatch):
    monkeypatch.delenv(orcarouter.ENV_API_KEY, raising=False)
    store = orcarouter.credential_store
    store.clear()
    store.set_runtime_key(FAKE_KEY)
    monkeypatch.setattr(
        "ai_engine.providers._safe_http_post_json",
        lambda url, headers, payload, timeout=60: (401, {"error": "revoked"}),
    )
    provider = OrcaRouterProvider()
    with pytest.raises(orcarouter.OrcaRouterAuthError):
        provider.chat_completion(LIVE_MODEL, [{"role": "user", "content": "hi"}])
    assert store.needs_reauth() is True
    store.clear()


def test_provider_403_is_model_access_not_reauth(monkeypatch):
    monkeypatch.delenv(orcarouter.ENV_API_KEY, raising=False)
    store = orcarouter.credential_store
    store.clear()
    store.set_runtime_key(FAKE_KEY)
    monkeypatch.setattr(
        "ai_engine.providers._safe_http_post_json",
        lambda url, headers, payload, timeout=60: (403, {"error": "no access"}),
    )
    provider = OrcaRouterProvider()
    with pytest.raises(orcarouter.OrcaRouterAccessError):
        provider.chat_completion(
            "orca/orcacyber-ultra-1.0", [{"role": "user", "content": "hi"}]
        )
    assert store.needs_reauth() is False
    store.clear()


def test_provider_errors_do_not_leak_the_key(monkeypatch, caplog):
    monkeypatch.setattr(
        "ai_engine.providers._safe_http_post_json",
        lambda url, headers, payload, timeout=60: (500, None),
    )
    provider = OrcaRouterProvider(api_key=FAKE_KEY)
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(RuntimeError) as excinfo:
            provider.chat_completion(LIVE_MODEL, [{"role": "user", "content": "hi"}])
    assert FAKE_KEY not in str(excinfo.value)
    assert FAKE_KEY not in caplog.text


# ---------------------------------------------------------------------------
# Live smoke test (operator credential required)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.getenv("ORCAROUTER_API_KEY"),
    reason="ORCAROUTER_API_KEY is not configured for the live check",
)
def test_live_orcarouter_catalog_and_inference():
    """Exercise the real gateway through the provider code path."""
    provider = OrcaRouterProvider()
    assert provider.is_available()

    models = provider.fetch_remote_models()
    assert models, "live catalog returned no chat models"
    assert any(m.model_id == LIVE_MODEL for m in models)

    text = provider.chat_completion(
        LIVE_MODEL,
        [{"role": "user", "content": "Reply with the single word: routed"}],
        max_tokens=16,
        temperature=0.0,
    )
    assert isinstance(text, str) and text.strip()
