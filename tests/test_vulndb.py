"""Tests for HackBot Vulnerability Database."""

import json
import time
import tempfile
from pathlib import Path

import pytest

from hackbot.core.vulndb import (
    VulnDB,
    VulnRecord,
    AssessmentRecord,
    DBStats,
    VALID_STATUSES,
    SEVERITY_WEIGHTS,
    _fingerprint,
)


@pytest.fixture
def db(tmp_path):
    """Provide a fresh in-memory-like VulnDB for each test."""
    return VulnDB(db_path=tmp_path / "test.db")


# ── Fingerprint ──────────────────────────────────────────────────────────────

def test_fingerprint_deterministic():
    """Same inputs produce the same fingerprint."""
    fp1 = _fingerprint("192.168.1.1", "SQL Injection", "High")
    fp2 = _fingerprint("192.168.1.1", "SQL Injection", "High")
    assert fp1 == fp2
    assert len(fp1) == 16


def test_fingerprint_case_insensitive():
    """Fingerprint is case-insensitive."""
    fp1 = _fingerprint("EXAMPLE.COM", "XSS", "High")
    fp2 = _fingerprint("example.com", "xss", "high")
    assert fp1 == fp2


def test_fingerprint_different_inputs():
    """Different inputs produce different fingerprints."""
    fp1 = _fingerprint("192.168.1.1", "SQL Injection", "High")
    fp2 = _fingerprint("192.168.1.1", "SQL Injection", "Medium")
    assert fp1 != fp2


# ── Assessment CRUD ──────────────────────────────────────────────────────────

def test_create_assessment(db):
    aid = db.create_assessment("192.168.1.1", scope="network")
    assert aid == 1
    a = db.get_assessment(aid)
    assert a is not None
    assert a.target == "192.168.1.1"
    assert a.scope == "network"
    assert a.finished_at is None


def test_finish_assessment(db):
    aid = db.create_assessment("10.0.0.1")
    db.finish_assessment(aid, total_steps=5, total_findings=3)
    a = db.get_assessment(aid)
    assert a.finished_at is not None
    assert a.total_steps == 5
    assert a.total_findings == 3


def test_list_assessments(db):
    db.create_assessment("10.0.0.1")
    db.create_assessment("192.168.1.1")
    db.create_assessment("10.0.0.1")
    all_list = db.list_assessments()
    assert len(all_list) == 3
    filtered = db.list_assessments(target="10.0.0")
    assert len(filtered) == 2


def test_get_assessment_not_found(db):
    assert db.get_assessment(999) is None


# ── Finding CRUD ─────────────────────────────────────────────────────────────

SAMPLE_FINDING = {
    "title": "SQL Injection in login form",
    "severity": "High",
    "description": "The login form is vulnerable to SQL injection.",
    "evidence": "' OR '1'='1",
    "recommendation": "Use parameterized queries.",
    "tool": "sqlmap",
    "timestamp": time.time(),
}


def test_add_and_get_finding(db):
    aid = db.create_assessment("example.com")
    fid = db.add_finding(aid, SAMPLE_FINDING, target="example.com")
    assert fid >= 1

    f = db.get_finding(fid)
    assert f is not None
    assert f.title == "SQL Injection in login form"
    assert f.severity == "High"
    assert f.status == "open"
    assert f.target == "example.com"
    assert f.tool == "sqlmap"
    assert f.risk_score == SEVERITY_WEIGHTS["High"]


def test_finding_deduplication(db):
    aid = db.create_assessment("example.com")
    fid1 = db.add_finding(aid, SAMPLE_FINDING, target="example.com")
    fid2 = db.add_finding(aid, SAMPLE_FINDING, target="example.com")
    # Same finding + target = same ID (updated, not duplicated)
    assert fid1 == fid2


def test_finding_different_targets(db):
    aid = db.create_assessment("multiple")
    fid1 = db.add_finding(aid, SAMPLE_FINDING, target="a.example.com")
    fid2 = db.add_finding(aid, SAMPLE_FINDING, target="b.example.com")
    assert fid1 != fid2


