"""Coverage-aware comparison of two finalized assessment reports.

The comparator deliberately avoids claiming a finding is fixed merely because it is absent.
It distinguishes persistent/new findings from not-reproduced and not-retested outcomes and
binds prior remediation guidance/evidence to the exact recheck without claiming remediation
was actually applied.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

_ADAPTER_SOURCE = re.compile(r"^adapter/([a-z0-9][a-z0-9._/-]{0,95})/([^/\s]{1,64})$")
_FIXED_METHOD_BY_ADAPTER = {
    ("native-web-headers", "1"): "HEAD",
}


def _tool_for_rule(rule: str) -> str | None:
    if rule.startswith("web/"):
        return "native-web-headers"
    if rule.startswith("header/"):
        return "http_baseline"  # legacy reports before the registry-backed web adapter
    if rule == "lab/missing-authorization":
        return "verify_lab_canary"
    return None


def _finding_adapter(
    finding: dict[str, Any], tool: str | None
) -> dict[str, str] | None:
    source = finding.get("source")
    if not tool or not isinstance(source, str):
        return None
    matched = _ADAPTER_SOURCE.fullmatch(source)
    if not matched or matched.group(1) != tool:
        return None
    return {"id": matched.group(1), "version": matched.group(2)}


def _finding_method(finding: dict[str, Any], tool: str | None) -> str | None:
    if tool not in {"http_baseline", "native-web-headers"}:
        return None
    evidence = finding.get("evidence")
    method = evidence.get("method") if isinstance(evidence, dict) else None
    if not isinstance(method, str) or not method.strip():
        return None
    return method.strip().upper()


def _check_adapter(check: dict[str, Any]) -> dict[str, str] | None:
    adapter = check.get("adapter")
    if not isinstance(adapter, dict):
        return None
    adapter_id = adapter.get("id")
    version = adapter.get("version")
    if not isinstance(adapter_id, str) or not isinstance(version, str):
        return None
    return {"id": adapter_id, "version": version}


def _check_method(check: dict[str, Any]) -> str | None:
    evidence = check.get("evidence")
    method = evidence.get("method") if isinstance(evidence, dict) else None
    if isinstance(method, str) and method.strip():
        return method.strip().upper()

    adapter = _check_adapter(check)
    if adapter is None:
        return None
    return _FIXED_METHOD_BY_ADAPTER.get((adapter["id"], adapter["version"]))


def _observation_result(
    tool: str | None,
    status: str,
    reason: str | None,
    *,
    expected_adapter: dict[str, str] | None,
    observed_adapters: list[dict[str, str]],
    expected_method: str | None,
    observed_methods: list[str],
) -> dict[str, Any]:
    return {
        "tool": tool,
        "status": status,
        "reason": reason,
        "expected_adapter": expected_adapter,
        "observed_adapters": observed_adapters,
        "expected_method": expected_method,
        "observed_methods": observed_methods,
    }


def _tool_observation(
    report: dict[str, Any], tool: str | None, finding: dict[str, Any] | None = None
) -> dict[str, Any]:
    finding = finding or {}
    expected_adapter = _finding_adapter(finding, tool)
    expected_method = _finding_method(finding, tool)
    if not tool:
        return _observation_result(
            None,
            "unmapped",
            "No comparable execution mapping exists for this rule.",
            expected_adapter=None,
            observed_adapters=[],
            expected_method=None,
            observed_methods=[],
        )

    observations = []
    for check in report.get("checks", []):
        if not isinstance(check, dict) or check.get("tool") != tool:
            continue
        observations.append(
            {
                "status": (
                    check.get("status")
                    if isinstance(check.get("status"), str)
                    else "unknown"
                ),
                "reason": (
                    check.get("reason")
                    if isinstance(check.get("reason"), str)
                    else None
                ),
                "adapter": _check_adapter(check),
                "method": _check_method(check),
            }
        )

    observed_adapters = []
    for item in observations:
        adapter = item["adapter"]
        if adapter and adapter not in observed_adapters:
            observed_adapters.append(adapter)
    observed_adapters.sort(key=lambda item: (item["id"], item["version"]))
    observed_methods = sorted(
        {item["method"] for item in observations if item["method"] is not None}
    )

    def result(status: str, reason: str | None) -> dict[str, Any]:
        return _observation_result(
            tool,
            status,
            reason,
            expected_adapter=expected_adapter,
            observed_adapters=observed_adapters,
            expected_method=expected_method,
            observed_methods=observed_methods,
        )

    if not observations:
        return result("not_executed", "Mapped check is absent from the current run.")

    candidates = observations
    if expected_adapter is not None:
        candidates = [
            item for item in candidates if item["adapter"] == expected_adapter
        ]
        if not candidates:
            status = "version_changed" if observed_adapters else "identity_unknown"
            reason = (
                "Mapped adapter identity changed; absence is not comparable reproduction evidence."
                if observed_adapters
                else "Mapped check did not record the adapter identity needed for a comparable recheck."
            )
            return result(status, reason)
    elif tool == "native-web-headers":
        return result(
            "identity_unknown",
            "Prior adapter identity is unavailable; absence is not comparable reproduction evidence.",
        )

    if expected_method is not None:
        method_candidates = [
            item for item in candidates if item["method"] == expected_method
        ]
        if not method_candidates:
            candidate_methods = sorted(
                {item["method"] for item in candidates if item["method"] is not None}
            )
            status = "method_changed" if candidate_methods else "method_unknown"
            reason = (
                "Mapped check method changed; absence is not comparable reproduction evidence."
                if candidate_methods
                else "Mapped check did not record the method needed for a comparable recheck."
            )
            return result(status, reason)
        candidates = method_candidates

    if any(item["status"] == "completed" for item in candidates):
        return result("completed", None)

    first = candidates[0]
    return result(first["status"], first["reason"])


def _sha256_text(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _recheck_binding(
    previous_run: str,
    current_run: str,
    finding: dict[str, Any],
    coverage: dict[str, Any],
    comparable_scope: bool,
) -> dict[str, Any]:
    """Create a non-secret review link from prior evidence/remediation to this recheck."""
    remediation = finding.get("remediation")
    evidence_sha = finding.get("evidence_sha256")
    return {
        "previous_run": previous_run,
        "current_run": current_run,
        "previous_finding_id": (
            finding.get("id") if isinstance(finding.get("id"), str) else None
        ),
        "previous_evidence_sha256": (
            evidence_sha if isinstance(evidence_sha, str) else None
        ),
        "remediation_sha256": _sha256_text(remediation),
        "remediation_guidance_present": isinstance(remediation, str)
        and bool(remediation),
        "remediation_applied": "unknown",
        "comparable_scope": comparable_scope,
        "coverage": coverage,
    }


def _optional_equal(previous: dict[str, Any], current: dict[str, Any], key: str):
    left = previous.get(key)
    right = current.get(key)
    if not isinstance(left, str) or not isinstance(right, str):
        return None
    return left == right


def _scope_identity_equal(
    previous: dict[str, Any], current: dict[str, Any], key: str
) -> bool | None:
    """Compare scope identity only when both reports recorded a nonempty string."""
    left = previous.get(key)
    right = current.get(key)
    if (
        not isinstance(left, str)
        or not left.strip()
        or not isinstance(right, str)
        or not right.strip()
    ):
        return None
    return left == right


def _index_findings(report: dict[str, Any], label: str) -> dict[str, dict[str, Any]]:
    """Index findings only when every comparison identity is explicit and unambiguous."""
    indexed: dict[str, dict[str, Any]] = {}
    for position, item in enumerate(report.get("findings", [])):
        if not isinstance(item, dict):
            raise ValueError(f"{label} report finding {position + 1} must be an object")
        fingerprint = item.get("fingerprint")
        if not isinstance(fingerprint, str) or not fingerprint.strip():
            raise ValueError(
                f"{label} report finding {position + 1} is missing a comparison fingerprint"
            )
        if fingerprint in indexed:
            raise ValueError(
                f"{label} report contains duplicate fingerprint {fingerprint!r}; "
                "instance-level comparison would be ambiguous"
            )
        indexed[fingerprint] = item
    return indexed


def compare_reports(
    previous: dict[str, Any], current: dict[str, Any]
) -> dict[str, Any]:
    if not isinstance(previous, dict) or not isinstance(current, dict):
        raise ValueError("reports must be objects")
    for report in (previous, current):
        if (
            not isinstance(report.get("id"), str)
            or not report["id"].strip()
            or not isinstance(report.get("findings", []), list)
            or not isinstance(report.get("checks", []), list)
        ):
            raise ValueError("invalid report shape")
        if report.get("status") == "running":
            raise ValueError("running reports cannot be compared")
    if previous["id"] == current["id"]:
        raise ValueError("reports must be distinct assessment runs")

    same_target = _scope_identity_equal(previous, current, "target")
    same_environment = _scope_identity_equal(previous, current, "environment")
    comparable_scope = same_target is True and same_environment is True
    old = _index_findings(previous, "previous")
    new = _index_findings(current, "current")

    items = []
    counts = {"still_present": 0, "new": 0, "not_reproduced": 0, "not_retested": 0}
    for fingerprint, finding in sorted(old.items()):
        tool = _tool_for_rule(str(finding.get("rule", "")))
        coverage = _tool_observation(current, tool, finding)
        if fingerprint in new:
            state = "still_present"
            reason = "Matching fingerprint remains present in the current run."
        elif comparable_scope and coverage["status"] == "completed":
            state = "not_reproduced"
            reason = "Comparable check completed with matching execution identity, but the prior fingerprint was not observed. This is not an automatic fixed verdict."
        else:
            state = "not_retested"
            if same_target is None or same_environment is None:
                reason = "Target or environment identity was not recorded; comparable successful coverage was not established."
            elif not comparable_scope:
                reason = "Target or environment changed; comparable successful coverage was not established."
            elif coverage["status"] != "completed":
                reason = coverage["reason"] or (
                    "Comparable successful coverage for this rule was not established; the mapped check was not completed."
                )
            else:
                reason = (
                    "Comparable successful coverage for this rule was not established."
                )
        counts[state] += 1
        items.append(
            {
                "fingerprint": fingerprint,
                "title": finding.get("title"),
                "rule": finding.get("rule"),
                "state": state,
                "reason": reason,
                "recheck": _recheck_binding(
                    previous["id"], current["id"], finding, coverage, comparable_scope
                ),
            }
        )

    for fingerprint, finding in sorted(new.items()):
        if fingerprint not in old:
            counts["new"] += 1
            items.append(
                {
                    "fingerprint": fingerprint,
                    "title": finding.get("title"),
                    "rule": finding.get("rule"),
                    "state": "new",
                    "reason": "Fingerprint was not present in the previous report.",
                    "recheck": {
                        "previous_run": previous["id"],
                        "current_run": current["id"],
                        "previous_finding_id": None,
                        "previous_evidence_sha256": None,
                        "remediation_sha256": None,
                        "remediation_guidance_present": False,
                        "remediation_applied": "not_applicable",
                        "comparable_scope": comparable_scope,
                        "coverage": _tool_observation(
                            current,
                            _tool_for_rule(str(finding.get("rule", ""))),
                            finding,
                        ),
                    },
                }
            )

    return {
        "schema": "secscan_ai.retest-diff/v1",
        "previous_run": previous["id"],
        "current_run": current["id"],
        "comparable_scope": comparable_scope,
        "scope_comparison": {
            "same_target": same_target,
            "same_environment": same_environment,
            "same_mode": _optional_equal(previous, current, "mode"),
            "same_engine_version": _optional_equal(previous, current, "engine_version"),
            "previous_engine_version": previous.get("engine_version"),
            "current_engine_version": current.get("engine_version"),
        },
        "counts": counts,
        "items": items,
        "conclusion": "comparison_only",
        "note": "Absent findings are never labeled fixed solely by absence. A not-reproduced state requires the same recorded target/environment plus completed comparable execution identity and method. Remediation guidance is hash-linked for review, but whether it was applied remains unknown unless separate evidence establishes that fact.",
    }
