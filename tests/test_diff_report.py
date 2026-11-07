"""
Tests for HackBot Diff Report Module
======================================
"""

import json
import time
import tempfile
from pathlib import Path

import pytest

from hackbot.core.diff_report import (
    DiffEngine,
    DiffFinding,
    DiffReport,
    DiffStatus,
    SeverityDelta,
    TrendDirection,
    _finding_fingerprint,
    _match_findings,
    _normalize,
    _risk_score,
    _similarity,
    _trend_icon,
    list_agent_sessions,
    load_session_findings,
    MATCH_THRESHOLD,
    SEVERITY_ORDER,
)


# ── Helper Factories ─────────────────────────────────────────────────────────

def make_finding(title="SQL Injection", severity="High", description="Found SQLi",
                 evidence="", recommendation="Parameterize queries", tool="sqlmap"):
    return {
        "title": title,
        "severity": severity,
        "description": description,
        "evidence": evidence,
        "recommendation": recommendation,
        "tool": tool,
        "timestamp": time.time(),
    }


def make_session(session_id="test_1", name="Agent: 10.0.0.1", target="10.0.0.1",
                 findings=None, mode="agent"):
    return {
        "id": session_id,
        "mode": mode,
        "name": name,
        "target": target,
        "created": time.time() - 3600,
        "updated": time.time() - 3600,
        "findings": findings or [],
        "messages": [],
        "message_count": 0,
    }


# ── Basic Data Classes ───────────────────────────────────────────────────────

class TestDiffStatus:
    def test_enum_values(self):
        assert DiffStatus.NEW.value == "New"
        assert DiffStatus.FIXED.value == "Fixed"
        assert DiffStatus.PERSISTENT.value == "Persistent"
        assert DiffStatus.REGRESSION.value == "Regression"


class TestTrendDirection:
    def test_enum_values(self):
        assert TrendDirection.IMPROVED.value == "Improved"
        assert TrendDirection.DEGRADED.value == "Degraded"
        assert TrendDirection.UNCHANGED.value == "Unchanged"


class TestDiffFinding:
    def test_to_dict_basic(self):
        f = DiffFinding(
            title="XSS", severity="Medium", description="Cross-site scripting",
            status=DiffStatus.NEW, tool="burp",
        )
        d = f.to_dict()
        assert d["title"] == "XSS"
        assert d["severity"] == "Medium"
        assert d["status"] == "New"
        assert d["tool"] == "burp"
        assert "old_severity" not in d  # empty string not included

    def test_to_dict_with_severity_change(self):
        f = DiffFinding(
            title="XSS", severity="High", description="Upgraded",
            status=DiffStatus.PERSISTENT, old_severity="Medium",
        )
        d = f.to_dict()
        assert d["old_severity"] == "Medium"
        assert d["status"] == "Persistent"


class TestSeverityDelta:
    def test_positive_delta(self):
        sd = SeverityDelta(severity="High", old_count=2, new_count=5)
        assert sd.delta == 3
        assert sd.direction == "↑"

    def test_negative_delta(self):
        sd = SeverityDelta(severity="High", old_count=5, new_count=2)
        assert sd.delta == -3
        assert sd.direction == "↓"

    def test_zero_delta(self):
        sd = SeverityDelta(severity="Medium", old_count=3, new_count=3)
        assert sd.delta == 0
        assert sd.direction == "—"

    def test_to_dict(self):
        sd = SeverityDelta(severity="Critical", old_count=1, new_count=3)
        d = sd.to_dict()
        assert d["severity"] == "Critical"
        assert d["delta"] == 2
        assert d["direction"] == "↑"


