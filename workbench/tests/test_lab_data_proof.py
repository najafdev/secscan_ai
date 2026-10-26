import json
import unittest
from unittest import mock

from workbench.engine import Assessment, Scope, verify_integrity
from workbench.lab import CanaryLab


def scope(fixed=False):
    return Scope.parse(
        {
            "target": "lab",
            "mode": "verify",
            "authorized": True,
            "authorization": "Synthetic data proof",
            "approve_verification": True,
        }
    )


class SyntheticDataProofTests(unittest.TestCase):
    def test_canary_lab_loopback_bind_does_not_require_reverse_dns(self):
        with mock.patch(
            "socket.getfqdn", side_effect=AssertionError("reverse DNS should not run")
        ):
            with CanaryLab() as lab:
                status, _, body = lab.request("/record")
        self.assertEqual(status, 200)
        self.assertEqual(body, lab.marker)

    def test_verified_lab_proof_contains_safe_data_summary(self):
        report = Assessment(scope()).run()
        finding = next(
            item
            for item in report["findings"]
            if item["verification"] == "verified_in_lab"
        )
        evidence = finding["evidence"]
        summary = evidence["data_summary"]
        rendered = json.dumps(evidence)
        self.assertEqual(summary["row_count"], 2)
        self.assertFalse(summary["ordinary_values_exported"])
        self.assertEqual(
            evidence["demonstrated_impact"],
            "unauthenticated read of designated synthetic records",
        )
        self.assertFalse(evidence["customer_data_sampled"])
        self.assertTrue(
            summary["synthetic_canaries"][0]["value"].startswith("SECSCAN_AI-SYNTHETIC-")
        )
        self.assertNotIn("synthetic-alpha", rendered)
        self.assertNotIn("synthetic-beta", rendered)
        self.assertTrue(verify_integrity(report))

    def test_fixed_fixture_does_not_export_data_summary(self):
        report = Assessment(scope()).run(fixed_lab=True)
        check = next(
            item for item in report["checks"] if item["tool"] == "verify_lab_canary"
        )
        self.assertEqual(check["result"], "not_demonstrated")
        self.assertIsNone(check["evidence"]["data_summary"])
        self.assertFalse(check["evidence"]["customer_data_sampled"])


if __name__ == "__main__":
    unittest.main()
