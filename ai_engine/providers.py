#!/usr/bin/env python3
# SecScan AI core module
"""
Provider client implementations for SecScan AI multi-model AI support.

Implements a unified interface to call different AI providers through a
common abstract base class. Supports OpenAI, Anthropic, Google Gemini,
DeepSeek, GLM (Zhipu), Ollama (local), and OpenRouter.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

# Third-party imports — wrapped so the module loads even when
# optional dependencies are missing.
try:
    import openai

    _HAS_OPENAI = hasattr(openai, "OpenAI")
except ImportError:
    openai = None  # type: ignore[assignment]
    _HAS_OPENAI = False

try:
    import requests

    _HAS_REQUESTS = True
except ImportError:
    requests = None  # type: ignore[assignment]
    _HAS_REQUESTS = False

from .model_registry import ModelProvider, ModelInfo, MODEL_CATALOG, get_model_info
from .orcarouter import (
    CAPABILITY_CHAT,
    OrcaRouterAccessError,
    OrcaRouterAuthError,
    credential_store,
    discover_models,
    resolve_api_base,
)

logger = logging.getLogger(__name__)

__all__ = [
    "BaseProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "DeepSeekProvider",
    "GLMProvider",
    "OllamaProvider",
    "OpenRouterProvider",
    "OrcaRouterProvider",
    "LiteLLMProvider",
    "NineBRouterProvider",
    "CustomRouterProvider",
    "ProviderFactory",
]


# ---------------------------------------------------------------------------
# HTTP Helpers for Dynamic Model Discovery
# ---------------------------------------------------------------------------

def _safe_http_get(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 5,
) -> Optional[Dict[str, Any]]:
    """Perform a safe HTTP GET request with fallback between requests and urllib."""
    if _HAS_REQUESTS and requests is not None and hasattr(requests, "get"):
        try:
            resp = requests.get(url, headers=headers or {}, timeout=timeout)
            if hasattr(resp, "status_code") and resp.status_code == 200:
                if hasattr(resp, "json"):
                    return resp.json()
            return None
        except Exception as exc:
            logger.debug("GET %s via requests failed: %s", url, exc)
    try:
        import json
        import urllib.request
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if getattr(response, "status", 200) == 200:
                return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        logger.debug("GET %s via urllib failed: %s", url, exc)
    return None


def _safe_http_post_json(
    url: str,
    headers: Dict[str, str],
    payload: Dict[str, Any],
    timeout: int = 60,
) -> Tuple[int, Any]:
    """POST JSON with a bounded response, returning ``(status, decoded body)``.

    The HTTP status is returned instead of raised so callers can distinguish a
    terminal credential rejection (401/403) from a transient failure.
    """
    import json

    body_bytes = json.dumps(payload).encode("utf-8")
    if _HAS_REQUESTS and requests is not None and hasattr(requests, "post"):
        try:
            response = requests.post(
                url, headers=headers, data=body_bytes, timeout=timeout
            )
            status = getattr(response, "status_code", 0)
            try:
                data = response.json()
            except Exception:
                data = None
            return status, data
        except Exception as exc:
            raise RuntimeError(f"OrcaRouter request failed: {type(exc).__name__}")

    import urllib.error
    import urllib.request

    request = urllib.request.Request(url, data=body_bytes, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(getattr(response, "status", 200)), json.loads(
                response.read().decode("utf-8")
            )
    except urllib.error.HTTPError as exc:
        try:
            data = json.loads(exc.read().decode("utf-8"))
        except Exception:
            data = None
        return int(exc.code), data



# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------


class BaseProvider(ABC):
    """Abstract base class for all AI provider clients.

    Parameters:
        api_key:  Authentication key for the provider API.
        base_url: Optional override for the provider's API endpoint.
    """

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    def chat_completion(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Send a chat-completion request and return the assistant's text.

        Args:
            model_id:    Provider-specific model identifier.
            messages:    Conversation history as a list of role/content dicts.
            max_tokens:  Maximum number of tokens in the response.
            temperature: Sampling temperature.

        Returns:
            The assistant's response text.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Return ``True`` when the provider is ready to serve requests."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name of this provider."""

    def fetch_remote_models(self) -> List[ModelInfo]:
        """Query the remote provider API for available models.

        Returns:
            List of ModelInfo objects discovered from the provider.
        """
        return []


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------


