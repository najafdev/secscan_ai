"""Cross-platform checkout smoke test for the isolated workbench.

This intentionally uses only the Python standard library. It starts the real loopback
server in-process, exercises the authenticated HTTP surface, runs the owned synthetic
verification fixture, confirms durable persistence/export, and shuts everything down.
It does not contact an external target or model service.
"""

from __future__ import annotations

import http.client
import json
import tempfile
import threading
import time
from pathlib import Path

from workbench.engine import verify_integrity
from workbench.server import State
from workbench.workspace_server import WorkbenchServer

TOKEN = "fresh-install-smoke-token"
INPUT = {
    "target": "lab",
    "mode": "verify",
    "authorized": True,
    "authorization": "Cross-platform fresh-install owned fixture",
    "approve_verification": True,
    "use_ai": False,
    "model": "",
    "allow_cloud": False,
}


def call(server: WorkbenchServer, path: str, body=None):
    headers = {"Authorization": "Bearer " + TOKEN}
    payload = None
    method = "GET"
    if body is not None:
        method = "POST"
        headers["Content-Type"] = "application/json"
        payload = json.dumps(body)
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        connection.request(method, path, body=payload, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        return response.status, dict(response.getheaders()), raw
    finally:
        connection.close()


def main():
    with tempfile.TemporaryDirectory(prefix="secscan_ai-fresh-install-") as directory:
        state = State(Path(directory) / "state")
        server = WorkbenchServer(("127.0.0.1", 0), state, TOKEN)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            status, headers, page = call(server, "/")
            assert status == 200, status
            assert b"Evidence Workbench" in page
            assert TOKEN.encode() not in page
            assert headers.get("Cache-Control") == "no-store"

            status, _, raw = call(server, "/api/health")
            assert status == 200, status
            health = json.loads(raw)
            assert health["third_party_adapters"] == "not_integrated"
            assert health["local_only_scope"] == "server_binding"

            status, _, raw = call(server, "/api/adapters")
            assert status == 200, status
            adapters = json.loads(raw)["adapters"]
            ids = {item["adapter"]["id"] for item in adapters}
            assert {"native-project-metadata", "native-web-headers"}.issubset(ids)

            status, _, raw = call(server, "/api/runs", INPUT)
            assert status == 202, (status, raw)
            run_id = json.loads(raw)["id"]

            deadline = time.monotonic() + 15
            report = None
            while time.monotonic() < deadline:
                status, _, raw = call(server, "/api/runs/" + run_id)
                assert status == 200, status
                report = json.loads(raw)
                if report["status"] != "running":
                    break
                time.sleep(0.05)
            assert (
                report is not None and report["status"] != "running"
            ), "synthetic run did not finish"
            assert report["verdict"] == "verified_in_synthetic_lab_only"
            assert verify_integrity(report)
            assert report["durability"]["status"] == "durable"
            assert any(
                item.get("verification") == "verified_in_lab"
                for item in report["findings"]
            )

            status, export_headers, exported = call(
                server, "/api/runs/" + run_id + "/export.json"
            )
            assert status == 200, status
            assert "attachment" in export_headers.get("Content-Disposition", "")
            assert verify_integrity(json.loads(exported))

            status, _, raw = call(server, "/api/runs")
            assert status == 200
            history = json.loads(raw)["runs"]
            assert history and history[0]["id"] == run_id

            print(
                json.dumps(
                    {
                        "schema": "secscan_ai.fresh-install-smoke/v1",
                        "platform_runtime": __import__("platform").platform(),
                        "python": __import__("sys").version.split()[0],
                        "loopback_server": True,
                        "synthetic_assessment_completed": True,
                        "durable_export_verified": True,
                        "third_party_scanners_bundled": False,
                        "external_target_contacted": False,
                        "live_model_used": False,
                    },
                    indent=2,
                )
            )
        finally:
            state.cancel.set()
            if state.worker:
                state.worker.join(timeout=5)
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    main()
