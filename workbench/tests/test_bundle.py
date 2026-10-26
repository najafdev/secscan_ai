import hashlib
import io
import json
import unittest
import zipfile
from workbench.bundle import build_bundle


class BundleTests(unittest.TestCase):
    def report(self):
        return {
            "id": "a" * 32,
            "status": "completed",
            "target": "lab://fixture",
            "findings": [],
            "checks": [],
            "integrity": {
                "algorithm": "sha256",
                "report_sha256": "fixture",
                "signed": False,
            },
        }

    def test_bundle_contains_manifest_and_exports(self):
        raw = build_bundle(self.report(), "# report")
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            self.assertEqual(
                set(archive.namelist()), {"manifest.json", "report.json", "report.md"}
            )
            manifest = json.loads(archive.read("manifest.json"))
            self.assertFalse(manifest["signed"])
            self.assertEqual(manifest["run_id"], "a" * 32)
            self.assertEqual(
                manifest["files"]["report.md"]["sha256"],
                hashlib.sha256(b"# report").hexdigest(),
            )

    def test_optional_retest_diff(self):
        raw = build_bundle(
            self.report(), "# report", {"schema": "secscan_ai.retest-diff/v1"}
        )
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            self.assertIn("retest-diff.json", archive.namelist())

    def test_deterministic_archive_file_order(self):
        raw = build_bundle(self.report(), "# report")
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            self.assertEqual(archive.namelist(), sorted(archive.namelist()))

    def test_running_report_rejected(self):
        report = self.report()
        report["status"] = "running"
        with self.assertRaises(ValueError):
            build_bundle(report, "# report")


if __name__ == "__main__":
    unittest.main()
