# SecScan AI core module
from .advanced_engine import (
    AdvancedAIEngine,
    AnalysisResult,
    PatternRecognizer,
    VulnerabilityCorrelator,
    ContextManager,
)
from .cve_intelligence import (
    CVEIntelligenceEngine,
    CVEInfo,
)
from .attack_chainer import (
    AttackChainingEngine,
    AttackGraph,
    AttackNode,
    AttackEdge,
    AttackStage,
)
from .llm_red_team import (
    LLMRedTeamEngine,
    OWASPLLMCategory,
    RedTeamProbe,
    ProbeResult,
    LLMRedTeamReport,
)
from .model_registry import (
    ModelProvider,
    ModelInfo,
    MODEL_CATALOG,
    DYNAMIC_MODEL_CATALOG,
    get_model_info,
    list_all_models,
    get_models_by_provider,
    get_available_providers,
    register_dynamic_model,
    clear_dynamic_models,
    fetch_all_provider_models,
    normalize_provider,
)
from .orcarouter import (
    DISPLAY_NAME as ORCAROUTER_DISPLAY_NAME,
    OrcaRouterAuthError,
    credential_store as orca_credential_store,
    discover_models as discover_orcarouter_models,
)
from .providers import (
    ProviderFactory,
    BaseProvider,
    OpenAIProvider,
    AnthropicProvider,
    GoogleProvider,
    DeepSeekProvider,
    GLMProvider,
    OllamaProvider,
    OpenRouterProvider,
    LiteLLMProvider,
    NineBRouterProvider,
    CustomRouterProvider,
)


def get_advanced_ai_engine(
    model_id: str = None, provider: str = None, custom_route: str = None
):
    """Initialize and return the advanced AI engine with optional model or custom route selection."""
    return AdvancedAIEngine(
        model_id=model_id, provider=provider, custom_route=custom_route
    )


__all__ = [
    "AdvancedAIEngine",
    "AnalysisResult",
    "PatternRecognizer",
    "VulnerabilityCorrelator",
    "ContextManager",
    "CVEIntelligenceEngine",
    "CVEInfo",
    "AttackChainingEngine",
    "AttackGraph",
    "AttackNode",
    "AttackEdge",
    "AttackStage",
    "LLMRedTeamEngine",
    "OWASPLLMCategory",
    "RedTeamProbe",
    "ProbeResult",
    "LLMRedTeamReport",
    "get_advanced_ai_engine",
    "ModelProvider",
    "ModelInfo",
    "MODEL_CATALOG",
    "DYNAMIC_MODEL_CATALOG",
    "get_model_info",
    "list_all_models",
    "get_models_by_provider",
    "get_available_providers",
    "register_dynamic_model",
    "clear_dynamic_models",
    "fetch_all_provider_models",
    "normalize_provider",
    "ProviderFactory",
    "BaseProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "DeepSeekProvider",
    "GLMProvider",
    "OllamaProvider",
    "OpenRouterProvider",
    "LiteLLMProvider",
    "NineBRouterProvider",
    "CustomRouterProvider",
]
