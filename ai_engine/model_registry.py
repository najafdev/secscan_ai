# SecScan AI core module
"""Model registry and provider abstraction layer for SecScan AI.

Provides a centralized catalog of supported AI models across multiple
providers, along with helper functions for querying model metadata,
filtering by provider, and discovering available providers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

__all__ = [
    "ModelProvider",
    "ModelInfo",
    "MODEL_CATALOG",
    "DYNAMIC_MODEL_CATALOG",
    "get_models_by_provider",
    "get_model_info",
    "list_all_models",
    "get_available_providers",
    "register_dynamic_model",
    "clear_dynamic_models",
    "fetch_all_provider_models",
    "normalize_provider",
]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ModelProvider(Enum):
    """Supported AI model providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    LOCAL = "local"
    OPENROUTER = "openrouter"
    GLM = "glm"
    LITELLM = "litellm"
    NINEBROUTER = "9brouter"
    CUSTOM_ROUTER = "custom_router"
    ORCAROUTER = "orcarouter"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ModelInfo:
    """Metadata for a single AI model.

    Attributes:
        model_id: The canonical identifier used when calling the provider API
            (e.g. ``'gpt-5'``, ``'claude-sonnet-4-20250514'``).
        provider: The :class:`ModelProvider` that hosts this model.
        display_name: A human-friendly label for UI rendering.
        max_tokens: Maximum number of *output* tokens the model can generate
            in a single completion.
        supports_streaming: Whether the model supports streaming responses.
        supports_tools: Whether the model supports tool / function calling.
        context_window: Total context window size (input + output) in tokens.
        description: Optional free-text description of the model.
        input_modalities: Modalities the model accepts, as advertised by the
            provider catalog.  Defaults to text only so unknown models fail
            closed for multimodal entries.
        reasoning_efforts: Verified reasoning-effort levels, when the provider
            advertises them.
    """

    model_id: str
    provider: ModelProvider
    display_name: str
    max_tokens: int
    supports_streaming: bool = True
    supports_tools: bool = False
    context_window: int = 128_000
    description: str = ""
    input_modalities: tuple = ("text",)
    reasoning_efforts: tuple = ()


# ---------------------------------------------------------------------------
# Model catalog
# ---------------------------------------------------------------------------

