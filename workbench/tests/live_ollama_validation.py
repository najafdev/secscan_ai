"""Live local-model compatibility evidence for the bounded review workflow.

This module is executed explicitly by CI, not by unittest discovery. It talks to a real
Ollama daemon containing one preloaded small model, runs the workbench's fixed
assessment-data-free structured-output self-test, and writes a machine-readable record.
It does not run an assessment, execute a tool, use customer data, or contact a cloud
model through the workbench.

For CI, the daemon may live on a Docker ``--internal`` bridge. The production Ollama
client intentionally accepts loopback only, so this module can create a temporary
loopback TCP relay to one literal private/loopback upstream IP supplied by the workflow.
The relay does not parse, persist, log, redirect, discover, or choose destinations.
"""

from __future__ import annotations

import ipaddress
import json
import os
import socket
import threading
import time
from contextlib import nullcontext
from pathlib import Path

from workbench.ollama import Ollama

SCHEMA = "secscan_ai.live-model-validation/v1"
DEFAULT_MODEL = "smollm2:135m-instruct-q5_K_M"
DEFAULT_DIGEST_PREFIX = "a703ae7fccb0"
UPSTREAM_PORT = 11434


class _LoopbackRelay:
    """Ephemeral test-only loopback relay to one validated private IP."""

    def __init__(self, upstream_host: str, upstream_port: int = UPSTREAM_PORT):
        try:
            address = ipaddress.ip_address(upstream_host)
        except ValueError as exc:
            raise RuntimeError(
                "live-model relay upstream must be a literal IP address"
            ) from exc
        if (
            address.version != 4
            or not address.is_private
            or address.is_multicast
            or address.is_unspecified
        ):
            raise RuntimeError(
                "live-model relay upstream must be one private IPv4 address"
            )
        if (
            isinstance(upstream_port, bool)
            or not isinstance(upstream_port, int)
            or not 1 <= upstream_port <= 65535
        ):
            raise RuntimeError("live-model relay upstream port is invalid")
        self.upstream_host = str(address)
        self.upstream_port = upstream_port
        self.listener: socket.socket | None = None
        self._stop = threading.Event()
        self._accept_thread: threading.Thread | None = None
        self._workers: list[threading.Thread] = []
        self.port: int | None = None

    @staticmethod
    def _copy(source: socket.socket, destination: socket.socket) -> None:
        try:
            while True:
                data = source.recv(65536)
                if not data:
                    break
                destination.sendall(data)
        except OSError:
            pass
        finally:
            try:
                destination.shutdown(socket.SHUT_WR)
            except OSError:
                pass

    def _bridge(self, client: socket.socket) -> None:
        upstream: socket.socket | None = None
        try:
            upstream = socket.create_connection(
                (self.upstream_host, self.upstream_port), timeout=5
            )
            client.settimeout(90)
            upstream.settimeout(90)
            left = threading.Thread(
                target=self._copy, args=(client, upstream), daemon=True
            )
            right = threading.Thread(
                target=self._copy, args=(upstream, client), daemon=True
            )
            left.start()
            right.start()
            left.join(timeout=95)
            right.join(timeout=95)
        finally:
            try:
                client.close()
            except OSError:
                pass
            if upstream is not None:
                try:
                    upstream.close()
                except OSError:
                    pass

    def _accept(self) -> None:
        assert self.listener is not None
        while not self._stop.is_set():
            try:
                client, _ = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            worker = threading.Thread(target=self._bridge, args=(client,), daemon=True)
            self._workers.append(worker)
            worker.start()

    def __enter__(self) -> int:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(8)
        listener.settimeout(0.2)
        self.listener = listener
        self.port = int(listener.getsockname()[1])
        self._accept_thread = threading.Thread(
            target=self._accept, name="secscan_ai-live-model-relay", daemon=True
        )
        self._accept_thread.start()
        return self.port

    def __exit__(self, exc_type, exc, traceback) -> None:
        self._stop.set()
        if self.listener is not None:
            self.listener.close()
        if self._accept_thread is not None:
            self._accept_thread.join(timeout=1)
        for worker in self._workers:
            worker.join(timeout=1)


def _catalog_digest(client: Ollama, model: str) -> str:
    value = client.request("/api/tags")
    models = value.get("models")
    if not isinstance(models, list):
        raise RuntimeError("Ollama catalog did not contain a model list")
    for item in models:
        if isinstance(item, dict) and item.get("name") == model:
            digest = item.get("digest")
            if not isinstance(digest, str) or len(digest) < 12:
                raise RuntimeError("Selected model did not report a usable digest")
            return digest
    raise RuntimeError(
        "Selected live-validation model was not present in the Ollama catalog"
    )


