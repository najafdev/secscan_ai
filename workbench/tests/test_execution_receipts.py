import copy
import tempfile
import threading
import time
import unittest
from pathlib import Path

from workbench.execution_receipts import normalize_execution_receipt
from workbench.registry import ExecutionRegistry, RegistryPolicy


class ExecutionReceiptTests(unittest.TestCase):
    def test_project_plan_is_io_free_and_does_not_disclose_full_root(self):
        missing = Path(tempfile.gettempdir()) / "secscan_ai-plan-missing-root"
        plan = ExecutionRegistry().plan(
            "native-project-metadata",
            {
                "root": missing,
                "asset_key": "fixture",
                "max_files": 25,
                "timeout_seconds": 5,
            },
        )
        self.assertEqual(plan["declaration"]["limits"]["max_objects"], 25)
        self.assertEqual(plan["declaration"]["limits"]["timeout_seconds"], 5)
        self.assertFalse(plan["request_summary"]["full_path_included"])
        self.assertNotIn(str(missing), repr(plan["request_summary"]))

    def test_project_receipt_accounts_objects_and_never_reads_secret_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text("API_KEY=DO_NOT_EXPORT")
            (root / "app.py").write_text("print('hello')")
            receipt = ExecutionRegistry().execute_with_receipt(
                "native-project-metadata",
                {"root": directory, "asset_key": "fixture", "max_files": 10},
            )
        self.assertEqual(receipt["schema"], "secscan_ai.execution-receipt/v1")
        self.assertEqual(receipt["usage"]["objects_tested"], 2)
        self.assertEqual(receipt["usage"]["network_requests"], 0)
        self.assertLessEqual(
            receipt["usage"]["objects_tested"],
            receipt["declaration"]["limits"]["max_objects"],
        )
        self.assertNotIn("DO_NOT_EXPORT", repr(receipt))
        self.assertTrue(
            all(
                item["verification"] == "candidate"
                for item in receipt["result"]["findings"]
            )
        )

    def test_web_receipt_accounts_exact_single_request_and_body_free_scope(self):
        calls = []
        receipt = ExecutionRegistry().execute_with_receipt(
            "native-web-headers",
            {"target": "https://example.com", "asset_key": "fixture"},
            web_reader=lambda target: calls.append(target)
            or {
                "status": 200,
                "headers": {"content-type": "text/html"},
                "method": "HEAD",
                "redirect_followed": False,
            },
        )
        self.assertEqual(calls, ["https://example.com"])
        self.assertEqual(receipt["usage"]["network_requests"], 1)
        self.assertEqual(receipt["declaration"]["limits"]["max_requests"], 1)
        self.assertEqual(receipt["request_summary"]["method"], "HEAD")
        self.assertFalse(receipt["request_summary"]["redirects"])
        self.assertFalse(receipt["request_summary"]["response_body"])

    def test_plan_respects_operator_authority_before_io(self):
        with self.assertRaises(PermissionError):
            ExecutionRegistry(RegistryPolicy(allow_network=False)).plan(
                "native-web-headers",
                {"target": "https://example.com", "asset_key": "fixture"},
            )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(PermissionError):
                ExecutionRegistry(RegistryPolicy(allow_filesystem=False)).plan(
                    "native-project-metadata",
                    {"root": directory, "asset_key": "fixture"},
                )

    def test_receipt_rejects_self_verified_finding(self):
        receipt = ExecutionRegistry().execute_with_receipt(
            "native-web-headers",
            {"target": "https://example.com", "asset_key": "fixture"},
            web_reader=lambda _: {
                "status": 200,
                "headers": {"content-type": "text/html"},
                "method": "HEAD",
                "redirect_followed": False,
            },
        )
        tampered = copy.deepcopy(receipt)
        tampered["result"]["findings"][0]["verification"] = "verified"
        with self.assertRaises(ValueError):
            normalize_execution_receipt(tampered)

    def test_receipt_rejects_usage_over_declared_budgets(self):
        receipt = ExecutionRegistry().execute_with_receipt(
            "native-web-headers",
            {"target": "https://example.com", "asset_key": "fixture"},
            web_reader=lambda _: {
                "status": 204,
                "headers": {"content-type": "text/plain"},
                "method": "HEAD",
                "redirect_followed": False,
            },
        )
        for field, value in (("network_requests", 2), ("objects_tested", 2)):
            tampered = copy.deepcopy(receipt)
            tampered["usage"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                normalize_execution_receipt(tampered)

    def test_receipt_rejects_sensitive_or_execution_fields_in_summary(self):
        receipt = ExecutionRegistry().execute_with_receipt(
            "native-web-headers",
            {"target": "https://example.com", "asset_key": "fixture"},
            web_reader=lambda _: {
                "status": 204,
                "headers": {"content-type": "text/plain"},
                "method": "HEAD",
                "redirect_followed": False,
            },
        )
        for field in (
            "password",
            "token",
            "cookie",
            "authorization",
            "command",
            "argv",
        ):
            tampered = copy.deepcopy(receipt)
            tampered["request_summary"][field] = "do-not-store"
            with self.subTest(field=field), self.assertRaises(ValueError):
                normalize_execution_receipt(tampered)

    def test_pre_cancelled_receipt_stops_before_reader(self):
        cancel = threading.Event()
        cancel.set()
        calls = []
        with self.assertRaises(InterruptedError):
            ExecutionRegistry().execute_with_receipt(
                "native-web-headers",
                {"target": "https://example.com", "asset_key": "fixture"},
                cancel=cancel,
                web_reader=lambda target: calls.append(target),
            )
        self.assertEqual(calls, [])

    def test_elapsed_time_is_observational_and_nonnegative(self):
        receipt = ExecutionRegistry().execute_with_receipt(
            "native-web-headers",
            {"target": "https://example.com", "asset_key": "fixture"},
            web_reader=lambda _: (
                time.sleep(0.002)
                or {
                    "status": 204,
                    "headers": {"content-type": "text/plain"},
                    "method": "HEAD",
                    "redirect_followed": False,
                }
            ),
        )
        self.assertGreaterEqual(receipt["usage"]["elapsed_ms"], 0)


if __name__ == "__main__":
    unittest.main()
