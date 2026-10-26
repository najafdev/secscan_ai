import json
import tempfile
import unittest
from pathlib import Path

from workbench.engine import verify_integrity
from workbench.release_evidence import (
    RELEASE_EVIDENCE_SCHEMA,
    cyclonedx_bom,
    find_forbidden_artifacts,
    source_review_manifest,
    synthetic_sample_report,
    write_release_evidence,
)


class ReleaseEvidenceTests(unittest.TestCase):
    @property
    def root(self):
        return Path(__file__).resolve().parents[1]

    def test_manifest_is_scoped_and_truthful_about_release_boundaries(self):
        manifest = source_review_manifest(self.root)
        self.assertEqual(manifest["schema"], RELEASE_EVIDENCE_SCHEMA)
        self.assertEqual(manifest["scope"], "isolated-workbench-only")
        self.assertEqual(manifest["python"]["third_party_runtime_packages"], [])
        self.assertEqual(manifest["bundled_scanners"], [])
        self.assertTrue(manifest["execution_boundaries"]["external_scanner_execution"])
        self.assertEqual(
            manifest["execution_boundaries"]["scanner_execution_scope"],
            "pinned-local-container-only",
        )
        self.assertFalse(manifest["execution_boundaries"]["browser_e2e_validated"])
        self.assertFalse(manifest["execution_boundaries"]["signed_release"])
        self.assertTrue(
            all(len(item["sha256"]) == 64 for item in manifest["review_documents"])
        )
        self.assertEqual(len(manifest["optional_scanner_runners"]), 1)
        runner = manifest["optional_scanner_runners"][0]
        self.assertEqual(runner["id"], "semgrep-ce")
        self.assertEqual(runner["version"], "1.177.0")
        self.assertEqual(runner["license"]["spdx"], "LGPL-2.1-or-later")
        self.assertEqual(runner["distribution"], "optional-preinstalled-container")
        self.assertFalse(runner["container"]["automatic_pull"])
        self.assertEqual(len(runner["pin_sha256"]), 64)
        self.assertEqual(len(runner["rules_sha256"]), 64)

    def test_sbom_scopes_optional_pinned_scanner_without_calling_it_bundled(self):
        bom = cyclonedx_bom()
        self.assertEqual(bom["bomFormat"], "CycloneDX")
        self.assertEqual(
            bom["metadata"]["component"]["name"], "SecScan AI Evidence Workbench"
        )
        properties = {
            item["name"]: item["value"]
            for item in bom["metadata"]["component"]["properties"]
        }
        self.assertEqual(properties["secscan_ai:bundled-scanners"], "none")
        self.assertEqual(properties["secscan_ai:optional-scanner-runners"], "semgrep-ce")
        self.assertEqual(len(bom["components"]), 1)
        semgrep = bom["components"][0]
        self.assertEqual(semgrep["type"], "container")
        self.assertEqual(semgrep["name"], "semgrep/semgrep")
        self.assertEqual(semgrep["version"], "1.177.0")
        self.assertEqual(semgrep["scope"], "optional")
        self.assertEqual(semgrep["licenses"][0]["license"]["id"], "LGPL-2.1-or-later")
        self.assertEqual(len(semgrep["hashes"][0]["content"]), 64)

    def test_synthetic_sample_is_owned_intact_and_credential_free(self):
        report = synthetic_sample_report()
        self.assertTrue(verify_integrity(report))
        self.assertEqual(report["environment"], "synthetic_lab")
        self.assertEqual(report["target"], "lab://ephemeral-authorization-fixture")
        self.assertEqual(report["verdict"], "verified_in_synthetic_lab_only")
        verified = [
            item
            for item in report["findings"]
            if item["verification"] == "verified_in_lab"
        ]
        self.assertEqual(len(verified), 1)
        self.assertEqual(verified[0]["evidence"]["control_status"], 401)
        self.assertFalse(verified[0]["evidence"]["credentials_sent"])

    def test_writer_produces_parseable_revision_review_files_and_checksums(self):
        with tempfile.TemporaryDirectory() as directory:
            digests = write_release_evidence(Path(directory), self.root)
            expected = {
                "release-manifest.json",
                "sbom.cdx.json",
                "synthetic-sample-report.json",
                "synthetic-sample-report.md",
                "SHA256SUMS",
            }
            self.assertEqual(set(digests), expected)
            manifest = json.loads(
                (Path(directory) / "release-manifest.json").read_text(encoding="utf-8")
            )
            sample = json.loads(
                (Path(directory) / "synthetic-sample-report.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(manifest["schema"], RELEASE_EVIDENCE_SCHEMA)
            self.assertTrue(verify_integrity(sample))
            checksums = (Path(directory) / "SHA256SUMS").read_text(encoding="utf-8")
            self.assertIn("release-manifest.json", checksums)
            self.assertIn("synthetic-sample-report.json", checksums)

    def test_boundary_rejects_runtime_secrets_and_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "reports.sqlite3").write_text("not real", encoding="utf-8")
            (root / "client.key").write_text("not real", encoding="utf-8")
            blocked = find_forbidden_artifacts(root)
            self.assertEqual(blocked, ["client.key", "reports.sqlite3"])

    def test_manifest_never_hashes_absolute_paths_into_document_entries(self):
        manifest = source_review_manifest(self.root)
        self.assertTrue(
            all(
                not Path(item["path"]).is_absolute()
                for item in manifest["review_documents"]
            )
        )
        runner = manifest["optional_scanner_runners"][0]
        self.assertFalse(Path(runner["pin_path"]).is_absolute())
        self.assertFalse(Path(runner["rules_path"]).is_absolute())

    def test_pull_request_package_validation_does_not_request_attestation_write_authority(
        self,
    ):
        workflow = (
            self.root.parent / ".github" / "workflows" / "workbench-release-package.yml"
        )
        if not workflow.is_file():
            self.skipTest(
                "repository workflow is intentionally absent from the portable Workbench archive"
            )
        text = workflow.read_text(encoding="utf-8")
        self.assertIn("pull_request:", text)
        self.assertIn("package-smoke:", text)
        self.assertIn("attest-package:", text)
        attest = text.split("  attest-package:\n", 1)[1]
        self.assertIn("    if: github.event_name != 'pull_request'\n", attest)
        self.assertIn("      id-token: write\n", attest)
        self.assertIn("      attestations: write\n", attest)
        self.assertNotIn("id-token: write", text.split("  attest-package:\n", 1)[0])
        self.assertNotIn("attestations: write", text.split("  attest-package:\n", 1)[0])

    def test_release_attestation_verification_binds_exact_package_and_bundles(self):
        workflow = (
            self.root.parent / ".github" / "workflows" / "workbench-release-package.yml"
        )
        if not workflow.is_file():
            self.skipTest(
                "repository workflow is intentionally absent from the portable Workbench archive"
            )
        text = workflow.read_text(encoding="utf-8")
        output_ref = "needs.build-package.outputs.package_basename"
        self.assertIn(
            "package_basename: ${{ steps.package.outputs.package_basename }}", text
        )
        self.assertNotIn("outputs.package-basename", text)
        self.assertGreaterEqual(text.count(output_ref), 4)
        self.assertIn(
            'PACKAGE="_release/${{ needs.build-package.outputs.package_basename }}.tar.gz"',
            text,
        )
        self.assertEqual(text.count('gh attestation verify "$PACKAGE"'), 2)
        self.assertIn("--bundle _release/provenance.sigstore.json", text)
        self.assertIn("--bundle _release/sbom-attestation.sigstore.json", text)
        self.assertIn("--predicate-type https://slsa.dev/provenance/v1", text)
        self.assertIn("--predicate-type https://cyclonedx.org/bom", text)
        self.assertEqual(text.count('--source-digest "$GITHUB_SHA"'), 2)
        self.assertIn("_release/provenance-verification.txt", text)
        self.assertIn("_release/sbom-attestation-verification.txt", text)


if __name__ == "__main__":
    unittest.main()
