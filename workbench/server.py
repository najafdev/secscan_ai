"""Single-user loopback workbench. Not a public-facing production web server."""

import argparse
import copy
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__
from .bundle import build_bundle
from .engine import Assessment, Scope, digest, markdown, now, seal, verify_integrity
from .ollama import Ollama, OllamaError
from .retest import compare_reports


class Busy(Exception):
    pass


def durable_for_review(report):
    """Legacy finalized rows remain reviewable; explicit memory-only results do not."""
    durability = report.get("durability") if isinstance(report, dict) else None
    return not isinstance(durability, dict) or durability.get("status") == "durable"


class Store:
    """SQLite report store with a separate checkpoint table for in-flight work."""

    def __init__(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = directory / "reports.sqlite3"
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, started TEXT NOT NULL, content TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS active_runs (id TEXT PRIMARY KEY, started TEXT NOT NULL, content TEXT NOT NULL)"
            )
            connection.commit()
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    def save_active(self, report):
        if (
            not isinstance(report, dict)
            or report.get("status") != "running"
            or not isinstance(report.get("id"), str)
        ):
            raise ValueError("Only running report snapshots may be checkpointed")
        raw = json.dumps(report)
        if len(raw.encode()) > 2_000_000:
            raise ValueError("Running report snapshot is too large")
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO active_runs VALUES (?, ?, ?)",
                (report["id"], report["started_at"], raw),
            )
            connection.commit()

    def finalize(self, report):
        """Atomically publish an intact terminal report and retire its active checkpoint."""
        if not verify_integrity(report) or report.get("status") == "running":
            raise ValueError("Refusing to finalize a running or invalid report")
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT OR REPLACE INTO reports VALUES (?, ?, ?)",
                (report["id"], report["started_at"], json.dumps(report)),
            )
            connection.execute("DELETE FROM active_runs WHERE id = ?", (report["id"],))
            connection.commit()

    def save(self, report):
        """Compatibility alias used by existing tests/callers."""
        self.finalize(report)

    def recover_interrupted(self):
        """Convert trustworthy stale running checkpoints into explicit interrupted reports."""
        recovered = 0
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            rows = connection.execute(
                "SELECT id, content FROM active_runs ORDER BY started"
            ).fetchall()
            for run_id, raw in rows:
                try:
                    report = json.loads(raw)
                    if (
                        not isinstance(report, dict)
                        or report.get("id") != run_id
                        or report.get("status") != "running"
                    ):
                        raise ValueError("invalid active snapshot")
                    candidate = copy.deepcopy(report)
                    seal(candidate)
                    if not verify_integrity(candidate):
                        raise ValueError("active snapshot integrity chain mismatch")
                    report["status"] = "interrupted"
                    report["verdict"] = "inconclusive"
                    report["finished_at"] = now()
                    previous = (
                        report["events"][-1]["sha256"]
                        if report.get("events")
                        else "0" * 64
                    )
                    event = {
                        "sequence": len(report.get("events", [])) + 1,
                        "at": now(),
                        "kind": "interrupted",
                        "message": "Recovered after an unclean workbench stop; completion is not assumed.",
                        "details": {"recovered_after_restart": True},
                        "previous_sha256": previous,
                    }
                    event["sha256"] = digest(event)
                    report.setdefault("events", []).append(event)
                    report.setdefault("limitations", []).append(
                        "This run was interrupted before durable finalization and was recovered from a running checkpoint."
                    )
                    report["durability"] = {
                        "status": "durable",
                        "storage": "sqlite",
                        "terminal_publication": "restart_recovery_transaction",
                        "checkpoint_gap_observed": False,
                    }
                    seal(report)
                    if not verify_integrity(report):
                        raise ValueError("recovered report failed integrity validation")
                    connection.execute(
                        "INSERT OR REPLACE INTO reports VALUES (?, ?, ?)",
                        (run_id, report["started_at"], json.dumps(report)),
                    )
                    connection.execute(
                        "DELETE FROM active_runs WHERE id = ?", (run_id,)
                    )
                    recovered += 1
                except (ValueError, TypeError, json.JSONDecodeError):
                    connection.execute(
                        "DELETE FROM active_runs WHERE id = ?", (run_id,)
                    )
            connection.commit()
        return recovered

    def get(self, run_id):
        with closing(sqlite3.connect(self.path)) as connection:
            row = connection.execute(
                "SELECT content FROM reports WHERE id = ?", (run_id,)
            ).fetchone()
        if not row:
            return None
        report = json.loads(row[0])
        if not verify_integrity(report):
            raise ValueError("Stored report checksum mismatch")
        return report

    def recent(self):
        with closing(sqlite3.connect(self.path)) as connection:
            rows = connection.execute(
                "SELECT content FROM reports ORDER BY started DESC LIMIT 50"
            ).fetchall()
        result = []
        for row in rows:
            report = json.loads(row[0])
            if verify_integrity(report):
                result.append(
                    {
                        k: report[k]
                        for k in (
                            "id",
                            "started_at",
                            "target",
                            "mode",
                            "status",
                            "verdict",
                        )
                    }
                )
        return result


