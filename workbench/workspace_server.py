"""Extended loopback server exposing reviewed adapter planning and durable receipts.

This layer keeps adapter execution separate from the legacy assessment routes. Plans are
minimized, approval is bound to an exact request digest, and only the closed
ExecutionRegistry can execute work. Raw project paths are resubmitted for execution and
are not stored by the lifecycle database.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import threading
from pathlib import Path
from socketserver import TCPServer

from . import __version__
from .adapter_lifecycle import AdapterLifecycle, AdapterLifecyclePersistenceError
from .adapter_report import build_adapter_report
from .registry import ExecutionRegistry, RegistryPolicy
from .server import Handler, LocalServer, State


def _public_record(record, *, include_receipt=False):
    if record is None:
        return None
    result = {
        "id": record["id"],
        "adapter_id": record["adapter_id"],
        "status": record["status"],
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
        "plan_sha256": record["plan_sha256"],
        "declaration": record["declaration"],
        "request_summary": record["request_summary"],
        "outcome": record.get("outcome"),
    }
    if include_receipt and record.get("receipt") is not None:
        result["receipt"] = record["receipt"]
    return result


class WorkbenchHandler(Handler):
    """Adds authenticated adapter lifecycle routes without widening base API authority."""

    def _adapter_json(self):
        if self.headers.get("Transfer-Encoding") or self.headers.get(
            "Content-Encoding"
        ):
            raise ValueError("Encoded and chunked request bodies are not supported")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Invalid Content-Length") from exc
        if (
            not 0 < length <= 16384
            or self.headers.get("Content-Type", "").split(";")[0] != "application/json"
        ):
            raise ValueError("Send a JSON object no larger than 16 KiB")
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise ValueError("Request body must be a JSON object")
        return value

    def do_GET(self):
        reviewed_assets = {
            "/adapter.js": ("adapter.js", "text/javascript; charset=utf-8"),
            "/reviewer.js": ("reviewer.js", "text/javascript; charset=utf-8"),
            "/reviewer.css": ("reviewer.css", "text/css; charset=utf-8"),
        }
        if self.path in reviewed_assets:
            if not self.guard(False):
                return
            filename, kind = reviewed_assets[self.path]
            return self.reply(
                200,
                (Path(__file__).parent / "static" / filename).read_bytes(),
                kind,
            )
        if self.path == "/api/adapters":
            if not self.guard(True):
                return
            return self.reply(
                200,
                {
                    "adapters": self.server.adapter_registry.describe(),
                    "active_id": self.server.adapter_active,
                    "recovered_interruptions": self.server.adapter_lifecycle.recovered_interruptions,
                },
            )
        if self.path == "/api/adapter-runs":
            if not self.guard(True):
                return
            try:
                return self.reply(200, {"runs": self.server.adapter_lifecycle.recent()})
            except ValueError as exc:
                return self.reply(409, {"error": str(exc)})
        match = re.fullmatch(r"/api/adapter-runs/([a-f0-9]{32})", self.path)
        if match:
            if not self.guard(True):
                return
            try:
                record = self.server.adapter_lifecycle.get(match[1])
            except ValueError as exc:
                return self.reply(409, {"error": str(exc)})
            if record is None:
                return self.reply(404, {"error": "Adapter lifecycle record not found"})
            return self.reply(200, _public_record(record, include_receipt=True))
        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/runs":
            with self.server.operation_gate:
                if self.server.adapter_active is not None:
                    if not self.guard(True):
                        return
                    return self.reply(
                        409,
                        {
                            "error": "A reviewed adapter execution is active. Stop or finish it before starting an assessment."
                        },
                    )
                return super().do_POST()

        adapter_route = self.path.startswith("/api/adapters/") or self.path.startswith(
            "/api/adapter-runs/"
        )
        if not adapter_route:
            return super().do_POST()
        if not self.guard(True):
            return
        try:
            data = self._adapter_json()
            if self.path == "/api/adapters/plan":
                if (
                    set(data) != {"adapter_id", "request"}
                    or not isinstance(data.get("adapter_id"), str)
                    or not isinstance(data.get("request"), dict)
                ):
                    raise ValueError("Send exactly adapter_id and request")
                record = self.server.adapter_lifecycle.plan(
                    data["adapter_id"], data["request"]
                )
                return self.reply(201, _public_record(record))

            match = re.fullmatch(
                r"/api/adapter-runs/([a-f0-9]{32})/(approve|execute|cancel|report)",
                self.path,
            )
            if not match:
                return self.reply(404, {"error": "Not found"})
            lifecycle_id, action = match.groups()

            if action == "report":
                if data:
                    raise ValueError("Adapter report import takes an empty JSON object")
                record = self.server.adapter_lifecycle.get(lifecycle_id)
                if record is None:
                    return self.reply(
                        404, {"error": "Adapter lifecycle record not found"}
                    )
                report = build_adapter_report(record)
                existing = self.server.state.store.get(report["id"])
                if existing is None:
                    self.server.state.store.finalize(report)
                    return self.reply(201, {"id": report["id"], "created": True})
                return self.reply(200, {"id": existing["id"], "created": False})

            if action == "approve":
                if set(data) != {"plan_sha256"} or not isinstance(
                    data.get("plan_sha256"), str
                ):
                    raise ValueError("Send exactly plan_sha256")
                record = self.server.adapter_lifecycle.approve(
                    lifecycle_id, data["plan_sha256"]
                )
                return self.reply(200, _public_record(record))

            if action == "cancel":
                if data:
                    raise ValueError("Adapter cancellation takes an empty JSON object")
                with self.server.operation_gate:
                    if (
                        self.server.adapter_active != lifecycle_id
                        or self.server.adapter_cancel is None
                    ):
                        return self.reply(
                            409, {"error": "This adapter execution is not active"}
                        )
                    self.server.adapter_cancel.set()
                return self.reply(
                    202, {"status": "cancellation_requested", "id": lifecycle_id}
                )

            if (
                set(data) != {"adapter_id", "request"}
                or not isinstance(data.get("adapter_id"), str)
                or not isinstance(data.get("request"), dict)
            ):
                raise ValueError(
                    "Send exactly adapter_id and the same typed request used for planning"
                )
            with self.server.operation_gate:
                if self.server.adapter_active is not None:
                    return self.reply(
                        409, {"error": "Another reviewed adapter execution is active"}
                    )
                if self.server.state.active is not None:
                    return self.reply(
                        409,
                        {
                            "error": "An assessment is active. Finish or cancel it before adapter execution."
                        },
                    )
                self.server.adapter_active = lifecycle_id
                self.server.adapter_cancel = threading.Event()
                cancel = self.server.adapter_cancel
            try:
                record = self.server.adapter_lifecycle.execute(
                    lifecycle_id, data["adapter_id"], data["request"], cancel=cancel
                )
                return self.reply(200, _public_record(record, include_receipt=True))
            finally:
                with self.server.operation_gate:
                    if self.server.adapter_active == lifecycle_id:
                        self.server.adapter_active = None
                        self.server.adapter_cancel = None
        except KeyError:
            self.reply(404, {"error": "Adapter lifecycle record not found"})
        except InterruptedError:
            self.reply(
                409,
                {
                    "error": "Adapter execution was cancelled; no successful receipt was fabricated."
                },
            )
        except TimeoutError:
            self.reply(
                408, {"error": "Adapter execution exceeded its reviewed time bound."}
            )
        except PermissionError as exc:
            self.reply(403, {"error": str(exc)})
        except AdapterLifecyclePersistenceError:
            self.reply(
                503,
                {
                    "error": "Adapter execution ended without a durably published terminal record. Check run status; do not automatically re-execute."
                },
            )
        except (ValueError, TypeError, UnicodeDecodeError) as exc:
            self.reply(400, {"error": str(exc)})
        except Exception:
            self.reply(
                500,
                {
                    "error": "Adapter lifecycle error. No successful execution receipt was fabricated."
                },
            )


class WorkbenchServer(LocalServer):
    """Base loopback server plus one serialized reviewed-adapter execution lane."""

    def server_bind(self):
        """Bind loopback without HTTPServer's reverse-DNS lookup."""
        TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]

    def __init__(self, address, state, token):
        super().__init__(address, state, token)
        self.RequestHandlerClass = WorkbenchHandler
        self.adapter_registry = ExecutionRegistry(
            RegistryPolicy(
                max_effect="passive", allow_filesystem=True, allow_network=True
            )
        )
        self.adapter_lifecycle = AdapterLifecycle(
            state.store.path, self.adapter_registry
        )
        self.operation_gate = threading.Lock()
        self.adapter_active = None
        self.adapter_cancel = None