def test_add_findings_bulk(db):
    aid = db.create_assessment("bulk.test")
    findings = [
        {"title": "XSS", "severity": "Medium"},
        {"title": "CSRF", "severity": "Medium"},
        {"title": "Open Redirect", "severity": "Low"},
    ]
    ids = db.add_findings_bulk(aid, findings, target="bulk.test")
    assert len(ids) == 3
    assert len(set(ids)) == 3


def test_get_finding_not_found(db):
    assert db.get_finding(999) is None


# ── Search ───────────────────────────────────────────────────────────────────

def test_search_by_query(db):
    aid = db.create_assessment("search.test")
    db.add_finding(aid, {"title": "SQL Injection", "severity": "High"}, target="search.test")
    db.add_finding(aid, {"title": "XSS Reflected", "severity": "Medium"}, target="search.test")

    results = db.search_findings(query="SQL")
    assert len(results) == 1
    assert results[0].title == "SQL Injection"


def test_search_by_severity(db):
    aid = db.create_assessment("sev.test")
    db.add_finding(aid, {"title": "A", "severity": "Critical"}, target="sev.test")
    db.add_finding(aid, {"title": "B", "severity": "Low"}, target="sev.test")
    db.add_finding(aid, {"title": "C", "severity": "Critical"}, target="sev.test")

    results = db.search_findings(severity="Critical")
    assert len(results) == 2


def test_search_by_status(db):
    aid = db.create_assessment("st.test")
    fid = db.add_finding(aid, {"title": "Open Bug", "severity": "High"}, target="st.test")
    db.add_finding(aid, {"title": "Other", "severity": "Low"}, target="st.test")
    db.update_status(fid, "resolved")

    results = db.search_findings(status="open")
    assert len(results) == 1
    assert results[0].title == "Other"


def test_search_by_target(db):
    aid = db.create_assessment("multi")
    db.add_finding(aid, {"title": "A", "severity": "High"}, target="alpha.com")
    db.add_finding(aid, {"title": "B", "severity": "Low"}, target="beta.com")

    results = db.search_findings(target="alpha")
    assert len(results) == 1


def test_search_combined_filters(db):
    aid = db.create_assessment("combo")
    db.add_finding(aid, {"title": "SQL Injection", "severity": "Critical"}, target="web.app")
    db.add_finding(aid, {"title": "SQL Injection", "severity": "High"}, target="api.app")
    db.add_finding(aid, {"title": "XSS", "severity": "Critical"}, target="web.app")

    results = db.search_findings(query="SQL", severity="Critical")
    assert len(results) == 1
    assert results[0].target == "web.app"


def test_search_limit_offset(db):
    aid = db.create_assessment("pag.test")
    for i in range(10):
        db.add_finding(aid, {"title": f"Bug {i}", "severity": "Low"}, target=f"host{i}")

    page1 = db.search_findings(limit=3, offset=0)
    page2 = db.search_findings(limit=3, offset=3)
    assert len(page1) == 3
    assert len(page2) == 3
    assert page1[0].id != page2[0].id


def test_get_findings_by_assessment(db):
    a1 = db.create_assessment("a1.test")
    a2 = db.create_assessment("a2.test")
    db.add_finding(a1, {"title": "Bug A", "severity": "High"}, target="a1.test")
    db.add_finding(a2, {"title": "Bug B", "severity": "Low"}, target="a2.test")

    results = db.get_findings_by_assessment(a1)
    assert len(results) == 1
    assert results[0].title == "Bug A"


def test_get_findings_by_target(db):
    aid = db.create_assessment("target.test")
    db.add_finding(aid, {"title": "A", "severity": "High"}, target="srv1")
    db.add_finding(aid, {"title": "B", "severity": "Low"}, target="srv2")

    results = db.get_findings_by_target("srv1")
    assert len(results) == 1


# ── Remediation / Status ────────────────────────────────────────────────────

def test_update_status(db):
    aid = db.create_assessment("status.test")
    fid = db.add_finding(aid, {"title": "Bug", "severity": "High"}, target="status.test")

    assert db.update_status(fid, "in_progress", note="Working on it")
    f = db.get_finding(fid)
    assert f.status == "in_progress"

    assert db.update_status(fid, "resolved", note="Fixed in v2.0")
    f = db.get_finding(fid)
    assert f.status == "resolved"
    assert f.resolved_at is not None