class State:
    def __init__(self, directory):
        self.store = Store(directory)
        self.recovered_interruptions = self.store.recover_interrupted()
        self.lock = threading.Lock()
        self.active = None
        self.live = None
        self.cancel = threading.Event()
        self.worker = None
        self.checkpoint_persistence_failed = False

    def start(self, data):
        scope = Scope.parse(data)
        with self.lock:
            if self.active:
                raise Busy(
                    "An assessment is already running. Cancel it or let its bounded work finish."
                )
            self.cancel = threading.Event()
            assessment = Assessment(scope, cancel=self.cancel, notify=self.update)
            self.active = assessment.report["id"]
            self.live = copy.deepcopy(assessment.report)
            self.checkpoint_persistence_failed = False
            run_id = self.active
            try:
                self.store.save_active(self.live)
            except Exception:
                self.active = None
                self.live = None
                raise
            self.worker = threading.Thread(
                target=self.run, args=(assessment,), daemon=True
            )
            self.worker.start()
        return run_id

    def update(self, report):
        # Progress snapshots are publishable only while they are explicitly running.
        # Terminal state is published by run() after durable commit succeeds or after
        # the result is explicitly marked memory-only.
        if not isinstance(report, dict) or report.get("status") != "running":
            return
        with self.lock:
            if self.active != report.get("id"):
                return
            self.live = copy.deepcopy(report)
        try:
            self.store.save_active(report)
        except Exception:
            with self.lock:
                if self.active == report.get("id"):
                    self.checkpoint_persistence_failed = True

    def run(self, assessment):
        report = assessment.run()
        with self.lock:
            checkpoint_gap = bool(self.checkpoint_persistence_failed)

        durable = copy.deepcopy(report)
        durable["durability"] = {
            "status": "durable",
            "storage": "sqlite",
            "terminal_publication": "after_atomic_commit",
            "checkpoint_gap_observed": checkpoint_gap,
        }
        seal(durable)
        try:
            self.store.finalize(durable)
            published = durable
        except Exception:
            published = copy.deepcopy(report)
            published["durability"] = {
                "status": "not_durable",
                "storage": "memory_only",
                "terminal_publication": "after_persistence_failure",
                "checkpoint_gap_observed": checkpoint_gap,
                "reason": "terminal_persistence_failed",
            }
            published.setdefault("limitations", []).append(
                "Terminal persistence failed. This intact result is memory-only and cannot be exported or compared as durable review evidence."
            )
            seal(published)
        with self.lock:
            self.live = published
            self.active = None

    def get(self, run_id):
        with self.lock:
            if self.live and self.live["id"] == run_id:
                return copy.deepcopy(self.live)
        return self.store.get(run_id)


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False
    request_queue_size = 8

    def __init__(self, address, state, token):
        self.state = state
        self.token = token
        self.slots = threading.BoundedSemaphore(12)
        super().__init__(address, Handler)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()


