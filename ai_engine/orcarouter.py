# SecScan AI core module
"""OrcaRouter Cyber Inference integration.

This module holds the OrcaRouter-specific pieces that are shared by the
provider client, the CLI, and the web dashboard:

* credential resolution (environment variable, ``config.ini`` and a
  runtime-only dashboard override) with masking and terminal ``401`` state;
* capability-aware model discovery against the live model catalog;
* a small, verified cold-start seed used only while discovery is unavailable.

OrcaRouter is an OpenAI-compatible gateway.  Inference and model discovery
live on ``https://api.orcarouter.ai/v1``.  The credential is a normal
OrcaRouter API key (``sk-orca-...``) that belongs to the operator.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

__all__ = [
    "PROVIDER_ID",
    "DISPLAY_NAME",
    "BRAND_URL",
    "CYBER_URL",
    "CYBER_MODELS_URL",
    "DEFAULT_API_BASE",
    "AUTH_BASE",
    "KEY_DASHBOARD_URL",
    "DEFAULT_CYBER_MODEL",
    "CYBER_MODEL_IDS",
    "CYBER_MODEL_ALIASES",
    "FALLBACK_MODEL_ID",
    "ENV_API_KEY",
    "OrcaRouterAuthError",
    "OrcaRouterAccessError",
    "CatalogModel",
    "CatalogResult",
    "Credential",
    "CredentialStore",
    "resolve_api_base",
    "mask_secret",
    "is_well_formed_key",
    "parse_catalog_item",
    "filter_catalog",
    "verified_seed",
    "discover_models",
    "credential_store",
]

PROVIDER_ID = "orcarouter"
DISPLAY_NAME = "OrcaRouter Cyber Inference"
BRAND_URL = "https://www.orcarouter.ai"
CYBER_URL = "https://www.orcarouter.ai/cyber"
CYBER_MODELS_URL = "https://www.orcarouter.ai/models?tier=cyber"
KEY_DASHBOARD_URL = "https://www.orcarouter.ai/console"

DEFAULT_API_BASE = "https://api.orcarouter.ai/v1"
AUTH_BASE = "https://www.orcarouter.ai"

ENV_API_KEY = "ORCAROUTER_API_KEY"

# Cyber-tier models recommended by OrcaRouter for authorized security work.
# The live catalog exposes them under the ``orca/`` namespace; those ids are
# authoritative, and the unqualified ids are accepted as compatibility aliases.
DEFAULT_CYBER_MODEL = "orca/orcacyber-ultra-1.0"
CYBER_MODEL_IDS: Tuple[str, ...] = (
    "orca/orcacyber-ultra-1.0",
    "orca/orcacyber-zero-1.5",
    "orca/orcacyber-zero-1.0",
)
CYBER_MODEL_ALIASES = {
    "orcacyber-ultra-1.0": "orca/orcacyber-ultra-1.0",
    "orcacyber-zero-1.5": "orca/orcacyber-zero-1.5",
    "orcacyber-zero-1.0": "orca/orcacyber-zero-1.0",
}
FALLBACK_MODEL_ID = "orcarouter/fusion"

# Discovery bounds so a catalog response cannot consume unbounded memory.
MAX_CATALOG_BYTES = 2 * 1024 * 1024
MAX_CATALOG_ITEMS = 500
CATALOG_TIMEOUT_SECONDS = 8

# Endpoint types that can serve the OpenAI-style chat contract SecScan AI speaks.
CHAT_ENDPOINT_TYPES: frozenset = frozenset(
    {"openai", "anthropic", "gemini", "openai-response"}
)

# Non-text endpoint families that must never appear in a text chat list.
NON_CHAT_ENDPOINT_TYPES: frozenset = frozenset(
    {"image-generation", "openai-video", "jina-rerank", "embeddings"}
)

CAPABILITY_CHAT = "chat"
CAPABILITY_EMBEDDING = "embedding"
CAPABILITY_IMAGE = "image"
CAPABILITY_VIDEO = "video"
CAPABILITY_RERANK = "rerank"


class OrcaRouterAuthError(RuntimeError):
    """Raised when OrcaRouter rejects the credential.

    The caller must treat this as a terminal re-authentication requirement,
    not as something to retry: OrcaRouter issues durable API keys and has no
    refresh grant.
    """

    def __init__(self, message: str, generation: Optional[int] = None):
        super().__init__(message)
        self.generation = generation


class OrcaRouterAccessError(RuntimeError):
    """Raised when the credential is valid but not entitled to the model.

    A ``403`` for a specific model usually means the workspace has not
    unlocked that tier (for example the OrcaCyber tier).  This must not mark
    the credential for re-authentication.
    """


def resolve_api_base(base_url: Optional[str] = None) -> str:
    """Return the inference origin, honouring explicit overrides first."""
    for candidate in (
        base_url,
        os.getenv("ORCAROUTER_BASE_URL"),
        os.getenv("ORCA_API_BASE_URL"),
        os.getenv("ORCA_BASE_URL"),
        DEFAULT_API_BASE,
    ):
        if candidate:
            return candidate.rstrip("/")
    return DEFAULT_API_BASE


def mask_secret(secret: Optional[str]) -> str:
    """Return a masked, non-reversible label for *secret*.

    Only the documented ``sk-orca-`` marker and the last four characters are
    kept; the middle never leaves the process boundary it was read in.
    """
    if not secret:
        return ""
    if len(secret) <= 12:
        return "sk-orca-…"
    return f"sk-orca-…{secret[-4:]}"


def is_well_formed_key(secret: str) -> bool:
    """Lightweight format check only.

    An ``sk-orca-`` prefix is not proof of validity; the first real request
    establishes that.  This keeps obvious paste mistakes out of the store.
    """
    if not isinstance(secret, str):
        return False
    candidate = secret.strip()
    return (
        len(candidate) >= 20
        and candidate.startswith("sk-orca-")
        and " " not in candidate
    )


@dataclass(frozen=True)
class Credential:
    """A resolved OrcaRouter credential and its provenance."""

    key: str
    source: str
    generation: int = 0

    @property
    def masked(self) -> str:
        return mask_secret(self.key)


@dataclass(frozen=True)
class CatalogModel:
    """Minimal, UI-safe metadata for one catalog entry."""

    model_id: str
    display_name: str
    context_window: int = 128_000
    input_modalities: Tuple[str, ...] = ("text",)
    endpoint_types: Tuple[str, ...] = ("openai",)
    description: str = ""
    reasoning_efforts: Tuple[str, ...] = ()
    cyber_tier: bool = False


@dataclass
class CatalogResult:
    """Outcome of a model-discovery attempt."""

    models: List[CatalogModel] = field(default_factory=list)
    source: str = "live"
    degraded: bool = False
    reason: str = ""
    capability: str = CAPABILITY_CHAT


class CredentialStore:
    """Process-local OrcaRouter credential state.

    The key is read from the operator's existing secret location: the
    ``ORCAROUTER_API_KEY`` environment variable, ``config.ini`` under
    ``[ai] orcarouter_api_key``, or a runtime override supplied through the
    dashboard.  The runtime override is intentionally *not* written to disk:
    the project's established convention is that credentials live in the
    environment or the operator-managed config file.
    """

    def __init__(self, config_reader: Optional[Callable[[], Optional[str]]] = None):
        self._config_reader = config_reader
        self._runtime_key: Optional[str] = None
        self._generation = 0
        self._needs_reauth_generation: Optional[int] = None
        self._lock = threading.Lock()

    def set_config_reader(self, reader: Optional[Callable[[], Optional[str]]]) -> None:
        """Attach the project's config-file reader (``[ai] orcarouter_api_key``)."""
        with self._lock:
            self._config_reader = reader

    @property
    def generation(self) -> int:
        with self._lock:
            return self._generation

    def resolve(self, api_key: Optional[str] = None) -> Optional[Credential]:
        """Resolve the active credential, preferring an explicit argument."""
        with self._lock:
            return self._resolve_locked(api_key)

    def _resolve_locked(self, api_key: Optional[str] = None) -> Optional[Credential]:
        generation = self._generation
        if api_key:
            return Credential(key=api_key, source="argument", generation=generation)
        if self._runtime_key:
            return Credential(
                key=self._runtime_key, source="dashboard", generation=generation
            )
        env_key = os.getenv(ENV_API_KEY)
        if env_key:
            return Credential(key=env_key, source="env", generation=generation)
        if self._config_reader is not None:
            try:
                config_key = self._config_reader()
            except Exception:  # pragma: no cover - defensive config guard
                config_key = None
            if config_key:
                return Credential(
                    key=config_key, source="config", generation=generation
                )
        return None

    def set_runtime_key(self, secret: str) -> Credential:
        """Store a dashboard-supplied key for this process only."""
        if not is_well_formed_key(secret):
            raise ValueError(
                "OrcaRouter API keys start with 'sk-orca-' and contain no spaces."
            )
        with self._lock:
            self._runtime_key = secret.strip()
            self._generation += 1
            self._needs_reauth_generation = None
            return Credential(
                key=self._runtime_key, source="dashboard", generation=self._generation
            )

    def clear(self) -> None:
        """Forget the runtime override and any re-authentication state."""
        with self._lock:
            self._runtime_key = None
            self._generation += 1
            self._needs_reauth_generation = None

    def mark_needs_reauth(self, generation: Optional[int] = None) -> bool:
        """Mark the credential generation that OrcaRouter rejected.

        A late failure from an older generation must never poison a key that
        was replaced in the meantime; only the current generation is marked.
        """
        with self._lock:
            if generation is not None and generation != self._generation:
                return False
            self._needs_reauth_generation = self._generation
            return True

    def mark_needs_reauth_for_key(self, key: Optional[str]) -> bool:
        """Mark re-auth only when *key* is still the active credential.

        This keeps a rejected request from an older credential generation
        from flagging a freshly replaced key.
        """
        with self._lock:
            active = self._resolve_locked()
            if active is None or not key or active.key != key:
                return False
            self._needs_reauth_generation = self._generation
            return True

    def needs_reauth(self) -> bool:
        with self._lock:
            return self._needs_reauth_generation is not None

    def status(self) -> Dict[str, Any]:
        """Return a browser-safe credential status payload (never the key)."""
        credential = self.resolve()
        with self._lock:
            needs_reauth = self._needs_reauth_generation is not None
            generation = self._generation
        return {
            "configured": credential is not None,
            "masked": credential.masked if credential else "",
            "source": credential.source if credential else "",
            "needs_reauth": needs_reauth,
            "generation": generation,
        }


