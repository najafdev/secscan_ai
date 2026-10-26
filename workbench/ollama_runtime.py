"""Ollama gateway with per-assessment local-only or cloud-allowed processing.

The daemon connection remains loopback-only. Inference may be cloud-backed only
with explicit caller consent. Metadata is not an attestation of daemon egress.
No automatic pull, sign-in, provider fallback or model substitution is supported.
"""

from __future__ import annotations

import http.client
import json
import os
import queue
import re
import socket
import threading
import time
from typing import Any

MAX_RESPONSE_BYTES = 262144
MAX_REQUEST_BYTES = 65536
MAX_MODELS = 256
MAX_MODEL_NAME = 120
CLOUD_NOTE = (
    "Set OLLAMA_NO_CLOUD=1 on the Ollama service and restart it. "
    "This client cannot attest the daemon's cloud configuration or network egress."
)


class OllamaError(ValueError):
    """Stable, user-safe failure details; never include response bodies or prompts."""

    def __init__(
        self, code: str, message: str, next_step: str, *, retryable: bool = False
    ):
        super().__init__(message)
        self.code = code
        self.next_step = next_step
        self.retryable = retryable

    def public(self) -> dict[str, Any]:
        return {
            "error": str(self),
            "code": self.code,
            "next_step": self.next_step,
            "retryable": self.retryable,
            "provider": "ollama",
        }


def valid_model_name(value: Any) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= MAX_MODEL_NAME
        and re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._/-]*(?::[A-Za-z0-9][A-Za-z0-9._-]*)?", value
        )
        is not None
        and ".." not in value
        and "//" not in value
        and not value.endswith("/")
    )


def remote_metadata(value: dict[str, Any]) -> bool:
    # Check both fields: a cloud alias need not have 'cloud' in its visible name.
    return any(
        value.get(key) not in (None, "") for key in ("remote_host", "remote_model")
    )


