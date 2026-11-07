"""
Tests for HackBot Multi-Target Campaign System
================================================
"""

import json
import time
import tempfile
from pathlib import Path

import pytest

from hackbot.core.campaigns import (
    Campaign,
    CampaignManager,
    CampaignStatus,
    TargetResult,
    TargetStatus,
    get_campaign_manager,
    reset_campaign_manager,
)


# ── Helper Factories ─────────────────────────────────────────────────────────

def make_finding(title="SQL Injection", severity="High", description="Found SQLi",
                 tool="sqlmap", recommendation="Parameterize queries"):
    return {
        "title": title,
        "severity": severity,
        "description": description,
        "tool": tool,
        "recommendation": recommendation,
        "timestamp": time.time(),
    }


def make_campaign(name="Test Campaign", targets=None, **kwargs):
    c = Campaign(name=name, **kwargs)
    if targets:
        c.add_targets(targets)
    return c


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def manager(tmp_dir):
    return CampaignManager(campaigns_dir=tmp_dir)


# ── TargetStatus Enum ────────────────────────────────────────────────────────

class TestTargetStatus:
    def test_values(self):
        assert TargetStatus.PENDING == "pending"
        assert TargetStatus.RUNNING == "running"
        assert TargetStatus.COMPLETED == "completed"
        assert TargetStatus.FAILED == "failed"
        assert TargetStatus.SKIPPED == "skipped"

    def test_from_string(self):
        assert TargetStatus("pending") == TargetStatus.PENDING
        assert TargetStatus("completed") == TargetStatus.COMPLETED


# ── CampaignStatus Enum ─────────────────────────────────────────────────────

class TestCampaignStatus:
    def test_values(self):
        assert CampaignStatus.DRAFT == "draft"
        assert CampaignStatus.RUNNING == "running"
        assert CampaignStatus.PAUSED == "paused"
        assert CampaignStatus.COMPLETED == "completed"
        assert CampaignStatus.ABORTED == "aborted"

    def test_from_string(self):
        assert CampaignStatus("draft") == CampaignStatus.DRAFT
        assert CampaignStatus("aborted") == CampaignStatus.ABORTED


# ── TargetResult ─────────────────────────────────────────────────────────────

class TestTargetResult:
    def test_default_creation(self):
        r = TargetResult(target="10.0.0.1")
        assert r.target == "10.0.0.1"
        assert r.status == TargetStatus.PENDING
        assert r.findings == []
        assert r.tool_history == []
        assert r.session_id == ""
        assert r.started_at == 0.0
        assert r.completed_at == 0.0
        assert r.error == ""
        assert r.steps == 0
        assert r.summary == ""

    def test_to_dict(self):
        r = TargetResult(
            target="10.0.0.1",
            status=TargetStatus.COMPLETED,
            findings=[make_finding()],
            steps=5,
            started_at=1000.0,
            completed_at=1060.0,
            session_id="sess_1",
            summary="Found SQLi",
        )
        d = r.to_dict()
        assert d["target"] == "10.0.0.1"
        assert d["status"] == "completed"
        assert d["finding_count"] == 1
        assert d["duration"] == 60.0
        assert d["session_id"] == "sess_1"
        assert d["steps"] == 5
        assert d["summary"] == "Found SQLi"

    def test_to_dict_no_duration(self):
        r = TargetResult(target="x")
        d = r.to_dict()
        assert d["duration"] == 0

    def test_from_dict(self):
        data = {
            "target": "app.example.com",
            "status": "failed",
            "findings": [make_finding(title="XSS")],
            "tool_history": [{"tool": "nikto"}],
            "session_id": "s2",
            "started_at": 500.0,
            "completed_at": 560.0,
            "error": "timed out",
            "steps": 10,
            "summary": "XSS found",
        }
        r = TargetResult.from_dict(data)
        assert r.target == "app.example.com"
        assert r.status == TargetStatus.FAILED
        assert len(r.findings) == 1
        assert r.error == "timed out"
        assert r.steps == 10

    def test_from_dict_defaults(self):
        r = TargetResult.from_dict({"target": "host"})
        assert r.status == TargetStatus.PENDING
        assert r.findings == []
        assert r.session_id == ""

    def test_roundtrip(self):
        original = TargetResult(
            target="host1",
            status=TargetStatus.COMPLETED,
            findings=[make_finding()],
            started_at=100.0,
            completed_at=200.0,
            steps=3,
        )
        d = original.to_dict()
        restored = TargetResult.from_dict(d)
        assert restored.target == original.target
        assert restored.status == original.status
        assert len(restored.findings) == len(original.findings)
        assert restored.steps == original.steps


