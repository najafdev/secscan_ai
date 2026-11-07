"""
HackBot Multi-Target Campaign System
======================================
Define a scope with multiple hosts or URLs and run coordinated security
assessments across all of them.

A **campaign** is a named collection of targets with shared configuration
(scope rules, instructions, concurrency) that the agent assesses one-by-one,
aggregating findings into a unified campaign report.

Usage (CLI)::

    /campaign new "Internal Audit Q1" 192.168.1.1 192.168.1.2 app.example.com
    /campaign start
    /campaign status
    /campaign findings
    /campaign report

Usage (Agent)::

    The agent can reference the campaign context to correlate findings across
    targets and prioritize based on the overall attack surface.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from hackbot.config import DATA_DIR

logger = logging.getLogger(__name__)

# ── Campaign Storage ─────────────────────────────────────────────────────────

CAMPAIGNS_DIR = DATA_DIR / "campaigns"


def ensure_campaigns_dir() -> Path:
    """Create the campaigns directory if it doesn't exist."""
    CAMPAIGNS_DIR.mkdir(parents=True, exist_ok=True)
    return CAMPAIGNS_DIR


# ── Enums ────────────────────────────────────────────────────────────────────

class TargetStatus(str, Enum):
    """Status of a single target within a campaign."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class CampaignStatus(str, Enum):
    """Overall campaign status."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABORTED = "aborted"


# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class TargetResult:
    """
    Findings and metadata for a single target in the campaign.

    Attributes:
        target: Host/URL string.
        status: Current assessment status.
        findings: List of finding dicts (same format as AgentMode.Finding.to_dict()).
        tool_history: List of tool result dicts from the assessment.
        session_id: Agent session ID for this target's assessment.
        started_at: Timestamp when assessment began.
        completed_at: Timestamp when assessment finished.
        error: Error message if status is FAILED.
        steps: Number of agent steps executed.
        summary: AI-generated summary for this target.
    """
    target: str
    status: TargetStatus = TargetStatus.PENDING
    findings: List[Dict[str, Any]] = field(default_factory=list)
    tool_history: List[Dict[str, Any]] = field(default_factory=list)
    session_id: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    error: str = ""
    steps: int = 0
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "status": self.status.value,
            "findings": self.findings,
            "tool_history": self.tool_history,
            "session_id": self.session_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "steps": self.steps,
            "summary": self.summary,
            "finding_count": len(self.findings),
            "duration": round(self.completed_at - self.started_at, 1) if self.completed_at else 0,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TargetResult":
        return cls(
            target=data["target"],
            status=TargetStatus(data.get("status", "pending")),
            findings=data.get("findings", []),
            tool_history=data.get("tool_history", []),
            session_id=data.get("session_id", ""),
            started_at=data.get("started_at", 0.0),
            completed_at=data.get("completed_at", 0.0),
            error=data.get("error", ""),
            steps=data.get("steps", 0),
            summary=data.get("summary", ""),
        )