MODEL_CATALOG: Dict[str, ModelInfo] = {
    # ----- OpenAI --------------------------------------------------------
    "gpt-5": ModelInfo(
        model_id="gpt-5",
        provider=ModelProvider.OPENAI,
        display_name="GPT-5",
        max_tokens=16_384,
        supports_tools=True,
        context_window=200_000,
        description="OpenAI's most capable general-purpose model.",
    ),
    "gpt-5.6": ModelInfo(
        model_id="gpt-5.6",
        provider=ModelProvider.OPENAI,
        display_name="GPT-5.6",
        max_tokens=16_384,
        supports_tools=True,
        context_window=200_000,
        description="Incremental improvement over GPT-5 with enhanced reasoning.",
    ),
    "gpt-4o": ModelInfo(
        model_id="gpt-4o",
        provider=ModelProvider.OPENAI,
        display_name="GPT-4o",
        max_tokens=4_096,
        supports_tools=True,
        context_window=128_000,
        description="OpenAI's optimized multimodal model.",
    ),
    "gpt-4o-mini": ModelInfo(
        model_id="gpt-4o-mini",
        provider=ModelProvider.OPENAI,
        display_name="GPT-4o Mini",
        max_tokens=4_096,
        supports_tools=True,
        context_window=128_000,
        description="Lightweight variant of GPT-4o optimized for speed and cost.",
    ),
    "o3": ModelInfo(
        model_id="o3",
        provider=ModelProvider.OPENAI,
        display_name="o3",
        max_tokens=100_000,
        supports_tools=True,
        context_window=200_000,
        description="OpenAI reasoning model with extended output capacity.",
    ),
    "o4-mini": ModelInfo(
        model_id="o4-mini",
        provider=ModelProvider.OPENAI,
        display_name="o4-mini",
        max_tokens=65_536,
        supports_tools=True,
        context_window=200_000,
        description="Compact reasoning model balancing capability and efficiency.",
    ),
    "gpt-astra": ModelInfo(
        model_id="gpt-astra",
        provider=ModelProvider.OPENAI,
        display_name="GPT Astra",
        max_tokens=32_768,
        supports_tools=True,
        context_window=256_000,
        description="OpenAI's frontier GPT Astra model specialized in complex reasoning, cybersecurity analysis, and computer use.",
    ),
    "gpt-6-astra": ModelInfo(
        model_id="gpt-6-astra",
        provider=ModelProvider.OPENAI,
        display_name="GPT-6 Astra",
        max_tokens=32_768,
        supports_tools=True,
        context_window=256_000,
        description="OpenAI GPT-6 Astra next-gen flagship model for autonomous penetration testing and deep multi-step security analysis.",
    ),
    "gpt-4.5-preview": ModelInfo(
        model_id="gpt-4.5-preview",
        provider=ModelProvider.OPENAI,
        display_name="GPT-4.5 Preview",
        max_tokens=16_384,
        supports_tools=True,
        context_window=128_000,
        description="OpenAI's extensive knowledge model with deep world understanding and reasoning.",
    ),
    "o1": ModelInfo(
        model_id="o1",
        provider=ModelProvider.OPENAI,
        display_name="o1",
        max_tokens=100_000,
        supports_tools=True,
        context_window=200_000,
        description="OpenAI o1 full reasoning model with extended chain-of-thought processing.",
    ),
    "o1-mini": ModelInfo(
        model_id="o1-mini",
        provider=ModelProvider.OPENAI,
        display_name="o1-mini",
        max_tokens=65_536,
        supports_tools=True,
        context_window=128_000,
        description="Fast and cost-effective OpenAI reasoning model optimized for code and technical tasks.",
    ),

    # ----- Anthropic -----------------------------------------------------
    "claude-sonnet-5": ModelInfo(
        model_id="claude-sonnet-4-20250514",
        provider=ModelProvider.ANTHROPIC,
        display_name="Claude Sonnet 5",
        max_tokens=16_384,
        supports_tools=True,
        context_window=200_000,
        description="Anthropic's high-performance model with strong coding ability.",
    ),
    "claude-opus-4.8": ModelInfo(
        model_id="claude-opus-4-20250918",
        provider=ModelProvider.ANTHROPIC,
        display_name="Claude Opus 4.8",
        max_tokens=16_384,
        supports_tools=True,
        context_window=200_000,
        description="Anthropic's most powerful model for complex analysis.",
    ),
    "claude-haiku-3.5": ModelInfo(
        model_id="claude-3-5-haiku-20241022",
        provider=ModelProvider.ANTHROPIC,
        display_name="Claude Haiku 3.5",
        max_tokens=8_192,
        supports_tools=True,
        context_window=200_000,
        description="Fast and affordable Anthropic model for lightweight tasks.",
    ),
    "claude-3.7-sonnet": ModelInfo(
        model_id="claude-3-7-sonnet-20250219",
        provider=ModelProvider.ANTHROPIC,
        display_name="Claude 3.7 Sonnet",
        max_tokens=16_384,
        supports_tools=True,
        context_window=200_000,
        description="Anthropic's hybrid model combining instantaneous response with extended thinking.",
    ),

    # ----- Google Gemini -------------------------------------------------
    "gemini-3.5-flash": ModelInfo(
        model_id="gemini-3.5-flash",
        provider=ModelProvider.GOOGLE,
        display_name="Gemini 3.5 Flash",
        max_tokens=8_192,
        context_window=1_000_000,
        description="Ultra-fast Google model optimized for low-latency workloads.",
    ),
    "gemini-3.1-pro": ModelInfo(
        model_id="gemini-3.1-pro",
        provider=ModelProvider.GOOGLE,
        display_name="Gemini 3.1 Pro",
        max_tokens=8_192,
        context_window=2_000_000,
        description="Google's professional-grade model with a 2M token context.",
    ),
    "gemini-2.5-pro": ModelInfo(
        model_id="gemini-2.5-pro",
        provider=ModelProvider.GOOGLE,
        display_name="Gemini 2.5 Pro",
        max_tokens=65_536,
        context_window=1_000_000,
        description="Google's advanced reasoning model with extended output.",
    ),
    "gemini-2.5-flash": ModelInfo(
        model_id="gemini-2.5-flash",
        provider=ModelProvider.GOOGLE,
        display_name="Gemini 2.5 Flash",
        max_tokens=65_536,
        context_window=1_000_000,
        description="Fast Google model combining speed with large output capacity.",
    ),
    "gemini-2.0-flash": ModelInfo(
        model_id="gemini-2.0-flash",
        provider=ModelProvider.GOOGLE,
        display_name="Gemini 2.0 Flash",
        max_tokens=8_192,
        supports_tools=True,
        context_window=1_000_000,
        description="Next-generation multimodal model built for speed and agentic workflows.",
    ),
    "gemini-2.0-pro": ModelInfo(
        model_id="gemini-2.0-pro-exp-02-05",
        provider=ModelProvider.GOOGLE,
        display_name="Gemini 2.0 Pro",
        max_tokens=8_192,
        supports_tools=True,
        context_window=2_000_000,
        description="Google's most powerful model for complex coding, reasoning, and world knowledge.",
    ),

    # ----- DeepSeek ------------------------------------------------------
    "deepseek-r1": ModelInfo(
        model_id="deepseek-r1",
        provider=ModelProvider.DEEPSEEK,
        display_name="DeepSeek R1",
        max_tokens=8_192,
        context_window=128_000,
        description="DeepSeek reasoning model with chain-of-thought capability.",
    ),
    "deepseek-v3": ModelInfo(
        model_id="deepseek-chat",
        provider=ModelProvider.DEEPSEEK,
        display_name="DeepSeek V3",
        max_tokens=8_192,
        context_window=128_000,
        description="DeepSeek's general-purpose conversational model.",
    ),
    "deepseek-r1-zero": ModelInfo(
        model_id="deepseek-reasoner",
        provider=ModelProvider.DEEPSEEK,
        display_name="DeepSeek Reasoner",
        max_tokens=8_192,
        supports_tools=True,
        context_window=128_000,
        description="DeepSeek's pure RL-trained reasoning model for algorithmic and logic-heavy security tasks.",
    ),

    # ----- GLM -----------------------------------------------------------
    "glm-5.2": ModelInfo(
        model_id="glm-5.2",
        provider=ModelProvider.GLM,
        display_name="GLM 5.2",
        max_tokens=4_096,
        context_window=128_000,
        description="Zhipu AI's latest bilingual large language model.",
    ),
    "glm-4-plus": ModelInfo(
        model_id="glm-4-plus",
        provider=ModelProvider.GLM,
        display_name="GLM-4 Plus",
        max_tokens=4_096,
        context_window=128_000,
        description="Enhanced variant of GLM-4 with improved instruction following.",
    ),

    # ----- Local LLMs (Ollama) -------------------------------------------
    "llama3.3:70b": ModelInfo(
        model_id="llama3.3:70b",
        provider=ModelProvider.LOCAL,
        display_name="LLaMA 3.3 70B",
        max_tokens=4_096,
        supports_streaming=False,
        context_window=128_000,
        description="Meta's 70B parameter LLaMA model running locally via Ollama.",
    ),
    "llama3.2:3b": ModelInfo(
        model_id="llama3.2:3b",
        provider=ModelProvider.LOCAL,
        display_name="LLaMA 3.2 3B",
        max_tokens=4_096,
        supports_streaming=False,
        context_window=128_000,
        description="Lightweight 3B LLaMA model for resource-constrained environments.",
    ),
    "mistral:7b": ModelInfo(
        model_id="mistral:7b",
        provider=ModelProvider.LOCAL,
        display_name="Mistral 7B",
        max_tokens=4_096,
        supports_streaming=False,
        context_window=128_000,
        description="Mistral AI's efficient 7B parameter model via Ollama.",
    ),
    "codellama:13b": ModelInfo(
        model_id="codellama:13b",
        provider=ModelProvider.LOCAL,
        display_name="Code LLaMA 13B",
        max_tokens=4_096,
        supports_streaming=False,
        context_window=128_000,
        description="Meta's code-specialized 13B model for programming tasks.",
    ),
    "qwen2.5:32b": ModelInfo(
        model_id="qwen2.5:32b",
        provider=ModelProvider.LOCAL,
        display_name="Qwen 2.5 32B",
        max_tokens=4_096,
        supports_streaming=False,
        context_window=128_000,
        description="Alibaba's 32B parameter Qwen model via Ollama.",
    ),
    "deepseek-r1:14b": ModelInfo(
        model_id="deepseek-r1:14b",
        provider=ModelProvider.LOCAL,
        display_name="DeepSeek R1 14B",
        max_tokens=4_096,
        supports_streaming=False,
        context_window=128_000,
        description="Local 14B distillation of the DeepSeek R1 reasoning model.",
    ),
    "phi-4:14b": ModelInfo(
        model_id="phi-4:14b",
        provider=ModelProvider.LOCAL,
        display_name="Phi-4 14B",
        max_tokens=4_096,
        supports_streaming=False,
        context_window=128_000,
        description="Microsoft's compact yet capable Phi-4 model via Ollama.",
    ),

    # ----- OpenRouter ----------------------------------------------------
    "openrouter/auto": ModelInfo(
        model_id="openrouter/auto",
        provider=ModelProvider.OPENROUTER,
        display_name="OpenRouter Auto",
        max_tokens=4_096,
        context_window=128_000,
        description="Automatic model routing via the OpenRouter aggregator.",
    ),
    "openrouter/openai/gpt-astra": ModelInfo(
        model_id="openai/gpt-astra",
        provider=ModelProvider.OPENROUTER,
        display_name="GPT Astra (via OpenRouter)",
        max_tokens=32_768,
        supports_tools=True,
        context_window=256_000,
        description="OpenAI GPT Astra routed through OpenRouter's API gateway.",
    ),
    "openrouter/anthropic/claude-3.7-sonnet": ModelInfo(
        model_id="anthropic/claude-3-7-sonnet-20250219",
        provider=ModelProvider.OPENROUTER,
        display_name="Claude 3.7 Sonnet (via OpenRouter)",
        max_tokens=16_384,
        supports_tools=True,
        context_window=200_000,
        description="Anthropic Claude 3.7 Sonnet routed through OpenRouter.",
    ),
    "openrouter/deepseek/deepseek-r1": ModelInfo(
        model_id="deepseek/deepseek-r1",
        provider=ModelProvider.OPENROUTER,
        display_name="DeepSeek R1 (via OpenRouter)",
        max_tokens=8_192,
        context_window=128_000,
        description="DeepSeek R1 reasoning model routed through OpenRouter.",
    ),
    "openrouter/meta-llama/llama-3.3-70b-instruct": ModelInfo(
        model_id="meta-llama/llama-3.3-70b-instruct",
        provider=ModelProvider.OPENROUTER,
        display_name="LLaMA 3.3 70B Instruct (via OpenRouter)",
        max_tokens=4_096,
        context_window=128_000,
        description="Meta LLaMA 3.3 70B Instruct model routed through OpenRouter.",
    ),

    # ----- 9B Router (Intelligent Model & Task Dispatcher) -----------------
    "9brouter/agent-router": ModelInfo(
        model_id="agent-router-9b",
        provider=ModelProvider.NINEBROUTER,
        display_name="9B Agent Router",
        max_tokens=4_096,
        supports_tools=True,
        context_window=128_000,
        description="High-throughput 9B router for analyzing security prompt complexity, tool planning, and model dispatch.",
    ),
    "9brouter/qwen2.5:9b": ModelInfo(
        model_id="qwen2.5:9b",
        provider=ModelProvider.NINEBROUTER,
        display_name="Qwen 2.5 9B Router",
        max_tokens=4_096,
        supports_tools=True,
        context_window=128_000,
        description="Qwen 2.5 9B router model tailored for rapid intent recognition and pentesting orchestration.",
    ),
    "9brouter/gemma2:9b": ModelInfo(
        model_id="gemma2:9b",
        provider=ModelProvider.NINEBROUTER,
        display_name="Gemma 2 9B Router",
        max_tokens=4_096,
        context_window=128_000,
        description="Google Gemma 2 9B router model for lightweight decision-making and query routing.",
    ),

    # ----- Custom Router (User-defined Endpoint / Proxy / Gateway) ---------
    "custom_router/default": ModelInfo(
        model_id="custom-default",
        provider=ModelProvider.CUSTOM_ROUTER,
        display_name="Custom Router Default",
        max_tokens=4_096,
        supports_tools=True,
        context_window=128_000,
        description="User-configured OpenAI-compatible router, reverse proxy, or private gateway endpoint.",
    ),

    # ----- LiteLLM (AI Gateway) ------------------------------------------
    "litellm/anthropic/claude-sonnet-4-20250514": ModelInfo(
        model_id="anthropic/claude-sonnet-4-20250514",
        provider=ModelProvider.LITELLM,
        display_name="Claude Sonnet 4 (via LiteLLM)",
        max_tokens=16_384,
        supports_tools=True,
        context_window=200_000,
        description="Anthropic Claude Sonnet 4 routed through the LiteLLM AI gateway.",
    ),
    "litellm/gpt-4o": ModelInfo(
        model_id="gpt-4o",
        provider=ModelProvider.LITELLM,
        display_name="GPT-4o (via LiteLLM)",
        max_tokens=4_096,
        supports_tools=True,
        context_window=128_000,
        description="OpenAI GPT-4o routed through the LiteLLM AI gateway.",
    ),
    "litellm/gemini/gemini-2.5-flash": ModelInfo(
        model_id="gemini/gemini-2.5-flash",
        provider=ModelProvider.LITELLM,
        display_name="Gemini 2.5 Flash (via LiteLLM)",
        max_tokens=65_536,
        context_window=1_000_000,
        description="Google Gemini 2.5 Flash routed through the LiteLLM AI gateway.",
    ),

    # ----- OrcaRouter Cyber Inference ------------------------------------
    # Recommended defaults for authorized security teams. OrcaCyber Ultra and
    # Zero require the cyber tier to be unlocked for the workspace; the live
    # catalog from /v1/models is authoritative once a key is configured.
    "orca/orcacyber-ultra-1.0": ModelInfo(
        model_id="orca/orcacyber-ultra-1.0",
        provider=ModelProvider.ORCAROUTER,
        display_name="OrcaCyber Ultra 1.0 (via OrcaRouter)",
        max_tokens=16_384,
        supports_tools=True,
        context_window=200_000,
        description="Security-code scanning model tuned for multi-step reasoning over large codebases.",
        reasoning_efforts=("low", "medium", "high"),
    ),
    "orca/orcacyber-zero-1.5": ModelInfo(
        model_id="orca/orcacyber-zero-1.5",
        provider=ModelProvider.ORCAROUTER,
        display_name="OrcaCyber Zero 1.5 (via OrcaRouter)",
        max_tokens=8_192,
        supports_tools=True,
        context_window=128_000,
        description="OrcaCyber-harness-driven security model for scoped authorized tasks.",
    ),
    "orca/orcacyber-zero-1.0": ModelInfo(
        model_id="orca/orcacyber-zero-1.0",
        provider=ModelProvider.ORCAROUTER,
        display_name="OrcaCyber Zero 1.0 (via OrcaRouter)",
        max_tokens=8_192,
        supports_tools=True,
        context_window=128_000,
        description="Previous OrcaCyber Zero release for scoped authorized tasks.",
    ),
    "orcarouter/fusion": ModelInfo(
        model_id="orcarouter/fusion",
        provider=ModelProvider.ORCAROUTER,
        display_name="OrcaRouter Fusion (via OrcaRouter)",
        max_tokens=8_192,
        supports_tools=True,
        context_window=128_000,
        description="General routing model used when the cyber tier is not unlocked.",
    ),
    "orcarouter/auto": ModelInfo(
        model_id="orcarouter/auto",
        provider=ModelProvider.ORCAROUTER,
        display_name="OrcaRouter Auto (via OrcaRouter)",
        max_tokens=8_192,
        supports_tools=True,
        context_window=128_000,
        description="Automatic model routing across the OrcaRouter catalog.",
    ),
    "openai/gpt-5.5": ModelInfo(
        model_id="openai/gpt-5.5",
        provider=ModelProvider.ORCAROUTER,
        display_name="GPT-5.5 (via OrcaRouter)",
        max_tokens=16_384,
        supports_tools=True,
        context_window=400_000,
        description="OpenAI GPT-5.5 routed through the OrcaRouter gateway.",
        reasoning_efforts=("low", "medium", "high", "xhigh"),
    ),
    "anthropic/claude-opus-4.8": ModelInfo(
        model_id="anthropic/claude-opus-4.8",
        provider=ModelProvider.ORCAROUTER,
        display_name="Claude Opus 4.8 (via OrcaRouter)",
        max_tokens=16_384,
        supports_tools=True,
        context_window=200_000,
        description="Anthropic Claude Opus 4.8 routed through the OrcaRouter gateway.",
        input_modalities=("text", "image"),
    ),
    "google/gemini-3.5-flash": ModelInfo(
        model_id="google/gemini-3.5-flash",
        provider=ModelProvider.ORCAROUTER,
        display_name="Gemini 3.5 Flash (via OrcaRouter)",
        max_tokens=65_536,
        supports_tools=True,
        context_window=1_000_000,
        description="Google Gemini 3.5 Flash routed through the OrcaRouter gateway.",
        input_modalities=("text", "image"),
    ),
    "deepseek/deepseek-v4-pro": ModelInfo(
        model_id="deepseek/deepseek-v4-pro",
        provider=ModelProvider.ORCAROUTER,
        display_name="DeepSeek V4 Pro (via OrcaRouter)",
        max_tokens=8_192,
        supports_tools=True,
        context_window=128_000,
        description="DeepSeek V4 Pro reasoning model routed through the OrcaRouter gateway.",
        reasoning_efforts=("low", "high"),
    ),
}