# ── Campaign Data Model ─────────────────────────────────────────────────────

class TestCampaign:
    def test_default_creation(self):
        c = Campaign()
        assert c.name == ""
        assert c.targets == []
        assert c.results == {}
        assert c.status == CampaignStatus.DRAFT
        assert c.scope == ""
        assert c.instructions == ""
        assert c.current_target_idx == -1
        assert c.max_steps_per_target == 50
        assert c.tags == []
        assert c.id.startswith("campaign_")

    def test_creation_with_name(self):
        c = Campaign(name="Audit Q1")
        assert c.name == "Audit Q1"

    # ── Target Management ────────────────────────────────────────────────

    def test_add_target(self):
        c = Campaign()
        assert c.add_target("10.0.0.1")
        assert "10.0.0.1" in c.targets
        assert "10.0.0.1" in c.results
        assert c.results["10.0.0.1"].status == TargetStatus.PENDING

    def test_add_target_duplicate(self):
        c = Campaign()
        c.add_target("10.0.0.1")
        assert not c.add_target("10.0.0.1")
        assert len(c.targets) == 1

    def test_add_target_empty(self):
        c = Campaign()
        assert not c.add_target("")
        assert not c.add_target("   ")

    def test_add_target_strips_whitespace(self):
        c = Campaign()
        c.add_target("  host1  ")
        assert "host1" in c.targets

    def test_add_targets(self):
        c = Campaign()
        count = c.add_targets(["a.com", "b.com", "c.com"])
        assert count == 3
        assert len(c.targets) == 3

    def test_add_targets_with_duplicates(self):
        c = Campaign()
        count = c.add_targets(["a.com", "b.com", "a.com"])
        assert count == 2

    def test_remove_target(self):
        c = make_campaign(targets=["a", "b", "c"])
        assert c.remove_target("b")
        assert "b" not in c.targets
        assert "b" not in c.results

    def test_remove_target_not_found(self):
        c = make_campaign(targets=["a"])
        assert not c.remove_target("z")

    def test_clear_targets(self):
        c = make_campaign(targets=["a", "b", "c"])
        c.clear_targets()
        assert c.targets == []
        assert c.results == {}

    # ── Status Queries ───────────────────────────────────────────────────

    def test_target_count(self):
        c = make_campaign(targets=["a", "b"])
        assert c.target_count == 2

    def test_completed_count(self):
        c = make_campaign(targets=["a", "b", "c"])
        c.results["a"].status = TargetStatus.COMPLETED
        c.results["b"].status = TargetStatus.FAILED
        c.results["c"].status = TargetStatus.PENDING
        assert c.completed_count == 2  # COMPLETED + FAILED count

    def test_completed_count_includes_skipped(self):
        c = make_campaign(targets=["a", "b"])
        c.results["a"].status = TargetStatus.SKIPPED
        c.results["b"].status = TargetStatus.PENDING
        assert c.completed_count == 1

    def test_pending_count(self):
        c = make_campaign(targets=["a", "b", "c"])
        c.results["a"].status = TargetStatus.COMPLETED
        assert c.pending_count == 2

    def test_running_target(self):
        c = make_campaign(targets=["a", "b"])
        assert c.running_target is None
        c.results["b"].status = TargetStatus.RUNNING
        assert c.running_target == "b"

    def test_current_target(self):
        c = make_campaign(targets=["a", "b", "c"])
        assert c.current_target is None
        c.current_target_idx = 1
        assert c.current_target == "b"

    def test_current_target_out_of_range(self):
        c = make_campaign(targets=["a"])
        c.current_target_idx = 5
        assert c.current_target is None

    def test_next_pending_target(self):
        c = make_campaign(targets=["a", "b", "c"])
        assert c.next_pending_target == "a"
        c.results["a"].status = TargetStatus.COMPLETED
        assert c.next_pending_target == "b"

    def test_next_pending_target_none(self):
        c = make_campaign(targets=["a"])
        c.results["a"].status = TargetStatus.COMPLETED
        assert c.next_pending_target is None

    def test_is_complete(self):
        c = make_campaign(targets=["a", "b"])
        assert not c.is_complete
        c.results["a"].status = TargetStatus.COMPLETED
        c.results["b"].status = TargetStatus.SKIPPED
        assert c.is_complete

    def test_is_complete_empty_campaign(self):
        c = Campaign()
        assert not c.is_complete

    def test_total_findings(self):
        c = make_campaign(targets=["a", "b"])
        c.results["a"].findings = [make_finding(), make_finding(title="XSS")]
        c.results["b"].findings = [make_finding(title="CSRF")]
        assert c.total_findings == 3

    def test_total_duration(self):
        c = make_campaign(targets=["a", "b"])
        c.results["a"].started_at = 100.0
        c.results["a"].completed_at = 160.0
        c.results["b"].started_at = 200.0
        c.results["b"].completed_at = 280.0
        assert c.total_duration == 140.0

    def test_total_duration_skips_unfinished(self):
        c = make_campaign(targets=["a", "b"])
        c.results["a"].started_at = 100.0
        c.results["a"].completed_at = 160.0
        assert c.total_duration == 60.0

    def test_progress_pct(self):
        c = make_campaign(targets=["a", "b", "c", "d"])
        c.results["a"].status = TargetStatus.COMPLETED
        c.results["b"].status = TargetStatus.FAILED
        assert c.progress_pct() == 50.0

    def test_progress_pct_empty(self):
        c = Campaign()
        assert c.progress_pct() == 0.0

    def test_progress_pct_all_done(self):
        c = make_campaign(targets=["a"])
        c.results["a"].status = TargetStatus.COMPLETED
        assert c.progress_pct() == 100.0

    # ── Finding Aggregation ──────────────────────────────────────────────

    def test_all_findings(self):
        c = make_campaign(targets=["a", "b"])
        c.results["a"].findings = [make_finding(title="SQLi")]
        c.results["b"].findings = [make_finding(title="XSS")]
        all_f = c.all_findings()
        assert len(all_f) == 2
        assert all_f[0]["campaign_target"] == "a"
        assert all_f[1]["campaign_target"] == "b"

    def test_all_findings_empty(self):
        c = make_campaign(targets=["a"])
        assert c.all_findings() == []

    def test_findings_by_severity(self):
        c = make_campaign(targets=["a"])
        c.results["a"].findings = [
            make_finding(title="SQLi", severity="Critical"),
            make_finding(title="XSS", severity="High"),
            make_finding(title="Info leak", severity="Critical"),
        ]
        by_sev = c.findings_by_severity()
        assert len(by_sev["Critical"]) == 2
        assert len(by_sev["High"]) == 1

    def test_severity_counts(self):
        c = make_campaign(targets=["a", "b"])
        c.results["a"].findings = [
            make_finding(severity="High"),
            make_finding(severity="Medium"),
        ]
        c.results["b"].findings = [
            make_finding(severity="High"),
            make_finding(severity="Low"),
        ]
        counts = c.severity_counts()
        assert counts["High"] == 2
        assert counts["Medium"] == 1
        assert counts["Low"] == 1

    def test_findings_by_target(self):
        c = make_campaign(targets=["a", "b", "c"])
        c.results["a"].findings = [make_finding()]
        c.results["c"].findings = [make_finding(), make_finding()]
        fbt = c.findings_by_target()
        assert "a" in fbt
        assert "b" not in fbt  # no findings
        assert len(fbt["c"]) == 2

    # ── Serialization ────────────────────────────────────────────────────

    def test_to_dict(self):
        c = make_campaign(name="Audit", targets=["a", "b"], scope="internal")
        d = c.to_dict()
        assert d["name"] == "Audit"
        assert d["targets"] == ["a", "b"]
        assert d["status"] == "draft"
        assert d["scope"] == "internal"
        assert d["target_count"] == 2
        assert d["completed_count"] == 0
        assert d["total_findings"] == 0
        assert d["progress_pct"] == 0.0
        assert "results" in d

    def test_to_dict_with_results(self):
        c = make_campaign(targets=["a"])
        c.results["a"].status = TargetStatus.COMPLETED
        c.results["a"].findings = [make_finding()]
        d = c.to_dict()
        assert d["total_findings"] == 1
        assert d["results"]["a"]["status"] == "completed"

    def test_from_dict(self):
        data = {
            "id": "campaign_test",
            "name": "Test Campaign",
            "targets": ["a", "b"],
            "status": "running",
            "scope": "external",
            "instructions": "do stuff",
            "created_at": 1000,
            "updated_at": 2000,
            "current_target_idx": 1,
            "max_steps_per_target": 30,
            "tags": ["web"],
            "results": {
                "a": {"target": "a", "status": "completed", "findings": [make_finding()], "steps": 5},
                "b": {"target": "b", "status": "pending"},
            },
        }
        c = Campaign.from_dict(data)
        assert c.id == "campaign_test"
        assert c.name == "Test Campaign"
        assert c.status == CampaignStatus.RUNNING
        assert c.scope == "external"
        assert c.max_steps_per_target == 30
        assert c.tags == ["web"]
        assert c.results["a"].status == TargetStatus.COMPLETED
        assert len(c.results["a"].findings) == 1

    def test_roundtrip(self):
        c = make_campaign(name="RT", targets=["a", "b", "c"], scope="all")
        c.results["a"].status = TargetStatus.COMPLETED
        c.results["a"].findings = [make_finding()]
        c.results["b"].status = TargetStatus.FAILED
        c.results["b"].error = "timeout"
        data = c.to_dict()
        c2 = Campaign.from_dict(data)
        assert c2.name == c.name
        assert c2.targets == c.targets
        assert c2.results["a"].status == TargetStatus.COMPLETED
        assert c2.results["b"].error == "timeout"
        assert c2.total_findings == c.total_findings

    # ── Summary Markdown ─────────────────────────────────────────────────

    def test_get_summary_markdown(self):
        c = make_campaign(name="Audit Q1", targets=["a", "b"], scope="internal")
        c.results["a"].status = TargetStatus.COMPLETED
        c.results["a"].findings = [make_finding(severity="Critical", title="RCE")]
        c.results["b"].status = TargetStatus.PENDING
        md = c.get_summary_markdown()
        assert "# Campaign: Audit Q1" in md
        assert "DRAFT" in md
        assert "Total Findings" in md
        assert "Critical" in md
        assert "RCE" in md
        assert "| a |" in md
        assert "| b |" in md

    def test_summary_no_findings(self):
        c = make_campaign(name="Empty", targets=["a"])
        md = c.get_summary_markdown()
        assert "# Campaign: Empty" in md
        assert "Critical & High Findings" not in md

    def test_summary_with_scope(self):
        c = make_campaign(name="Scoped", targets=["a"], scope="web apps only")
        md = c.get_summary_markdown()
        assert "web apps only" in md

    # ── Agent Context ────────────────────────────────────────────────────

    def test_agent_context_first_target(self):
        c = make_campaign(name="CTX", targets=["a", "b"])
        ctx = c.get_agent_context("a")
        assert "CAMPAIGN CONTEXT" in ctx
        assert "Target 1 of 2" in ctx
        assert "first target" in ctx.lower()

    def test_agent_context_with_previous_findings(self):
        c = make_campaign(name="CTX", targets=["a", "b", "c"])
        c.results["a"].findings = [make_finding(title="SQLi", severity="High")]
        ctx = c.get_agent_context("b")
        assert "CAMPAIGN CONTEXT" in ctx
        assert "Target 2 of 3" in ctx
        assert "SQLi" in ctx
        assert "on a" in ctx

    def test_agent_context_caps_findings(self):
        c = make_campaign(name="CTX", targets=["a", "b"])
        c.results["a"].findings = [
            make_finding(title=f"Finding_{i}") for i in range(35)
        ]
        ctx = c.get_agent_context("b")
        assert "and 5 more" in ctx