def main():
    parser = argparse.ArgumentParser(
        description="SecScan AI Evidence Workbench (local single-user preview)"
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--data-dir", type=Path, default=Path.home() / ".secscan_ai-workbench"
    )
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    os.umask(0o077)
    token = secrets.token_urlsafe(32)
    state = State(args.data_dir)
    server = WorkbenchServer(("127.0.0.1", args.port), state, token)
    print("SecScan AI Evidence Workbench " + __version__)
    print("Open locally: http://127.0.0.1:" + str(args.port) + "/#token=" + token)
    print(
        "Keep this launch URL private. Loopback only; do not expose through a tunnel."
    )
    print(
        "Native checks and reviewed adapter planning are ready. External scanners are NOT bundled in this milestone."
    )
    print(
        "The current Ollama adapter supports local or explicitly approved cloud-backed models; product evidence/action contracts are provider-neutral."
    )
    if state.recovered_interruptions:
        print(
            f"Recovered {state.recovered_interruptions} interrupted assessment run(s); none were marked completed."
        )
    if server.adapter_lifecycle.recovered_interruptions:
        print(
            f"Recovered {server.adapter_lifecycle.recovered_interruptions} interrupted adapter execution(s); none were marked completed."
        )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        state.cancel.set()
        with server.operation_gate:
            if server.adapter_cancel is not None:
                server.adapter_cancel.set()
    finally:
        server.server_close()
        if state.worker:
            state.worker.join(timeout=10)


if __name__ == "__main__":
    main()