# ---------------------------------------------------------------------------
# Provider metadata (for discovery / UI)
# ---------------------------------------------------------------------------

_PROVIDER_META: Dict[ModelProvider, Dict[str, Any]] = {
    ModelProvider.OPENAI: {
        "name": "OpenAI",
        "description": "GPT and o-series models from OpenAI.",
        "required_env_vars": ["OPENAI_API_KEY"],
    },
    ModelProvider.ANTHROPIC: {
        "name": "Anthropic",
        "description": "Claude family of models from Anthropic.",
        "required_env_vars": ["ANTHROPIC_API_KEY"],
    },
    ModelProvider.GOOGLE: {
        "name": "Google",
        "description": "Gemini models from Google DeepMind.",
        "required_env_vars": ["GOOGLE_API_KEY"],
    },
    ModelProvider.DEEPSEEK: {
        "name": "DeepSeek",
        "description": "Reasoning and chat models from DeepSeek.",
        "required_env_vars": ["DEEPSEEK_API_KEY"],
    },
    ModelProvider.LOCAL: {
        "name": "Local (Ollama)",
        "description": "Locally-hosted models served via Ollama.",
        "required_env_vars": [],
    },
    ModelProvider.OPENROUTER: {
        "name": "OpenRouter",
        "description": "Multi-provider model aggregator with automatic routing.",
        "required_env_vars": ["OPENROUTER_API_KEY"],
    },
    ModelProvider.GLM: {
        "name": "GLM (Zhipu AI)",
        "description": "GLM series models from Zhipu AI.",
        "required_env_vars": ["GLM_API_KEY"],
    },
    ModelProvider.LITELLM: {
        "name": "LiteLLM",
        "description": "Unified AI gateway supporting 100+ LLM providers via a single interface.",
        "required_env_vars": ["LITELLM_API_KEY"],
    },
    ModelProvider.NINEBROUTER: {
        "name": "9B Router",
        "description": "9B parameter intelligent model and tool router for automated task dispatching.",
        "required_env_vars": ["NINEBROUTER_BASE_URL"],
    },
    ModelProvider.CUSTOM_ROUTER: {
        "name": "Custom Router",
        "description": "Custom user-defined OpenAI-compatible router, reverse proxy, or API gateway.",
        "required_env_vars": ["CUSTOM_ROUTER_BASE_URL"],
    },
    ModelProvider.ORCAROUTER: {
        "name": "OrcaRouter Cyber Inference",
        "description": (
            "Cyber inference provider for authorized security teams: OrcaCyber models "
            "for red-team work plus gateway controls for blue-team work, all behind one "
            "OpenAI-compatible endpoint."
        ),
        "required_env_vars": ["ORCAROUTER_API_KEY"],
    },
}