# ---------------------------------------------------------------------------
# Model catalog discovery
# ---------------------------------------------------------------------------


def _coerce_str_tuple(value: Any) -> Tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value if isinstance(item, str))


def _item_input_modalities(item: Dict[str, Any]) -> Tuple[str, ...]:
    architecture = item.get("architecture")
    if isinstance(architecture, dict):
        modalities = _coerce_str_tuple(architecture.get("input_modalities"))
        if modalities:
            return modalities
    return _coerce_str_tuple(item.get("input_modalities")) or ("text",)


def parse_catalog_item(item: Any) -> Optional[CatalogModel]:
    """Parse one catalog record, rejecting shapes the client cannot speak."""
    if not isinstance(item, dict):
        return None
    model_id = item.get("id")
    if not isinstance(model_id, str) or not model_id.strip():
        return None
    model_id = model_id.strip()
    if len(model_id) > 256 or any(ch.isspace() for ch in model_id):
        return None

    endpoint_types = _coerce_str_tuple(item.get("supported_endpoint_types")) or (
        "openai",
    )
    context_window = item.get("context_length", item.get("context_window", 128_000))
    if not isinstance(context_window, int) or context_window <= 0:
        context_window = 128_000

    description = item.get("description")
    if not isinstance(description, str):
        description = ""
    display_name = item.get("name")
    if not isinstance(display_name, str) or not display_name.strip():
        display_name = model_id

    reasoning = _coerce_str_tuple(item.get("reasoning_efforts"))
    if not reasoning and item.get("supported_reasoning_effort"):
        reasoning = _coerce_str_tuple(item.get("supported_reasoning_effort"))

    return CatalogModel(
        model_id=model_id,
        display_name=display_name.strip()[:120],
        context_window=context_window,
        input_modalities=_item_input_modalities(item),
        endpoint_types=endpoint_types,
        description=description[:240],
        reasoning_efforts=reasoning,
        cyber_tier=bool(item.get("cyber")) or model_id in CYBER_MODEL_IDS,
    )