def test_update_status_invalid(db):
    aid = db.create_assessment("inv.test")
    fid = db.add_finding(aid, {"title": "Bug", "severity": "Low"}, target="inv.test")

    with pytest.raises(ValueError, match="Invalid status"):
        db.update_status(fid, "invalid_status")


def test_update_status_not_found(db):
    assert db.update_status(999, "resolved") is False


def test_update_status_noop(db):
    """Updating to the same status is a no-op."""
    aid = db.create_assessment("noop.test")
    fid = db.add_finding(aid, {"title": "Bug", "severity": "Low"}, target="noop.test")
    assert db.update_status(fid, "open") is True  # already open


def test_remediation_log(db):
    aid = db.create_assessment("rlog.test")
    fid = db.add_finding(aid, {"title": "Bug", "severity": "High"}, target="rlog.test")

    db.update_status(fid, "in_progress", note="Investigating")
    db.update_status(fid, "resolved", note="Patched")

    log = db.get_remediation_log(fid)
    assert len(log) == 2
    assert log[0]["old_status"] == "open"
    assert log[0]["new_status"] == "in_progress"
    assert log[0]["note"] == "Investigating"
    assert log[1]["new_status"] == "resolved"


def test_resolved_finding_reopened(db):
    """A resolved finding found again should be reopened."""
    aid = db.create_assessment("reopen.test")
    fid = db.add_finding(aid, {"title": "Bug", "severity": "High"}, target="reopen.test")
    db.update_status(fid, "resolved")

    # Same finding found again
    fid2 = db.add_finding(aid, {"title": "Bug", "severity": "High"}, target="reopen.test")
    assert fid2 == fid  # deduplicated

    f = db.get_finding(fid)
    assert f.status == "open"  # reopened


# ── Risk Scoring ─────────────────────────────────────────────────────────────

def test_calculate_risk_score(db):
    aid = db.create_assessment("risk.test")
    db.add_finding(aid, {"title": "Crit", "severity": "Critical"}, target="risk.test")
    db.add_finding(aid, {"title": "High", "severity": "High"}, target="risk.test")

    score = db.calculate_risk_score("risk.test")
    expected = SEVERITY_WEIGHTS["Critical"] + SEVERITY_WEIGHTS["High"]
    assert score == expected


def test_risk_only_open(db):
    """Risk score only counts open findings."""
    aid = db.create_assessment("ropen.test")
    fid = db.add_finding(aid, {"title": "Resolved", "severity": "Critical"}, target="ropen.test")
    db.update_status(fid, "resolved")
    db.add_finding(aid, {"title": "Open", "severity": "Low"}, target="ropen.test")

    score = db.calculate_risk_score("ropen.test")
    assert score == SEVERITY_WEIGHTS["Low"]


def test_risk_snapshot(db):
    aid = db.create_assessment("snap.test")
    db.add_finding(aid, {"title": "A", "severity": "Critical"}, target="snap.test")
    db.add_finding(aid, {"title": "B", "severity": "Low"}, target="snap.test")

    snap = db.take_risk_snapshot("snap.test")
    assert snap["critical"] == 1
    assert snap["low"] == 1
    assert snap["total"] == 2
    assert snap["risk_score"] > 0


def test_risk_history(db):
    aid = db.create_assessment("hist.test")
    db.add_finding(aid, {"title": "A", "severity": "High"}, target="hist.test")

    db.take_risk_snapshot("hist.test")
    db.take_risk_snapshot("hist.test")

    history = db.get_risk_history("hist.test")
    assert len(history) == 2


# ── Statistics ───────────────────────────────────────────────────────────────

def test_get_stats_empty(db):
    stats = db.get_stats()
    assert stats.total_assessments == 0
    assert stats.total_findings == 0
    assert stats.overall_risk_score == 0.0


def test_get_stats_populated(db):
    a1 = db.create_assessment("a.com")
    a2 = db.create_assessment("b.com")
    db.add_finding(a1, {"title": "X", "severity": "Critical"}, target="a.com")
    db.add_finding(a1, {"title": "Y", "severity": "High"}, target="a.com")
    db.add_finding(a2, {"title": "Z", "severity": "Low"}, target="b.com")

    stats = db.get_stats()
    assert stats.total_assessments == 2
    assert stats.total_findings == 3
    assert stats.unique_targets == 2
    assert stats.open_findings == 3
    assert stats.by_severity.get("Critical") == 1
    assert stats.by_severity.get("High") == 1
    assert stats.by_severity.get("Low") == 1
    assert stats.overall_risk_score > 0