# ---------------------------------------------------------------------------
# Dynamic Model Catalog & Registry
# ---------------------------------------------------------------------------

DYNAMIC_MODEL_CATALOG: Dict[str, ModelInfo] = {}


def normalize_provider(val: Any) -> Optional[ModelProvider]:
    """Normalize a provider name string or ModelProvider to a ModelProvider enum member."""
    if isinstance(val, ModelProvider):
        return val
    if not isinstance(val, str):
        return None
    val_clean = val.lower().strip().replace("-", "_")
    alias_map = {
        "openai": ModelProvider.OPENAI,
        "anthropic": ModelProvider.ANTHROPIC,
        "claude": ModelProvider.ANTHROPIC,
        "google": ModelProvider.GOOGLE,
        "gemini": ModelProvider.GOOGLE,
        "deepseek": ModelProvider.DEEPSEEK,
        "glm": ModelProvider.GLM,
        "zhipu": ModelProvider.GLM,
        "local": ModelProvider.LOCAL,
        "ollama": ModelProvider.LOCAL,
        "openrouter": ModelProvider.OPENROUTER,
        "litellm": ModelProvider.LITELLM,
        "9brouter": ModelProvider.NINEBROUTER,
        "9b": ModelProvider.NINEBROUTER,
        "custom": ModelProvider.CUSTOM_ROUTER,
        "custom_router": ModelProvider.CUSTOM_ROUTER,
        "orcarouter": ModelProvider.ORCAROUTER,
        "orca": ModelProvider.ORCAROUTER,
        "orca_router": ModelProvider.ORCAROUTER,
    }
    return alias_map.get(val_clean)


