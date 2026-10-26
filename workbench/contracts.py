"""Versioned, execution-neutral contracts for importing scanner observations.

Adapters may report observations, confidence and evidence, but they cannot promote their
own output to an independently verified state. Verification is a separate workbench step.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any

ADAPTER_SCHEMA = "secscan_ai.adapter-result/v1"
_ALLOWED_STATUS = {"completed", "partial", "error", "skipped"}
_ALLOWED_SEVERITY = {"info", "low", "medium", "high", "critical"}
_ID = re.compile(r"[a-z0-9][a-z0-9._/-]{0,95}")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, name: str, maximum: int, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be text")
    value = value.strip()
    if (
        (not value and not allow_empty)
        or len(value) > maximum
        or any(ord(c) < 32 or ord(c) == 127 for c in value)
    ):
        raise ValueError(f"invalid {name}")
    return value


def _bounded_json(value: Any, name: str, maximum_bytes: int = 32768) -> Any:
    try:
        raw = _canonical(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be JSON-compatible") from exc
    if len(raw) > maximum_bytes:
        raise ValueError(f"{name} is too large")
    return value


@dataclass(frozen=True)
class AdapterIdentity:
    adapter_id: str
    version: str

    @classmethod
    def parse(cls, value: Any) -> "AdapterIdentity":
        if not isinstance(value, dict) or set(value) != {"id", "version"}:
            raise ValueError("adapter must contain exactly id and version")
        adapter_id = _text(value["id"], "adapter id", 96)
        version = _text(value["version"], "adapter version", 64)
        if not _ID.fullmatch(adapter_id.lower()):
            raise ValueError("invalid adapter id")
        return cls(adapter_id.lower(), version)


def normalize_adapter_result(payload: Any, *, asset_key: str) -> dict[str, Any]:
    """Validate a scanner adapter envelope and normalize observations conservatively.

    `asset_key` is an internal, engagement-scoped stable identifier supplied by the
    workbench. Raw target URLs or credentials do not belong in this contract.
    """
    if not isinstance(payload, dict):
        raise ValueError("adapter result must be an object")
    allowed = {"schema", "adapter", "status", "coverage", "findings", "error"}
    if set(payload) - allowed:
        raise ValueError("adapter result contains unsupported fields")
    if payload.get("schema") != ADAPTER_SCHEMA:
        raise ValueError("unsupported adapter schema")
    identity = AdapterIdentity.parse(payload.get("adapter"))
    status = payload.get("status")
    if status not in _ALLOWED_STATUS:
        raise ValueError("invalid adapter status")
    asset_key = _text(asset_key, "asset key", 160)

    coverage = payload.get("coverage", {})
    if not isinstance(coverage, dict) or set(coverage) - {
        "objects_tested",
        "objects_total",
        "notes",
    }:
        raise ValueError("invalid coverage object")
    tested = coverage.get("objects_tested")
    total = coverage.get("objects_total")
    if tested is not None and (type(tested) is not int or tested < 0):
        raise ValueError("objects_tested must be a nonnegative integer or null")
    if total is not None and (type(total) is not int or total < 0):
        raise ValueError("objects_total must be a nonnegative integer or null")
    if tested is not None and total is not None and tested > total:
        raise ValueError("objects_tested cannot exceed objects_total")
    notes = coverage.get("notes", [])
    if not isinstance(notes, list) or len(notes) > 32:
        raise ValueError("coverage notes must be a short list")
    clean_notes = [_text(item, "coverage note", 300) for item in notes]

    error = payload.get("error")
    if error is not None:
        error = _text(error, "adapter error", 500)
    if status == "error" and not error:
        raise ValueError("errored adapter results require an error summary")

    findings = payload.get("findings", [])
    if not isinstance(findings, list) or len(findings) > 500:
        raise ValueError("findings must be a bounded list")
    normalized = []
    seen_fingerprints: set[str] = set()
    for item in findings:
        if not isinstance(item, dict):
            raise ValueError("each finding must be an object")
        fields = {
            "rule",
            "title",
            "severity",
            "confidence",
            "evidence",
            "remediation",
            "external_id",
        }
        if set(item) - fields:
            raise ValueError("finding contains unsupported fields")
        rule = _text(item.get("rule"), "rule", 160)
        title = _text(item.get("title"), "title", 240)
        severity = item.get("severity")
        if severity not in _ALLOWED_SEVERITY:
            raise ValueError("invalid severity")
        confidence = item.get("confidence")
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not math.isfinite(confidence)
            or not 0 <= confidence <= 1
        ):
            raise ValueError("confidence must be a finite number from 0 to 1")
        evidence = _bounded_json(item.get("evidence", {}), "evidence")
        remediation = _text(
            item.get("remediation", "Not supplied by adapter"), "remediation", 2000
        )
        external_id = item.get("external_id")
        if external_id is not None:
            external_id = _text(external_id, "external id", 200)
        fingerprint = _digest(
            {
                "asset": asset_key,
                "adapter": identity.adapter_id,
                "rule": rule,
                "external_id": external_id,
            }
        )
        if fingerprint in seen_fingerprints:
            raise ValueError(
                "adapter findings contain an ambiguous duplicate identity; "
                "supply a stable external_id that distinguishes each occurrence"
            )
        seen_fingerprints.add(fingerprint)
        normalized.append(
            {
                "id": fingerprint[:16],
                "fingerprint": fingerprint,
                "rule": rule,
                "title": title,
                "severity": severity,
                "confidence": float(confidence),
                "verification": "candidate",
                "evidence": evidence,
                "evidence_sha256": _digest(evidence),
                "remediation": remediation,
                "source": f"adapter/{identity.adapter_id}/{identity.version}",
                "external_id": external_id,
            }
        )

    return {
        "schema": ADAPTER_SCHEMA,
        "adapter": {"id": identity.adapter_id, "version": identity.version},
        "status": status,
        "coverage": {
            "objects_tested": tested,
            "objects_total": total,
            "notes": clean_notes,
        },
        "findings": normalized,
        "error": error,
        "verification_authority": "workbench_only",
    }