def filter_catalog(
    models: Iterable[CatalogModel],
    capability: str = CAPABILITY_CHAT,
    required_input_modalities: Sequence[str] = (),
) -> List[CatalogModel]:
    """Filter catalog entries for the capability an entry point actually uses.

    Non-text requirements fail closed: a model is only kept when its catalog
    metadata explicitly declares every required input modality.
    """
    required = tuple(m for m in required_input_modalities if m and m.lower() != "text")
    kept: List[CatalogModel] = []
    for model in models:
        endpoint_types = set(model.endpoint_types)

        if capability == CAPABILITY_CHAT:
            if endpoint_types & NON_CHAT_ENDPOINT_TYPES and not (
                endpoint_types & CHAT_ENDPOINT_TYPES
            ):
                continue
            if not endpoint_types & CHAT_ENDPOINT_TYPES:
                continue
            modalities = {m.lower() for m in model.input_modalities}
            if required and not all(mod in modalities for mod in required):
                continue
        elif capability == CAPABILITY_EMBEDDING:
            if (
                "embeddings" not in endpoint_types
                and CAPABILITY_EMBEDDING not in endpoint_types
            ):
                continue
        elif capability == CAPABILITY_IMAGE:
            if "image-generation" not in endpoint_types:
                continue
        elif capability == CAPABILITY_VIDEO:
            if "openai-video" not in endpoint_types:
                continue
        elif capability == CAPABILITY_RERANK:
            if "jina-rerank" not in endpoint_types:
                continue
        else:
            continue
        kept.append(model)

    return sorted(kept, key=lambda m: (not m.cyber_tier, m.model_id.lower()))


