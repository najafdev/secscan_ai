"""
HackBot Diff Report — Assessment Comparison Engine
====================================================
Compare two assessments of the same target to identify:
- New vulnerabilities (appeared in the newer scan)
- Fixed vulnerabilities (present in the old scan but gone)
- Persistent vulnerabilities (still present)
- Severity changes and trend analysis
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ── Enums & Data Classes ─────────────────────────────────────────────────────

class DiffStatus(str, Enum):
    """Status of a finding between two assessments."""
    NEW = "New"
    FIXED = "Fixed"
    PERSISTENT = "Persistent"
    REGRESSION = "Regression"  # Was fixed previously, now back


class TrendDirection(str, Enum):
    IMPROVED = "Improved"
    DEGRADED = "Degraded"
    UNCHANGED = "Unchanged"


SEVERITY_ORDER = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
}


@dataclass
class DiffFinding:
    """A finding annotated with its diff status."""
    title: str
    severity: str
    description: str
    status: DiffStatus
    evidence: str = ""
    recommendation: str = ""
    tool: str = ""
    old_severity: str = ""  # Only if severity changed

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "title": self.title,
            "severity": self.severity,
            "description": self.description,
            "status": self.status.value,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "tool": self.tool,
        }
        if self.old_severity:
            d["old_severity"] = self.old_severity
        return d


@dataclass
class SeverityDelta:
    """Change in findings count for a severity level."""
    severity: str
    old_count: int
    new_count: int

    @property
    def delta(self) -> int:
        return self.new_count - self.old_count

    @property
    def direction(self) -> str:
        if self.delta > 0:
            return "↑"
        elif self.delta < 0:
            return "↓"
        return "—"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "old_count": self.old_count,
            "new_count": self.new_count,
            "delta": self.delta,
            "direction": self.direction,
        }


@dataclass
class DiffReport:
    """Complete diff report comparing two assessments."""
    target: str
    old_session_id: str
    new_session_id: str
    old_session_name: str = ""
    new_session_name: str = ""
    old_date: float = 0.0
    new_date: float = 0.0
    new_findings: List[DiffFinding] = field(default_factory=list)
    fixed_findings: List[DiffFinding] = field(default_factory=list)
    persistent_findings: List[DiffFinding] = field(default_factory=list)
    regression_findings: List[DiffFinding] = field(default_factory=list)
    severity_deltas: List[SeverityDelta] = field(default_factory=list)
    trend: TrendDirection = TrendDirection.UNCHANGED
    risk_score_old: float = 0.0
    risk_score_new: float = 0.0

    @property
    def total_old(self) -> int:
        return len(self.fixed_findings) + len(self.persistent_findings)

    @property
    def total_new(self) -> int:
        return len(self.new_findings) + len(self.persistent_findings) + len(self.regression_findings)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "old_session_id": self.old_session_id,
            "new_session_id": self.new_session_id,
            "old_session_name": self.old_session_name,
            "new_session_name": self.new_session_name,
            "old_date": self.old_date,
            "new_date": self.new_date,
            "new_findings": [f.to_dict() for f in self.new_findings],
            "fixed_findings": [f.to_dict() for f in self.fixed_findings],
            "persistent_findings": [f.to_dict() for f in self.persistent_findings],
            "regression_findings": [f.to_dict() for f in self.regression_findings],
            "severity_deltas": [s.to_dict() for s in self.severity_deltas],
            "trend": self.trend.value,
            "risk_score_old": self.risk_score_old,
            "risk_score_new": self.risk_score_new,
            "total_old": self.total_old,
            "total_new": self.total_new,
            "summary": self.summary_text(),
        }

    def summary_text(self) -> str:
        """One-line summary of changes."""
        parts = []
        if self.new_findings:
            parts.append(f"+{len(self.new_findings)} new")
        if self.fixed_findings:
            parts.append(f"-{len(self.fixed_findings)} fixed")
        if self.persistent_findings:
            parts.append(f"{len(self.persistent_findings)} persistent")
        if self.regression_findings:
            parts.append(f"{len(self.regression_findings)} regressions")
        return ", ".join(parts) if parts else "No changes detected"

    def to_markdown(self) -> str:
        """Render the diff report as Markdown."""
        old_ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(self.old_date)) if self.old_date else "Unknown"
        new_ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(self.new_date)) if self.new_date else "Unknown"

        lines = [
            f"# Assessment Diff Report — {self.target}",
            "",
            "## Comparison Overview",
            "",
            "| | Baseline | Current |",
            "|---|---|---|",
            f"| **Session** | {self.old_session_name or self.old_session_id} | {self.new_session_name or self.new_session_id} |",
            f"| **Date** | {old_ts} | {new_ts} |",
            f"| **Total Findings** | {self.total_old} | {self.total_new} |",
            f"| **Risk Score** | {self.risk_score_old:.1f} | {self.risk_score_new:.1f} |",
            "",
            f"**Overall Trend:** {_trend_icon(self.trend)} {self.trend.value}",
            "",
            "## Severity Breakdown",
            "",
            "| Severity | Baseline | Current | Change |",
            "|----------|----------|---------|--------|",
        ]

        for sd in self.severity_deltas:
            lines.append(
                f"| {sd.severity} | {sd.old_count} | {sd.new_count} | {sd.direction} {abs(sd.delta)} |"
            )

        lines.append("")

        # New findings
        if self.new_findings:
            lines.append(f"## 🆕 New Vulnerabilities ({len(self.new_findings)})")
            lines.append("")
            lines.append("These vulnerabilities were **not present** in the baseline assessment.")
            lines.append("")
            for f in self.new_findings:
                lines.append(f"### [{f.severity}] {f.title}")
                lines.append("")
                lines.append(f"{f.description}")
                if f.evidence:
                    lines.append(f"\n**Evidence:** {f.evidence}")
                if f.recommendation:
                    lines.append(f"\n**Recommendation:** {f.recommendation}")
                lines.append("")

        # Fixed findings
        if self.fixed_findings:
            lines.append(f"## ✅ Fixed Vulnerabilities ({len(self.fixed_findings)})")
            lines.append("")
            lines.append("These vulnerabilities were **remediated** since the baseline assessment.")
            lines.append("")
            for f in self.fixed_findings:
                lines.append(f"- ~~[{f.severity}] {f.title}~~")
            lines.append("")

        # Persistent findings
        if self.persistent_findings:
            lines.append(f"## ⚠️ Persistent Vulnerabilities ({len(self.persistent_findings)})")
            lines.append("")
            lines.append("These vulnerabilities remain **unresolved** from the baseline assessment.")
            lines.append("")
            for f in self.persistent_findings:
                sev_change = ""
                if f.old_severity and f.old_severity != f.severity:
                    sev_change = f" (was {f.old_severity})"
                lines.append(f"- [{f.severity}] {f.title}{sev_change}")
            lines.append("")

        # Regressions
        if self.regression_findings:
            lines.append(f"## 🔴 Regressions ({len(self.regression_findings)})")
            lines.append("")
            lines.append("These are findings that reappeared after being previously fixed.")
            lines.append("")
            for f in self.regression_findings:
                lines.append(f"- [{f.severity}] {f.title}")
            lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **New:** {len(self.new_findings)}")
        lines.append(f"- **Fixed:** {len(self.fixed_findings)}")
        lines.append(f"- **Persistent:** {len(self.persistent_findings)}")
        lines.append(f"- **Regressions:** {len(self.regression_findings)}")
        lines.append(f"- **Risk Score Change:** {self.risk_score_old:.1f} → {self.risk_score_new:.1f}")
        lines.append("")

        return "\n".join(lines)


def _trend_icon(trend: TrendDirection) -> str:
    """Return an icon for the trend direction."""
    return {
        TrendDirection.IMPROVED: "📉",
        TrendDirection.DEGRADED: "📈",
        TrendDirection.UNCHANGED: "➡️",
    }.get(trend, "➡️")


# ── Matching Engine ──────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Normalize a string for fuzzy comparison."""
    return text.strip().lower()


