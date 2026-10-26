"""Privacy-preserving helpers for database/API proof artifacts.

Real record values are never sampled by default. A value is emitted only when it is an
explicit synthetic canary generated for proof, identified by the workbench marker prefix.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

_SYNTHETIC_PREFIX = "SECSCAN_AI-SYNTHETIC-"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "unknown"


def summarize_records(records: Any) -> dict[str, Any]:
    """Return useful proof metadata without exporting ordinary record values."""
    if (
        not isinstance(records, list)
        or len(records) > 1000
        or any(not isinstance(row, dict) for row in records)
    ):
        raise ValueError("records must be a bounded list of objects")
    raw = _canonical(records)
    if len(raw) > 2_000_000:
        raise ValueError("record evidence is too large")

    columns = sorted(
        {
            str(key)
            for row in records
            for key in row
            if isinstance(key, str) and len(key) <= 160
        }
    )
    types = {
        column: sorted({_type_name(row[column]) for row in records if column in row})
        for column in columns
    }
    canaries = []
    for row_index, row in enumerate(records):
        for column, value in row.items():
            if (
                isinstance(column, str)
                and isinstance(value, str)
                and value.startswith(_SYNTHETIC_PREFIX)
            ):
                canaries.append(
                    {"row_index": row_index, "column": column, "value": value[:160]}
                )
                if len(canaries) >= 8:
                    break
        if len(canaries) >= 8:
            break
    return {
        "row_count": len(records),
        "columns": columns,
        "types": types,
        "content_sha256": hashlib.sha256(raw).hexdigest(),
        "ordinary_values_exported": False,
        "synthetic_canaries": canaries,
        "proof_note": "Ordinary record values are omitted. Synthetic canaries may be shown because they are generated test data.",
    }
