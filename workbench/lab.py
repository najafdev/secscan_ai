"""Ephemeral loopback-only authorization fixture. Never a remote exploitation target."""

import hashlib
import http.client
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from socketserver import TCPServer

from .evidence_safety import summarize_records


class _LoopbackHTTPServer(ThreadingHTTPServer):
    """HTTP server that keeps loopback startup independent of reverse DNS."""

    def server_bind(self):
        # HTTPServer.server_bind() calls socket.getfqdn(), which can block on
        # hosted/offline systems even though this fixture binds only 127.0.0.1.
        TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = str(host)
        self.server_port = int(port)


class CanaryLab:
    def __init__(self, fixed=False):
        self.fixed = fixed
        canary = "SECSCAN_AI-SYNTHETIC-" + secrets.token_hex(24)
        # Every value in this fixture is generated test data. The proof exporter still
        # exposes only schema/count/hash plus the explicitly marked canary.
        self.records = [
            {
                "id": 101,
                "account": "synthetic-alpha",
                "role": "viewer",
                "marker": canary,
            },
            {
                "id": 102,
                "account": "synthetic-beta",
                "role": "analyst",
                "marker": "synthetic-control-row",
            },
        ]
        self.marker = json.dumps(
            self.records, sort_keys=True, separators=(",", ":")
        ).encode()
        lab = self

        class Handler(BaseHTTPRequestHandler):
            def do_HEAD(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", "0")
                self.end_headers()

            def do_GET(self):
                if self.path == "/control" or (lab.fixed and self.path == "/record"):
                    status, body, content_type = (
                        401,
                        b"Authorization required",
                        "text/plain",
                    )
                elif self.path == "/record":
                    status, body, content_type = 200, lab.marker, "application/json"
                else:
                    status, body, content_type = 404, b"Not found", "text/plain"
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_):
                pass

        self.server = _LoopbackHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, path, method="GET"):
        if path not in ("/", "/control", "/record"):
            raise ValueError("Unknown synthetic lab action")
        conn = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=3
        )
        try:
            conn.request(method, path, headers={"Connection": "close"})
            response = conn.getresponse()
            return (
                response.status,
                dict((k.lower(), v) for k, v in response.getheaders()),
                response.read(4096),
            )
        finally:
            conn.close()

    def prove(self):
        control, _, _ = self.request("/control")
        status, _, body = self.request("/record")
        matched = status == 200 and secrets.compare_digest(body, self.marker)
        return {
            "control_status": control,
            "record_status": status,
            "synthetic_marker_matched": matched,
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "expected_sha256": hashlib.sha256(self.marker).hexdigest(),
            "credentials_sent": False,
            "paths": ["/control", "/record"],
            "environment": "ephemeral synthetic loopback lab",
            "data_summary": summarize_records(self.records) if matched else None,
            "demonstrated_impact": (
                "unauthenticated read of designated synthetic records"
                if matched
                else "not demonstrated"
            ),
            "customer_data_sampled": False,
        }