def _finding_fingerprint(finding: Dict[str, Any]) -> str:
    """
    Create a fingerprint for a finding to match across assessments.

    Uses title (primary) and falls back to description similarity.
    Normalizes case and whitespace to improve matching.
    """
    title = _normalize(finding.get("title", ""))
    # Use first 80 chars of description as secondary identifier
    desc = _normalize(finding.get("description", ""))[:80]
    tool = _normalize(finding.get("tool", ""))
    return f"{title}|{desc}|{tool}"


def _similarity(fp1: str, fp2: str) -> float:
    """
    Simple token-based similarity between two fingerprints.
    Returns a score between 0.0 and 1.0.
    """
    parts1 = fp1.split("|")
    parts2 = fp2.split("|")

    # Exact title match → high confidence
    if parts1[0] and parts1[0] == parts2[0]:
        return 1.0

    # Token overlap in title
    tokens1 = set(parts1[0].split())
    tokens2 = set(parts2[0].split())
    if not tokens1 or not tokens2:
        return 0.0

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    jaccard = len(intersection) / len(union) if union else 0.0

    # Boost if same tool
    if parts1[2] and parts1[2] == parts2[2]:
        jaccard = min(1.0, jaccard + 0.15)

    return jaccard


MATCH_THRESHOLD = 0.65  # Minimum similarity to consider findings the same


