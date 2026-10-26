import json
import os
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from workbench.semgrep_runner import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    RULES_PATH,
    SEMGREP_IMAGE,
    SEMGREP_IMAGE_DIGEST,
    SEMGREP_VERSION,
    SemgrepContainerAdapter,
    SemgrepPolicy,
    semgrep_tool_public_metadata,
)

ASSET = "asset:semgrep-fixture"


def semgrep_output(*, vulnerable: bool = True):
    results = []
    if vulnerable:
        results.append(
            {
                "check_id": "secscan_ai.python.dynamic-eval",
                "path": "app.py",
                "start": {"line": 2},
                "end": {"line": 2},
                "extra": {
                    "message": "Dynamic eval executes a runtime expression and requires security review.",
                    "severity": "WARNING",
                    "fingerprint": "fixture-fingerprint",
                    "lines": "return eval(user_input)",
                    "metavars": {"$X": {"abstract_content": "user_input"}},
                },
            }
        )
    return json.dumps(
        {"results": results, "paths": {"scanned": ["app.py"]}, "errors": []}
    ).encode()


class FakeSemgrepAdapter(SemgrepContainerAdapter):
    def __init__(self, *args, output=None, return_code=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.output = semgrep_output() if output is None else output
        self.return_code = return_code
        self.commands = []

    @staticmethod
    def _docker_path():
        return "/reviewed/docker"

    @staticmethod
    def _ensure_image_present(docker):
        return None

    def _execute_docker(
        self, docker, command, *, container_name, deadline, cancel=None
    ):
        self.commands.append(list(command))
        return self.return_code, self.output


class SemgrepRunnerTests(unittest.TestCase):
    def fixture(
        self, directory, text="def parse(user_input):\n    return eval(user_input)\n"
    ):
        root = Path(directory)
        (root / "app.py").write_text(text, encoding="utf-8")
        return root

    def test_tool_pin_is_exact_and_public_metadata_is_non_secret(self):
        metadata = semgrep_tool_public_metadata()
        self.assertEqual(metadata["id"], "semgrep-ce")
        self.assertEqual(metadata["version"], "1.177.0")
        self.assertEqual(metadata["license"]["spdx"], "LGPL-2.1-or-later")
        self.assertEqual(metadata["container"]["manifest_digest"], SEMGREP_IMAGE_DIGEST)
        self.assertFalse(metadata["container"]["automatic_pull"])
        self.assertFalse(metadata["rules"]["external_registry"])
        self.assertTrue(SEMGREP_IMAGE.endswith(SEMGREP_IMAGE_DIGEST))
        self.assertEqual(SEMGREP_VERSION, "1.177.0")
        self.assertTrue(RULES_PATH.is_file())

    def test_declaration_is_fixed_container_read_only_and_offline(self):
        declaration = SemgrepContainerAdapter().execution_declaration()
        self.assertEqual(
            declaration["adapter"], {"id": ADAPTER_ID, "version": ADAPTER_VERSION}
        )
        self.assertEqual(declaration["launcher"], "fixed_container")
        self.assertEqual(declaration["effect_level"], "read_only")
        self.assertEqual(declaration["filesystem"], "read_only_content")
        self.assertEqual(declaration["network"], "none")
        self.assertTrue(declaration["subprocess"])
        self.assertFalse(declaration["writes"])
        self.assertFalse(declaration["follows_symlinks"])
        self.assertEqual(declaration["limits"]["max_requests"], 0)

    def test_command_has_no_pull_no_network_and_read_only_mounts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            adapter = SemgrepContainerAdapter()
            command = adapter._build_command(
                "/usr/bin/docker", root.resolve(), "secscan_ai-semgrep-test"
            )
        joined = " ".join(command)
        self.assertIn("--pull never", joined)
        self.assertIn("--network none", joined)
        self.assertIn("--read-only", command)
        self.assertIn("--cap-drop ALL", joined)
        self.assertIn("--security-opt no-new-privileges", joined)
        self.assertIn("--user", command)
        self.assertIn(SEMGREP_IMAGE, command)
        self.assertNotIn("--privileged", command)
        mounts = [
            command[index + 1]
            for index, value in enumerate(command[:-1])
            if value == "-v"
        ]
        self.assertTrue(any(value.endswith(":/src:ro") for value in mounts))
        self.assertTrue(any(value.endswith(":/workbench.yml:ro") for value in mounts))
        self.assertIn("SEMGREP_SEND_METRICS=off", command)
        self.assertIn("SEMGREP_ENABLE_VERSION_CHECK=0", command)
        self.assertIn("SEMGREP_VERSION_CACHE_PATH=/tmp/semgrep_version", command)
        self.assertIn("SEMGREP_LOG_FILE=/tmp/semgrep.log", command)
        self.assertIn("XDG_CACHE_HOME=/tmp/.cache", command)
        self.assertIn("--disable-version-check", command)
        self.assertEqual(command[-1], "/src")

    def test_runner_rebinds_parser_to_execution_identity_and_discards_source(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = FakeSemgrepAdapter()
            result = adapter.run(self.fixture(directory), asset_key=ASSET)
        self.assertEqual(
            result["adapter"], {"id": ADAPTER_ID, "version": ADAPTER_VERSION}
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["coverage"]["objects_tested"], 1)
        self.assertEqual(result["coverage"]["objects_total"], 1)
        finding = result["findings"][0]
        self.assertEqual(finding["verification"], "candidate")
        self.assertEqual(finding["source"], f"adapter/{ADAPTER_ID}/{ADAPTER_VERSION}")
        serialized = json.dumps(result)
        self.assertNotIn("eval(user_input)", serialized)
        self.assertNotIn("abstract_content", serialized)
        self.assertEqual(len(adapter.commands), 1)

    def test_runner_does_not_hide_scanner_failure_or_diagnostic_text(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = FakeSemgrepAdapter(
                return_code=7, output=b"customer-secret-diagnostic"
            )
            result = adapter.run(self.fixture(directory), asset_key=ASSET)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["findings"], [])
        self.assertIn("code 7", result["error"])
        self.assertNotIn("customer-secret-diagnostic", json.dumps(result))

    def test_preflight_enforces_file_budget_before_scanner_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "one.py").write_text("pass\n", encoding="utf-8")
            (root / "two.py").write_text("pass\n", encoding="utf-8")
            adapter = FakeSemgrepAdapter(policy=SemgrepPolicy(max_files=1))
            with self.assertRaisesRegex(ValueError, "file-count bound"):
                adapter.run(root, asset_key=ASSET)
            self.assertEqual(adapter.commands, [])

    def test_cancel_before_launch_prevents_scanner_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            cancel = threading.Event()
            cancel.set()
            adapter = FakeSemgrepAdapter()
            with self.assertRaises(InterruptedError):
                adapter.run(root, asset_key=ASSET, cancel=cancel)
            self.assertEqual(adapter.commands, [])

    def test_plan_metadata_omits_full_project_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            summary = SemgrepContainerAdapter().plan_metadata(root, asset_key=ASSET)
        self.assertEqual(summary["project_label"], Path(directory).name)
        self.assertFalse(summary["full_path_included"])
        self.assertNotIn(str(Path(directory).resolve()), json.dumps(summary))
        self.assertEqual(summary["container_network"], "none")
        self.assertEqual(summary["image_digest"], SEMGREP_IMAGE_DIGEST)

    def test_root_symlink_is_rejected(self):
        if os.name == "nt":
            self.skipTest("symlink creation is privilege-dependent on Windows")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            target = base / "target"
            target.mkdir()
            link = base / "link"
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "must not be a symlink"):
                SemgrepContainerAdapter().plan_metadata(link, asset_key=ASSET)