class OpenAIProvider(BaseProvider):
    """Provider client for the OpenAI API (GPT family).

    Falls back to the ``OPENAI_API_KEY`` environment variable when no
    *api_key* is supplied explicitly.
    """

    def __init__(self, api_key: str = None, base_url: str = None):
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        super().__init__(api_key=resolved_key, base_url=base_url)
        self._client: Optional[object] = None

    def _get_client(self) -> "openai.OpenAI":
        """Lazily create and cache the OpenAI client."""
        if self._client is None:
            if not _HAS_OPENAI:
                raise ImportError(
                    "The 'openai' package is required for OpenAIProvider. "
                    "Install it with: pip install openai"
                )
            kwargs: Dict = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = openai.OpenAI(**kwargs)
        return self._client  # type: ignore[return-value]

    def chat_completion(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Call OpenAI chat completions endpoint."""
        client = self._get_client()
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as exc:
            logger.error("OpenAI chat completion failed: %s", exc)
            raise

    def is_available(self) -> bool:
        """Available when an API key is configured."""
        return bool(self.api_key)

    @property
    def provider_name(self) -> str:
        return "OpenAI"

    def fetch_remote_models(self) -> List[ModelInfo]:
        """Fetch available models from OpenAI API."""
        models: List[ModelInfo] = []
        if not self.is_available():
            return models

        if _HAS_OPENAI:
            try:
                client = self._get_client()
                remote_models = client.models.list()
                data = getattr(remote_models, "data", remote_models)
                for m in data:
                    mid = getattr(m, "id", None) or (m.get("id") if isinstance(m, dict) else str(m))
                    if mid:
                        models.append(
                            ModelInfo(
                                model_id=mid,
                                provider=ModelProvider.OPENAI,
                                display_name=f"OpenAI {mid}",
                                max_tokens=16384,
                                supports_streaming=True,
                                supports_tools=True,
                                context_window=128000,
                                description=f"Discovered OpenAI model: {mid}",
                            )
                        )
                if models:
                    return models
            except Exception as exc:
                logger.debug("OpenAI client.models.list() failed: %s", exc)

        url = f"{self.base_url.rstrip('/') if self.base_url else 'https://api.openai.com/v1'}/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = _safe_http_get(url, headers=headers)
        if data and "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                mid = item.get("id") if isinstance(item, dict) else str(item)
                if mid:
                    models.append(
                        ModelInfo(
                            model_id=mid,
                            provider=ModelProvider.OPENAI,
                            display_name=f"OpenAI {mid}",
                            max_tokens=16384,
                            supports_streaming=True,
                            supports_tools=True,
                            context_window=128000,
                            description=f"Discovered OpenAI model: {mid}",
                        )
                    )
        return models


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------


class AnthropicProvider(BaseProvider):
    """Provider client for the Anthropic Messages API (Claude family).

    Uses raw HTTP via *requests* rather than a vendor SDK.
    Falls back to the ``ANTHROPIC_API_KEY`` environment variable.
    """

    _DEFAULT_BASE_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str = None, base_url: str = None):
        resolved_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        super().__init__(
            api_key=resolved_key, base_url=base_url or self._DEFAULT_BASE_URL
        )

    def chat_completion(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Call the Anthropic Messages API."""
        if not _HAS_REQUESTS:
            raise ImportError(
                "The 'requests' package is required for AnthropicProvider. "
                "Install it with: pip install requests"
            )
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": model_id,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        try:
            resp = requests.post(
                self.base_url, headers=headers, json=payload, timeout=120
            )
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]
        except Exception as exc:
            logger.error("Anthropic chat completion failed: %s", exc)
            raise

    def is_available(self) -> bool:
        return bool(self.api_key)

    @property
    def provider_name(self) -> str:
        return "Anthropic"

    def fetch_remote_models(self) -> List[ModelInfo]:
        """Fetch available models from Anthropic API or latest Claude catalog."""
        models: List[ModelInfo] = []
        if not self.is_available():
            return models

        url = "https://api.anthropic.com/v1/models"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        data = _safe_http_get(url, headers=headers)
        if data and "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                mid = item.get("id")
                dname = item.get("display_name", f"Claude {mid}")
                if mid:
                    models.append(
                        ModelInfo(
                            model_id=mid,
                            provider=ModelProvider.ANTHROPIC,
                            display_name=dname,
                            max_tokens=8192,
                            supports_streaming=True,
                            supports_tools=True,
                            context_window=200000,
                            description=f"Discovered Claude model: {dname}",
                        )
                    )
        if not models:
            # Fallback list of modern Claude frontier models
            known_claude = [
                ("claude-3-7-sonnet-20250219", "Claude 3.7 Sonnet", 200000),
                ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet v2", 200000),
                ("claude-3-5-haiku-20241022", "Claude 3.5 Haiku", 200000),
                ("claude-3-opus-20240229", "Claude 3 Opus", 200000),
                ("claude-3-sonnet-20240229", "Claude 3 Sonnet", 200000),
                ("claude-3-haiku-20240307", "Claude 3 Haiku", 200000),
            ]
            for mid, dname, ctx in known_claude:
                models.append(
                    ModelInfo(
                        model_id=mid,
                        provider=ModelProvider.ANTHROPIC,
                        display_name=dname,
                        max_tokens=8192,
                        supports_streaming=True,
                        supports_tools=True,
                        context_window=ctx,
                        description=f"Anthropic Claude frontier model: {dname}",
                    )
                )
        return models


# ---------------------------------------------------------------------------
# Google (Gemini / Generative Language API)
# ---------------------------------------------------------------------------