class TestDiffReport:
    def test_total_old(self):
        report = DiffReport(
            target="t", old_session_id="a", new_session_id="b",
            fixed_findings=[DiffFinding("X", "H", "d", DiffStatus.FIXED)],
            persistent_findings=[
                DiffFinding("Y", "M", "d2", DiffStatus.PERSISTENT),
                DiffFinding("Z", "L", "d3", DiffStatus.PERSISTENT),
            ],
        )
        assert report.total_old == 3

    def test_total_new(self):
        report = DiffReport(
            target="t", old_session_id="a", new_session_id="b",
            new_findings=[DiffFinding("X", "H", "d", DiffStatus.NEW)],
            persistent_findings=[DiffFinding("Y", "M", "d2", DiffStatus.PERSISTENT)],
            regression_findings=[DiffFinding("Z", "L", "d3", DiffStatus.REGRESSION)],
        )
        assert report.total_new == 3

    def test_summary_text(self):
        report = DiffReport(
            target="t", old_session_id="a", new_session_id="b",
            new_findings=[DiffFinding("X", "H", "d", DiffStatus.NEW)],
            fixed_findings=[
                DiffFinding("A", "M", "d", DiffStatus.FIXED),
                DiffFinding("B", "L", "d", DiffStatus.FIXED),
            ],
        )
        summary = report.summary_text()
        assert "+1 new" in summary
        assert "-2 fixed" in summary

    def test_summary_text_no_changes(self):
        report = DiffReport(target="t", old_session_id="a", new_session_id="b")
        assert report.summary_text() == "No changes detected"

    def test_to_dict(self):
        report = DiffReport(
            target="10.0.0.1", old_session_id="s1", new_session_id="s2",
            trend=TrendDirection.IMPROVED,
            risk_score_old=17.0, risk_score_new=4.0,
        )
        d = report.to_dict()
        assert d["target"] == "10.0.0.1"
        assert d["trend"] == "Improved"
        assert d["risk_score_old"] == 17.0
        assert d["risk_score_new"] == 4.0
        assert "summary" in d

    def test_to_markdown(self):
        report = DiffReport(
            target="10.0.0.1", old_session_id="s1", new_session_id="s2",
            old_date=time.time() - 86400, new_date=time.time(),
            new_findings=[DiffFinding("New SQL Injection", "Critical", "SQLi in login", DiffStatus.NEW, recommendation="Fix it")],
            fixed_findings=[DiffFinding("Old XSS", "Medium", "Reflected XSS", DiffStatus.FIXED)],
            persistent_findings=[DiffFinding("CSRF", "Low", "CSRF on forms", DiffStatus.PERSISTENT, old_severity="Medium")],
            severity_deltas=[
                SeverityDelta("Critical", 0, 1),
                SeverityDelta("Medium", 1, 0),
            ],
            trend=TrendDirection.DEGRADED,
            risk_score_old=4.0, risk_score_new=10.0,
        )
        md = report.to_markdown()
        assert "# Assessment Diff Report" in md
        assert "10.0.0.1" in md
        assert "New SQL Injection" in md
        assert "Old XSS" in md
        assert "CSRF" in md
        assert "(was Medium)" in md
        assert "Fix it" in md
        assert "New Vulnerabilities (1)" in md
        assert "Fixed Vulnerabilities (1)" in md
        assert "Persistent Vulnerabilities (1)" in md
        assert "Degraded" in md


# ── Utility Functions ────────────────────────────────────────────────────────

class TestNormalize:
    def test_lowercase_strip(self):
        assert _normalize("  SQL Injection  ") == "sql injection"

    def test_empty(self):
        assert _normalize("") == ""


class TestFindingFingerprint:
    def test_basic(self):
        f = make_finding(title="SQL Injection", description="Found in login", tool="sqlmap")
        fp = _finding_fingerprint(f)
        assert "sql injection" in fp
        assert "sqlmap" in fp

    def test_truncates_description(self):
        long_desc = "A" * 200
        f = make_finding(description=long_desc)
        fp = _finding_fingerprint(f)
        parts = fp.split("|")
        assert len(parts[1]) <= 80


class TestSimilarity:
    def test_exact_title_match(self):
        assert _similarity("sqli|desc|sqlmap", "sqli|other|nmap") == 1.0

    def test_partial_token_overlap(self):
        sim = _similarity("sql injection in login|d|sqlmap", "sql injection found|d|sqlmap")
        assert sim >= 0.5

    def test_no_overlap(self):
        sim = _similarity("xss vulnerability|d|nikto", "buffer overflow|d|gdb")
        assert sim < MATCH_THRESHOLD

    def test_tool_boost(self):
        sim_no_tool = _similarity("sql injection|d|", "sql injection found|d|")
        sim_tool = _similarity("sql injection|d|sqlmap", "sql injection found|d|sqlmap")
        assert sim_tool >= sim_no_tool

    def test_empty_tokens(self):
        assert _similarity("||", "||") == 0.0