def register_dynamic_model(model_info: ModelInfo) -> None:
    """Register a dynamically discovered model into the dynamic catalog."""
    DYNAMIC_MODEL_CATALOG[model_info.model_id] = model_info


def clear_dynamic_models() -> None:
    """Clear all dynamically discovered models."""
    DYNAMIC_MODEL_CATALOG.clear()


# ---------------------------------------------------------------------------
# Public query helpers
# ---------------------------------------------------------------------------

def get_models_by_provider(provider: ModelProvider) -> List[ModelInfo]:
    """Return all registered models that belong to *provider* from both static and dynamic catalogs.

    Args:
        provider: The :class:`ModelProvider` to filter by.

    Returns:
        A list of :class:`ModelInfo` instances for the given provider,
        sorted alphabetically by ``model_id``.
    """
    models_by_id: Dict[str, ModelInfo] = {}
    for m in MODEL_CATALOG.values():
        if m.provider is provider:
            models_by_id[m.model_id] = m
    for m in DYNAMIC_MODEL_CATALOG.values():
        if m.provider is provider:
            models_by_id[m.model_id] = m
    return sorted(models_by_id.values(), key=lambda m: m.model_id)


def get_model_info(model_id: str) -> Optional[ModelInfo]:
    """Look up a single model by its catalog key or dynamic router prefix.

    Args:
        model_id: The key used in :data:`MODEL_CATALOG` (e.g. ``'gpt-5'``,
            ``'gpt-astra'``, ``'claude-sonnet-5'``), dynamic catalog, or a prefixed route
            such as ``'openrouter/<model>'``, ``'9brouter/<model>'``, or
            ``'custom_router/<model>'``.

    Returns:
        The corresponding :class:`ModelInfo`, or ``None`` if not found.
    """
    if model_id in MODEL_CATALOG:
        return MODEL_CATALOG[model_id]

    if model_id in DYNAMIC_MODEL_CATALOG:
        return DYNAMIC_MODEL_CATALOG[model_id]

    # OrcaCyber compatibility aliases: the live catalog exposes the cyber
    # models under the ``orca/`` namespace, and those ids are authoritative.
    if model_id in ("orcacyber-ultra-1.0", "orcacyber-zero-1.5", "orcacyber-zero-1.0"):
        return ModelInfo(
            model_id=f"orca/{model_id}",
            provider=ModelProvider.ORCAROUTER,
            display_name=f"{model_id} (via OrcaRouter)",
            max_tokens=8_192,
            supports_streaming=True,
            supports_tools=True,
            context_window=128_000,
            description=f"OrcaCyber model '{model_id}' routed through OrcaRouter.",
        )

    # Dynamic OpenRouter routing prefix (e.g. openrouter/mistralai/mistral-large)
    if model_id.startswith("openrouter/"):
        sub_id = model_id[len("openrouter/") :]
        return ModelInfo(
            model_id=sub_id,
            provider=ModelProvider.OPENROUTER,
            display_name=f"{sub_id} (via OpenRouter)",
            max_tokens=4096,
            supports_streaming=True,
            supports_tools=True,
            context_window=128_000,
            description=f"Dynamically routed OpenRouter model: {sub_id}",
        )

    # Dynamic 9B Router routing prefix (e.g. 9brouter/specialist-9b)
    if model_id.startswith("9brouter/"):
        sub_id = model_id[len("9brouter/") :]
        return ModelInfo(
            model_id=sub_id,
            provider=ModelProvider.NINEBROUTER,
            display_name=f"{sub_id} (via 9B Router)",
            max_tokens=4096,
            supports_streaming=True,
            supports_tools=True,
            context_window=128_000,
            description=f"Dynamically routed 9B router model: {sub_id}",
        )

    # Dynamic Custom Router routing prefix (e.g. custom_router/sec-gpt or custom/my-llm)
    if model_id.startswith("custom_router/") or model_id.startswith("custom/"):
        prefix = "custom_router/" if model_id.startswith("custom_router/") else "custom/"
        sub_id = model_id[len(prefix) :]
        return ModelInfo(
            model_id=sub_id,
            provider=ModelProvider.CUSTOM_ROUTER,
            display_name=f"{sub_id} (via Custom Router)",
            max_tokens=4096,
            supports_streaming=True,
            supports_tools=True,
            context_window=128_000,
            description=f"Dynamically routed custom model: {sub_id}",
        )

    return None