# ── Campaign Manager ────────────────────────────────────────────────────────

class TestCampaignManager:
    # ── CRUD ─────────────────────────────────────────────────────────────

    def test_create_campaign(self, manager):
        c = manager.create_campaign("Test", ["a", "b"])
        assert c.name == "Test"
        assert c.target_count == 2
        # Check file was saved
        files = list(manager.campaigns_dir.glob("campaign_*.json"))
        assert len(files) == 1

    def test_create_campaign_with_options(self, manager):
        c = manager.create_campaign(
            name="Full",
            targets=["a"],
            scope="internal",
            instructions="check web",
            max_steps_per_target=30,
            tags=["web"],
        )
        assert c.scope == "internal"
        assert c.instructions == "check web"
        assert c.max_steps_per_target == 30
        assert c.tags == ["web"]

    def test_save_and_load_campaign(self, manager):
        c = manager.create_campaign("Test", ["a", "b"])
        loaded = manager.load_campaign(c.id)
        assert loaded is not None
        assert loaded.name == "Test"
        assert loaded.target_count == 2

    def test_load_campaign_not_found(self, manager):
        assert manager.load_campaign("nonexistent") is None

    def test_load_campaign_partial_match(self, manager):
        c = manager.create_campaign("Test", ["a"])
        # Partial match on ID
        partial = c.id[9:20]  # take a slice after "campaign_"
        loaded = manager.load_campaign(partial)
        assert loaded is not None
        assert loaded.id == c.id

    def test_delete_campaign(self, manager):
        c = manager.create_campaign("Del", ["a"])
        assert manager.delete_campaign(c.id)
        assert manager.load_campaign(c.id) is None
        files = list(manager.campaigns_dir.glob("campaign_*.json"))
        assert len(files) == 0

    def test_delete_campaign_not_found(self, manager):
        assert not manager.delete_campaign("nope")

    def test_delete_active_campaign(self, manager):
        c = manager.create_campaign("Active", ["a"])
        manager.active_campaign = c
        manager.delete_campaign(c.id)
        assert manager.active_campaign is None

    def test_list_campaigns_empty(self, manager):
        assert manager.list_campaigns() == []

    def test_list_campaigns(self, manager):
        c1 = manager.create_campaign("A", ["a"])
        c2 = manager.create_campaign("B", ["b"])
        # Ensure unique IDs (millisecond timestamps can collide)
        if c1.id == c2.id:
            c2.id = c2.id + "_2"
            manager.save_campaign(c2)
        campaigns = manager.list_campaigns()
        assert len(campaigns) == 2
        # Newest first
        assert campaigns[0]["name"] in ("A", "B")

    def test_list_campaigns_limit(self, manager):
        for i in range(5):
            c = Campaign(id=f"campaign_limit_{i}", name=f"C{i}")
            c.add_target("a")
            manager.save_campaign(c)
        assert len(manager.list_campaigns(limit=3)) == 3

    def test_list_campaigns_includes_metadata(self, manager):
        c = manager.create_campaign("Meta", ["a", "b", "c"])
        result = manager.list_campaigns()[0]
        assert result["name"] == "Meta"
        assert result["target_count"] == 3
        assert result["status"] == "draft"
        assert "created_at" in result
        assert "updated_at" in result

    # ── Orchestration ────────────────────────────────────────────────────

    def test_start_campaign(self, manager):
        c = manager.create_campaign("Start", ["a", "b"])
        first = manager.start_campaign(c)
        assert first == "a"
        assert c.status == CampaignStatus.RUNNING
        assert manager.active_campaign == c

    def test_start_campaign_no_targets(self, manager):
        c = Campaign(name="Empty")
        result = manager.start_campaign(c)
        assert "ERROR" in result

    def test_begin_target(self, manager):
        c = manager.create_campaign("Begin", ["a", "b"])
        manager.start_campaign(c)
        result = manager.begin_target(c, "a")
        assert result.status == TargetStatus.RUNNING
        assert result.started_at > 0
        assert c.current_target_idx == 0

    def test_begin_target_resets_previous_data(self, manager):
        c = manager.create_campaign("Reset", ["a"])
        c.results["a"].findings = [make_finding()]
        c.results["a"].error = "old error"
        manager.begin_target(c, "a")
        assert c.results["a"].findings == []
        assert c.results["a"].error == ""

    def test_complete_target(self, manager):
        c = manager.create_campaign("Complete", ["a", "b"])
        manager.start_campaign(c)
        manager.begin_target(c, "a")
        findings = [make_finding(), make_finding(title="XSS")]
        result = manager.complete_target(c, "a", findings=findings, tool_history=[],
                                          session_id="s1", steps=5, summary="Done")
        assert result.status == TargetStatus.COMPLETED
        assert result.completed_at > 0
        assert len(result.findings) == 2
        assert result.session_id == "s1"
        assert result.steps == 5
        assert result.summary == "Done"
        assert c.status == CampaignStatus.RUNNING  # b still pending

    def test_complete_last_target_completes_campaign(self, manager):
        c = manager.create_campaign("AllDone", ["a"])
        manager.start_campaign(c)
        manager.begin_target(c, "a")
        manager.complete_target(c, "a", findings=[], tool_history=[])
        assert c.status == CampaignStatus.COMPLETED

    def test_fail_target(self, manager):
        c = manager.create_campaign("Fail", ["a", "b"])
        manager.start_campaign(c)
        manager.begin_target(c, "a")
        result = manager.fail_target(c, "a", error="connection refused")
        assert result.status == TargetStatus.FAILED
        assert result.error == "connection refused"
        assert result.completed_at > 0

    def test_fail_target_with_partial_findings(self, manager):
        c = manager.create_campaign("PartialFail", ["a"])
        manager.start_campaign(c)
        manager.begin_target(c, "a")
        findings = [make_finding()]
        result = manager.fail_target(c, "a", error="timeout", findings=findings, steps=3)
        assert len(result.findings) == 1
        assert result.steps == 3
        assert c.status == CampaignStatus.COMPLETED  # only target

    def test_skip_target(self, manager):
        c = manager.create_campaign("Skip", ["a", "b"])
        manager.start_campaign(c)
        result = manager.skip_target(c, "a", reason="Not in scope")
        assert result.status == TargetStatus.SKIPPED
        assert result.error == "Not in scope"
        assert result.completed_at > 0

    def test_skip_target_default_reason(self, manager):
        c = manager.create_campaign("Skip2", ["a"])
        result = manager.skip_target(c, "a")
        assert result.error == "Skipped by user"

    def test_advance_to_next(self, manager):
        c = manager.create_campaign("Advance", ["a", "b", "c"])
        manager.start_campaign(c)
        c.results["a"].status = TargetStatus.COMPLETED
        nxt = manager.advance_to_next(c)
        assert nxt == "b"

    def test_advance_to_next_all_done(self, manager):
        c = make_campaign(targets=["a"])
        c.results["a"].status = TargetStatus.COMPLETED
        assert manager.advance_to_next(c) is None

    def test_pause_campaign(self, manager):
        c = manager.create_campaign("Pause", ["a", "b"])
        manager.start_campaign(c)
        manager.begin_target(c, "a")
        manager.pause_campaign(c)
        assert c.status == CampaignStatus.PAUSED
        # Running target should be reset to pending
        assert c.results["a"].status == TargetStatus.PENDING
        assert c.results["a"].started_at == 0.0

    def test_pause_non_running_ignored(self, manager):
        c = make_campaign(targets=["a"])
        c.status = CampaignStatus.DRAFT
        manager.pause_campaign(c)
        assert c.status == CampaignStatus.DRAFT

    def test_abort_campaign(self, manager):
        c = manager.create_campaign("Abort", ["a", "b"])
        manager.start_campaign(c)
        manager.begin_target(c, "a")
        manager.abort_campaign(c)
        assert c.status == CampaignStatus.ABORTED
        assert c.results["a"].status == TargetStatus.FAILED
        assert c.results["a"].error == "Campaign aborted"

    def test_abort_marks_running_failed(self, manager):
        c = make_campaign(targets=["a", "b"])
        c.status = CampaignStatus.RUNNING
        c.results["a"].status = TargetStatus.RUNNING
        c.results["b"].status = TargetStatus.PENDING
        manager.abort_campaign(c)
        assert c.results["a"].status == TargetStatus.FAILED
        assert c.results["b"].status == TargetStatus.PENDING

    def test_resume_campaign(self, manager):
        c = manager.create_campaign("Resume", ["a", "b"])
        manager.start_campaign(c)
        manager.pause_campaign(c)
        nxt = manager.resume_campaign(c)
        assert c.status == CampaignStatus.RUNNING
        assert nxt == "a"
        assert manager.active_campaign == c

    def test_resume_non_paused_returns_none(self, manager):
        c = make_campaign(targets=["a"])
        c.status = CampaignStatus.DRAFT
        assert manager.resume_campaign(c) is None

    # ── Full Lifecycle ───────────────────────────────────────────────────

    def test_full_lifecycle(self, manager):
        """Complete campaign from create → start → assess all → complete."""
        c = manager.create_campaign("Full", ["host1", "host2", "host3"])
        assert c.status == CampaignStatus.DRAFT

        # Start
        first = manager.start_campaign(c)
        assert first == "host1"
        assert c.status == CampaignStatus.RUNNING

        # Assess host1
        manager.begin_target(c, "host1")
        assert c.results["host1"].status == TargetStatus.RUNNING
        manager.complete_target(c, "host1",
                                 findings=[make_finding(title="SQLi on host1")],
                                 tool_history=[{"tool": "sqlmap"}],
                                 steps=3)
        assert c.results["host1"].status == TargetStatus.COMPLETED

        # Advance to host2
        nxt = manager.advance_to_next(c)
        assert nxt == "host2"
        manager.begin_target(c, "host2")
        manager.skip_target(c, "host2", "offline")
        assert c.results["host2"].status == TargetStatus.SKIPPED

        # Advance to host3
        nxt = manager.advance_to_next(c)
        assert nxt == "host3"
        manager.begin_target(c, "host3")
        manager.complete_target(c, "host3", findings=[], tool_history=[], steps=2)

        # Campaign should auto-complete
        assert c.status == CampaignStatus.COMPLETED
        assert c.total_findings == 1
        assert c.progress_pct() == 100.0

    def test_lifecycle_with_pause_resume(self, manager):
        """Pause mid-campaign and resume."""
        c = manager.create_campaign("PauseResume", ["a", "b"])
        manager.start_campaign(c)
        manager.begin_target(c, "a")
        manager.complete_target(c, "a", findings=[], tool_history=[])

        # Pause before assessing b
        manager.begin_target(c, "b")
        manager.pause_campaign(c)
        assert c.status == CampaignStatus.PAUSED
        assert c.results["b"].status == TargetStatus.PENDING

        # Resume
        nxt = manager.resume_campaign(c)
        assert nxt == "b"
        assert c.status == CampaignStatus.RUNNING

    # ── Reporting ────────────────────────────────────────────────────────

    def test_get_campaign_report(self, manager):
        c = manager.create_campaign("Report", ["a"])
        c.results["a"].status = TargetStatus.COMPLETED
        c.results["a"].findings = [make_finding()]
        manager.save_campaign(c)
        report = manager.get_campaign_report(c)
        assert "campaign" in report
        assert "markdown" in report
        assert "severity_counts" in report
        assert "all_findings" in report
        assert "findings_by_target" in report
        assert len(report["all_findings"]) == 1

    def test_save_campaign_report(self, manager):
        c = manager.create_campaign("SaveReport", ["a"])
        c.results["a"].findings = [make_finding()]
        path = manager.save_campaign_report(c)
        assert path.exists()
        with open(path) as f:
            data = json.load(f)
        assert data["campaign"]["name"] == "SaveReport"