@dataclass
class Campaign:
    """
    A multi-target assessment campaign.

    Attributes:
        id: Unique campaign identifier.
        name: Human-readable campaign name.
        targets: Ordered list of target strings (hosts/URLs).
        results: Per-target results keyed by target string.
        status: Overall campaign status.
        scope: Shared scope rules for all targets.
        instructions: Shared instructions for the agent.
        created_at: Campaign creation timestamp.
        updated_at: Last update timestamp.
        current_target_idx: Index of the currently active target.
        max_steps_per_target: Maximum agent steps per target.
        tags: Optional tags for organizing campaigns.
    """
    id: str = field(default_factory=lambda: f"campaign_{int(time.time() * 1000)}")
    name: str = ""
    targets: List[str] = field(default_factory=list)
    results: Dict[str, TargetResult] = field(default_factory=dict)
    status: CampaignStatus = CampaignStatus.DRAFT
    scope: str = ""
    instructions: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    current_target_idx: int = -1
    max_steps_per_target: int = 50
    tags: List[str] = field(default_factory=list)

    # ── Target Management ────────────────────────────────────────────────

    def add_target(self, target: str) -> bool:
        """Add a target to the campaign. Returns False if duplicate."""
        normalized = target.strip()
        if not normalized:
            return False
        if normalized in self.targets:
            return False
        self.targets.append(normalized)
        self.results[normalized] = TargetResult(target=normalized)
        self.updated_at = time.time()
        return True

    def add_targets(self, targets: List[str]) -> int:
        """Add multiple targets. Returns count of successfully added."""
        return sum(1 for t in targets if self.add_target(t))

    def remove_target(self, target: str) -> bool:
        """Remove a target from the campaign."""
        if target in self.targets:
            self.targets.remove(target)
            self.results.pop(target, None)
            self.updated_at = time.time()
            return True
        return False

    def clear_targets(self) -> None:
        """Remove all targets."""
        self.targets.clear()
        self.results.clear()
        self.updated_at = time.time()

    # ── Status Queries ───────────────────────────────────────────────────

    @property
    def target_count(self) -> int:
        return len(self.targets)

    @property
    def completed_count(self) -> int:
        return sum(
            1 for r in self.results.values()
            if r.status in (TargetStatus.COMPLETED, TargetStatus.FAILED, TargetStatus.SKIPPED)
        )

    @property
    def pending_count(self) -> int:
        return sum(1 for r in self.results.values() if r.status == TargetStatus.PENDING)

    @property
    def running_target(self) -> Optional[str]:
        """Return the currently running target, if any."""
        for r in self.results.values():
            if r.status == TargetStatus.RUNNING:
                return r.target
        return None

    @property
    def current_target(self) -> Optional[str]:
        """Return the current target based on index."""
        if 0 <= self.current_target_idx < len(self.targets):
            return self.targets[self.current_target_idx]
        return None

    @property
    def next_pending_target(self) -> Optional[str]:
        """Return the next target that hasn't been assessed yet."""
        for t in self.targets:
            if self.results.get(t, TargetResult(target=t)).status == TargetStatus.PENDING:
                return t
        return None

    @property
    def is_complete(self) -> bool:
        """True if all targets have been assessed."""
        return all(
            r.status in (TargetStatus.COMPLETED, TargetStatus.FAILED, TargetStatus.SKIPPED)
            for r in self.results.values()
        ) and len(self.targets) > 0

    @property
    def total_findings(self) -> int:
        return sum(len(r.findings) for r in self.results.values())

    @property
    def total_duration(self) -> float:
        return sum(
            (r.completed_at - r.started_at)
            for r in self.results.values()
            if r.completed_at > 0
        )

    def progress_pct(self) -> float:
        """Return completion percentage (0-100)."""
        if not self.targets:
            return 0.0
        return round((self.completed_count / self.target_count) * 100, 1)

    # ── Finding Aggregation ──────────────────────────────────────────────

    def all_findings(self) -> List[Dict[str, Any]]:
        """Return all findings across all targets, tagged with source target."""
        findings = []
        for t, r in self.results.items():
            for f in r.findings:
                finding = dict(f)
                finding["campaign_target"] = t
                findings.append(finding)
        return findings

    def findings_by_severity(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group all findings by severity."""
        by_sev: Dict[str, List[Dict[str, Any]]] = {}
        for f in self.all_findings():
            sev = f.get("severity", "Info")
            by_sev.setdefault(sev, []).append(f)
        return by_sev

    def severity_counts(self) -> Dict[str, int]:
        """Count findings per severity across all targets."""
        counts: Dict[str, int] = {}
        for f in self.all_findings():
            sev = f.get("severity", "Info")
            counts[sev] = counts.get(sev, 0) + 1
        return counts

    def findings_by_target(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group findings by target."""
        return {t: r.findings for t, r in self.results.items() if r.findings}

    # ── Serialization ────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "targets": self.targets,
            "results": {t: r.to_dict() for t, r in self.results.items()},
            "status": self.status.value,
            "scope": self.scope,
            "instructions": self.instructions,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "current_target_idx": self.current_target_idx,
            "max_steps_per_target": self.max_steps_per_target,
            "tags": self.tags,
            "target_count": self.target_count,
            "completed_count": self.completed_count,
            "total_findings": self.total_findings,
            "progress_pct": self.progress_pct(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Campaign":
        c = cls(
            id=data["id"],
            name=data.get("name", ""),
            targets=data.get("targets", []),
            status=CampaignStatus(data.get("status", "draft")),
            scope=data.get("scope", ""),
            instructions=data.get("instructions", ""),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            current_target_idx=data.get("current_target_idx", -1),
            max_steps_per_target=data.get("max_steps_per_target", 50),
            tags=data.get("tags", []),
        )
        c.results = {}
        for t, r_data in data.get("results", {}).items():
            c.results[t] = TargetResult.from_dict(r_data)
        return c

    # ── Summary Generation ───────────────────────────────────────────────

    def get_summary_markdown(self) -> str:
        """Generate a markdown summary of the campaign."""
        lines = [f"# Campaign: {self.name or self.id}\n"]
        lines.append(f"**Status:** {self.status.value.upper()}")
        lines.append(f"**Targets:** {self.target_count} | "
                      f"**Completed:** {self.completed_count} | "
                      f"**Progress:** {self.progress_pct()}%")
        lines.append(f"**Total Findings:** {self.total_findings}")
        if self.scope:
            lines.append(f"**Scope:** {self.scope}")
        lines.append("")

        # Severity summary
        counts = self.severity_counts()
        if counts:
            lines.append("## Severity Summary\n")
            for sev in ["Critical", "High", "Medium", "Low", "Info"]:
                if sev in counts:
                    lines.append(f"- **{sev}:** {counts[sev]}")
            lines.append("")

        # Per-target summary
        lines.append("## Targets\n")
        lines.append("| Target | Status | Findings | Steps | Duration |")
        lines.append("|--------|--------|----------|-------|----------|")
        for t in self.targets:
            r = self.results.get(t, TargetResult(target=t))
            dur = f"{r.completed_at - r.started_at:.0f}s" if r.completed_at else "-"
            status_icon = {
                TargetStatus.PENDING: "⏳",
                TargetStatus.RUNNING: "🔄",
                TargetStatus.COMPLETED: "✅",
                TargetStatus.FAILED: "❌",
                TargetStatus.SKIPPED: "⏭️",
            }.get(r.status, "?")
            lines.append(f"| {t} | {status_icon} {r.status.value} | {len(r.findings)} | {r.steps} | {dur} |")
        lines.append("")

        # Critical/High findings details
        critical_high = [
            f for f in self.all_findings()
            if f.get("severity") in ("Critical", "High")
        ]
        if critical_high:
            lines.append("## Critical & High Findings\n")
            for f in critical_high:
                tag = f.get("campaign_target", "?")
                lines.append(f"### [{f.get('severity')}] {f.get('title', 'Untitled')}")
                lines.append(f"**Target:** {tag}\n")
                lines.append(f"{f.get('description', '')}")
                if f.get("recommendation"):
                    lines.append(f"\n**Recommendation:** {f['recommendation']}")
                lines.append("")

        return "\n".join(lines)

    def get_agent_context(self, current_target: str) -> str:
        """
        Generate context for the agent when assessing a specific target
        within the campaign, including cross-target intelligence.
        """
        lines = [
            f"\n--- CAMPAIGN CONTEXT ---",
            f"Campaign: {self.name or self.id}",
            f"Target {self.targets.index(current_target) + 1} of {self.target_count}: {current_target}",
        ]

        # Share findings from previously assessed targets
        prev_findings: List[str] = []
        for t in self.targets:
            if t == current_target:
                break
            r = self.results.get(t)
            if r and r.findings:
                prev_findings.extend(
                    f"  - [{f.get('severity', '?')}] {f.get('title', '?')} (on {t})"
                    for f in r.findings
                )

        if prev_findings:
            lines.append(f"\nPrevious targets assessed ({len(prev_findings)} findings found):")
            lines.extend(prev_findings[:30])  # Cap at 30 to avoid prompt bloat
            if len(prev_findings) > 30:
                lines.append(f"  ... and {len(prev_findings) - 30} more")
            lines.append("\nUse this intelligence to guide your assessment — "
                         "look for similar vulnerabilities and shared infrastructure.")
        else:
            lines.append("\nThis is the first target in the campaign. "
                         "Document your findings thoroughly to inform subsequent assessments.")

        lines.append("--- END CAMPAIGN CONTEXT ---\n")
        return "\n".join(lines)


# ── Campaign Manager ─────────────────────────────────────────────────────────

class CampaignManager:
    """
    Manages campaign lifecycle: create, persist, run, and report.

    Does NOT own AgentMode instances — the caller (CLI or GUI) is responsible
    for creating and driving the agent.  CampaignManager tracks state and
    provides the orchestration logic.
    """

    def __init__(self, campaigns_dir: Optional[Path] = None):
        self.campaigns_dir = campaigns_dir or CAMPAIGNS_DIR
        self.campaigns_dir.mkdir(parents=True, exist_ok=True)
        self.active_campaign: Optional[Campaign] = None

    # ── CRUD ─────────────────────────────────────────────────────────────

    def create_campaign(
        self,
        name: str,
        targets: List[str],
        scope: str = "",
        instructions: str = "",
        max_steps_per_target: int = 50,
        tags: Optional[List[str]] = None,
    ) -> Campaign:
        """Create a new campaign and save it."""
        campaign = Campaign(
            name=name,
            scope=scope,
            instructions=instructions,
            max_steps_per_target=max_steps_per_target,
            tags=tags or [],
        )
        campaign.add_targets(targets)
        self.save_campaign(campaign)
        return campaign

    def save_campaign(self, campaign: Campaign) -> Path:
        """Persist campaign to disk."""
        campaign.updated_at = time.time()
        path = self.campaigns_dir / f"{campaign.id}.json"
        with open(path, "w") as f:
            json.dump(campaign.to_dict(), f, indent=2, default=str)
        return path

    def load_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """Load a campaign by ID (supports partial match)."""
        # Try exact match first
        path = self.campaigns_dir / f"{campaign_id}.json"
        if path.exists():
            return self._load_from_path(path)

        # Partial match
        for p in self.campaigns_dir.glob("campaign_*.json"):
            if campaign_id in p.stem:
                return self._load_from_path(p)
        return None

    def _load_from_path(self, path: Path) -> Optional[Campaign]:
        """Load campaign from a file path."""
        try:
            with open(path) as f:
                data = json.load(f)
            return Campaign.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load campaign from {path}: {e}")
            return None

    def delete_campaign(self, campaign_id: str) -> bool:
        """Delete a campaign by ID."""
        path = self.campaigns_dir / f"{campaign_id}.json"
        if path.exists():
            path.unlink()
            if self.active_campaign and self.active_campaign.id == campaign_id:
                self.active_campaign = None
            return True
        return False

    def list_campaigns(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all saved campaigns, newest first."""
        campaigns = []
        for path in self.campaigns_dir.glob("campaign_*.json"):
            try:
                with open(path) as f:
                    data = json.load(f)
                campaigns.append({
                    "id": data["id"],
                    "name": data.get("name", ""),
                    "status": data.get("status", "draft"),
                    "target_count": data.get("target_count", len(data.get("targets", []))),
                    "completed_count": data.get("completed_count", 0),
                    "total_findings": data.get("total_findings", 0),
                    "progress_pct": data.get("progress_pct", 0),
                    "created_at": data.get("created_at", 0),
                    "updated_at": data.get("updated_at", 0),
                    "tags": data.get("tags", []),
                })
            except Exception:
                continue

        campaigns.sort(key=lambda c: c.get("updated_at", 0), reverse=True)
        return campaigns[:limit]

    # ── Orchestration ────────────────────────────────────────────────────

    def start_campaign(self, campaign: Campaign) -> str:
        """
        Mark a campaign as running and prepare for sequential execution.

        Returns the first pending target or an error message.
        """
        if not campaign.targets:
            return "ERROR: Campaign has no targets"

        campaign.status = CampaignStatus.RUNNING
        campaign.current_target_idx = -1
        self.active_campaign = campaign
        self.save_campaign(campaign)

        next_target = campaign.next_pending_target
        if next_target:
            return next_target
        return "ERROR: No pending targets"

    def begin_target(self, campaign: Campaign, target: str) -> TargetResult:
        """Mark a target as RUNNING — called before agent.start()."""
        result = campaign.results.get(target, TargetResult(target=target))
        result.status = TargetStatus.RUNNING
        result.started_at = time.time()
        result.findings = []
        result.tool_history = []
        result.error = ""
        campaign.results[target] = result

        if target in campaign.targets:
            campaign.current_target_idx = campaign.targets.index(target)

        self.save_campaign(campaign)
        return result

    def complete_target(
        self,
        campaign: Campaign,
        target: str,
        findings: List[Dict[str, Any]],
        tool_history: List[Dict[str, Any]],
        session_id: str = "",
        steps: int = 0,
        summary: str = "",
    ) -> TargetResult:
        """
        Record results for a completed target assessment.

        Called after the agent finishes or is stopped for this target.
        """
        result = campaign.results.get(target, TargetResult(target=target))
        result.status = TargetStatus.COMPLETED
        result.completed_at = time.time()
        result.findings = findings
        result.tool_history = tool_history
        result.session_id = session_id
        result.steps = steps
        result.summary = summary
        campaign.results[target] = result

        # Check if campaign is now complete
        if campaign.is_complete:
            campaign.status = CampaignStatus.COMPLETED

        campaign.updated_at = time.time()
        self.save_campaign(campaign)
        return result

    def fail_target(
        self,
        campaign: Campaign,
        target: str,
        error: str,
        findings: Optional[List[Dict[str, Any]]] = None,
        tool_history: Optional[List[Dict[str, Any]]] = None,
        session_id: str = "",
        steps: int = 0,
    ) -> TargetResult:
        """Record a failed target assessment."""
        result = campaign.results.get(target, TargetResult(target=target))
        result.status = TargetStatus.FAILED
        result.completed_at = time.time()
        result.error = error
        result.findings = findings or []
        result.tool_history = tool_history or []
        result.session_id = session_id
        result.steps = steps
        campaign.results[target] = result

        if campaign.is_complete:
            campaign.status = CampaignStatus.COMPLETED

        campaign.updated_at = time.time()
        self.save_campaign(campaign)
        return result

    def skip_target(self, campaign: Campaign, target: str, reason: str = "") -> TargetResult:
        """Skip a target."""
        result = campaign.results.get(target, TargetResult(target=target))
        result.status = TargetStatus.SKIPPED
        result.completed_at = time.time()
        result.error = reason or "Skipped by user"
        campaign.results[target] = result

        if campaign.is_complete:
            campaign.status = CampaignStatus.COMPLETED

        campaign.updated_at = time.time()
        self.save_campaign(campaign)
        return result

    def advance_to_next(self, campaign: Campaign) -> Optional[str]:
        """
        Get the next pending target in the campaign.

        Returns the target string or None if all targets have been assessed.
        """
        return campaign.next_pending_target

    def pause_campaign(self, campaign: Campaign) -> None:
        """Pause a running campaign."""
        if campaign.status == CampaignStatus.RUNNING:
            campaign.status = CampaignStatus.PAUSED
            # Mark any running target back to pending
            for r in campaign.results.values():
                if r.status == TargetStatus.RUNNING:
                    r.status = TargetStatus.PENDING
                    r.started_at = 0.0
            self.save_campaign(campaign)

    def abort_campaign(self, campaign: Campaign) -> None:
        """Abort a campaign entirely."""
        campaign.status = CampaignStatus.ABORTED
        for r in campaign.results.values():
            if r.status == TargetStatus.RUNNING:
                r.status = TargetStatus.FAILED
                r.error = "Campaign aborted"
                r.completed_at = time.time()
        self.save_campaign(campaign)

    def resume_campaign(self, campaign: Campaign) -> Optional[str]:
        """Resume a paused campaign and return the next target."""
        if campaign.status != CampaignStatus.PAUSED:
            return None
        campaign.status = CampaignStatus.RUNNING
        self.active_campaign = campaign
        self.save_campaign(campaign)
        return campaign.next_pending_target

    # ── Reporting ────────────────────────────────────────────────────────

    def get_campaign_report(self, campaign: Campaign) -> Dict[str, Any]:
        """Generate a JSON-serializable campaign report."""
        return {
            "campaign": campaign.to_dict(),
            "markdown": campaign.get_summary_markdown(),
            "severity_counts": campaign.severity_counts(),
            "all_findings": campaign.all_findings(),
            "findings_by_target": {
                t: [f for f in findings]
                for t, findings in campaign.findings_by_target().items()
            },
        }

    def save_campaign_report(self, campaign: Campaign) -> Path:
        """Save campaign report as JSON."""
        from hackbot.config import REPORTS_DIR
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        safe_name = (campaign.name or campaign.id).replace(" ", "_").replace("/", "_")[:40]
        path = REPORTS_DIR / f"campaign_{safe_name}_{ts}.json"
        report = self.get_campaign_report(campaign)
        with open(path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        return path


# ── Singleton ────────────────────────────────────────────────────────────────

_global_manager: Optional[CampaignManager] = None


def get_campaign_manager(campaigns_dir: Optional[Path] = None) -> CampaignManager:
    """Get (or create) the global CampaignManager singleton."""
    global _global_manager
    if _global_manager is None:
        _global_manager = CampaignManager(campaigns_dir=campaigns_dir)
    return _global_manager


def reset_campaign_manager() -> None:
    """Reset the global manager (for testing)."""
    global _global_manager
    _global_manager = None
