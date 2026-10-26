"""Cross-platform smoke test for the exact portable Workbench source archive.

Executed explicitly by release-package CI, not by unittest discovery. The harness treats
the archive as untrusted input: it refuses traversal and link members, verifies the
recorded SHA-256, checks package metadata against the workflow revision, then runs the
packaged Workbench's compile and owned-loopback fresh-install smoke from an extracted
copy. It does not contact an assessment target or invoke an optional scanner runtime.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_in(directory: Path) -> Path:
    packages = sorted(directory.glob("secscan_ai-evidence-workbench-*.tar.gz"))
    if len(packages) != 1:
        raise RuntimeError(
            f"expected exactly one portable package, found {len(packages)}"
        )
    return packages[0]


def _expected_digest(directory: Path) -> str:
    checksum_path = directory / "SHA256SUMS"
    lines = [
        line.strip()
        for line in checksum_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(lines) != 1:
        raise RuntimeError(
            "release checksum file must contain exactly one package digest"
        )
    parts = lines[0].split()
    if (
        len(parts) != 2
        or len(parts[0]) != 64
        or any(ch not in "0123456789abcdef" for ch in parts[0].lower())
    ):
        raise RuntimeError("release checksum record is malformed")
    return parts[0].lower()


def _safe_members(archive: tarfile.TarFile) -> list[tarfile.TarInfo]:
    members = archive.getmembers()
    if not members:
        raise RuntimeError("portable package is empty")
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or member.issym() or member.islnk():
            raise RuntimeError(f"unsafe package member: {member.name}")
    return members


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: python -m workbench.tests.package_smoke <artifact-directory>"
        )
    directory = Path(sys.argv[1]).resolve()
    package = _package_in(directory)
    actual = _sha256(package)
    expected = _expected_digest(directory)
    if actual != expected:
        raise RuntimeError("portable package SHA-256 does not match SHA256SUMS")

    with tempfile.TemporaryDirectory(prefix="secscan_ai-package-smoke-") as temporary:
        destination = Path(temporary)
        with tarfile.open(package, "r:gz") as archive:
            members = _safe_members(archive)
            archive.extractall(destination, members=members, filter="data")
        roots = [path for path in destination.iterdir() if path.is_dir()]
        if len(roots) != 1:
            raise RuntimeError(
                "portable package must extract to exactly one top-level directory"
            )
        root = roots[0]
        manifest = json.loads(
            (root / "PACKAGE-MANIFEST.json").read_text(encoding="utf-8")
        )
        if manifest.get("schema") != "secscan_ai.portable-source-release/v1":
            raise RuntimeError("portable package manifest schema is invalid")
        expected_revision = os.environ.get("GITHUB_SHA")
        if (
            expected_revision
            and manifest.get("checked_out_revision") != expected_revision
        ):
            raise RuntimeError(
                "portable package revision does not match the workflow checkout"
            )
        if (
            manifest.get("entrypoint") != "python -m workbench"
            or manifest.get("native_installer") is not False
        ):
            raise RuntimeError("portable package entrypoint/type metadata is invalid")
        if manifest.get("third_party_python_runtime_packages") != []:
            raise RuntimeError(
                "portable package unexpectedly declares third-party Python runtime packages"
            )
        if manifest.get("bundled_scanner_binaries_or_images") != []:
            raise RuntimeError(
                "portable package unexpectedly bundles scanner binaries/images"
            )
        if not (root / "release-evidence" / "sbom.cdx.json").is_file():
            raise RuntimeError("portable package is missing its CycloneDX SBOM")

        subprocess.run(
            [sys.executable, "-m", "compileall", "-q", "workbench"],
            cwd=root,
            check=True,
        )
        subprocess.run(
            [sys.executable, "-m", "workbench.tests.fresh_install_smoke"],
            cwd=root,
            check=True,
        )

    print(
        json.dumps(
            {
                "schema": "secscan_ai.portable-source-package-smoke/v1",
                "package": package.name,
                "sha256": actual,
                "revision": os.environ.get("GITHUB_SHA", "unknown"),
                "platform": sys.platform,
                "python": sys.version.split()[0],
                "compile": "passed",
                "fresh_install_smoke": "passed",
                "external_assessment_target": False,
                "optional_scanner_executed": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
