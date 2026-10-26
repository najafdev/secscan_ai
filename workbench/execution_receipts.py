"""Versioned receipts for bounded adapter execution.

Receipts record what authority was declared, what sanitized scope was presented to the
operator, what bounded work was observed, and the normalized adapter result. They are
review metadata only: a receipt never upgrades a candidate observation to verified.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from .execution_contracts import ExecutionDeclaration

EXECUTION_RECEIPT_SCHEMA = "secscan_ai.execution-receipt/v1"
_MAX_SUMMARY_BYTES = 8192
_FORBIDDEN_SUMMARY_KEYS = {
    "password",
    "passwd",
    "token",
    "cookie",
    "authorization",
    "secret",
    "credential",
    "credentials",
    "command",
    "argv",
    "environment",
}


def _bounded_json(value: Any, name: str, maximum: int = _MAX_SUMMARY_BYTES) -> Any:
    try:
        raw = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be JSON-compatible") from exc
    if len(raw) > maximum:
        raise ValueError(f"{name} is too large")
    return value


def _contains_forbidden_key(value: Any) -> bool:
    """Reject sensitive/execution field names at any nesting depth."""
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).strip().lower() in _FORBIDDEN_SUMMARY_KEYS:
                return True
            if _contains_forbidden_key(item):
                return True
    elif isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def _nonnegative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def normalize_execution_receipt(payload: Any) -> dict[str, Any]:
    """Validate an execution receipt against its declaration and candidate-only result."""
    if not isinstance(payload, dict):
        raise ValueError("execution receipt must be an object")
    required = {"schema", "declaration", "request_summary", "usage", "result"}
    if set(payload) != required:
        raise ValueError("execution receipt fields do not match the v1 contract")
    if payload.get("schema") != EXECUTION_RECEIPT_SCHEMA:
        raise ValueError("unsupported execution receipt schema")

    declaration = ExecutionDeclaration.parse(payload.get("declaration"))
    summary = _bounded_json(
        copy.deepcopy(payload.get("request_summary")), "request summary"
    )
    if not isinstance(summary, dict):
        raise ValueError("request summary must be an object")
    if _contains_forbidden_key(summary):
        raise ValueError(
            "request summary contains a forbidden sensitive/execution field"
        )

    usage = payload.get("usage")
    if not isinstance(usage, dict) or set(usage) != {
        "objects_tested",
        "network_requests",
        "elapsed_ms",
    }:
        raise ValueError("execution usage fields do not match the v1 contract")
    objects_tested = _nonnegative_int(usage.get("objects_tested"), "objects_tested")
    network_requests = _nonnegative_int(
        usage.get("network_requests"), "network_requests"
    )
    elapsed_ms = _nonnegative_int(usage.get("elapsed_ms"), "elapsed_ms")
    if objects_tested > declaration.max_objects:
        raise ValueError("execution receipt exceeds declared object budget")
    if network_requests > declaration.max_requests:
        raise ValueError("execution receipt exceeds declared request budget")

    result = copy.deepcopy(payload.get("result"))
    if (
        not isinstance(result, dict)
        or result.get("verification_authority") != "workbench_only"
    ):
        raise ValueError(
            "execution receipt requires a normalized workbench adapter result"
        )
    adapter = result.get("adapter")
    if (
        not isinstance(adapter, dict)
        or adapter.get("id") != declaration.adapter_id
        or adapter.get("version") != declaration.version
    ):
        raise ValueError("execution receipt adapter identity mismatch")
    findings = result.get("findings")
    if not isinstance(findings, list) or any(
        not isinstance(item, dict) or item.get("verification") != "candidate"
        for item in findings
    ):
        raise ValueError(
            "execution receipt cannot contain self-verified adapter findings"
        )

    return {
        "schema": EXECUTION_RECEIPT_SCHEMA,
        "declaration": declaration.public(),
        "request_summary": summary,
        "usage": {
            "objects_tested": objects_tested,
            "network_requests": network_requests,
            "elapsed_ms": elapsed_ms,
        },
        "result": result,
    }