class LocalRuntime:
    """Loopback transport for local or cloud-backed Ollama model selection."""

    def __init__(
        self,
        model: str = "",
        port: int | str | None = None,
        *,
        allow_cloud: bool = False,
    ):
        if type(allow_cloud) is not bool:
            raise OllamaError(
                "invalid_policy",
                "allow_cloud must be boolean.",
                "Choose a processing policy explicitly.",
            )
        self.allow_cloud = allow_cloud
        self._calls = []
        self._attempts = 0
        self._last_metadata = None
        self._catalog_cloud_names = set()
        self._deadline_at = None
        self._cancel = None
        if not isinstance(model, str) or (model and not valid_model_name(model)):
            raise OllamaError(
                "invalid_model",
                "Invalid Ollama model name.",
                "Select an exact installed model from Detect.",
            )
        if "cloud" in model.lower() and not self.allow_cloud:
            raise OllamaError(
                "cloud_model_blocked",
                "The local-only policy does not allow this cloud-tagged model.",
                "Select a local model or explicitly allow cloud processing for this assessment.",
            )
        value = os.getenv("SECSCAN_AI_OLLAMA_PORT", "11434") if port is None else port
        if (
            isinstance(value, bool)
            or not isinstance(value, (str, int))
            or not str(value).isascii()
            or not str(value).isdigit()
        ):
            raise OllamaError(
                "invalid_port",
                "Invalid local Ollama port.",
                "Use an integer port between 1 and 65535.",
            )
        self.port = int(value)
        if not 1 <= self.port <= 65535:
            raise OllamaError(
                "invalid_port",
                "Invalid local Ollama port.",
                "Use an integer port between 1 and 65535.",
            )
        self.model = model

    @property
    def endpoint(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def set_deadline(self, expires_at: float) -> None:
        """Attach the assessment's monotonic absolute deadline to every later request."""
        if isinstance(expires_at, bool) or not isinstance(expires_at, (int, float)):
            raise OllamaError(
                "invalid_deadline",
                "Invalid assessment deadline.",
                "Restart the assessment.",
            )
        self._deadline_at = float(expires_at)
        self._operation_timeout(90)

    def set_cancel(self, cancel) -> None:
        """Attach a cooperative cancellation event to later requests."""
        if cancel is not None and not callable(getattr(cancel, "is_set", None)):
            raise OllamaError(
                "invalid_cancel",
                "Invalid cancellation handle.",
                "Restart the assessment.",
            )
        self._cancel = cancel

    def _cancelled(self) -> bool:
        return self._cancel is not None and self._cancel.is_set()

    def _operation_timeout(self, cap: float) -> float:
        if self._deadline_at is None:
            return float(cap)
        remaining = self._deadline_at - time.monotonic()
        if remaining <= 0:
            raise OllamaError(
                "deadline_exceeded",
                "Assessment wall-clock deadline exceeded before the model operation.",
                "Start a new assessment if additional approved time is required.",
            )
        return max(0.001, min(float(cap), remaining))

    def request(self, route: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        methods = {"/api/tags": "GET", "/api/show": "POST", "/api/chat": "POST"}
        if route not in methods or (data is None) != (methods[route] == "GET"):
            raise OllamaError(
                "route_blocked",
                "Unsupported Ollama operation.",
                "Only model discovery, metadata and chat are supported.",
            )
        if data is not None and not isinstance(data, dict):
            raise OllamaError(
                "invalid_request",
                "Ollama request must be an object.",
                "Review the request contract.",
            )
        body = (
            json.dumps(data, allow_nan=False).encode("utf-8")
            if data is not None
            else None
        )
        if body is not None and len(body) > MAX_REQUEST_BYTES:
            raise OllamaError(
                "request_too_large",
                "AI context exceeds the request budget.",
                "Reduce the evidence summary before retrying.",
            )
        timeout = self._operation_timeout(90 if route == "/api/chat" else 3)
        if self._cancelled():
            raise OllamaError(
                "cancelled",
                "Model operation cancelled before network I/O.",
                "No model request was sent.",
            )

        result_queue: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)
        holder: dict[str, Any] = {"connection": None}

        def deliver(ok: bool, value: Any) -> None:
            try:
                result_queue.put((ok, value), block=False)
            except queue.Full:
                pass

        def perform() -> None:
            # http.client neither reads proxy environment variables nor follows redirects.
            conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=timeout)
            holder["connection"] = conn
            response = None
            try:
                conn.request(
                    methods[route],
                    route,
                    body=body,
                    headers={"Content-Type": "application/json", "Connection": "close"},
                )
                response = conn.getresponse()
                if 300 <= response.status < 400:
                    raise OllamaError(
                        "redirect_blocked",
                        "Ollama redirect refused.",
                        "Connect directly to the trusted local daemon.",
                    )
                if response.status in (401, 403):
                    raise OllamaError(
                        "authentication_unsupported",
                        "Ollama requested authentication.",
                        "Check the local gateway. Cloud models require operator-managed Ollama sign-in; the workbench never collects API keys.",
                    )
                if response.status == 404:
                    raise OllamaError(
                        "not_found",
                        "The selected model or Ollama endpoint was not found.",
                        "Refresh installed models and check the local Ollama version.",
                    )
                if response.status in (429, 503):
                    raise OllamaError(
                        "busy",
                        "Ollama is busy or has no available capacity.",
                        "Check local resources or cloud quota and retry explicitly. No automatic retry or model fallback occurs.",
                        retryable=True,
                    )
                if response.status != 200:
                    raise OllamaError(
                        "service_error",
                        "Ollama could not complete this request.",
                        "Check the local daemon logs and model compatibility.",
                    )
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise OllamaError(
                        "response_too_large",
                        "Ollama response exceeds the byte budget.",
                        "Use a smaller response or model catalog.",
                    )
                value = json.loads(raw)
                if not isinstance(value, dict) or "error" in value:
                    raise OllamaError(
                        "invalid_response",
                        "Ollama returned an invalid response.",
                        "Check the daemon version and selected model.",
                    )
                deliver(True, value)
            except OllamaError as exc:
                deliver(False, exc)
            except (TimeoutError, socket.timeout) as exc:
                deadline_hit = (
                    self._deadline_at is not None
                    and time.monotonic() >= self._deadline_at
                )
                if deadline_hit:
                    deliver(
                        False,
                        OllamaError(
                            "deadline_exceeded",
                            "Assessment wall-clock deadline expired during the model operation.",
                            "Start a new assessment if additional approved time is required.",
                        ),
                    )
                else:
                    deliver(
                        False,
                        OllamaError(
                            "timeout",
                            "Ollama did not respond within the socket timeout.",
                            "Check local load or select a smaller installed model.",
                            retryable=True,
                        ),
                    )
            except (
                json.JSONDecodeError,
                UnicodeDecodeError,
                RecursionError,
                http.client.HTTPException,
            ):
                deliver(
                    False,
                    OllamaError(
                        "invalid_response",
                        "Ollama returned a malformed response.",
                        "Check that the configured port belongs to Ollama.",
                    ),
                )
            except OSError:
                deliver(
                    False,
                    OllamaError(
                        "unreachable",
                        "The local Ollama service is unreachable.",
                        "Start Ollama and check SECSCAN_AI_OLLAMA_PORT.",
                        retryable=True,
                    ),
                )
            finally:
                if response is not None:
                    try:
                        response.close()
                    except OSError:
                        pass
                conn.close()

        def abort_connection() -> None:
            conn = holder.get("connection")
            if conn is None:
                return
            sock = getattr(conn, "sock", None)
            if sock is not None:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            conn.close()

        worker = threading.Thread(
            target=perform, name="secscan_ai-ollama-request", daemon=True
        )
        worker.start()
        while True:
            if self._cancelled():
                abort_connection()
                worker.join(timeout=0.2)
                raise OllamaError(
                    "cancelled",
                    "Model operation cancelled; no response was accepted.",
                    "Already-dispatched model computation may finish in the Ollama service, but the workbench discards its result.",
                )
            if self._deadline_at is not None and time.monotonic() >= self._deadline_at:
                abort_connection()
                worker.join(timeout=0.2)
                raise OllamaError(
                    "deadline_exceeded",
                    "Assessment wall-clock deadline expired during the model operation.",
                    "Start a new assessment if additional approved time is required.",
                )
            wait = 0.025
            if self._deadline_at is not None:
                wait = min(wait, max(0.001, self._deadline_at - time.monotonic()))
            try:
                ok, value = result_queue.get(timeout=wait)
            except queue.Empty:
                continue
            if ok:
                return value
            raise value

    def catalog(self) -> dict[str, Any]:
        models = self.request("/api/tags").get("models")
        if not isinstance(models, list) or len(models) > MAX_MODELS:
            raise OllamaError(
                "invalid_catalog",
                "Invalid or oversized Ollama model catalog.",
                "Keep the local model catalog within the supported limit of 256 entries.",
            )
        names, cloud_names, blocked = set(), set(), 0
        for item in models:
            if not isinstance(item, dict) or not valid_model_name(item.get("name")):
                raise OllamaError(
                    "invalid_catalog",
                    "Ollama returned malformed model metadata.",
                    "Refresh the catalog after checking the daemon.",
                )
            name = item["name"]
            if "cloud" in name.lower() or remote_metadata(item):
                cloud_names.add(name)
                if not self.allow_cloud:
                    blocked += 1
                    continue
            names.add(name)
        self._catalog_cloud_names = set(cloud_names)
        available = sorted(names)
        state = (
            "models_detected"
            if available
            else ("no_local_models" if models else "empty")
        )
        note = (
            f"{len(available)} model candidate(s) detected; Check model validates capabilities before inference. "
            if available
            else "No eligible models detected under this policy. No automatic download will occur. "
        )
        return {
            "provider": "ollama",
            "endpoint": self.endpoint,
            "available": True,
            "state": state,
            "models": available,
            "blocked_models": blocked,
            "cloud_models": sorted(cloud_names),
            "processing_policy": self.processing_policy,
            "cloud_configuration": "not_attested",
            "note": note + self.policy_note,
        }

    def diagnostics(self) -> dict[str, Any]:
        try:
            return self.catalog()
        except OllamaError as exc:
            return {
                "available": False,
                "state": exc.code,
                "models": [],
                "endpoint": self.endpoint,
                "cloud_configuration": "not_attested",
                "note": str(exc) + " " + exc.next_step,
                **exc.public(),
            }

    def local_models(self) -> list[str]:
        """Legacy name: candidates allowed by the selected policy, not an egress claim."""
        return self.catalog()["models"]

    def ensure_local(self) -> None:
        if not self.model or self.model not in self.local_models():
            raise OllamaError(
                "model_not_installed",
                "Select an exact model name available through this Ollama gateway and policy.",
                "Refresh Detect. Automatic pulls and model substitution are disabled.",
            )

    def inspect_model(self, *, require_tools: bool = False) -> dict[str, Any]:
        if not isinstance(require_tools, bool):
            raise ValueError("require_tools must be boolean")
        self.ensure_local()
        value = self.request("/api/show", {"model": self.model})
        cloud_backed = (
            remote_metadata(value)
            or "cloud" in self.model.lower()
            or self.model in self._catalog_cloud_names
        )
        if cloud_backed and not self.allow_cloud:
            raise OllamaError(
                "cloud_model_blocked",
                "The selected alias resolves to a cloud-backed model.",
                "Choose a local model or explicitly approve cloud processing for this assessment.",
            )
        capabilities = value.get("capabilities")
        if (
            not isinstance(capabilities, list)
            or len(capabilities) > 32
            or any(not isinstance(c, str) or len(c) > 80 for c in capabilities)
        ):
            raise OllamaError(
                "capabilities_unknown",
                "Ollama did not report model capabilities.",
                "Use a daemon/model version that reports completion and tool capabilities.",
            )
        if "completion" not in capabilities:
            raise OllamaError(
                "completion_unsupported",
                "This model cannot provide chat analysis.",
                "Choose a completion-capable model, not an embedding-only model.",
            )
        if require_tools and "tools" not in capabilities:
            raise OllamaError(
                "tools_unsupported",
                "This model does not report tool-calling support.",
                "Use Analyst mode or select a tool-capable model. No automatic substitution.",
            )
        details = value.get("details", {})
        if not isinstance(details, dict):
            raise OllamaError(
                "invalid_response",
                "Invalid model details.",
                "Check the local Ollama daemon.",
            )
        metadata = {
            "provider": "ollama",
            "model": self.model,
            "endpoint": self.endpoint,
            "processing_policy": self.processing_policy,
            "execution_location": (
                "cloud_reported" if cloud_backed else "local_reported"
            ),
            "cloud_processing_approved": self.allow_cloud,
            "state": "metadata_checked",
            "capabilities": sorted(set(capabilities)),
            "tool_calling": "tools" in capabilities,
            "parameter_size": str(details.get("parameter_size", "unknown"))[:80],
            "quantization": str(details.get("quantization_level", "unknown"))[:80],
            "cloud_configuration": "not_attested",
            "inference_tested": False,
            "note": "Metadata checked; this does not test inference quality or hardware capacity. "
            + self.policy_note,
        }
        self._last_metadata = dict(metadata)
        return metadata

    @property
    def processing_policy(self) -> str:
        return "cloud_allowed" if self.allow_cloud else "local_only"

    @property
    def policy_note(self) -> str:
        if self.allow_cloud:
            return (
                "Cloud processing is allowed for this request. Selected Ollama models may send "
                "prompts to a cloud service; provider limits may apply. No silent fallback. "
                "Model metadata does not attest the daemon's network egress."
            )
        return CLOUD_NOTE

    def telemetry(self) -> dict[str, Any]:
        """Protocol-reported usage, not billing or an inference-quality benchmark."""

        def total(field):
            values = [call[field] for call in self._calls]
            return (
                sum(values)
                if values and all(value is not None for value in values)
                else None
            )

        return {
            "provider": "ollama",
            "model": self.model,
            "processing_policy": self.processing_policy,
            "execution_location": (self._last_metadata or {}).get(
                "execution_location", "unknown"
            ),
            "cloud_processing_approved": self.allow_cloud,
            "inference_attempts": self._attempts,
            "responses_received": len(self._calls),
            "prompt_tokens_reported": total("prompt_tokens"),
            "output_tokens_reported": total("output_tokens"),
            "calls": [dict(call) for call in self._calls],
            "billing_cost": None,
            "assessment_deadline_attached": self._deadline_at is not None,
            "cancellation_attached": self._cancel is not None,
            "cancellation_behavior": "client_result_discarded; already-dispatched daemon work may continue",
            "note": "Usage is daemon-reported, may be missing and excludes unreported failed calls. Not a bill.",
        }

    def chat(self, messages: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
        if set(extra) - {"tools", "format"}:
            raise OllamaError(
                "override_blocked",
                "AI request configuration override denied.",
                "Model, endpoint, budgets and sampling are controlled by the runtime.",
            )
        if not isinstance(messages, list) or not 1 <= len(messages) <= 16:
            raise ValueError("Invalid message count")
        for message in messages:
            if (
                not isinstance(message, dict)
                or set(message) - {"role", "content", "tool_calls", "tool_name"}
                or message.get("role") not in {"system", "user", "assistant", "tool"}
                or not isinstance(message.get("content"), str)
            ):
                raise ValueError("Invalid chat message")
        tools = extra.get("tools", [])
        if not isinstance(tools, list) or len(tools) > 1:
            raise ValueError("At most one allowlisted tool is supported")
        # Apply the selected processing policy before *every* inference.
        metadata = self.inspect_model(require_tools=bool(tools))
        schema_strategy = "server_schema" if "format" in extra else "not_requested"
        if metadata["execution_location"] == "cloud_reported" and "format" in extra:
            schema = extra.pop("format")
            instruction = (
                "Return only one JSON value matching this contract, without Markdown: "
                + json.dumps(schema, allow_nan=False)
            )
            messages = [dict(message) for message in messages]
            if messages[0]["role"] == "system":
                messages[0]["content"] += "\n" + instruction
            else:
                if len(messages) >= 16:
                    raise ValueError(
                        "No message budget remains for the output contract"
                    )
                messages.insert(0, {"role": "system", "content": instruction})
            schema_strategy = "prompt_then_validate"
        data = {
            "model": self.model,
            "stream": False,
            "messages": messages,
            "options": {"temperature": 0, "num_predict": 768, "num_ctx": 4096},
            "keep_alive": "2m",
            **extra,
        }
        if len(json.dumps(data, allow_nan=False).encode("utf-8")) > MAX_REQUEST_BYTES:
            raise OllamaError(
                "request_too_large",
                "AI context exceeds the request budget.",
                "Reduce the evidence summary.",
            )
        self._attempts += 1
        response = self.request("/api/chat", data)

        def reported_count(key):
            count = response.get(key)
            return count if type(count) is int and 0 <= count <= 10**12 else None

        self._calls.append(
            {
                "prompt_tokens": reported_count("prompt_eval_count"),
                "output_tokens": reported_count("eval_count"),
                "schema_strategy": schema_strategy,
                "done": response.get("done") is True,
            }
        )
        if remote_metadata(response):
            if self._last_metadata is None:
                self._last_metadata = {}
            self._last_metadata["execution_location"] = "cloud_reported"
        if remote_metadata(response) and not self.allow_cloud:
            raise OllamaError(
                "remote_execution_reported",
                "Ollama reported remote inference; output rejected.",
                "Stop using this daemon and verify its cloud/egress policy. Rejection cannot undo an already-sent prompt.",
            )
        if response.get("done") is not True:
            raise OllamaError(
                "incomplete_response",
                "Ollama did not finish its response.",
                "Retry explicitly after checking local capacity.",
                retryable=True,
            )
        if response.get("done_reason") == "length":
            raise OllamaError(
                "output_truncated",
                "Ollama reached the output budget.",
                "Reduce context or select a more suitable model.",
            )
        message = response.get("message")
        if (
            not isinstance(message, dict)
            or message.get("role", "assistant") != "assistant"
            or not isinstance(message.get("content", ""), str)
        ):
            raise OllamaError(
                "invalid_response",
                "Invalid assistant message.",
                "Check model compatibility.",
            )
        result = {"role": "assistant", "content": message.get("content", "")}
        if "tool_calls" in message:
            calls = message["tool_calls"]
            if (
                not isinstance(calls, list)
                or len(calls) > 1
                or any(
                    not isinstance(c, dict) or not isinstance(c.get("function"), dict)
                    for c in calls
                )
            ):
                raise OllamaError(
                    "invalid_tool_call",
                    "Malformed tool request rejected.",
                    "Use a model compatible with the declared tool schema.",
                )
            result["tool_calls"] = calls
        return result
