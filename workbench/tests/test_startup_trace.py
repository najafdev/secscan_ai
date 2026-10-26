"""Hosted macOS startup stall diagnostic without weakening the main readiness test."""

import os
from pathlib import Path
import queue
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
ENTRY = ROOT / "workbench" / "start.py"


def unused_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@unittest.skipUnless(sys.platform == "darwin", "macOS-only hosted startup diagnostic")
class MacStartupTraceTests(unittest.TestCase):
    def test_stalled_launcher_reports_python_stack(self):
        with tempfile.TemporaryDirectory(prefix="workbench-mac-trace-") as directory:
            env = os.environ.copy()
            env["SECSCAN_AI_STARTUP_TRACE"] = "1"
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(ENTRY),
                    "--data-dir",
                    directory,
                    "--port",
                    str(unused_port()),
                ],
                cwd=directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
            lines = queue.Queue()
            reader = threading.Thread(
                target=lambda: [lines.put(line) for line in process.stdout], daemon=True
            )
            reader.start()
            ready = False
            try:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    try:
                        line = lines.get(timeout=0.2)
                    except queue.Empty:
                        if process.poll() is not None:
                            break
                        continue
                    if line.startswith("Open locally: "):
                        ready = True
                        break
                if not ready:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                    diagnostics = process.stderr.read()
                    self.fail(
                        "macOS launcher did not become ready; captured child stack:\n"
                        + diagnostics[-12000:]
                    )
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=10)
                reader.join(timeout=2)
                process.stdout.close()
                process.stderr.close()


if __name__ == "__main__":
    unittest.main()