def verified_seed(capability: str = CAPABILITY_CHAT) -> List[CatalogModel]:
    """Return the small, verified cold-start catalog.

    These entries are only used when live discovery is unavailable, and the
    UI labels them as degraded.  Ordering puts the cyber-tier models first.
    """
    if capability != CAPABILITY_CHAT:
        # No verified seed exists for other capabilities; fail closed rather
        # than invent model names.
        return []
    return [
        CatalogModel(
            model_id=DEFAULT_CYBER_MODEL,
            display_name="OrcaCyber Ultra 1.0",
            context_window=200_000,
            endpoint_types=("openai",),
            description=(
                "Cybersecurity reasoning model tuned for multi-step analysis of "
                "large codebases; recommended default for authorized security work."
            ),
            reasoning_efforts=("low", "medium", "high"),
            cyber_tier=True,
        ),
        CatalogModel(
            model_id="orca/orcacyber-zero-1.5",
            display_name="OrcaCyber Zero 1.5",
            context_window=128_000,
            endpoint_types=("openai",),
            description="OrcaCyber-harness-driven security model for scoped tasks.",
            cyber_tier=True,
        ),
        CatalogModel(
            model_id=FALLBACK_MODEL_ID,
            display_name="OrcaRouter Fusion",
            context_window=128_000,
            endpoint_types=("openai",),
            description="General routing model used when the cyber tier is not unlocked.",
        ),
        CatalogModel(
            model_id="openai/gpt-5.5",
            display_name="GPT-5.5 (via OrcaRouter)",
            context_window=400_000,
            endpoint_types=("openai",),
            description="General-purpose reasoning model routed through OrcaRouter.",
            reasoning_efforts=("low", "medium", "high", "xhigh"),
        ),
        CatalogModel(
            model_id="anthropic/claude-opus-4.8",
            display_name="Claude Opus 4.8 (via OrcaRouter)",
            context_window=200_000,
            endpoint_types=("openai-response", "openai"),
            input_modalities=("text", "image"),
            description="Anthropic flagship model routed through OrcaRouter.",
        ),
        CatalogModel(
            model_id="google/gemini-3.5-flash",
            display_name="Gemini 3.5 Flash (via OrcaRouter)",
            context_window=1_000_000,
            endpoint_types=("gemini", "openai"),
            input_modalities=("text", "image"),
            description="Fast Gemini model routed through OrcaRouter.",
        ),
        CatalogModel(
            model_id="deepseek/deepseek-v4-pro",
            display_name="DeepSeek V4 Pro (via OrcaRouter)",
            context_window=128_000,
            endpoint_types=("openai",),
            description="DeepSeek reasoning model routed through OrcaRouter.",
            reasoning_efforts=("low", "high"),
        ),
        CatalogModel(
            model_id="orcarouter/auto",
            display_name="OrcaRouter Auto",
            context_window=128_000,
            endpoint_types=("openai",),
            description="Automatic model routing across the OrcaRouter catalog.",
        ),
    ]


