"""
Vulnerability Database
======================
Local SQLite database for tracking all findings across assessments.

Features:
  - Persistent storage of every finding ever discovered
  - Query history across all assessments
  - Track remediation status (open / in_progress / resolved / accepted / false_positive)
  - Calculate risk scores and severity trends over time
  - Deduplication: same finding on same target is tracked, not duplicated
  - Assessment metadata: target, scope, timestamps, tool history

Schema:
  assessments  — one row per agent run (target, scope, timestamps)
  findings     — every finding with FK to assessment
  remediation  — status changes / notes per finding
  risk_scores  — periodic risk snapshot per target

Usage::

    from hackbot.core.vulndb import VulnDB
    db = VulnDB()
    assessment_id = db.create_assessment("192.168.1.1", "network")
    db.add_finding(assessment_id, finding_dict)
    db.update_status(finding_id, "resolved", "Patched in v2.1")
    stats = db.get_stats()

Developed by Yashab Alam
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from hackbot.config import DATA_DIR, ensure_dirs

# ── Database location ────────────────────────────────────────────────────────

DB_FILE = DATA_DIR / "findings.db"

# ── Remediation statuses ─────────────────────────────────────────────────────

VALID_STATUSES = ("open", "in_progress", "resolved", "accepted", "false_positive")

# ── Schema ───────────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS assessments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    target          TEXT    NOT NULL,
    scope           TEXT    DEFAULT '',
    started_at      REAL    NOT NULL,
    finished_at     REAL    DEFAULT NULL,
    total_steps     INTEGER DEFAULT 0,
    total_findings  INTEGER DEFAULT 0,
    tools_used      TEXT    DEFAULT '[]',
    notes           TEXT    DEFAULT '',
    created_at      REAL    NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE IF NOT EXISTS findings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id   INTEGER NOT NULL REFERENCES assessments(id),
    fingerprint     TEXT    NOT NULL,
    title           TEXT    NOT NULL,
    severity        TEXT    NOT NULL DEFAULT 'Info',
    description     TEXT    DEFAULT '',
    evidence        TEXT    DEFAULT '',
    recommendation  TEXT    DEFAULT '',
    tool            TEXT    DEFAULT '',
    target          TEXT    DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'open',
    risk_score      REAL    DEFAULT 0.0,
    cve_ids         TEXT    DEFAULT '[]',
    tags            TEXT    DEFAULT '[]',
    found_at        REAL    NOT NULL,
    resolved_at     REAL    DEFAULT NULL,
    created_at      REAL    NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE IF NOT EXISTS remediation_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id  INTEGER NOT NULL REFERENCES findings(id),
    old_status  TEXT    NOT NULL,
    new_status  TEXT    NOT NULL,
    note        TEXT    DEFAULT '',
    changed_by  TEXT    DEFAULT 'system',
    changed_at  REAL   NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE IF NOT EXISTS risk_snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    target      TEXT    NOT NULL,
    critical    INTEGER DEFAULT 0,
    high        INTEGER DEFAULT 0,
    medium      INTEGER DEFAULT 0,
    low         INTEGER DEFAULT 0,
    info        INTEGER DEFAULT 0,
    risk_score  REAL    DEFAULT 0.0,
    open_count  INTEGER DEFAULT 0,
    total_count INTEGER DEFAULT 0,
    snapshot_at REAL    NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_findings_assessment ON findings(assessment_id);
CREATE INDEX IF NOT EXISTS idx_findings_target     ON findings(target);
CREATE INDEX IF NOT EXISTS idx_findings_severity   ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_status     ON findings(status);
CREATE INDEX IF NOT EXISTS idx_findings_fingerprint ON findings(fingerprint);
CREATE INDEX IF NOT EXISTS idx_remediation_finding ON remediation_log(finding_id);
CREATE INDEX IF NOT EXISTS idx_risk_target         ON risk_snapshots(target);
"""

# ── Severity weights for risk scoring ────────────────────────────────────────

SEVERITY_WEIGHTS = {
    "Critical": 10.0,
    "High": 7.5,
    "Medium": 5.0,
    "Low": 2.5,
    "Info": 0.5,
}


