"""Create a portable, unsigned evidence review bundle from a finalized report."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Any


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def build_bundle(
    report: dict[str, Any],
    markdown_text: str,
    retest_diff: dict[str, Any] | None = None,
) -> bytes:
    if (
        not isinstance(report, dict)
        or report.get("status") == "running"
        or not isinstance(report.get("id"), str)
    ):
        raise ValueError("bundle requires a finalized report")
    if not isinstance(markdown_text, str):
        raise ValueError("markdown export must be text")

    files: dict[str, bytes] = {
        "report.json": json.dumps(report, indent=2, sort_keys=True).encode(),
        "report.md": markdown_text.encode(),
    }
    if retest_diff is not None:
        files["retest-diff.json"] = json.dumps(
            retest_diff, indent=2, sort_keys=True
        ).encode()

    manifest = {
        "schema": "secscan_ai.evidence-bundle/v1",
        "run_id": report["id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "signed": False,
        "files": {
            name: {"sha256": _sha(raw), "bytes": len(raw)}
            for name, raw in sorted(files.items())
        },
        "note": "Checksums detect accidental/content changes relative to this manifest; this bundle is not a digital signature or proof of authorship.",
    }
    files["manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True).encode()

    output = io.BytesIO()
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, raw)
    return output.getvalue()