# ── Singleton ────────────────────────────────────────────────────────────────

class TestSingleton:
    def test_get_campaign_manager(self, tmp_dir):
        reset_campaign_manager()
        m = get_campaign_manager(campaigns_dir=tmp_dir)
        assert isinstance(m, CampaignManager)
        # Same instance on second call
        m2 = get_campaign_manager()
        assert m is m2
        reset_campaign_manager()

    def test_reset_campaign_manager(self, tmp_dir):
        reset_campaign_manager()
        m1 = get_campaign_manager(campaigns_dir=tmp_dir)
        reset_campaign_manager()
        m2 = get_campaign_manager(campaigns_dir=tmp_dir)
        assert m1 is not m2
        reset_campaign_manager()


# ── Edge Cases ───────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_campaign_with_single_target(self, manager):
        c = manager.create_campaign("Single", ["host"])
        manager.start_campaign(c)
        manager.begin_target(c, "host")
        manager.complete_target(c, "host", findings=[], tool_history=[])
        assert c.status == CampaignStatus.COMPLETED

    def test_all_targets_skipped(self, manager):
        c = manager.create_campaign("AllSkip", ["a", "b"])
        manager.start_campaign(c)
        manager.skip_target(c, "a")
        manager.skip_target(c, "b")
        assert c.status == CampaignStatus.COMPLETED

    def test_all_targets_failed(self, manager):
        c = manager.create_campaign("AllFail", ["a", "b"])
        manager.start_campaign(c)
        manager.fail_target(c, "a", "err")
        manager.fail_target(c, "b", "err")
        assert c.status == CampaignStatus.COMPLETED

    def test_mixed_statuses(self, manager):
        c = manager.create_campaign("Mixed", ["a", "b", "c"])
        manager.start_campaign(c)
        manager.complete_target(c, "a", [make_finding()], [])
        manager.skip_target(c, "b")
        manager.fail_target(c, "c", "down")
        assert c.status == CampaignStatus.COMPLETED
        assert c.total_findings == 1

    def test_save_preserves_findings_across_loads(self, manager):
        c = manager.create_campaign("Persist", ["a"])
        findings = [make_finding(title="Stored XSS", severity="Critical")]
        manager.complete_target(c, "a", findings, [{"tool": "zap"}], session_id="s1")
        loaded = manager.load_campaign(c.id)
        assert loaded.results["a"].findings[0]["title"] == "Stored XSS"
        assert loaded.results["a"].session_id == "s1"

    def test_corrupted_campaign_file(self, manager):
        bad_path = manager.campaigns_dir / "campaign_bad.json"
        bad_path.write_text("not json {{{")
        assert manager.load_campaign("campaign_bad") is None

    def test_concurrent_campaigns(self, manager):
        c1 = Campaign(id="campaign_conc_1", name="C1")
        c1.add_target("a")
        manager.save_campaign(c1)
        c2 = Campaign(id="campaign_conc_2", name="C2")
        c2.add_target("b")
        manager.save_campaign(c2)
        manager.start_campaign(c1)
        assert manager.active_campaign == c1
        manager.start_campaign(c2)
        assert manager.active_campaign == c2
        assert len(manager.list_campaigns()) == 2

    def test_large_target_list(self, manager):
        targets = [f"192.168.1.{i}" for i in range(1, 101)]
        c = manager.create_campaign("Large", targets)
        assert c.target_count == 100
        assert c.progress_pct() == 0.0

    def test_severity_count_with_no_severity_key(self):
        c = make_campaign(targets=["a"])
        c.results["a"].findings = [{"title": "test"}]  # no severity key
        counts = c.severity_counts()
        assert counts.get("Info", 0) == 1