def _fingerprint(target: str, title: str, severity: str) -> str:
    """Generate a stable fingerprint for deduplication.

    Same target + title + severity = same finding across assessments.
    """
    raw = f"{target.lower().strip()}|{title.lower().strip()}|{severity.lower().strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Dataclasses for query results ────────────────────────────────────────────

@dataclass
class VulnRecord:
    """A single finding record from the database."""
    id: int
    assessment_id: int
    fingerprint: str
    title: str
    severity: str
    description: str
    evidence: str
    recommendation: str
    tool: str
    target: str
    status: str
    risk_score: float
    cve_ids: List[str]
    tags: List[str]
    found_at: float
    resolved_at: Optional[float]
    created_at: float

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "VulnRecord":
        return cls(
            id=row["id"],
            assessment_id=row["assessment_id"],
            fingerprint=row["fingerprint"],
            title=row["title"],
            severity=row["severity"],
            description=row["description"],
            evidence=row["evidence"],
            recommendation=row["recommendation"],
            tool=row["tool"],
            target=row["target"],
            status=row["status"],
            risk_score=row["risk_score"],
            cve_ids=json.loads(row["cve_ids"] or "[]"),
            tags=json.loads(row["tags"] or "[]"),
            found_at=row["found_at"],
            resolved_at=row["resolved_at"],
            created_at=row["created_at"],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "assessment_id": self.assessment_id,
            "fingerprint": self.fingerprint,
            "title": self.title,
            "severity": self.severity,
            "description": self.description,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "tool": self.tool,
            "target": self.target,
            "status": self.status,
            "risk_score": self.risk_score,
            "cve_ids": self.cve_ids,
            "tags": self.tags,
            "found_at": self.found_at,
            "resolved_at": self.resolved_at,
            "created_at": self.created_at,
        }