def _match_findings(
    old_findings: List[Dict[str, Any]],
    new_findings: List[Dict[str, Any]],
) -> Tuple[
    List[Tuple[Dict[str, Any], Dict[str, Any]]],  # matched pairs
    List[Dict[str, Any]],  # unmatched old (fixed)
    List[Dict[str, Any]],  # unmatched new
]:
    """
    Match findings between two assessments using fingerprint similarity.

    Returns:
        (matched_pairs, unmatched_old, unmatched_new)
    """
    old_fps = [(_finding_fingerprint(f), f) for f in old_findings]
    new_fps = [(_finding_fingerprint(f), f) for f in new_findings]

    matched_old_indices: set[int] = set()
    matched_new_indices: set[int] = set()
    matched_pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []

    # Build similarity matrix and greedily match best pairs
    scores: List[Tuple[float, int, int]] = []
    for i, (fp_old, _) in enumerate(old_fps):
        for j, (fp_new, _) in enumerate(new_fps):
            sim = _similarity(fp_old, fp_new)
            if sim >= MATCH_THRESHOLD:
                scores.append((sim, i, j))

    # Sort by descending similarity → greedily assign best matches
    scores.sort(key=lambda x: x[0], reverse=True)
    for sim, i, j in scores:
        if i in matched_old_indices or j in matched_new_indices:
            continue
        matched_pairs.append((old_fps[i][1], new_fps[j][1]))
        matched_old_indices.add(i)
        matched_new_indices.add(j)

    unmatched_old = [old_fps[i][1] for i in range(len(old_fps)) if i not in matched_old_indices]
    unmatched_new = [new_fps[j][1] for j in range(len(new_fps)) if j not in matched_new_indices]

    return matched_pairs, unmatched_old, unmatched_new


# ── Risk Score Calculation ───────────────────────────────────────────────────

def _risk_score(findings: List[Dict[str, Any]]) -> float:
    """
    Calculate a numeric risk score from findings.

    Score = sum of severity weights:
      Critical=10, High=7, Medium=4, Low=1, Info=0
    """
    weights = {"critical": 10.0, "high": 7.0, "medium": 4.0, "low": 1.0, "info": 0.0}
    total = 0.0
    for f in findings:
        sev = _normalize(f.get("severity", "info"))
        total += weights.get(sev, 0.0)
    return total


# ── Diff Engine ──────────────────────────────────────────────────────────────

