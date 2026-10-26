"""Replay release shell contracts offline; fake gh is NOT signature verification."""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "workflows"
    / "workbench-release-package.yml"
)
REVISION = "a" * 40
BASENAME = "secscan_ai-evidence-workbench-" + REVISION
REPOSITORY = "HostX0/SecScan AI"
PROVENANCE = "https://slsa.dev/provenance/v1"
SBOM = "https://cyclonedx.org/bom"


def step_script(text, name):
    """Extract one literal shell block, failing loudly if its shape changes."""
    section = text.split("      - name: " + name + "\n", 1)[1]
    section = section.split("      - name: ", 1)[0]
    block = section.split("        run: |\n", 1)[1]
    lines = []
    for line in block.splitlines():
        if line and not line.startswith("          "):
            break
        lines.append(line[10:] if line else "")
    return "\n".join(lines) + "\n"


@unittest.skipUnless(
    WORKFLOW.is_file(), "portable package excludes repository workflows"
)
class ReleaseWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding="utf-8")
        self.attest = self.text.split("  attest-package:\n", 1)[1]

    def test_every_cross_job_output_reference_is_declared(self):
        build = self.text.split("  build-package:\n", 1)[1].split("    steps:\n", 1)[0]
        declared = re.findall(r"^      ([\w-]+):", build, re.MULTILINE)
        references = re.findall(r"needs\.build-package\.outputs\.([\w-]+)", self.text)
        self.assertTrue(references)
        for reference in references:
            self.assertIn(reference, declared)

    def test_package_key_is_consistent_and_preflight_receives_it(self):
        guard = self.attest.split(
            "      - name: Validate downloaded package identity", 1
        )[1]
        self.assertIn(
            "PACKAGE_BASENAME: ${{ needs.build-package.outputs.package_basename }}",
            guard,
        )
        self.assertNotIn("outputs.package-basename", self.text)
        self.assertGreaterEqual(
            self.attest.count("needs.build-package.outputs.package_basename"), 5
        )

    def test_downloaded_bytes_checked_before_any_signature_is_requested(self):
        guard = self.attest.index("      - name: Validate downloaded package identity")
        sign = self.attest.index("      - name: Generate signed build provenance")
        self.assertLess(guard, sign)
        script = step_script(self.text, "Validate downloaded package identity")
        self.assertIn("sha256sum --check --strict _release/SHA256SUMS", script)
        self.assertIn("GITHUB_SHA", script)

    def test_external_prs_keep_smoke_but_no_signing_authority(self):
        self.assertIn("    if: github.event_name != 'pull_request'\n", self.attest)
        self.assertIn("needs: [build-package, package-smoke]", self.attest)
        before = self.text.split("  attest-package:\n", 1)[0]
        self.assertIn("os: [ubuntu-latest, macos-latest, windows-latest]", before)
        self.assertNotIn("id-token: write", before)
        self.assertNotIn("attestations: write", before)
        self.assertNotIn("pull_request_target", self.text)
        self.assertNotIn("continue-on-error", self.text)
        self.assertNotIn("|| true", self.text)

    def test_both_verification_logs_are_in_the_deliverable(self):
        upload = self.attest.split(
            "      - name: Upload attested portable release evidence", 1
        )[1]
        self.assertIn("_release/provenance-verification.txt", upload)
        self.assertIn("_release/sbom-attestation-verification.txt", upload)

    def replay(
        self,
        *,
        package=BASENAME,
        missing=False,
        tampered=False,
        fail="",
        preflight=True,
    ):
        if os.name == "nt" or not shutil.which("bash") or not shutil.which("sha256sum"):
            self.skipTest(
                "shell replay requires POSIX bash/sha256sum; CI signing uses Ubuntu"
            )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = root / "_release"
            release.mkdir()
            archive = release / (BASENAME + ".tar.gz")
            content = b"owned synthetic package bytes; no scanner or customer data\n"
            archive.write_bytes(content)
            checksum = hashlib.sha256(content).hexdigest()
            (release / "SHA256SUMS").write_text(
                f"{checksum}  _release/{archive.name}\n", encoding="utf-8"
            )
            if tampered:
                archive.write_bytes(b"changed after package smoke")
            if missing:
                archive.unlink()
            for name in ("provenance.json", "sbom.json"):
                (root / name).write_text("{}", encoding="utf-8")
            executable = root / "gh"
            executable.write_text(
                "#!" + sys.executable + "\n" + textwrap.dedent("""\
                    import json, os, sys
                    from pathlib import Path
                    args = sys.argv[1:]
                    with Path(os.environ["CALL_LOG"]).open("a") as log:
                        log.write(json.dumps(args) + "\\n")
                    if len(args) < 3 or not Path(args[2]).is_file():
                        sys.exit(23)
                    predicate = args[args.index("--predicate-type") + 1] if "--predicate-type" in args else ""
                    if predicate == os.environ.get("FAIL_PREDICATE", "never"):
                        print("synthetic verifier rejection")
                        sys.exit(17)
                    print("synthetic command success; NOT cryptographic verification")
                    """),
                encoding="utf-8",
            )
            executable.chmod(0o700)
            env = {
                "PATH": str(root) + os.pathsep + os.environ.get("PATH", ""),
                "GITHUB_SHA": REVISION,
                "GITHUB_REPOSITORY": REPOSITORY,
                "PROVENANCE_BUNDLE": str(root / "provenance.json"),
                "SBOM_BUNDLE": str(root / "sbom.json"),
                "PROVENANCE_URL": "https://example.invalid/provenance",
                "SBOM_URL": "https://example.invalid/sbom",
                "PROVENANCE_ID": "1",
                "SBOM_ID": "2",
                "CALL_LOG": str(root / "calls.jsonl"),
                "FAIL_PREDICATE": fail,
            }
            if package is not None:
                env["PACKAGE_BASENAME"] = package
            scripts = []
            if preflight:
                scripts.append(
                    step_script(self.text, "Validate downloaded package identity")
                )
            scripts.append(
                step_script(self.text, "Preserve and verify attestation evidence")
            )
            script = "\n".join(scripts)
            # Resolve only declared build outputs, like GitHub's empty missing value.
            build = self.text.split("  build-package:\n", 1)[1].split(
                "    steps:\n", 1
            )[0]
            declared = re.findall(r"^      ([\w-]+):", build, re.MULTILINE)
            script = re.sub(
                r"\$\{\{\s*needs\.build-package\.outputs\.([\w-]+)\s*\}\}",
                lambda match: (package or "") if match.group(1) in declared else "",
                script,
            )
            result = subprocess.run(
                ["bash", "--noprofile", "--norc", "-c", script],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )
            log = root / "calls.jsonl"
            calls = (
                [json.loads(line) for line in log.read_text().splitlines()]
                if log.exists()
                else []
            )
            return result, calls

    def test_existing_verification_path_resolves_to_the_exact_package(self):
        result, calls = self.replay(preflight=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            calls[0][:3], ["attestation", "verify", f"_release/{BASENAME}.tar.gz"]
        )

    def test_both_bundles_predicates_source_and_workflow_are_verified(self):
        result, calls = self.replay()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(calls), 2)
        for args, predicate, bundle in zip(
            calls,
            (PROVENANCE, SBOM),
            ("provenance.sigstore.json", "sbom-attestation.sigstore.json"),
        ):
            for flag, value in (
                ("--predicate-type", predicate),
                ("--repo", REPOSITORY),
                ("--source-digest", REVISION),
                (
                    "--signer-workflow",
                    REPOSITORY + "/.github/workflows/workbench-release-package.yml",
                ),
                ("--bundle", "_release/" + bundle),
            ):
                with self.subTest(flag=flag, predicate=predicate):
                    self.assertEqual(args[args.index(flag) + 1], value)

    def test_missing_basename_fails_before_verifier(self):
        result, calls = self.replay(package=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])

    def test_empty_basename_fails_before_verifier(self):
        result, calls = self.replay(package="")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])

    def test_wrong_revision_fails_before_verifier(self):
        result, calls = self.replay(package="secscan_ai-evidence-workbench-" + "b" * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])

    def test_missing_package_fails_before_verifier(self):
        result, calls = self.replay(missing=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])

    def test_tampered_package_fails_before_verifier(self):
        result, calls = self.replay(tampered=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])

    def test_provenance_rejection_survives_tee_and_stops_sbom(self):
        result, calls = self.replay(fail=PROVENANCE)
        self.assertEqual(result.returncode, 17)
        self.assertEqual(len(calls), 1)

    def test_sbom_rejection_survives_tee(self):
        result, calls = self.replay(fail=SBOM)
        self.assertEqual(result.returncode, 17)
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