def _run_probe(
    *, port: int | None, model: str, expected_prefix: str, deadline_seconds: float
) -> tuple[dict, dict, str]:
    client = Ollama(model=model, port=port, allow_cloud=False)
    client.set_deadline(time.monotonic() + deadline_seconds)

    digest = _catalog_digest(client, model)
    normalized_digest = digest.lower().removeprefix("sha256:")
    if not normalized_digest.startswith(expected_prefix):
        raise RuntimeError(
            f"live-validation model digest mismatch: expected prefix {expected_prefix}, got {digest}"
        )

    result = client.self_test(require_tools=False)
    telemetry = client.telemetry()
    if result.get("state") != "inference_compatible":
        raise RuntimeError(
            "real model did not satisfy the fixed workbench inference contract"
        )
    if result.get("execution_location") != "local_reported":
        raise RuntimeError("real-model validation was not reported as local inference")
    if (
        result.get("processing_policy") != "local_only"
        or result.get("cloud_processing_approved") is not False
    ):
        raise RuntimeError("real-model validation did not preserve local-only policy")
    if (
        result.get("assessment_data_sent") is not False
        or result.get("self_test_scope") != "synthetic_self_test"
    ):
        raise RuntimeError(
            "real-model probe crossed the assessment-data-free self-test boundary"
        )
    if result.get("tool_calling_tested") is not False:
        raise RuntimeError(
            "live compatibility job must not execute or require a tool call"
        )
    if (
        telemetry.get("inference_attempts") != 1
        or telemetry.get("responses_received") != 1
    ):
        raise RuntimeError(
            "live-model validation expected exactly one inference request/response"
        )
    if telemetry.get("execution_location") != "local_reported":
        raise RuntimeError(
            "telemetry did not preserve local-reported processing location"
        )
    return result, telemetry, digest


def main() -> int:
    model = os.environ.get("SECSCAN_AI_LIVE_OLLAMA_MODEL", DEFAULT_MODEL)
    expected_prefix = os.environ.get(
        "SECSCAN_AI_LIVE_OLLAMA_DIGEST_PREFIX", DEFAULT_DIGEST_PREFIX
    ).lower()
    output_path = Path(
        os.environ.get(
            "SECSCAN_AI_LIVE_OLLAMA_EVIDENCE",
            "_live_model_review/live-model-validation.json",
        )
    )
    deadline_seconds = float(
        os.environ.get("SECSCAN_AI_LIVE_OLLAMA_DEADLINE_SECONDS", "60")
    )
    upstream_host = os.environ.get("SECSCAN_AI_LIVE_OLLAMA_UPSTREAM", "").strip()
    if not 5 <= deadline_seconds <= 180:
        raise RuntimeError("live-model deadline must be between 5 and 180 seconds")

    relay = _LoopbackRelay(upstream_host) if upstream_host else nullcontext(None)
    with relay as relay_port:
        result, telemetry, digest = _run_probe(
            port=relay_port,
            model=model,
            expected_prefix=expected_prefix,
            deadline_seconds=deadline_seconds,
        )

    document = {
        "schema": SCHEMA,
        "checked_out_revision": os.environ.get("GITHUB_SHA", "unknown"),
        "provider": "ollama",
        "model": model,
        "model_digest": digest,
        "expected_digest_prefix": expected_prefix,
        "processing_policy": result["processing_policy"],
        "execution_location": result["execution_location"],
        "cloud_processing_approved": False,
        "structured_output_tested": result.get("structured_output_tested") is True,
        "tool_calling_tested": False,
        "assessment_data_sent": False,
        "self_test_scope": "synthetic_self_test",
        "inference_attempts": telemetry["inference_attempts"],
        "responses_received": telemetry["responses_received"],
        "prompt_tokens_reported": telemetry.get("prompt_tokens_reported"),
        "output_tokens_reported": telemetry.get("output_tokens_reported"),
        "billing_cost": None,
        "assessment_started": False,
        "tool_executed": False,
        "external_assessment_target": False,
        "customer_data": False,
        "transport": (
            "loopback_relay_to_private_ci_network"
            if upstream_host
            else "direct_loopback"
        ),
        "note": (
            "A real preloaded model satisfied the fixed synthetic structured-output compatibility probe. "
            "This validates one model/runtime combination only; it is not a quality benchmark, a security verdict, "
            "or a claim that all Ollama/models/providers are compatible. Network isolation is supplied separately by CI."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(document, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
