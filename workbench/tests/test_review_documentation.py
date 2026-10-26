"""Guard current claims and known CI setup fixes, not historical completion."""

import hashlib
import re
import shlex
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
WORKFLOWS = WORKBENCH.parent / ".github" / "workflows"


def text(name):
    return (WORKBENCH / name).read_text(encoding="utf-8")


class ReviewDocumentationTests(unittest.TestCase):
    def assert_black_check_targets_repository(self, workflow):
        commands = [
            shlex.split(line.strip())
            for line in workflow.splitlines()
            if line.strip().startswith("black ")
        ]
        checks = [command for command in commands if "--check" in command]
        self.assertTrue(checks, "expected an enforced Black check command")
        for command in checks:
            with self.subTest(command=command):
                self.assertEqual(command[0], "black")
                self.assertIn("--diff", command)
                self.assertIn(".", command)

    def test_current_readme_has_accurate_entrypoint_and_execution_limits(self):
        readme = text("README.md")
        for expected in (
            "git clone --branch main",
            "python -m workbench",
            "Semgrep CE 1.177.0",
            "parser-only",
            "ZAP and Nmap",
            "not encrypted at rest",
            "not a universally sanitized",
            "No findings is not a security guarantee",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, readme)
        self.assertNotIn(
            "Live local/cloud model inference has not yet been validated", readme
        )
        self.assertNotIn(
            "executable ZAP, Nuclei, Semgrep, Trivy or Nmap runners;", readme
        )

    def test_model_compatibility_is_not_a_quality_or_egress_claim(self):
        doc = text("OLLAMA.md")
        for expected in (
            "real local-model compatibility probe",
            "35589788372",
            "not analysis quality",
            "**not** an egress guarantee",
            "no target, credentials or assessment evidence",
            "shared monotonic assessment deadline",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, doc)
        self.assertNotIn(
            "Socket timeouts remain per blocking operation, not a hard overall deadline",
            doc,
        )

    def test_release_attestations_are_distinct_from_report_signing(self):
        notes = text("RELEASE_NOTES.md")
        self.assertIn("GitHub/Sigstore build-provenance and SBOM attestations", notes)
        self.assertIn("not signed assessment reports", notes)
        self.assertIn("in progress", notes)

    def test_active_milestone_does_not_reuse_historical_stop_condition(self):
        roadmap = text("ROADMAP.md")
        self.assertIn("Active continuation acceptance", roadmap)
        self.assertIn("not permission to disable the resumed sprint", roadmap)
        for letter in "ABCDE":
            self.assertIn("### Gate " + letter, roadmap)
        self.assertNotIn(
            "**Current bounded milestone state: Gates A, B, C, D and E pass", roadmap
        )

    def test_first_milestone_records_preserved_byte_for_byte(self):
        for path, expected in (
            ("PROGRESS_HISTORY.md", "b24a2e46355d471b4f035df35e73f7f184afcf40"),
            ("ROADMAP_BASELINE.md", "edd13197f783349c5f592470d7ed3245589048d7"),
        ):
            raw = (WORKBENCH / path).read_bytes()
            actual = hashlib.sha1(
                b"blob " + str(len(raw)).encode() + b"\0" + raw
            ).hexdigest()
            self.assertEqual(actual, expected)

    def test_current_doc_links_resolve_inside_portable_component(self):
        for name in (
            "README.md",
            "ROADMAP.md",
            "PROGRESS.md",
            "OLLAMA.md",
            "RELEASE_NOTES.md",
        ):
            for destination in re.findall(r"\]\(([^)]+)\)", text(name)):
                if "://" in destination or destination.startswith("#"):
                    continue
                path = destination.split("#", 1)[0]
                with self.subTest(document=name, link=path):
                    self.assertTrue((WORKBENCH / path).is_file())

    @unittest.skipUnless(
        WORKFLOWS.is_dir(),
        "portable source package does not ship repository CI workflows",
    )
    def test_legacy_setup_fixes_keep_real_test_and_lint_commands(self):
        basic = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
        enterprise = (WORKFLOWS / "enterprise-ci.yml").read_text(encoding="utf-8")
        for doc in (basic, enterprise):
            self.assertNotIn("actions/upload-artifact@v3", doc)
            self.assertIn("actions/upload-artifact@v4", doc)
            for package in (
                "libldap2-dev",
                "libsasl2-dev",
                "portaudio19-dev",
                "python3-dev",
            ):
                self.assertIn(package, doc)

        code_quality = enterprise[
            enterprise.index("  code-quality:") : enterprise.index("  test-suite:")
        ]
        test_suite = enterprise[
            enterprise.index("  test-suite:") : enterprise.index("  docker-build:")
        ]
        self.assertEqual(
            enterprise.count("name: Install native build prerequisites"), 1
        )
        self.assertNotIn("apt-get install", code_quality)
        self.assertNotIn("pip install -r requirements.txt", code_quality)
        self.assertIn("QUALITY_PYTHON_VERSION: '3.11'", enterprise)
        self.assertIn("python-version: ${{ env.QUALITY_PYTHON_VERSION }}", code_quality)
        self.assertIn("mkdir -p .ci/black", code_quality)
        self.assertIn(
            "python --version 2>&1 | tee .ci/black/python-version.txt", code_quality
        )
        self.assertIn("black --version | tee .ci/black/black-version.txt", code_quality)
        self.assertIn("name: Install native build prerequisites", test_suite)
        self.assertIn("requirements-file: requirements-ci-py38.txt", test_suite)
        self.assertEqual(test_suite.count("requirements-file: requirements.txt"), 3)
        self.assertEqual(test_suite.count("dependency-scope: full"), 3)
        self.assertIn("dependency-scope: legacy-core", test_suite)
        self.assertIn('pip install -r "${{ matrix.requirements-file }}"', test_suite)

        for command in (
            "python test_installation.py",
            "from secscan_ai import SecScanAI, AIEngine, ToolManager",
            "flake8 secscan_ai.py --count --select=E9,F63,F7,F82",
            "docker run --rm secscan_ai:test --help",
        ):
            self.assertIn(command, basic)
        self.assert_black_check_targets_repository(enterprise)
        for command in (
            "pytest tests/unit/",
            "pytest tests/integration/",
            "flake8 . --count --select=E9,F63,F7,F82",
        ):
            self.assertIn(command, enterprise)
        # Inherited advisory checks are disclosed; this repair must not add new suppression.
        self.assertLessEqual(basic.count("|| true"), 1)
        self.assertLessEqual(enterprise.count("|| true"), 6)
        self.assertNotIn("continue-on-error", basic + enterprise)

    @unittest.skipUnless(
        WORKFLOWS.is_dir(),
        "portable source package does not ship repository CI workflows",
    )
    def test_fork_workflow_cannot_publish_or_claim_deployment_readiness(self):
        enterprise = (WORKFLOWS / "enterprise-ci.yml").read_text(encoding="utf-8")
        self.assertIn("push: false", enterprise)
        self.assertNotIn("docker/login-action", enterprise)
        self.assertNotIn("secrets.DOCKERHUB", enterprise)
        self.assertNotIn("Ready for enterprise deployment", enterprise)


if __name__ == "__main__":
    unittest.main()