class TestRiskScore:
    def test_empty(self):
        assert _risk_score([]) == 0.0

    def test_single_critical(self):
        assert _risk_score([make_finding(severity="Critical")]) == 10.0

    def test_mixed(self):
        findings = [
            make_finding(severity="Critical"),
            make_finding(severity="High"),
            make_finding(severity="Medium"),
            make_finding(severity="Low"),
            make_finding(severity="Info"),
        ]
        assert _risk_score(findings) == 10.0 + 7.0 + 4.0 + 1.0 + 0.0

    def test_case_insensitive(self):
        assert _risk_score([make_finding(severity="critical")]) == 10.0
        assert _risk_score([make_finding(severity="HIGH")]) == 7.0


class TestTrendIcon:
    def test_icons(self):
        assert _trend_icon(TrendDirection.IMPROVED) == "📉"
        assert _trend_icon(TrendDirection.DEGRADED) == "📈"
        assert _trend_icon(TrendDirection.UNCHANGED) == "➡️"


# ── Matching Engine ──────────────────────────────────────────────────────────

class TestMatchFindings:
    def test_exact_matches(self):
        old = [make_finding(title="SQL Injection"), make_finding(title="XSS")]
        new = [make_finding(title="SQL Injection"), make_finding(title="XSS")]
        matched, unmatched_old, unmatched_new = _match_findings(old, new)
        assert len(matched) == 2
        assert len(unmatched_old) == 0
        assert len(unmatched_new) == 0

    def test_new_finding(self):
        old = [make_finding(title="SQL Injection")]
        new = [make_finding(title="SQL Injection"), make_finding(title="SSRF")]
        matched, unmatched_old, unmatched_new = _match_findings(old, new)
        assert len(matched) == 1
        assert len(unmatched_new) == 1
        assert unmatched_new[0]["title"] == "SSRF"

    def test_fixed_finding(self):
        old = [make_finding(title="SQL Injection"), make_finding(title="XSS")]
        new = [make_finding(title="XSS")]
        matched, unmatched_old, unmatched_new = _match_findings(old, new)
        assert len(matched) == 1
        assert len(unmatched_old) == 1
        assert unmatched_old[0]["title"] == "SQL Injection"

    def test_empty_old(self):
        old = []
        new = [make_finding(title="XSS")]
        matched, unmatched_old, unmatched_new = _match_findings(old, new)
        assert len(matched) == 0
        assert len(unmatched_new) == 1

    def test_empty_new(self):
        old = [make_finding(title="XSS")]
        new = []
        matched, unmatched_old, unmatched_new = _match_findings(old, new)
        assert len(matched) == 0
        assert len(unmatched_old) == 1

    def test_both_empty(self):
        matched, unmatched_old, unmatched_new = _match_findings([], [])
        assert len(matched) == 0

    def test_no_matches(self):
        old = [make_finding(title="SQL Injection", tool="sqlmap")]
        new = [make_finding(title="Buffer Overflow", tool="gdb")]
        matched, unmatched_old, unmatched_new = _match_findings(old, new)
        assert len(matched) == 0
        assert len(unmatched_old) == 1
        assert len(unmatched_new) == 1


# ── Diff Engine ──────────────────────────────────────────────────────────────