class Handler(BaseHTTPRequestHandler):
    server_version = "SecScanAIWorkbench/" + __version__
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *_):
        pass

    def reply(
        self, status, value, kind="application/json; charset=utf-8", attachment=None
    ):
        body = value if isinstance(value, bytes) else json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        )
        self.send_header("Connection", "close")
        if attachment:
            self.send_header(
                "Content-Disposition", 'attachment; filename="' + attachment + '"'
            )
        self.end_headers()
        self.close_connection = True
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def guard(self, api):
        port = self.server.server_port
        hosts = {"127.0.0.1:" + str(port), "localhost:" + str(port)}
        if self.headers.get("Host") not in hosts:
            self.reply(403, {"error": "Invalid Host; use the loopback launch address"})
            return False
        origin = self.headers.get("Origin")
        if origin is not None and origin not in {"http://" + h for h in hosts}:
            self.reply(403, {"error": "Cross-origin requests are not allowed"})
            return False
        if api:
            supplied = self.headers.get("Authorization", "")
            expected = "Bearer " + self.server.token
            if not hmac.compare_digest(supplied.encode(), expected.encode()):
                self.reply(
                    401, {"error": "Unlock this session with the local launch token"}
                )
                return False
        return True

    def do_GET(self):
        api = self.path.startswith("/api/")
        if not self.guard(api):
            return
        try:
            static = {
                "/": ("index.html", "text/html; charset=utf-8"),
                "/style.css": ("style.css", "text/css; charset=utf-8"),
                "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            }
            if self.path in static:
                filename, kind = static[self.path]
                return self.reply(
                    200,
                    (Path(__file__).parent / "static" / filename).read_bytes(),
                    kind,
                )
            if self.path == "/api/health":
                return self.reply(
                    200,
                    {
                        "version": __version__,
                        "local_only": True,
                        "local_only_scope": "server_binding",
                        "ai_processing_policies": ["local_only", "cloud_allowed"],
                        "third_party_adapters": "not_integrated",
                        "review_features": ["coverage_aware_retest", "evidence_bundle"],
                        "recovered_interruptions": self.server.state.recovered_interruptions,
                        "active_run": self.server.state.active,
                    },
                )
            if self.path == "/api/models":
                try:
                    return self.reply(200, Ollama("").diagnostics())
                except OllamaError as exc:
                    return self.reply(
                        200,
                        {
                            "available": False,
                            "models": [],
                            "state": exc.code,
                            "note": str(exc) + " " + exc.next_step,
                            **exc.public(),
                        },
                    )
            if self.path == "/api/runs":
                return self.reply(200, {"runs": self.server.state.store.recent()})
            compare_match = re.fullmatch(
                r"/api/runs/([a-f0-9]{32})/compare/([a-f0-9]{32})", self.path
            )
            if compare_match:
                previous = self.server.state.get(compare_match[1])
                current = self.server.state.get(compare_match[2])
                if previous is None or current is None:
                    return self.reply(404, {"error": "Run not found"})
                if (
                    not verify_integrity(previous)
                    or not verify_integrity(current)
                    or not durable_for_review(previous)
                    or not durable_for_review(current)
                ):
                    return self.reply(
                        409,
                        {
                            "error": "Only durable, finalized, intact reports can be compared"
                        },
                    )
                return self.reply(200, compare_reports(previous, current))
            bundle_match = re.fullmatch(
                r"/api/runs/([a-f0-9]{32})/export\.bundle\.zip", self.path
            )
            if bundle_match:
                report = self.server.state.get(bundle_match[1])
                if report is None:
                    return self.reply(404, {"error": "Run not found"})
                if (
                    report["status"] == "running"
                    or not verify_integrity(report)
                    or not durable_for_review(report)
                ):
                    return self.reply(
                        409,
                        {
                            "error": "Only durable, finalized, intact reports can be exported"
                        },
                    )
                raw = build_bundle(report, markdown(report))
                return self.reply(
                    200,
                    raw,
                    "application/zip",
                    "secscan_ai-" + bundle_match[1] + "-evidence.zip",
                )
            match = re.fullmatch(
                r"/api/runs/([a-f0-9]{32})(?:/export\.(json|md))?", self.path
            )
            if match:
                report = self.server.state.get(match[1])
                if report is None:
                    return self.reply(404, {"error": "Run not found"})
                if match[2]:
                    if (
                        report["status"] == "running"
                        or not verify_integrity(report)
                        or not durable_for_review(report)
                    ):
                        return self.reply(
                            409,
                            {
                                "error": "Only durable, finalized, intact reports can be exported"
                            },
                        )
                    extension = match[2]
                    raw = (
                        markdown(report).encode()
                        if extension == "md"
                        else json.dumps(report, indent=2).encode()
                    )
                    kind = (
                        "text/markdown; charset=utf-8"
                        if extension == "md"
                        else "application/json"
                    )
                    return self.reply(
                        200, raw, kind, "secscan_ai-" + match[1] + "." + extension
                    )
                return self.reply(200, report)
            return self.reply(404, {"error": "Not found"})
        except ValueError as exc:
            self.reply(409, {"error": str(exc)})
        except Exception:
            self.reply(
                500,
                {"error": "Local service error. No assessment result was fabricated."},
            )

    def do_POST(self):
        if not self.guard(True):
            return
        try:
            if self.headers.get("Transfer-Encoding") or self.headers.get(
                "Content-Encoding"
            ):
                raise ValueError("Encoded and chunked request bodies are not supported")
            length = int(self.headers.get("Content-Length", "0"))
            if (
                not 0 < length <= 16384
                or self.headers.get("Content-Type", "").split(";")[0]
                != "application/json"
            ):
                raise ValueError("Send a JSON object no larger than 16 KiB")
            data = json.loads(self.rfile.read(length))
            if self.path == "/api/models/discover":
                if (
                    not isinstance(data, dict)
                    or set(data) - {"allow_cloud"}
                    or type(data.get("allow_cloud", False)) is not bool
                ):
                    raise ValueError("Send only optional boolean allow_cloud")
                return self.reply(
                    200,
                    Ollama(
                        "", allow_cloud=data.get("allow_cloud", False)
                    ).diagnostics(),
                )
            if self.path in ("/api/models/check", "/api/models/self-test"):
                if (
                    not isinstance(data, dict)
                    or set(data) - {"model", "require_tools", "allow_cloud"}
                    or not isinstance(data.get("model"), str)
                    or not data["model"]
                    or not isinstance(data.get("require_tools", False), bool)
                    or type(data.get("allow_cloud", False)) is not bool
                ):
                    raise ValueError(
                        "Send an exact model name and optional boolean require_tools"
                    )
                client = Ollama(
                    data["model"], allow_cloud=data.get("allow_cloud", False)
                )
                result = (
                    client.self_test(require_tools=data.get("require_tools", False))
                    if self.path == "/api/models/self-test"
                    else client.inspect_model(
                        require_tools=data.get("require_tools", False)
                    )
                )
                return self.reply(200, result)
            if self.path == "/api/runs":
                run_id = self.server.state.start(data)
                return self.reply(202, {"id": run_id})
            match = re.fullmatch(r"/api/runs/([a-f0-9]{32})/cancel", self.path)
            if match:
                with self.server.state.lock:
                    if self.server.state.active != match[1]:
                        return self.reply(409, {"error": "This run is not active"})
                    self.server.state.cancel.set()
                return self.reply(
                    202,
                    {
                        "status": "cancellation_requested",
                        "note": "In-flight bounded I/O is not interrupted instantly.",
                    },
                )
            self.reply(404, {"error": "Not found"})
        except OllamaError as exc:
            self.reply(422, exc.public())
        except Busy as exc:
            self.reply(409, {"error": str(exc)})
        except (ValueError, TypeError, UnicodeDecodeError):
            self.reply(
                400,
                {
                    "error": "Invalid request. Check the URL, authorization, mode approval and model selection."
                },
            )
        except Exception:
            self.reply(500, {"error": "Unable to start assessment"})


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
    server = LocalServer(("127.0.0.1", args.port), state, token)
    print("SecScan AI Evidence Workbench " + __version__)
    print("Open locally: http://127.0.0.1:" + str(args.port) + "/#token=" + token)
    print(
        "Keep this launch URL private. Loopback only; do not expose through a tunnel."
    )
    print(
        "Native checks are ready. External scanners are NOT bundled in this milestone."
    )
    print(
        "The current Ollama adapter supports local or explicitly approved cloud-backed models; product evidence/action contracts are provider-neutral."
    )
    if state.recovered_interruptions:
        print(
            f"Recovered {state.recovered_interruptions} interrupted run(s) from durable checkpoints; none were marked completed."
        )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        state.cancel.set()
    finally:
        server.server_close()
        if state.worker:
            state.worker.join(timeout=10)


if __name__ == "__main__":
    main()