@dataclass
class AssessmentRecord:
    """An assessment record from the database."""
    id: int
    target: str
    scope: str
    started_at: float
    finished_at: Optional[float]
    total_steps: int
    total_findings: int
    tools_used: List[str]
    notes: str
    created_at: float

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "AssessmentRecord":
        return cls(
            id=row["id"],
            target=row["target"],
            scope=row["scope"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            total_steps=row["total_steps"],
            total_findings=row["total_findings"],
            tools_used=json.loads(row["tools_used"] or "[]"),
            notes=row["notes"],
            created_at=row["created_at"],
        )


@dataclass
class DBStats:
    """Overall vulnerability database statistics."""
    total_assessments: int = 0
    total_findings: int = 0
    open_findings: int = 0
    resolved_findings: int = 0
    in_progress_findings: int = 0
    false_positive_findings: int = 0
    accepted_findings: int = 0
    by_severity: Dict[str, int] = field(default_factory=dict)
    by_target: Dict[str, int] = field(default_factory=dict)
    overall_risk_score: float = 0.0
    unique_targets: int = 0
    avg_findings_per_assessment: float = 0.0
    oldest_open_finding_days: float = 0.0
    last_assessment_at: Optional[float] = None


# ── VulnDB ───────────────────────────────────────────────────────────────────

class VulnDB:
    """Local SQLite vulnerability database for HackBot.

    Thread-safe — each operation opens its own connection via ``_connect()``.
    """

    def __init__(self, db_path: Optional[Path] = None):
        ensure_dirs()
        self.db_path = db_path or DB_FILE
        self._init_db()

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self):
        """Context manager that yields a SQLite connection with WAL mode."""
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── Assessment CRUD ──────────────────────────────────────────────────

    def create_assessment(
        self,
        target: str,
        scope: str = "",
        tools_used: Optional[List[str]] = None,
        notes: str = "",
    ) -> int:
        """Record a new assessment. Returns the assessment ID."""
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO assessments (target, scope, started_at, tools_used, notes)
                   VALUES (?, ?, ?, ?, ?)""",
                (target, scope, time.time(), json.dumps(tools_used or []), notes),
            )
            return int(cur.lastrowid or 0)

    def finish_assessment(
        self,
        assessment_id: int,
        total_steps: int = 0,
        total_findings: int = 0,
    ) -> None:
        """Mark an assessment as finished."""
        with self._connect() as conn:
            conn.execute(
                """UPDATE assessments
                   SET finished_at = ?, total_steps = ?, total_findings = ?
                   WHERE id = ?""",
                (time.time(), total_steps, total_findings, assessment_id),
            )

    def get_assessment(self, assessment_id: int) -> Optional[AssessmentRecord]:
        """Retrieve a single assessment by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM assessments WHERE id = ?", (assessment_id,)
            ).fetchone()
            return AssessmentRecord.from_row(row) if row else None

    def list_assessments(
        self,
        target: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[AssessmentRecord]:
        """List assessments, optionally filtered by target."""
        with self._connect() as conn:
            if target:
                rows = conn.execute(
                    """SELECT * FROM assessments WHERE target LIKE ?
                       ORDER BY started_at DESC LIMIT ? OFFSET ?""",
                    (f"%{target}%", limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM assessments
                       ORDER BY started_at DESC LIMIT ? OFFSET ?""",
                    (limit, offset),
                ).fetchall()
            return [AssessmentRecord.from_row(r) for r in rows]

    # ── Finding CRUD ─────────────────────────────────────────────────────

    def add_finding(
        self,
        assessment_id: int,
        finding: Dict[str, Any],
        target: str = "",
    ) -> int:
        """Add a finding to the database.

        If a finding with the same fingerprint already exists for this target,
        updates it instead of creating a duplicate.

        Args:
            assessment_id: The assessment this finding belongs to.
            finding: Dict with keys: title, severity, description, evidence,
                     recommendation, tool, timestamp.
            target: The target host/domain.

        Returns:
            The finding ID (new or existing).
        """
        title = finding.get("title", "Untitled")
        severity = finding.get("severity", "Info")
        fp = _fingerprint(target, title, severity)

        with self._connect() as conn:
            # Check for existing finding with same fingerprint + target
            existing = conn.execute(
                "SELECT id, status FROM findings WHERE fingerprint = ? AND target = ?",
                (fp, target),
            ).fetchone()

            if existing:
                # Update existing — refresh evidence / assessment link
                conn.execute(
                    """UPDATE findings
                       SET evidence = ?, recommendation = ?, tool = ?,
                           assessment_id = ?, description = ?
                       WHERE id = ?""",
                    (
                        finding.get("evidence", ""),
                        finding.get("recommendation", ""),
                        finding.get("tool", ""),
                        assessment_id,
                        finding.get("description", ""),
                        existing["id"],
                    ),
                )
                # If it was resolved but found again, reopen
                if existing["status"] == "resolved":
                    self._change_status_internal(
                        conn, existing["id"], existing["status"], "open",
                        "Re-opened: found again in new assessment",
                    )
                return int(existing["id"])

            risk = SEVERITY_WEIGHTS.get(severity, 0.5)
            cve_ids = finding.get("cve_ids", [])
            tags = finding.get("tags", [])

            cur = conn.execute(
                """INSERT INTO findings
                   (assessment_id, fingerprint, title, severity, description,
                    evidence, recommendation, tool, target, risk_score,
                    cve_ids, tags, found_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    assessment_id, fp, title, severity,
                    finding.get("description", ""),
                    finding.get("evidence", ""),
                    finding.get("recommendation", ""),
                    finding.get("tool", ""),
                    target,
                    risk,
                    json.dumps(cve_ids),
                    json.dumps(tags),
                    finding.get("timestamp", time.time()),
                ),
            )
            return int(cur.lastrowid or 0)

    def add_findings_bulk(
        self,
        assessment_id: int,
        findings: List[Dict[str, Any]],
        target: str = "",
    ) -> List[int]:
        """Add multiple findings at once. Returns list of finding IDs."""
        return [self.add_finding(assessment_id, f, target) for f in findings]

    def get_finding(self, finding_id: int) -> Optional[VulnRecord]:
        """Retrieve a single finding by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM findings WHERE id = ?", (finding_id,)
            ).fetchone()
            return VulnRecord.from_row(row) if row else None

    def search_findings(
        self,
        query: str = "",
        target: str = "",
        severity: str = "",
        status: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> List[VulnRecord]:
        """Search findings with flexible filters."""
        conditions = []
        params: List[Any] = []

        if query:
            conditions.append("(title LIKE ? OR description LIKE ? OR evidence LIKE ?)")
            params.extend([f"%{query}%"] * 3)
        if target:
            conditions.append("target LIKE ?")
            params.append(f"%{target}%")
        if severity:
            conditions.append("severity = ?")
            params.append(severity)
        if status:
            conditions.append("status = ?")
            params.append(status)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM findings {where} ORDER BY found_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [VulnRecord.from_row(r) for r in rows]

    def get_findings_by_assessment(self, assessment_id: int) -> List[VulnRecord]:
        """Get all findings for a specific assessment."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM findings WHERE assessment_id = ? ORDER BY found_at",
                (assessment_id,),
            ).fetchall()
            return [VulnRecord.from_row(r) for r in rows]

    def get_findings_by_target(self, target: str) -> List[VulnRecord]:
        """Get all findings for a target."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM findings WHERE target = ? ORDER BY found_at DESC",
                (target,),
            ).fetchall()
            return [VulnRecord.from_row(r) for r in rows]

    # ── Remediation / Status ─────────────────────────────────────────────

    def update_status(
        self,
        finding_id: int,
        new_status: str,
        note: str = "",
        changed_by: str = "user",
    ) -> bool:
        """Update the remediation status of a finding.

        Valid statuses: open, in_progress, resolved, accepted, false_positive
        """
        if new_status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{new_status}'. "
                f"Valid: {', '.join(VALID_STATUSES)}"
            )

        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, status FROM findings WHERE id = ?", (finding_id,)
            ).fetchone()
            if not row:
                return False

            old_status = row["status"]
            if old_status == new_status:
                return True  # No change needed

            resolved_at = time.time() if new_status == "resolved" else None

            conn.execute(
                """UPDATE findings SET status = ?, resolved_at = COALESCE(?, resolved_at)
                   WHERE id = ?""",
                (new_status, resolved_at, finding_id),
            )
            self._change_status_internal(
                conn, finding_id, old_status, new_status, note, changed_by
            )
            return True

    def _change_status_internal(
        self,
        conn,
        finding_id: int,
        old_status: str,
        new_status: str,
        note: str = "",
        changed_by: str = "system",
    ) -> None:
        """Record a status change in the remediation log."""
        conn.execute(
            """UPDATE findings SET status = ? WHERE id = ?""",
            (new_status, finding_id),
        )
        conn.execute(
            """INSERT INTO remediation_log (finding_id, old_status, new_status, note, changed_by)
               VALUES (?, ?, ?, ?, ?)""",
            (finding_id, old_status, new_status, note, changed_by),
        )

    def get_remediation_log(self, finding_id: int) -> List[Dict[str, Any]]:
        """Get the full remediation history of a finding."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM remediation_log WHERE finding_id = ?
                   ORDER BY changed_at""",
                (finding_id,),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "finding_id": r["finding_id"],
                    "old_status": r["old_status"],
                    "new_status": r["new_status"],
                    "note": r["note"],
                    "changed_by": r["changed_by"],
                    "changed_at": r["changed_at"],
                }
                for r in rows
            ]

    # ── Risk Scoring ─────────────────────────────────────────────────────

    def calculate_risk_score(self, target: str = "") -> float:
        """Calculate overall risk score for a target or globally.

        Risk = sum of severity weights for all open findings.
        """
        with self._connect() as conn:
            if target:
                rows = conn.execute(
                    "SELECT severity FROM findings WHERE target = ? AND status = 'open'",
                    (target,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT severity FROM findings WHERE status = 'open'"
                ).fetchall()

            return sum(SEVERITY_WEIGHTS.get(r["severity"], 0.5) for r in rows)

    def take_risk_snapshot(self, target: str) -> Dict[str, Any]:
        """Take a point-in-time risk snapshot for a target."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT severity, status FROM findings WHERE target = ?",
                (target,),
            ).fetchall()

            counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
            open_count = 0
            for r in rows:
                sev = r["severity"]
                if sev in counts:
                    counts[sev] += 1
                if r["status"] == "open":
                    open_count += 1

            risk = sum(
                SEVERITY_WEIGHTS.get(sev, 0.5) * count
                for sev, count in counts.items()
            )

            conn.execute(
                """INSERT INTO risk_snapshots
                   (target, critical, high, medium, low, info,
                    risk_score, open_count, total_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    target,
                    counts["Critical"], counts["High"], counts["Medium"],
                    counts["Low"], counts["Info"],
                    risk, open_count, len(rows),
                ),
            )

            return {
                "target": target,
                "critical": counts["Critical"],
                "high": counts["High"],
                "medium": counts["Medium"],
                "low": counts["Low"],
                "info": counts["Info"],
                "risk_score": risk,
                "open": open_count,
                "total": len(rows),
            }

    def get_risk_history(
        self, target: str, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Get risk score history for a target (for trend charts)."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM risk_snapshots WHERE target = ?
                   ORDER BY snapshot_at DESC LIMIT ?""",
                (target, limit),
            ).fetchall()
            return [
                {
                    "target": r["target"],
                    "critical": r["critical"],
                    "high": r["high"],
                    "medium": r["medium"],
                    "low": r["low"],
                    "info": r["info"],
                    "risk_score": r["risk_score"],
                    "open": r["open_count"],
                    "total": r["total_count"],
                    "snapshot_at": r["snapshot_at"],
                }
                for r in rows
            ]

    # ── Statistics ───────────────────────────────────────────────────────

    def get_stats(self, target: str = "") -> DBStats:
        """Get comprehensive vulnerability database statistics."""
        stats = DBStats()

        with self._connect() as conn:
            # Total assessments
            if target:
                row = conn.execute(
                    "SELECT COUNT(*) as c FROM assessments WHERE target LIKE ?",
                    (f"%{target}%",),
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) as c FROM assessments").fetchone()
            stats.total_assessments = row["c"]

            # Finding counts by status
            where = "WHERE target LIKE ?" if target else ""
            params: List[Any] = [f"%{target}%"] if target else []

            row = conn.execute(
                f"SELECT COUNT(*) as c FROM findings {where}", params
            ).fetchone()
            stats.total_findings = row["c"]

            for status_val in VALID_STATUSES:
                cond = f"WHERE status = ?" + (f" AND target LIKE ?" if target else "")
                p = [status_val] + ([f"%{target}%"] if target else [])
                row = conn.execute(
                    f"SELECT COUNT(*) as c FROM findings {cond}", p
                ).fetchone()
                setattr(stats, f"{status_val}_findings", row["c"])

            # By severity
            rows = conn.execute(
                f"""SELECT severity, COUNT(*) as c FROM findings
                    {where} GROUP BY severity""",
                params,
            ).fetchall()
            stats.by_severity = {r["severity"]: r["c"] for r in rows}

            # By target (top 20)
            rows = conn.execute(
                """SELECT target, COUNT(*) as c FROM findings
                   GROUP BY target ORDER BY c DESC LIMIT 20"""
            ).fetchall()
            stats.by_target = {r["target"]: r["c"] for r in rows}

            # Unique targets
            row = conn.execute(
                "SELECT COUNT(DISTINCT target) as c FROM findings"
            ).fetchone()
            stats.unique_targets = row["c"]

            # Risk score
            stats.overall_risk_score = self.calculate_risk_score(target)

            # Average findings per assessment
            if stats.total_assessments > 0:
                stats.avg_findings_per_assessment = (
                    stats.total_findings / stats.total_assessments
                )

            # Oldest open finding
            row = conn.execute(
                f"""SELECT MIN(found_at) as oldest FROM findings
                    WHERE status = 'open'""" + (
                    " AND target LIKE ?" if target else ""
                ),
                [f"%{target}%"] if target else [],
            ).fetchone()
            if row["oldest"]:
                stats.oldest_open_finding_days = (
                    (time.time() - row["oldest"]) / 86400
                )

            # Last assessment
            row = conn.execute(
                "SELECT MAX(started_at) as last_at FROM assessments"
            ).fetchone()
            stats.last_assessment_at = row["last_at"]

        return stats

    # ── Formatting ───────────────────────────────────────────────────────

    def format_stats(self, target: str = "") -> str:
        """Format stats as a readable report string."""
        s = self.get_stats(target)
        severity_icons = {
            "Critical": "🔴", "High": "🟠", "Medium": "🟡",
            "Low": "🔵", "Info": "⚪",
        }

        lines = [
            "📊 **Vulnerability Database Statistics**\n",
            f"**Assessments:** {s.total_assessments}",
            f"**Unique targets:** {s.unique_targets}",
            f"**Total findings:** {s.total_findings}",
            f"**Risk score:** {s.overall_risk_score:.1f}\n",
        ]

        if s.by_severity:
            lines.append("**By Severity:**")
            for sev in ("Critical", "High", "Medium", "Low", "Info"):
                count = s.by_severity.get(sev, 0)
                if count > 0:
                    icon = severity_icons.get(sev, "•")
                    lines.append(f"  {icon} {sev}: {count}")
            lines.append("")

        lines.append("**By Status:**")
        lines.append(f"  🔓 Open: {s.open_findings}")
        lines.append(f"  🔧 In Progress: {s.in_progress_findings}")
        lines.append(f"  ✅ Resolved: {s.resolved_findings}")
        lines.append(f"  🤝 Accepted: {s.accepted_findings}")
        lines.append(f"  ❌ False Positive: {s.false_positive_findings}")

        if s.oldest_open_finding_days > 0:
            lines.append(f"\n**Oldest open finding:** {s.oldest_open_finding_days:.0f} days")

        if s.by_target:
            lines.append("\n**Top Targets:**")
            for t, c in list(s.by_target.items())[:10]:
                lines.append(f"  • {t}: {c} findings")

        return "\n".join(lines)

    def format_findings_table(
        self,
        findings: List[VulnRecord],
        show_target: bool = True,
    ) -> str:
        """Format a list of findings as a readable table."""
        if not findings:
            return "No findings."

        severity_icons = {
            "Critical": "🔴", "High": "🟠", "Medium": "🟡",
            "Low": "🔵", "Info": "⚪",
        }
        status_icons = {
            "open": "🔓", "in_progress": "🔧", "resolved": "✅",
            "accepted": "🤝", "false_positive": "❌",
        }

        lines = [f"**Findings ({len(findings)})**\n"]
        for f in findings:
            sev_icon = severity_icons.get(f.severity, "•")
            st_icon = status_icons.get(f.status, "•")
            target_str = f" [{f.target}]" if show_target else ""
            lines.append(
                f"{sev_icon} #{f.id} **{f.title}** [{f.severity}] "
                f"{st_icon} {f.status}{target_str}"
            )
            if f.description:
                desc = f.description[:120] + "..." if len(f.description) > 120 else f.description
                lines.append(f"   {desc}")
            lines.append("")

        return "\n".join(lines)

    # ── Cleanup ──────────────────────────────────────────────────────────

    def delete_finding(self, finding_id: int) -> bool:
        """Delete a finding and its remediation log."""
        with self._connect() as conn:
            conn.execute("DELETE FROM remediation_log WHERE finding_id = ?", (finding_id,))
            cur = conn.execute("DELETE FROM findings WHERE id = ?", (finding_id,))
            return bool(cur.rowcount > 0)

    def delete_assessment(self, assessment_id: int) -> bool:
        """Delete an assessment and all its findings."""
        with self._connect() as conn:
            finding_ids = conn.execute(
                "SELECT id FROM findings WHERE assessment_id = ?", (assessment_id,)
            ).fetchall()
            for row in finding_ids:
                conn.execute("DELETE FROM remediation_log WHERE finding_id = ?", (row["id"],))
            conn.execute("DELETE FROM findings WHERE assessment_id = ?", (assessment_id,))
            cur = conn.execute("DELETE FROM assessments WHERE id = ?", (assessment_id,))
            return bool(cur.rowcount > 0)

    def purge_all(self) -> int:
        """Delete everything. Returns total rows deleted. USE WITH CAUTION."""
        with self._connect() as conn:
            c1 = conn.execute("DELETE FROM remediation_log").rowcount
            c2 = conn.execute("DELETE FROM findings").rowcount
            c3 = conn.execute("DELETE FROM assessments").rowcount
            c4 = conn.execute("DELETE FROM risk_snapshots").rowcount
            return int(c1 + c2 + c3 + c4)

    @property
    def db_size(self) -> str:
        """Human-readable database file size."""
        if not self.db_path.exists():
            return "0 B"
        size = float(self.db_path.stat().st_size)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