class DiffEngine:
    """
    Compare two security assessments and produce a diff report.

    Usage::

        engine = DiffEngine()
        report = engine.compare(old_session_data, new_session_data)
        print(report.to_markdown())
    """

    def compare(
        self,
        old_session: Dict[str, Any],
        new_session: Dict[str, Any],
    ) -> DiffReport:
        """
        Compare two session data dicts and produce a DiffReport.

        Parameters:
            old_session: Loaded session dict (baseline / older)
            new_session: Loaded session dict (current / newer)

        Returns:
            DiffReport with categorised findings
        """
        old_findings = old_session.get("findings", [])
        new_findings = new_session.get("findings", [])

        # Match findings between sessions
        matched, unmatched_old, unmatched_new = _match_findings(old_findings, new_findings)

        report = DiffReport(
            target=new_session.get("target", old_session.get("target", "Unknown")),
            old_session_id=old_session.get("id", ""),
            new_session_id=new_session.get("id", ""),
            old_session_name=old_session.get("name", ""),
            new_session_name=new_session.get("name", ""),
            old_date=old_session.get("created", 0.0),
            new_date=new_session.get("created", 0.0),
        )

        # Persistent findings (matched in both)
        for old_f, new_f in matched:
            old_sev = old_f.get("severity", "Info")
            new_sev = new_f.get("severity", "Info")
            report.persistent_findings.append(DiffFinding(
                title=new_f.get("title", ""),
                severity=new_sev,
                description=new_f.get("description", ""),
                status=DiffStatus.PERSISTENT,
                evidence=new_f.get("evidence", ""),
                recommendation=new_f.get("recommendation", ""),
                tool=new_f.get("tool", ""),
                old_severity=old_sev if old_sev != new_sev else "",
            ))

        # Fixed findings (in old, not in new)
        for f in unmatched_old:
            report.fixed_findings.append(DiffFinding(
                title=f.get("title", ""),
                severity=f.get("severity", "Info"),
                description=f.get("description", ""),
                status=DiffStatus.FIXED,
                evidence=f.get("evidence", ""),
                recommendation=f.get("recommendation", ""),
                tool=f.get("tool", ""),
            ))

        # New findings (in new, not in old)
        for f in unmatched_new:
            report.new_findings.append(DiffFinding(
                title=f.get("title", ""),
                severity=f.get("severity", "Info"),
                description=f.get("description", ""),
                status=DiffStatus.NEW,
                evidence=f.get("evidence", ""),
                recommendation=f.get("recommendation", ""),
                tool=f.get("tool", ""),
            ))

        # Sort each list by severity (Critical first)
        for lst in (report.new_findings, report.fixed_findings, report.persistent_findings):
            lst.sort(
                key=lambda f: SEVERITY_ORDER.get(_normalize(f.severity), 0),
                reverse=True,
            )

        # Calculate severity deltas
        report.severity_deltas = self._severity_deltas(old_findings, new_findings)

        # Risk scores
        report.risk_score_old = _risk_score(old_findings)
        report.risk_score_new = _risk_score(new_findings)

        # Determine trend
        if report.risk_score_new < report.risk_score_old:
            report.trend = TrendDirection.IMPROVED
        elif report.risk_score_new > report.risk_score_old:
            report.trend = TrendDirection.DEGRADED
        else:
            report.trend = TrendDirection.UNCHANGED

        return report

    def compare_findings_lists(
        self,
        old_findings: List[Dict[str, Any]],
        new_findings: List[Dict[str, Any]],
        target: str = "Unknown",
        old_label: str = "Baseline",
        new_label: str = "Current",
    ) -> DiffReport:
        """
        Compare two raw findings lists directly (without full session data).

        Convenience method when you don't have full session dicts.
        """
        old_session = {
            "id": "baseline",
            "name": old_label,
            "target": target,
            "findings": old_findings,
            "created": 0.0,
        }
        new_session = {
            "id": "current",
            "name": new_label,
            "target": target,
            "findings": new_findings,
            "created": time.time(),
        }
        return self.compare(old_session, new_session)

    @staticmethod
    def _severity_deltas(
        old_findings: List[Dict[str, Any]],
        new_findings: List[Dict[str, Any]],
    ) -> List[SeverityDelta]:
        """Calculate per-severity count changes."""
        def count_by_severity(findings: List[Dict[str, Any]]) -> Dict[str, int]:
            counts: Dict[str, int] = {}
            for f in findings:
                sev = f.get("severity", "Info")
                counts[sev] = counts.get(sev, 0) + 1
            return counts

        old_counts = count_by_severity(old_findings)
        new_counts = count_by_severity(new_findings)

        all_sevs = sorted(
            set(old_counts.keys()) | set(new_counts.keys()),
            key=lambda s: SEVERITY_ORDER.get(_normalize(s), 0),
            reverse=True,
        )

        return [
            SeverityDelta(
                severity=sev,
                old_count=old_counts.get(sev, 0),
                new_count=new_counts.get(sev, 0),
            )
            for sev in all_sevs
        ]


# ── Session Loader Utility ───────────────────────────────────────────────────

def load_session_findings(session_id: str, sessions_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Load a session from disk and return its data dict.

    Searches by exact ID or partial match.
    """
    from hackbot.config import SESSIONS_DIR
    sdir = sessions_dir or SESSIONS_DIR
    sdir = Path(sdir)

    if not sdir.exists():
        return None

    # Exact match
    path = sdir / f"{session_id}.json"
    if path.exists():
        try:
            with open(path) as f:
                data = json.load(f)
                return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, IOError):
            return None

    # Partial match
    matches = list(sdir.glob(f"*{session_id}*.json"))
    if matches:
        try:
            with open(matches[0]) as f:
                data = json.load(f)
                return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, IOError):
            return None

    return None


def list_agent_sessions(sessions_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """List agent sessions that have findings, sorted newest first."""
    from hackbot.config import SESSIONS_DIR
    sdir = sessions_dir or SESSIONS_DIR
    sdir = Path(sdir)

    if not sdir.exists():
        return []

    sessions = []
    for f in sdir.glob("*.json"):
        try:
            with open(f) as fh:
                data = json.load(fh)
            if data.get("mode") == "agent" and data.get("findings"):
                sessions.append({
                    "id": data.get("id", f.stem),
                    "name": data.get("name", f.stem),
                    "target": data.get("target", ""),
                    "created": data.get("created", 0.0),
                    "updated": data.get("updated", 0.0),
                    "finding_count": len(data.get("findings", [])),
                })
        except (json.JSONDecodeError, IOError, KeyError):
            continue

    sessions.sort(key=lambda s: s.get("updated", 0), reverse=True)
    return sessions
