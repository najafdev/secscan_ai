"""Revision-bound release-review evidence for the isolated workbench.

This module produces machine-readable packaging metadata and a real synthetic-lab
sample report without contacting an external assessment target. It is review evidence,
not a signed release, installer, SBOM for the legacy application, or security
certification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

from . import __version__

RELEASE_EVIDENCE_SCHEMA = "secscan_ai.review-release-evidence/v1"
CYCLONEDX_SPEC_VERSION = "1.5"
_REQUIRED_REVIEW_DOCS = (
    "README.md",
    "ADAPTERS.md",
    "OLLAMA.md",
    "PRODUCT_DIRECTION.md",
    "ROADMAP.md",
    "THREAT_MODEL.md",
    "REGRESSION_LABS.md",
    "RELEASE_NOTES.md",
)
_FORBIDDEN_PACKAGE_NAMES = {
    ".env",
    "reports.sqlite3",
    "credentials.json",
    "secrets.json",
    "id_rsa",
    "id_ed25519",
}
_FORBIDDEN_SUFFIXES = (".pem", ".key", ".p12", ".pfx")


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def find_forbidden_artifacts(root: Path) -> list[str]:
    """Return relative package paths that should never enter a review source bundle."""
    root = Path(root).resolve()
    blocked: list[str] = []
    for path in root.rglob("*"):
        if "__pycache__" in path.parts or path.name == ".DS_Store":
            continue
        if path.is_symlink():
            blocked.append(path.relative_to(root).as_posix() + " [symlink]")
            continue
        if not path.is_file():
            continue
        lower = path.name.lower()
        if lower in _FORBIDDEN_PACKAGE_NAMES or lower.endswith(_FORBIDDEN_SUFFIXES):
            blocked.append(path.relative_to(root).as_posix())
    return sorted(blocked)


def _optional_scanner_runner(root: Path) -> dict[str, Any]:
    from .semgrep_runner import semgrep_tool_public_metadata

    pin_path = root / "tooling" / "semgrep-1.177.0.json"
    rules_path = root / "rules" / "semgrep_workbench.yml"
    if not pin_path.is_file() or not rules_path.is_file():
        raise ValueError(
            "pinned Semgrep runner metadata or repository-authored rules are missing"
        )
    metadata = semgrep_tool_public_metadata()
    metadata.update(
        {
            "adapter_id": "semgrep-project-local",
            "adapter_version": "1.177.0-r1",
            "distribution": "optional-preinstalled-container",
            "pin_path": "tooling/semgrep-1.177.0.json",
            "pin_sha256": _sha256(pin_path),
            "rules_path": "rules/semgrep_workbench.yml",
            "rules_sha256": _sha256(rules_path),
            "validated_platform": "linux/amd64",
        }
    )
    return metadata


def source_review_manifest(root: Path) -> dict[str, Any]:
    """Hash human review boundaries and optional executable-tool pins."""
    root = Path(root).resolve()
    missing = [name for name in _REQUIRED_REVIEW_DOCS if not (root / name).is_file()]
    if missing:
        raise ValueError("missing required review documentation: " + ", ".join(missing))
    blocked = find_forbidden_artifacts(root)
    if blocked:
        raise ValueError(
            "forbidden runtime/secret artifacts found in workbench tree: "
            + ", ".join(blocked)
        )
    scanner = _optional_scanner_runner(root)
    return {
        "schema": RELEASE_EVIDENCE_SCHEMA,
        "workbench_version": __version__,
        "scope": "isolated-workbench-only",
        "python": {"minimum": "3.11", "third_party_runtime_packages": []},
        "bundled_scanners": [],
        "optional_scanner_runners": [scanner],
        "implemented_model_adapters": ["ollama"],
        "execution_boundaries": {
            "external_scanner_execution": True,
            "scanner_execution_scope": "pinned-local-container-only",
            "arbitrary_shell_execution": False,
            "public_server_supported": False,
            "browser_e2e_validated": False,
            "cross_platform_fresh_install_validated": False,
            "signed_release": False,
        },
        "review_documents": [
            {"path": name, "sha256": _sha256(root / name)}
            for name in _REQUIRED_REVIEW_DOCS
        ],
        "notes": [
            "Python standard-library modules are not enumerated as third-party packages.",
            "Ollama is an optional external runtime integration and is not bundled in this workbench source review artifact.",
            "Semgrep CE is supported only through the documented digest-pinned optional container runner; the image is not bundled or automatically pulled by assessment execution.",
            "The Semgrep container is constrained to network=none, a read-only project mount, repository-authored local rules and bounded process output.",
            "Trivy, Nuclei, ZAP and Nmap executables/images are not bundled or executable adapters in this milestone.",
            "This manifest describes the isolated workbench contribution, not the legacy repository application.",
        ],
    }


def cyclonedx_bom() -> dict[str, Any]:
    """Return a CycloneDX inventory including the optional pinned scanner runtime."""
    from .semgrep_runner import SEMGREP_IMAGE, SEMGREP_IMAGE_DIGEST, SEMGREP_VERSION

    serial = uuid.uuid5(
        uuid.NAMESPACE_URL, f"https://github.com/HostX0/secscan_ai/workbench/{__version__}"
    )
    digest_hex = SEMGREP_IMAGE_DIGEST.removeprefix("sha256:")
    return {
        "bomFormat": "CycloneDX",
        "specVersion": CYCLONEDX_SPEC_VERSION,
        "serialNumber": f"urn:uuid:{serial}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "SecScan AI Evidence Workbench",
                "version": __version__,
                "bom-ref": f"pkg:generic/secscan_ai-evidence-workbench@{__version__}",
                "properties": [
                    {"name": "secscan_ai:scope", "value": "isolated-workbench-only"},
                    {
                        "name": "secscan_ai:third-party-python-runtime-packages",
                        "value": "none",
                    },
                    {"name": "secscan_ai:bundled-scanners", "value": "none"},
                    {"name": "secscan_ai:optional-scanner-runners", "value": "semgrep-ce"},
                ],
            }
        },
        "components": [
            {
                "type": "container",
                "name": "semgrep/semgrep",
                "version": SEMGREP_VERSION,
                "scope": "optional",
                "bom-ref": f"container:semgrep/semgrep@{SEMGREP_IMAGE_DIGEST}",
                "hashes": [{"alg": "SHA-256", "content": digest_hex}],
                "licenses": [{"license": {"id": "LGPL-2.1-or-later"}}],
                "properties": [
                    {"name": "secscan_ai:image-reference", "value": SEMGREP_IMAGE},
                    {"name": "secscan_ai:bundled", "value": "false"},
                    {"name": "secscan_ai:automatic-pull", "value": "false"},
                    {"name": "secscan_ai:validated-platform", "value": "linux/amd64"},
                    {"name": "secscan_ai:container-network", "value": "none"},
                    {"name": "secscan_ai:rules-source", "value": "repository-authored"},
                ],
            }
        ],
    }


def synthetic_sample_report() -> dict[str, Any]:
    """Run the owned disposable authorization fixture and return its sealed report."""
    from .engine import Assessment, Scope, verify_integrity

    scope = Scope.parse(
        {
            "target": "lab",
            "mode": "verify",
            "authorized": True,
            "authorization": "RELEASE-SAMPLE-SYNTHETIC",
            "approve_verification": True,
            "use_ai": False,
            "model": "",
            "allow_cloud": False,
        }
    )
    report = Assessment(scope).run()
    if report.get("target") != "lab://ephemeral-authorization-fixture":
        raise RuntimeError("synthetic sample escaped its declared lab target")
    if (
        report.get("environment") != "synthetic_lab"
        or report.get("verdict") != "verified_in_synthetic_lab_only"
    ):
        raise RuntimeError(
            "synthetic sample did not demonstrate the expected owned fixture boundary"
        )
    if not verify_integrity(report):
        raise RuntimeError("synthetic sample report failed integrity validation")
    if any(
        item.get("evidence", {}).get("credentials_sent") is True
        for item in report.get("findings", [])
    ):
        raise RuntimeError("synthetic sample unexpectedly used credentials")
    return report


def write_release_evidence(
    output_dir: Path, root: Path | None = None
) -> dict[str, str]:
    """Write bounded review evidence and return relative output names with SHA-256 digests."""
    from .engine import markdown

    root = Path(root) if root is not None else Path(__file__).resolve().parent
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = source_review_manifest(root)
    sbom = cyclonedx_bom()
    sample = synthetic_sample_report()
    outputs = {
        "release-manifest.json": json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        "sbom.cdx.json": json.dumps(sbom, indent=2, sort_keys=True) + "\n",
        "synthetic-sample-report.json": json.dumps(sample, indent=2, sort_keys=True)
        + "\n",
        "synthetic-sample-report.md": markdown(sample) + "\n",
    }
    digests: dict[str, str] = {}
    for name, content in outputs.items():
        path = output_dir / name
        path.write_text(content, encoding="utf-8")
        digests[name] = _sha256(path)
    checksums = "".join(
        f"{digest}  {name}\n" for name, digest in sorted(digests.items())
    )
    (output_dir / "SHA256SUMS").write_text(checksums, encoding="utf-8")
    digests["SHA256SUMS"] = _sha256(output_dir / "SHA256SUMS")
    return digests


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate bounded Evidence Workbench release-review evidence"
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    digests = write_release_evidence(args.output_dir, args.root)
    print(
        json.dumps(
            {"schema": RELEASE_EVIDENCE_SCHEMA, "outputs": digests}, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