class GoogleProvider(BaseProvider):
    """Provider client for Google Generative Language API (Gemini family).

    Falls back to the ``GOOGLE_API_KEY`` environment variable.
    """

    _DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key: str = None, base_url: str = None):
        resolved_key = api_key or os.getenv("GOOGLE_API_KEY")
        super().__init__(
            api_key=resolved_key, base_url=base_url or self._DEFAULT_BASE_URL
        )

    def chat_completion(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Call the Google generateContent endpoint."""
        if not _HAS_REQUESTS:
            raise ImportError(
                "The 'requests' package is required for GoogleProvider. "
                "Install it with: pip install requests"
            )
        url = (
            f"{self.base_url}/models/{model_id}:generateContent" f"?key={self.api_key}"
        )
        # Flatten messages into a single prompt text for the REST API.
        combined_text = "\n".join(
            f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in messages
        )
        payload = {
            "contents": [{"parts": [{"text": combined_text}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        try:
            resp = requests.post(url, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as exc:
            logger.error("Google chat completion failed: %s", exc)
            raise

    def is_available(self) -> bool:
        return bool(self.api_key)

    @property
    def provider_name(self) -> str:
        return "Google"

    def fetch_remote_models(self) -> List[ModelInfo]:
        """Fetch available models from Google Generative Language API."""
        models: List[ModelInfo] = []
        if not self.is_available():
            return models

        url = f"{self.base_url.rstrip('/')}/models?key={self.api_key}"
        data = _safe_http_get(url)
        if data and "models" in data and isinstance(data["models"], list):
            for item in data["models"]:
                raw_name = item.get("name", "")
                mid = raw_name.replace("models/", "") if raw_name.startswith("models/") else raw_name
                dname = item.get("displayName", f"Gemini {mid}")
                input_limit = item.get("inputTokenLimit", 1000000)
                output_limit = item.get("outputTokenLimit", 8192)
                desc = item.get("description", f"Discovered Google model: {mid}")
                if mid:
                    models.append(
                        ModelInfo(
                            model_id=mid,
                            provider=ModelProvider.GOOGLE,
                            display_name=dname,
                            max_tokens=output_limit,
                            supports_streaming=True,
                            supports_tools=True,
                            context_window=input_limit,
                            description=desc,
                        )
                    )
        if not models:
            # Fallback list of modern Gemini frontier models
            known_gemini = [
                ("gemini-2.0-flash", "Gemini 2.0 Flash", 1048576, 8192),
                ("gemini-2.0-flash-thinking-exp", "Gemini 2.0 Flash Thinking", 1048576, 8192),
                ("gemini-2.0-pro", "Gemini 2.0 Pro", 2097152, 8192),
                ("gemini-1.5-pro", "Gemini 1.5 Pro", 2000000, 8192),
                ("gemini-1.5-flash", "Gemini 1.5 Flash", 1000000, 8192),
            ]
            for mid, dname, ctx, mtokens in known_gemini:
                models.append(
                    ModelInfo(
                        model_id=mid,
                        provider=ModelProvider.GOOGLE,
                        display_name=dname,
                        max_tokens=mtokens,
                        supports_streaming=True,
                        supports_tools=True,
                        context_window=ctx,
                        description=f"Google Gemini frontier model: {dname}",
                    )
                )
        return models


# ---------------------------------------------------------------------------
# DeepSeek (OpenAI-compatible)
# ---------------------------------------------------------------------------


class DeepSeekProvider(BaseProvider):
    """Provider client for the DeepSeek API (OpenAI-compatible).

    Falls back to the ``DEEPSEEK_API_KEY`` environment variable.
    """

    _DEFAULT_BASE_URL = "https://api.deepseek.com/v1"

    def __init__(self, api_key: str = None, base_url: str = None):
        resolved_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        super().__init__(
            api_key=resolved_key, base_url=base_url or self._DEFAULT_BASE_URL
        )
        self._client: Optional[object] = None

    def _get_client(self) -> "openai.OpenAI":
        """Lazily create and cache the OpenAI-compatible client."""
        if self._client is None:
            if not _HAS_OPENAI:
                raise ImportError(
                    "The 'openai' package is required for DeepSeekProvider. "
                    "Install it with: pip install openai"
                )
            self._client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._client  # type: ignore[return-value]

    def chat_completion(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Call DeepSeek chat completions via the OpenAI-compatible API."""
        client = self._get_client()
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as exc:
            logger.error("DeepSeek chat completion failed: %s", exc)
            raise

    def is_available(self) -> bool:
        return bool(self.api_key)

    @property
    def provider_name(self) -> str:
        return "DeepSeek"

    def fetch_remote_models(self) -> List[ModelInfo]:
        """Fetch available models from DeepSeek API or frontier models."""
        models: List[ModelInfo] = []
        if not self.is_available():
            return models

        if _HAS_OPENAI:
            try:
                client = self._get_client()
                remote_models = client.models.list()
                data = getattr(remote_models, "data", remote_models)
                for m in data:
                    mid = getattr(m, "id", None) or (m.get("id") if isinstance(m, dict) else str(m))
                    if mid:
                        models.append(
                            ModelInfo(
                                model_id=mid,
                                provider=ModelProvider.DEEPSEEK,
                                display_name=f"DeepSeek {mid}",
                                max_tokens=8192,
                                supports_streaming=True,
                                supports_tools=True,
                                context_window=128000,
                                description=f"Discovered DeepSeek model: {mid}",
                            )
                        )
                if models:
                    return models
            except Exception as exc:
                logger.debug("DeepSeek client.models.list() failed: %s", exc)

        url = f"{self.base_url.rstrip('/')}/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = _safe_http_get(url, headers=headers)
        if data and "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                mid = item.get("id") if isinstance(item, dict) else str(item)
                if mid:
                    models.append(
                        ModelInfo(
                            model_id=mid,
                            provider=ModelProvider.DEEPSEEK,
                            display_name=f"DeepSeek {mid}",
                            max_tokens=8192,
                            supports_streaming=True,
                            supports_tools=True,
                            context_window=128000,
                            description=f"Discovered DeepSeek model: {mid}",
                        )
                    )
        if not models:
            for mid, dname in [
                ("deepseek-chat", "DeepSeek Chat (V3)"),
                ("deepseek-reasoner", "DeepSeek Reasoner (R1)"),
                ("deepseek-r1-zero", "DeepSeek R1 Zero"),
            ]:
                models.append(
                    ModelInfo(
                        model_id=mid,
                        provider=ModelProvider.DEEPSEEK,
                        display_name=dname,
                        max_tokens=8192,
                        supports_streaming=True,
                        supports_tools=True,
                        context_window=128000,
                        description=f"DeepSeek frontier reasoning model: {dname}",
                    )
                )
        return models


# ---------------------------------------------------------------------------
# GLM / Zhipu (BigModel)
# ---------------------------------------------------------------------------


class GLMProvider(BaseProvider):
    """Provider client for the GLM / Zhipu BigModel API.

    Uses an OpenAI-compatible request/response format over raw HTTP.
    Falls back to ``GLM_API_KEY`` or ``ZHIPU_API_KEY`` environment variables.
    """

    _DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    def __init__(self, api_key: str = None, base_url: str = None):
        resolved_key = api_key or os.getenv("GLM_API_KEY") or os.getenv("ZHIPU_API_KEY")
        super().__init__(
            api_key=resolved_key, base_url=base_url or self._DEFAULT_BASE_URL
        )

    def chat_completion(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Call the GLM chat completions endpoint."""
        if not _HAS_REQUESTS:
            raise ImportError(
                "The 'requests' package is required for GLMProvider. "
                "Install it with: pip install requests"
            )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        try:
            resp = requests.post(
                self.base_url, headers=headers, json=payload, timeout=120
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.error("GLM chat completion failed: %s", exc)
            raise

    def is_available(self) -> bool:
        return bool(self.api_key)

    @property
    def provider_name(self) -> str:
        return "GLM"

    def fetch_remote_models(self) -> List[ModelInfo]:
        """Fetch available models from GLM / Zhipu API or registered frontier models."""
        models: List[ModelInfo] = []
        if not self.is_available():
            return models

        base = "https://open.bigmodel.cn/api/paas/v4"
        if self.base_url and "chat/completions" in self.base_url:
            base = self.base_url.replace("/chat/completions", "")
        url = f"{base.rstrip('/')}/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = _safe_http_get(url, headers=headers)
        if data and "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                mid = item.get("id") if isinstance(item, dict) else str(item)
                if mid:
                    models.append(
                        ModelInfo(
                            model_id=mid,
                            provider=ModelProvider.GLM,
                            display_name=f"GLM {mid}",
                            max_tokens=4096,
                            supports_streaming=True,
                            supports_tools=True,
                            context_window=128000,
                            description=f"Discovered GLM model: {mid}",
                        )
                    )
        if not models:
            known_glm = [
                ("glm-4-plus", "GLM-4 Plus", 128000),
                ("glm-4-0520", "GLM-4 (0520)", 128000),
                ("glm-4-air", "GLM-4 Air", 128000),
                ("glm-4-flash", "GLM-4 Flash", 128000),
                ("glm-4-long", "GLM-4 Long", 1000000),
                ("glm-4v-plus", "GLM-4V Plus (Multimodal)", 128000),
                ("glm-zero-preview", "GLM Zero (Preview)", 128000),
                ("codegeex-4", "CodeGeeX-4", 128000),
            ]
            for mid, dname, cwindow in known_glm:
                models.append(
                    ModelInfo(
                        model_id=mid,
                        provider=ModelProvider.GLM,
                        display_name=dname,
                        max_tokens=4096,
                        supports_streaming=True,
                        supports_tools=True,
                        context_window=cwindow,
                        description=f"GLM frontier model: {dname}",
                    )
                )
        return models


# ---------------------------------------------------------------------------
# Ollama (local LLM)
# ---------------------------------------------------------------------------


class OllamaProvider(BaseProvider):
    """Provider client for locally-running Ollama instances.

    Defaults to ``http://localhost:11434`` but honours the
    ``LOCAL_LLM_ENDPOINT`` environment variable.
    """

    _DEFAULT_BASE_URL = "http://localhost:11434"

    def __init__(self, api_key: str = None, base_url: str = None):
        resolved_url = base_url or os.getenv(
            "LOCAL_LLM_ENDPOINT", self._DEFAULT_BASE_URL
        )
        # Ollama does not require an API key.
        super().__init__(api_key=api_key, base_url=resolved_url)

    def chat_completion(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Call the Ollama ``/api/chat`` endpoint."""
        if not _HAS_REQUESTS:
            raise ImportError(
                "The 'requests' package is required for OllamaProvider. "
                "Install it with: pip install requests"
            )
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model_id,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        try:
            resp = requests.post(url, json=payload, timeout=300)
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]
        except Exception as exc:
            logger.error("Ollama chat completion failed: %s", exc)
            raise

    def is_available(self) -> bool:
        """Check connectivity by hitting the ``/api/tags`` endpoint."""
        if not _HAS_REQUESTS:
            return False
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    @property
    def provider_name(self) -> str:
        return "Ollama"

    def fetch_remote_models(self) -> List[ModelInfo]:
        """Fetch locally running models from Ollama /api/tags."""
        models: List[ModelInfo] = []
        url = f"{self.base_url.rstrip('/')}/api/tags"
        data = _safe_http_get(url)
        if data and "models" in data and isinstance(data["models"], list):
            for item in data["models"]:
                name = item.get("name") or item.get("model")
                if name:
                    models.append(
                        ModelInfo(
                            model_id=name,
                            provider=ModelProvider.LOCAL,
                            display_name=f"Ollama {name}",
                            max_tokens=4096,
                            supports_streaming=True,
                            supports_tools=False,
                            context_window=32000,
                            description=f"Local Ollama model: {name}",
                        )
                    )
        return models


# ---------------------------------------------------------------------------
# OpenRouter (OpenAI-compatible aggregator)
# ---------------------------------------------------------------------------


class OpenRouterProvider(BaseProvider):
    """Provider client for the OpenRouter API (OpenAI-compatible).

    Sends additional ``HTTP-Referer`` and ``X-Title`` headers required by
    the OpenRouter terms of service.  Falls back to the
    ``OPENROUTER_API_KEY`` environment variable.
    """

    _DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str = None, base_url: str = None):
        resolved_key = api_key or os.getenv("OPENROUTER_API_KEY")
        resolved_url = (
            base_url
            or os.getenv("OPENROUTER_BASE_URL")
            or os.getenv("OPENROUTER_API_BASE")
            or self._DEFAULT_BASE_URL
        )
        super().__init__(
            api_key=resolved_key, base_url=resolved_url
        )
        self._client: Optional[object] = None

    def _get_client(self) -> "openai.OpenAI":
        """Lazily create and cache the OpenAI-compatible client."""
        if self._client is None:
            if not _HAS_OPENAI:
                raise ImportError(
                    "The 'openai' package is required for OpenRouterProvider. "
                    "Install it with: pip install openai"
                )
            self._client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                default_headers={
                    "HTTP-Referer": "https://secscan.ai",
                    "X-Title": "SecScan AI",
                },
            )
        return self._client  # type: ignore[return-value]

    def chat_completion(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Call OpenRouter chat completions via the OpenAI-compatible API."""
        client = self._get_client()
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as exc:
            logger.error("OpenRouter chat completion failed: %s", exc)
            raise

    def is_available(self) -> bool:
        return bool(self.api_key)

    @property
    def provider_name(self) -> str:
        return "OpenRouter"

    def fetch_remote_models(self) -> List[ModelInfo]:
        """Fetch available models from OpenRouter /models endpoint."""
        models: List[ModelInfo] = []
        url = f"{self.base_url.rstrip('/')}/models"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        data = _safe_http_get(url, headers=headers)
        if data and "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                mid = item.get("id")
                name = item.get("name", mid)
                ctx = item.get("context_length", 128000)
                if mid:
                    models.append(
                        ModelInfo(
                            model_id=f"openrouter/{mid}",
                            provider=ModelProvider.OPENROUTER,
                            display_name=f"OpenRouter: {name}",
                            max_tokens=8192,
                            supports_streaming=True,
                            supports_tools=True,
                            context_window=ctx,
                            description=item.get("description", f"OpenRouter model: {mid}"),
                        )
                    )
        return models


# ---------------------------------------------------------------------------
# OrcaRouter Cyber Inference (OpenAI-compatible cyber gateway)
# ---------------------------------------------------------------------------


class OrcaRouterProvider(BaseProvider):
    """Provider client for OrcaRouter Cyber Inference.

    OrcaRouter is an OpenAI-compatible gateway aimed at authorized security
    teams: the OrcaCyber models serve red-team reasoning while the same
    endpoint carries the gateway's blue-team controls.  Inference lives on
    ``https://api.orcarouter.ai/v1``; the credential is a normal
    ``sk-orca-...`` API key resolved through
    :data:`ai_engine.orcarouter.credential_store`.

    A ``401``/``403`` from the gateway is terminal: OrcaRouter issues durable
    API keys, so the exact credential generation is marked for
    re-authentication instead of attempting a refresh.
    """

    _DEFAULT_BASE_URL = "https://api.orcarouter.ai/v1"

    def __init__(self, api_key: str = None, base_url: str = None):
        credential = credential_store.resolve(api_key) if api_key else credential_store.resolve()
        super().__init__(
            api_key=credential.key if credential else None,
            base_url=resolve_api_base(base_url),
        )
        self._client: Optional[object] = None

    def _get_client(self) -> "openai.OpenAI":
        """Lazily create and cache the OpenAI-compatible client."""
        if self._client is None:
            if not _HAS_OPENAI:
                raise ImportError(
                    "The 'openai' package is required for OrcaRouterProvider. "
                    "Install it with: pip install openai"
                )
            self._client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                default_headers={"X-Title": "SecScan AI"},
            )
        return self._client  # type: ignore[return-value]

    def _mark_rejected_credential(self) -> None:
        credential_store.mark_needs_reauth_for_key(self.api_key)

    def chat_completion(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Call OrcaRouter chat completions via the OpenAI-compatible API."""
        payload = {
            "model": model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if _HAS_OPENAI:
            client = self._get_client()
            try:
                response = client.chat.completions.create(**payload)
                return response.choices[0].message.content
            except Exception as exc:
                status = getattr(exc, "status_code", None)
                if status == 401:
                    self._mark_rejected_credential()
                    raise OrcaRouterAuthError(
                        f"OrcaRouter rejected the credential (HTTP {status})"
                    ) from None
                if status == 403:
                    raise OrcaRouterAccessError(
                        "OrcaRouter denied this model for the workspace "
                        f"(HTTP {status}); the cyber tier may not be unlocked"
                    ) from None
                logger.error("OrcaRouter chat completion failed: %s", exc)
                raise

        status, body = _safe_http_post_json(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-Title": "SecScan AI",
            },
            payload=payload,
        )
        if status == 401:
            self._mark_rejected_credential()
            raise OrcaRouterAuthError(
                f"OrcaRouter rejected the credential (HTTP {status})"
            )
        if status == 403:
            raise OrcaRouterAccessError(
                "OrcaRouter denied this model for the workspace "
                f"(HTTP {status}); the cyber tier may not be unlocked"
            )
        if status != 200:
            raise RuntimeError(f"OrcaRouter chat completion failed: HTTP {status}")
        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError("OrcaRouter returned an unexpected chat response")

    def is_available(self) -> bool:
        return bool(self.api_key)

    @property
    def provider_name(self) -> str:
        return "OrcaRouter Cyber Inference"

    def fetch_remote_models(self) -> List[ModelInfo]:
        """Fetch the live OrcaRouter chat catalog (authoritative when it works)."""
        try:
            result = discover_models(self.api_key, capability=CAPABILITY_CHAT)
        except OrcaRouterAuthError:
            self._mark_rejected_credential()
            return []
        if result.degraded:
            # The registry falls back to the verified static catalog; never
            # merge seed entries into a live result.
            return []
        return [
            ModelInfo(
                model_id=model.model_id,
                provider=ModelProvider.ORCAROUTER,
                display_name=model.display_name,
                max_tokens=8_192,
                supports_streaming=True,
                supports_tools=True,
                context_window=model.context_window,
                description=model.description,
                input_modalities=model.input_modalities,
                reasoning_efforts=model.reasoning_efforts,
            )
            for model in result.models
        ]


# ---------------------------------------------------------------------------
# LiteLLM (unified AI gateway)
# ---------------------------------------------------------------------------


class LiteLLMProvider(BaseProvider):
    """Provider client for the LiteLLM AI gateway.

    LiteLLM provides a unified interface to 100+ LLM providers (OpenAI,
    Anthropic, Google, Azure, Bedrock, Ollama, and more) using the OpenAI
    request/response format.  Falls back to the ``LITELLM_API_KEY``
    environment variable when no *api_key* is supplied explicitly.

    Model identifiers use the LiteLLM format, e.g.
    ``anthropic/claude-sonnet-4-20250514``, ``gpt-4o``,
    ``gemini/gemini-2.5-flash``, ``azure/my-deployment``.
    """

    def __init__(self, api_key: str = None, base_url: str = None):
        resolved_key = api_key or os.getenv("LITELLM_API_KEY")
        resolved_url = base_url or os.getenv("LITELLM_API_BASE")
        super().__init__(api_key=resolved_key, base_url=resolved_url)

    def chat_completion(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Call an LLM via the LiteLLM unified gateway."""
        try:
            import litellm
        except ImportError:
            raise ImportError(
                "The 'litellm' package is required for LiteLLMProvider. "
                "Install it with: pip install litellm"
            )

        kwargs: Dict = {
            "model": model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "drop_params": True,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.base_url:
            kwargs["api_base"] = self.base_url

        try:
            response = litellm.completion(**kwargs)
            return response.choices[0].message.content
        except Exception as exc:
            logger.error("LiteLLM chat completion failed: %s", exc)
            raise

    def is_available(self) -> bool:
        """Available when an API key or provider-specific env var is set."""
        if self.api_key:
            return True
        check_vars = [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
            "AZURE_API_KEY",
            "LITELLM_API_KEY",
        ]
        return any(os.getenv(v) for v in check_vars)

    @property
    def provider_name(self) -> str:
        return "LiteLLM"

    def fetch_remote_models(self) -> List[ModelInfo]:
        """Fetch models from LiteLLM proxy /models endpoint if configured."""
        models: List[ModelInfo] = []
        if self.base_url:
            url = f"{self.base_url.rstrip('/')}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            data = _safe_http_get(url, headers=headers)
            if data and "data" in data and isinstance(data["data"], list):
                for item in data["data"]:
                    mid = item.get("id") if isinstance(item, dict) else str(item)
                    if mid:
                        models.append(
                            ModelInfo(
                                model_id=mid,
                                provider=ModelProvider.LITELLM,
                                display_name=f"LiteLLM: {mid}",
                                max_tokens=8192,
                                supports_streaming=True,
                                supports_tools=True,
                                context_window=128000,
                                description=f"LiteLLM model: {mid}",
                            )
                        )
        return models


# ---------------------------------------------------------------------------
# 9B Router (Intelligent Model & Task Dispatcher)
# ---------------------------------------------------------------------------


class NineBRouterProvider(BaseProvider):
    """Provider client for 9B model routers and intelligent dispatch gateways.

    A 9B Router is an efficient, high-throughput 9B-parameter model (e.g.
    Qwen 2.5 9B, Gemma 2 9B, or a custom router endpoint) that analyzes
    cybersecurity task complexity, decomposes multi-step penetration testing
    prompts, and performs intent routing or direct generation.

    Uses an OpenAI-compatible API interface with fallback to direct HTTP POST.
    Defaults to ``http://localhost:8000/v1`` or ``NINEBROUTER_BASE_URL``.
    """

    _DEFAULT_BASE_URL = "http://localhost:8000/v1"

    def __init__(self, api_key: str = None, base_url: str = None):
        resolved_key = (
            api_key
            or os.getenv("NINEBROUTER_API_KEY")
            or "ninebrouter-local-key"
        )
        resolved_url = (
            base_url
            or os.getenv("NINEBROUTER_BASE_URL")
            or os.getenv("NINEBROUTER_ENDPOINT")
            or self._DEFAULT_BASE_URL
        )
        super().__init__(api_key=resolved_key, base_url=resolved_url)
        self._client: Optional[object] = None

    def _get_client(self) -> "openai.OpenAI":
        if self._client is None:
            if not _HAS_OPENAI:
                raise ImportError(
                    "The 'openai' package is required for NineBRouterProvider. "
                    "Install it with: pip install openai"
                )
            self._client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                default_headers={
                    "X-Router-Type": "9B-Dispatcher",
                    "X-Title": "SecScan AI-9B-Router",
                },
            )
        return self._client  # type: ignore[return-value]

    def chat_completion(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Call 9B Router completions via OpenAI SDK or raw HTTP fallback."""
        if _HAS_OPENAI:
            try:
                client = self._get_client()
                response = client.chat.completions.create(
                    model=model_id,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return response.choices[0].message.content
            except Exception as exc:
                if not _HAS_REQUESTS:
                    logger.error("NineBRouterProvider completion failed: %s", exc)
                    raise

        if not _HAS_REQUESTS:
            raise ImportError(
                "Either 'openai' or 'requests' package is required for NineBRouterProvider."
            )

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Router-Type": "9B-Dispatcher",
        }
        payload = {
            "model": model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"]
                if "text" in choice:
                    return choice["text"]
            if "response" in data:
                return data["response"]
            return str(data)
        except Exception as exc:
            logger.error("NineBRouterProvider raw HTTP completion failed: %s", exc)
            raise

    def is_available(self) -> bool:
        """Available when endpoint or key is configured, or local router port is reachable."""
        if os.getenv("NINEBROUTER_BASE_URL") or os.getenv("NINEBROUTER_API_KEY"):
            return True
        if self.base_url and self.base_url != self._DEFAULT_BASE_URL:
            return True
        if _HAS_REQUESTS:
            try:
                resp = requests.get(f"{self.base_url.rstrip('/')}/models", timeout=1)
                return resp.status_code in (200, 401, 403)
            except Exception:
                return False
        return False

    @property
    def provider_name(self) -> str:
        return "9B Router"

    def fetch_remote_models(self) -> List[ModelInfo]:
        """Fetch models from 9B router endpoint or return supported 9B specialist models."""
        models: List[ModelInfo] = []
        url = f"{self.base_url.rstrip('/')}/models"
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        data = _safe_http_get(url, headers=headers)
        if data and "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                mid = item.get("id") if isinstance(item, dict) else str(item)
                if mid:
                    models.append(
                        ModelInfo(
                            model_id=f"9brouter/{mid}" if not mid.startswith("9brouter/") else mid,
                            provider=ModelProvider.NINEBROUTER,
                            display_name=f"9B Router: {mid}",
                            max_tokens=4096,
                            supports_streaming=True,
                            supports_tools=True,
                            context_window=32768,
                            description=f"9B Router model: {mid}",
                        )
                    )
        if not models:
            for m_id, dname in [
                ("9brouter/agent-router", "9B Intelligent Agent Router"),
                ("9brouter/qwen2.5:9b", "Qwen 2.5 9B Security Router"),
                ("9brouter/gemma2:9b", "Gemma 2 9B Router"),
                ("9brouter/llama-3.1:9b", "Llama 3.1 9B Dispatcher"),
                ("9brouter/deepseek-r1:8b", "DeepSeek R1 8B Distill Router"),
            ]:
                models.append(
                    ModelInfo(
                        model_id=m_id,
                        provider=ModelProvider.NINEBROUTER,
                        display_name=dname,
                        max_tokens=4096,
                        supports_streaming=True,
                        supports_tools=True,
                        context_window=32768,
                        description="Specialized 9B parameter task and exploitation router",
                    )
                )
        return models


# ---------------------------------------------------------------------------
# Custom Router (Generic OpenAI-Compatible Route / Reverse Proxy / Gateway)
# ---------------------------------------------------------------------------


class CustomRouterProvider(BaseProvider):
    """Generic OpenAI-compatible custom route provider.

    Enables routing through any user-provided reverse proxy, enterprise AI gateway,
    or OpenAI-compatible router endpoint (e.g. OpenRouter private gateway,
    LiteLLM proxy, Portkey, Cloudflare AI Gateway, vLLM, or custom internal route).

    Configured via:
        - ``CUSTOM_ROUTER_BASE_URL`` or ``SECSCAN_AI_CUSTOM_ROUTE``
        - ``CUSTOM_ROUTER_API_KEY``
    """

    _DEFAULT_BASE_URL = "http://localhost:8080/v1"

    def __init__(self, api_key: str = None, base_url: str = None):
        resolved_key = (
            api_key
            or os.getenv("CUSTOM_ROUTER_API_KEY")
            or os.getenv("CUSTOM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or "custom-route-key"
        )
        resolved_url = (
            base_url
            or os.getenv("CUSTOM_ROUTER_BASE_URL")
            or os.getenv("SECSCAN_AI_CUSTOM_ROUTE")
            or os.getenv("CUSTOM_ROUTE_URL")
            or self._DEFAULT_BASE_URL
        )
        super().__init__(api_key=resolved_key, base_url=resolved_url)
        self._client: Optional[object] = None

    def _get_client(self) -> "openai.OpenAI":
        if self._client is None:
            if not _HAS_OPENAI:
                raise ImportError(
                    "The 'openai' package is required for CustomRouterProvider. "
                    "Install it with: pip install openai"
                )
            self._client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                default_headers={
                    "X-Title": "SecScan AI-Custom-Router",
                },
            )
        return self._client  # type: ignore[return-value]

    def chat_completion(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Call Custom Router completions via OpenAI SDK or raw HTTP fallback."""
        if _HAS_OPENAI:
            try:
                client = self._get_client()
                response = client.chat.completions.create(
                    model=model_id,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return response.choices[0].message.content
            except Exception as exc:
                if not _HAS_REQUESTS:
                    logger.error("CustomRouterProvider completion failed: %s", exc)
                    raise

        if not _HAS_REQUESTS:
            raise ImportError(
                "Either 'openai' or 'requests' package is required for CustomRouterProvider."
            )

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"]
                if "text" in choice:
                    return choice["text"]
            if "response" in data:
                return data["response"]
            return str(data)
        except Exception as exc:
            logger.error("CustomRouterProvider raw HTTP completion failed: %s", exc)
            raise

    def is_available(self) -> bool:
        """Available when custom route URL or API key is set."""
        return bool(
            os.getenv("CUSTOM_ROUTER_BASE_URL")
            or os.getenv("SECSCAN_AI_CUSTOM_ROUTE")
            or os.getenv("CUSTOM_ROUTER_API_KEY")
            or (self.base_url and self.base_url != self._DEFAULT_BASE_URL)
        )

    @property
    def provider_name(self) -> str:
        return "Custom Router"

    def fetch_remote_models(self) -> List[ModelInfo]:
        """Fetch models from custom OpenAI-compatible gateway /models endpoint."""
        models: List[ModelInfo] = []
        url = f"{self.base_url.rstrip('/')}/models"
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        data = _safe_http_get(url, headers=headers)
        if data and "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                mid = item.get("id") if isinstance(item, dict) else str(item)
                if mid:
                    models.append(
                        ModelInfo(
                            model_id=f"custom_router/{mid}" if not mid.startswith("custom_router/") and not mid.startswith("custom/") else mid,
                            provider=ModelProvider.CUSTOM_ROUTER,
                            display_name=f"Custom Router: {mid}",
                            max_tokens=8192,
                            supports_streaming=True,
                            supports_tools=True,
                            context_window=128000,
                            description=f"Custom routed model: {mid}",
                        )
                    )
        return models


# ---------------------------------------------------------------------------
# Provider Factory
# ---------------------------------------------------------------------------

# Mapping from ModelProvider enum values to their concrete classes.
_PROVIDER_CLASS_MAP: Dict[ModelProvider, type] = {
    ModelProvider.OPENAI: OpenAIProvider,
    ModelProvider.ANTHROPIC: AnthropicProvider,
    ModelProvider.GOOGLE: GoogleProvider,
    ModelProvider.DEEPSEEK: DeepSeekProvider,
    ModelProvider.GLM: GLMProvider,
    ModelProvider.LOCAL: OllamaProvider,
    ModelProvider.OPENROUTER: OpenRouterProvider,
    ModelProvider.ORCAROUTER: OrcaRouterProvider,
    ModelProvider.LITELLM: LiteLLMProvider,
    ModelProvider.NINEBROUTER: NineBRouterProvider,
    ModelProvider.CUSTOM_ROUTER: CustomRouterProvider,
}


class ProviderFactory:
    """Factory for lazily creating and caching provider instances.

    Usage::

        provider, model_info = ProviderFactory.get_provider_for_model("gpt-astra")
        answer = provider.chat_completion(
            model_id=model_info.model_id,
            messages=[{"role": "user", "content": "Hello!"}],
        )
    """

    _providers: Dict[ModelProvider, BaseProvider] = {}

    @classmethod
    def get_provider(
        cls,
        provider: ModelProvider,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> BaseProvider:
        """Return a provider instance, creating it on first access.

        If custom *api_key* or *base_url* is provided, creates a dedicated instance.
        """
        if api_key is not None or base_url is not None:
            provider_cls = _PROVIDER_CLASS_MAP.get(provider)
            if provider_cls is None:
                raise ValueError(
                    f"No provider implementation registered for {provider!r}"
                )
            return provider_cls(api_key=api_key, base_url=base_url)

        if provider not in cls._providers:
            provider_cls = _PROVIDER_CLASS_MAP.get(provider)
            if provider_cls is None:
                raise ValueError(
                    f"No provider implementation registered for {provider!r}"
                )
            cls._providers[provider] = provider_cls()
            logger.debug("Created provider instance for %s", provider.value)
        return cls._providers[provider]

    @classmethod
    def get_provider_for_model(
        cls,
        model_id: str,
        custom_route: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Tuple[BaseProvider, ModelInfo]:
        """Look up a model in the catalog and return its provider instance.

        Supports dynamic routing prefixes ('openrouter/...', '9brouter/...',
        'custom_router/...', 'custom/...') as well as custom route endpoints.

        Args:
            model_id: The model identifier as registered in
                :data:`MODEL_CATALOG`, or a dynamic route prefix.
            custom_route: Optional custom endpoint override URL.
            api_key: Optional API key override.

        Returns:
            A ``(provider_instance, model_info)`` tuple.

        Raises:
            ValueError: If *model_id* cannot be resolved.
        """
        model_info = get_model_info(model_id)
        if model_info is None:
            # Check for custom route or SECSCAN_AI_PROVIDER setting
            custom_provider_name = os.getenv("SECSCAN_AI_PROVIDER", "").lower()
            resolved_route = (
                custom_route
                or os.getenv("SECSCAN_AI_CUSTOM_ROUTE")
                or os.getenv("CUSTOM_ROUTER_BASE_URL")
            )
            if resolved_route or custom_provider_name in ("custom", "custom_router"):
                model_info = ModelInfo(
                    model_id=model_id,
                    provider=ModelProvider.CUSTOM_ROUTER,
                    display_name=f"{model_id} (via Custom Router)",
                    max_tokens=4096,
                    supports_streaming=True,
                    supports_tools=True,
                    context_window=128_000,
                    description=f"Model '{model_id}' dispatched via custom router endpoint.",
                )
            elif custom_provider_name in ("9brouter", "ninebrouter"):
                model_info = ModelInfo(
                    model_id=model_id,
                    provider=ModelProvider.NINEBROUTER,
                    display_name=f"{model_id} (via 9B Router)",
                    max_tokens=4096,
                    supports_streaming=True,
                    supports_tools=True,
                    context_window=128_000,
                    description=f"Model '{model_id}' dispatched via 9B router gateway.",
                )
            elif custom_provider_name == "openrouter":
                model_info = ModelInfo(
                    model_id=model_id,
                    provider=ModelProvider.OPENROUTER,
                    display_name=f"{model_id} (via OpenRouter)",
                    max_tokens=4096,
                    supports_streaming=True,
                    supports_tools=True,
                    context_window=128_000,
                    description=f"Model '{model_id}' dispatched via OpenRouter.",
                )
            elif custom_provider_name in ("orcarouter", "orca", "orca_router"):
                model_info = ModelInfo(
                    model_id=model_id,
                    provider=ModelProvider.ORCAROUTER,
                    display_name=f"{model_id} (via OrcaRouter Cyber Inference)",
                    max_tokens=8192,
                    supports_streaming=True,
                    supports_tools=True,
                    context_window=128_000,
                    description=(
                        f"Model '{model_id}' dispatched via OrcaRouter Cyber Inference."
                    ),
                )
            else:
                raise ValueError(f"Model '{model_id}' not found in MODEL_CATALOG")

        base_url_override = custom_route
        if model_info.provider == ModelProvider.CUSTOM_ROUTER and not base_url_override:
            base_url_override = (
                os.getenv("SECSCAN_AI_CUSTOM_ROUTE")
                or os.getenv("CUSTOM_ROUTER_BASE_URL")
            )
        provider = cls.get_provider(
            model_info.provider,
            api_key=api_key,
            base_url=base_url_override,
        )
        return provider, model_info

    @classmethod
    def get_available_providers(cls) -> List[ModelProvider]:
        """Return the list of providers that are currently available.

        A provider is considered *available* when its ``is_available()``
        method returns ``True`` (typically meaning an API key is
        configured or a local endpoint is reachable).
        """
        available: List[ModelProvider] = []
        for member in ModelProvider:
            try:
                provider = cls.get_provider(member)
                if provider.is_available():
                    available.append(member)
            except (ValueError, Exception) as exc:
                logger.debug("Provider %s not available: %s", member.value, exc)
        return available