def test_get_stats_filtered_by_target(db):
    a1 = db.create_assessment("a.com")
    db.add_finding(a1, {"title": "X", "severity": "High"}, target="a.com")
    db.add_finding(a1, {"title": "Y", "severity": "Low"}, target="b.com")

    stats = db.get_stats("a.com")
    assert stats.total_findings == 1


def test_format_stats(db):
    a1 = db.create_assessment("fmt.test")
    db.add_finding(a1, {"title": "Bug", "severity": "High"}, target="fmt.test")
    text = db.format_stats()
    assert "Vulnerability Database" in text
    assert "High" in text


def test_format_findings_table_empty(db):
    assert db.format_findings_table([]) == "No findings."


def test_format_findings_table(db):
    aid = db.create_assessment("tbl.test")
    db.add_finding(aid, {"title": "Bug A", "severity": "Critical"}, target="tbl.test")
    findings = db.search_findings()
    text = db.format_findings_table(findings)
    assert "Bug A" in text
    assert "Critical" in text


# ── Deletion ─────────────────────────────────────────────────────────────────

def test_delete_finding(db):
    aid = db.create_assessment("del.test")
    fid = db.add_finding(aid, {"title": "Temp", "severity": "Info"}, target="del.test")
    assert db.delete_finding(fid)
    assert db.get_finding(fid) is None


def test_delete_finding_not_found(db):
    assert db.delete_finding(999) is False


def test_delete_assessment(db):
    aid = db.create_assessment("delass.test")
    db.add_finding(aid, {"title": "A", "severity": "High"}, target="delass.test")
    db.add_finding(aid, {"title": "B", "severity": "Low"}, target="delass.test")

    assert db.delete_assessment(aid)
    assert db.get_assessment(aid) is None
    assert len(db.get_findings_by_assessment(aid)) == 0


def test_purge_all(db):
    aid = db.create_assessment("purge.test")
    db.add_finding(aid, {"title": "A", "severity": "High"}, target="purge.test")
    db.take_risk_snapshot("purge.test")

    count = db.purge_all()
    assert count >= 2
    assert db.get_stats().total_findings == 0


# ── VulnRecord ───────────────────────────────────────────────────────────────

def test_vuln_record_to_dict(db):
    aid = db.create_assessment("dict.test")
    fid = db.add_finding(
        aid,
        {
            "title": "Test",
            "severity": "Medium",
            "description": "desc",
            "cve_ids": ["CVE-2024-1234"],
            "tags": ["web", "auth"],
        },
        target="dict.test",
    )
    f = db.get_finding(fid)
    d = f.to_dict()
    assert d["title"] == "Test"
    assert d["severity"] == "Medium"
    assert d["cve_ids"] == ["CVE-2024-1234"]
    assert d["tags"] == ["web", "auth"]
    assert "id" in d
    assert "assessment_id" in d


# ── DB size ──────────────────────────────────────────────────────────────────

def test_db_size(db):
    size = db.db_size
    assert "B" in size or "KB" in size or "MB" in size


def test_db_size_no_file(tmp_path):
    db = VulnDB(db_path=tmp_path / "nonexistent_dir" / "test.db")
    # After init, file should exist
    assert db.db_path.exists()


# ── Valid statuses ───────────────────────────────────────────────────────────

def test_valid_statuses():
    assert "open" in VALID_STATUSES
    assert "in_progress" in VALID_STATUSES
    assert "resolved" in VALID_STATUSES
    assert "accepted" in VALID_STATUSES
    assert "false_positive" in VALID_STATUSES


def test_severity_weights():
    assert SEVERITY_WEIGHTS["Critical"] > SEVERITY_WEIGHTS["High"]
    assert SEVERITY_WEIGHTS["High"] > SEVERITY_WEIGHTS["Medium"]
    assert SEVERITY_WEIGHTS["Medium"] > SEVERITY_WEIGHTS["Low"]
    assert SEVERITY_WEIGHTS["Low"] > SEVERITY_WEIGHTS["Info"]