def _default_http_get(
    url: str, headers: Dict[str, str], timeout: int
) -> Tuple[int, bytes]:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(getattr(response, "status", 200)), response.read(
                MAX_CATALOG_BYTES
            )
    except urllib.error.HTTPError as exc:  # pragma: no cover - network dependent
        return int(exc.code), b""


def discover_models(
    api_key: Optional[str],
    capability: str = CAPABILITY_CHAT,
    base_url: Optional[str] = None,
    required_input_modalities: Sequence[str] = (),
    http_get: Optional[Callable[[str, Dict[str, str], int], Tuple[int, bytes]]] = None,
    timeout: int = CATALOG_TIMEOUT_SECONDS,
) -> CatalogResult:
    """Fetch the live OrcaRouter catalog, falling back to the verified seed.

    The live catalog is authoritative whenever it succeeds.  On a transport
    failure, a missing credential, or a malformed payload the verified seed is
    returned with ``degraded=True`` so the UI can label it.  A ``401``/``403``
    is surfaced as :class:`OrcaRouterAuthError` instead of being silently
    papered over with seed data.
    """
    if not api_key:
        return CatalogResult(
            models=verified_seed(capability),
            source="fallback",
            degraded=True,
            reason="missing_credentials",
            capability=capability,
        )

    origin = resolve_api_base(base_url)
    query = "?capability=" + urllib.parse.quote(capability)
    url = f"{origin}/models{query}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "X-Title": "SecScan AI",
    }
    getter = http_get or _default_http_get
    try:
        status, body = getter(url, headers, timeout)
    except Exception:
        return CatalogResult(
            models=verified_seed(capability),
            source="fallback",
            degraded=True,
            reason="network_error",
            capability=capability,
        )

    if status == 401:
        raise OrcaRouterAuthError(f"OrcaRouter rejected the credential (HTTP {status})")
    if status == 403:
        return CatalogResult(
            models=verified_seed(capability),
            source="fallback",
            degraded=True,
            reason="forbidden",
            capability=capability,
        )
    if status != 200:
        return CatalogResult(
            models=verified_seed(capability),
            source="fallback",
            degraded=True,
            reason=f"http_{status}",
            capability=capability,
        )

    try:
        payload = json.loads(body.decode("utf-8") if isinstance(body, bytes) else body)
    except (ValueError, UnicodeDecodeError):
        return CatalogResult(
            models=verified_seed(capability),
            source="fallback",
            degraded=True,
            reason="malformed_catalog",
            capability=capability,
        )

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        return CatalogResult(
            models=verified_seed(capability),
            source="fallback",
            degraded=True,
            reason="malformed_catalog",
            capability=capability,
        )

    parsed: List[CatalogModel] = []
    for item in data[:MAX_CATALOG_ITEMS]:
        model = parse_catalog_item(item)
        if model is not None:
            parsed.append(model)

    filtered = filter_catalog(
        parsed,
        capability=capability,
        required_input_modalities=required_input_modalities,
    )
    if not filtered:
        return CatalogResult(
            models=verified_seed(capability),
            source="fallback",
            degraded=True,
            reason="empty_catalog",
            capability=capability,
        )
    return CatalogResult(
        models=filtered, source="live", degraded=False, reason="", capability=capability
    )


# Process-wide store shared by the provider client, CLI and dashboard.  The
# host application attaches its config reader once at start-up.
credential_store = CredentialStore()