def list_all_models() -> List[ModelInfo]:
    """Return every model in both the static and dynamic catalogs.

    Returns:
        A list of all :class:`ModelInfo` instances, sorted alphabetically
        by ``model_id``.
    """
    combined: Dict[str, ModelInfo] = dict(MODEL_CATALOG)
    combined.update(DYNAMIC_MODEL_CATALOG)
    return sorted(combined.values(), key=lambda m: m.model_id)


def fetch_all_provider_models(
    providers: Optional[List[Any]] = None,
    force_refresh: bool = False,
) -> Dict[str, List[ModelInfo]]:
    """Query remote provider APIs and auto-register discovered models into DYNAMIC_MODEL_CATALOG.

    Args:
        providers: Optional list of provider enums or string names (e.g. ['openai', 'claude', 'gemini', 'deepseek', 'glm']).
                   If omitted, attempts to fetch from all supported providers.
        force_refresh: If True, clears existing dynamically fetched models before updating.

    Returns:
        A mapping of provider name to the list of newly discovered ModelInfo instances.
    """
    from .providers import ProviderFactory

    if force_refresh:
        clear_dynamic_models()

    if providers:
        target_providers: List[ModelProvider] = []
        for p in providers:
            norm = normalize_provider(p)
            if norm and norm not in target_providers:
                target_providers.append(norm)
    else:
        target_providers = list(ModelProvider)

    discovered: Dict[str, List[ModelInfo]] = {}

    for prov_enum in target_providers:
        prov_key = prov_enum.value
        discovered[prov_key] = []
        try:
            prov_instance = ProviderFactory.get_provider(prov_enum)
            models = prov_instance.fetch_remote_models()
            for m in models:
                register_dynamic_model(m)
                discovered[prov_key].append(m)
        except Exception:
            # Silent fallback so an error in one provider does not interrupt discovery in others
            pass

    return discovered


def get_available_providers() -> List[Dict[str, Any]]:
    """Return metadata for every supported provider.

    Each entry contains:
        - **name** (*str*): Human-readable provider name.
        - **description** (*str*): Short description of the provider.
        - **required_env_vars** (*List[str]*): Environment variables needed.
        - **model_count** (*int*): Number of models registered for this
          provider.

    Returns:
        A list of provider-info dictionaries, one per
        :class:`ModelProvider` member.
    """
    providers: List[Dict[str, Any]] = []
    for member in ModelProvider:
        meta = _PROVIDER_META[member]
        providers.append(
            {
                "id": member.value,
                "name": meta["name"],
                "description": meta["description"],
                "required_env_vars": meta["required_env_vars"],
                "model_count": len(get_models_by_provider(member)),
            }
        )
    return providers