class TestDiffEngine:
    def setup_method(self):
        self.engine = DiffEngine()

    def test_identical_sessions(self):
        findings = [make_finding(title="SQL Injection")]
        old = make_session(findings=findings)
        new = make_session(findings=findings)
        report = self.engine.compare(old, new)
        assert len(report.persistent_findings) == 1
        assert len(report.new_findings) == 0
        assert len(report.fixed_findings) == 0
        assert report.trend == TrendDirection.UNCHANGED

    def test_new_vulnerability(self):
        old = make_session(findings=[make_finding(title="XSS")])
        new = make_session(findings=[
            make_finding(title="XSS"),
            make_finding(title="SQL Injection", severity="Critical"),
        ])
        report = self.engine.compare(old, new)
        assert len(report.new_findings) == 1
        assert report.new_findings[0].title == "SQL Injection"
        assert report.trend == TrendDirection.DEGRADED
        assert report.risk_score_new > report.risk_score_old

    def test_fixed_vulnerability(self):
        old = make_session(findings=[
            make_finding(title="XSS"),
            make_finding(title="SQL Injection", severity="Critical"),
        ])
        new = make_session(findings=[make_finding(title="XSS")])
        report = self.engine.compare(old, new)
        assert len(report.fixed_findings) == 1
        assert report.fixed_findings[0].title == "SQL Injection"
        assert report.trend == TrendDirection.IMPROVED

    def test_severity_change_on_persistent(self):
        old = make_session(findings=[make_finding(title="XSS", severity="Medium")])
        new = make_session(findings=[make_finding(title="XSS", severity="High")])
        report = self.engine.compare(old, new)
        assert len(report.persistent_findings) == 1
        f = report.persistent_findings[0]
        assert f.old_severity == "Medium"
        assert f.severity == "High"

    def test_empty_sessions(self):
        old = make_session(findings=[])
        new = make_session(findings=[])
        report = self.engine.compare(old, new)
        assert report.total_old == 0
        assert report.total_new == 0
        assert report.trend == TrendDirection.UNCHANGED

    def test_all_fixed(self):
        old = make_session(findings=[
            make_finding(title="XSS"),
            make_finding(title="SQLi", severity="Critical"),
        ])
        new = make_session(findings=[])
        report = self.engine.compare(old, new)
        assert len(report.fixed_findings) == 2
        assert report.trend == TrendDirection.IMPROVED

    def test_all_new(self):
        old = make_session(findings=[])
        new = make_session(findings=[
            make_finding(title="XSS"),
            make_finding(title="SQLi", severity="Critical"),
        ])
        report = self.engine.compare(old, new)
        assert len(report.new_findings) == 2
        assert report.trend == TrendDirection.DEGRADED

    def test_severity_deltas(self):
        old = make_session(findings=[
            make_finding(title="A", severity="High"),
            make_finding(title="B", severity="High"),
            make_finding(title="C", severity="Medium"),
        ])
        new = make_session(findings=[
            make_finding(title="A", severity="High"),
            make_finding(title="D", severity="Critical"),
        ])
        report = self.engine.compare(old, new)
        deltas = {sd.severity: sd for sd in report.severity_deltas}
        assert "Critical" in deltas
        assert deltas["Critical"].old_count == 0
        assert deltas["Critical"].new_count == 1

    def test_compare_findings_lists(self):
        """Test convenience method for comparing raw lists."""
        old = [make_finding(title="SQL Injection")]
        new = [make_finding(title="SQL Injection"), make_finding(title="XSS")]
        report = self.engine.compare_findings_lists(old, new, target="example.com")
        assert report.target == "example.com"
        assert len(report.new_findings) == 1
        assert len(report.persistent_findings) == 1

    def test_uses_target_from_new_session(self):
        old = make_session(target="old.com")
        new = make_session(target="new.com")
        report = self.engine.compare(old, new)
        assert report.target == "new.com"

    def test_findings_sorted_by_severity(self):
        old = make_session(findings=[])
        new = make_session(findings=[
            make_finding(title="Low Issue", severity="Low"),
            make_finding(title="Critical Issue", severity="Critical"),
            make_finding(title="Medium Issue", severity="Medium"),
        ])
        report = self.engine.compare(old, new)
        sevs = [f.severity for f in report.new_findings]
        assert sevs == ["Critical", "Medium", "Low"]

    def test_markdown_output_not_empty(self):
        old = make_session(findings=[make_finding(title="XSS")])
        new = make_session(findings=[make_finding(title="SQLi", severity="Critical")])
        report = self.engine.compare(old, new)
        md = report.to_markdown()
        assert len(md) > 100
        assert "Assessment Diff Report" in md


# ── Session Loader ───────────────────────────────────────────────────────────

