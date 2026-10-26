import unittest

from workbench.execution_receipts import normalize_execution_receipt

DECL = {
    "schema": "secscan_ai.execution-declaration/v1",
    "adapter": {"id": "fake-safe", "version": "1"},
    "launcher": "native_python",
    "effect_level": "read_only",
    "filesystem": "read_only_metadata",
    "network": "none",
    "subprocess": False,
    "writes": False,
    "follows_symlinks": False,
    "limits": {"max_objects": 10, "max_requests": 0, "timeout_seconds": 5},
    "coverage_unit": "files",
}


def payload(summary):
    return {
        "schema": "secscan_ai.execution-receipt/v1",
        "declaration": DECL,
        "request_summary": summary,
        "usage": {"objects_tested": 1, "network_requests": 0, "elapsed_ms": 1},
        "result": {
            "adapter": {"id": "fake-safe", "version": "1"},
            "findings": [],
            "verification_authority": "workbench_only",
        },
    }


class NestedReceiptSafetyTests(unittest.TestCase):
    def test_nested_token_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "forbidden"):
            normalize_execution_receipt(payload({"scope": {"token": "x"}}))

    def test_nested_command_in_list_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "forbidden"):
            normalize_execution_receipt(payload({"steps": [{"command": "whoami"}]}))

    def test_benign_nested_summary_is_allowed(self):
        result = normalize_execution_receipt(
            payload({"scope": {"path": "src", "method": "metadata"}})
        )
        self.assertEqual(result["request_summary"]["scope"]["path"], "src")


if __name__ == "__main__":
    unittest.main()