@unittest.skipUnless(
    os.environ.get("SECSCAN_AI_RUN_REAL_SEMGREP") == "1",
    "real pinned Semgrep container integration is opt-in",
)
class SemgrepContainerIntegrationTests(unittest.TestCase):
    @staticmethod
    def _owned_fixture_diagnostic(adapter, directory):
        """Return bounded stderr only for the synthetic CI fixture if runner startup fails."""
        command = adapter._build_command(
            "docker", Path(directory).resolve(), "secscan_ai-semgrep-diagnostic"
        )
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
        text = completed.stderr.decode("utf-8", "replace")[-4000:]
        return f"exit={completed.returncode}; stderr={text}"

    def test_owned_vulnerable_and_fixed_projects(self):
        adapter = SemgrepContainerAdapter(
            SemgrepPolicy(max_files=10, timeout_seconds=90)
        )
        with tempfile.TemporaryDirectory() as vulnerable_dir, tempfile.TemporaryDirectory() as fixed_dir:
            Path(vulnerable_dir, "app.py").write_text(
                "def parse(user_input):\n    return eval(user_input)\n",
                encoding="utf-8",
            )
            Path(fixed_dir, "app.py").write_text(
                "import json\ndef parse(user_input):\n    return json.loads(user_input)\n",
                encoding="utf-8",
            )
            vulnerable = adapter.run(vulnerable_dir, asset_key="asset:owned-vulnerable")
            if vulnerable["status"] != "completed":
                self.fail(
                    "owned vulnerable fixture failed: "
                    + self._owned_fixture_diagnostic(adapter, vulnerable_dir)
                )
            fixed = adapter.run(fixed_dir, asset_key="asset:owned-fixed")
            if fixed["status"] != "completed":
                self.fail(
                    "owned fixed fixture failed: "
                    + self._owned_fixture_diagnostic(adapter, fixed_dir)
                )

        self.assertTrue(
            any(
                item["rule"] == "secscan_ai.python.dynamic-eval"
                for item in vulnerable["findings"]
            )
        )
        self.assertTrue(
            all(item["verification"] == "candidate" for item in vulnerable["findings"])
        )
        self.assertEqual(fixed["findings"], [])
        self.assertNotIn("eval(user_input)", json.dumps(vulnerable))
        self.assertEqual(vulnerable["adapter"]["id"], ADAPTER_ID)


if __name__ == "__main__":
    unittest.main()