class TestSessionLoader:
    def test_load_session_exact_match(self, tmp_path):
        session = make_session(session_id="agent_12345", findings=[make_finding()])
        path = tmp_path / "agent_12345.json"
        with open(path, "w") as f:
            json.dump(session, f)

        result = load_session_findings("agent_12345", sessions_dir=tmp_path)
        assert result is not None
        assert result["id"] == "agent_12345"
        assert len(result["findings"]) == 1

    def test_load_session_partial_match(self, tmp_path):
        session = make_session(session_id="agent_12345")
        path = tmp_path / "agent_12345.json"
        with open(path, "w") as f:
            json.dump(session, f)

        result = load_session_findings("12345", sessions_dir=tmp_path)
        assert result is not None

    def test_load_session_not_found(self, tmp_path):
        result = load_session_findings("nonexistent", sessions_dir=tmp_path)
        assert result is None

    def test_load_session_invalid_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json{{{")
        result = load_session_findings("bad", sessions_dir=tmp_path)
        assert result is None

    def test_load_session_nonexistent_dir(self):
        result = load_session_findings("test", sessions_dir=Path("/tmp/nonexistent_hackbot_test"))
        assert result is None

    def test_list_agent_sessions(self, tmp_path):
        s1 = make_session(session_id="agent_1", target="10.0.0.1", findings=[make_finding()])
        s2 = make_session(session_id="agent_2", target="10.0.0.2", findings=[make_finding(), make_finding(title="XSS")])
        s3 = make_session(session_id="chat_1", mode="chat")  # Not agent - should be filtered
        s4 = make_session(session_id="agent_3", findings=[])  # No findings - should be filtered

        for s in [s1, s2, s3, s4]:
            with open(tmp_path / f"{s['id']}.json", "w") as f:
                json.dump(s, f)

        sessions = list_agent_sessions(sessions_dir=tmp_path)
        assert len(sessions) == 2
        ids = {s["id"] for s in sessions}
        assert "agent_1" in ids
        assert "agent_2" in ids
        assert "chat_1" not in ids
        assert "agent_3" not in ids

    def test_list_agent_sessions_empty_dir(self, tmp_path):
        sessions = list_agent_sessions(sessions_dir=tmp_path)
        assert sessions == []

    def test_list_agent_sessions_nonexistent_dir(self):
        sessions = list_agent_sessions(sessions_dir=Path("/tmp/nonexistent_hackbot_test"))
        assert sessions == []

    def test_list_agent_sessions_has_finding_count(self, tmp_path):
        s = make_session(session_id="agent_x", findings=[make_finding(), make_finding(title="XSS")])
        with open(tmp_path / "agent_x.json", "w") as f:
            json.dump(s, f)

        sessions = list_agent_sessions(sessions_dir=tmp_path)
        assert sessions[0]["finding_count"] == 2


# ── Severity Order ───────────────────────────────────────────────────────────

class TestSeverityOrder:
    def test_critical_highest(self):
        assert SEVERITY_ORDER["critical"] > SEVERITY_ORDER["high"]
        assert SEVERITY_ORDER["high"] > SEVERITY_ORDER["medium"]
        assert SEVERITY_ORDER["medium"] > SEVERITY_ORDER["low"]
        assert SEVERITY_ORDER["low"] > SEVERITY_ORDER["info"]


# ── Integration / Edge Cases ─────────────────────────────────────────────────

class TestEdgeCases:
    def setup_method(self):
        self.engine = DiffEngine()

    def test_findings_with_missing_fields(self):
        """Findings with minimal data should still compare."""
        old = [{"title": "Issue A"}]
        new = [{"title": "Issue A"}, {"title": "Issue B"}]
        report = self.engine.compare_findings_lists(old, new)
        assert len(report.persistent_findings) == 1
        assert len(report.new_findings) == 1

    def test_many_findings(self):
        """Ensure engine handles larger sets."""
        old = [make_finding(title=f"Finding {i}") for i in range(50)]
        new = [make_finding(title=f"Finding {i}") for i in range(30, 80)]
        report = self.engine.compare_findings_lists(old, new)
        # 30-49 should be persistent, 0-29 fixed, 50-79 new
        assert len(report.persistent_findings) == 20
        assert len(report.fixed_findings) == 30
        assert len(report.new_findings) == 30

    def test_report_dict_round_trip(self):
        """Ensure to_dict produces valid serializable output."""
        old = make_session(findings=[make_finding()])
        new = make_session(findings=[make_finding(), make_finding(title="XSS")])
        report = self.engine.compare(old, new)
        d = report.to_dict()
        # Should be JSON-serializable
        serialized = json.dumps(d)
        assert isinstance(serialized, str)
        loaded = json.loads(serialized)
        assert loaded["trend"] in ("Improved", "Degraded", "Unchanged")
