"""
Tests for the MITRE ATT&CK Mapping Engine.
"""

import json

import pytest
from hackbot.core.attack import (
    Tactic,
    Technique,
    TechniqueMapping,
    AttackReport,
    AttackMapper,
    TACTICS,
    TECHNIQUES,
    TACTIC_MAP,
    TACTIC_NAME_MAP,
    TECHNIQUE_MAP,
    TOOL_TECHNIQUE_MAP,
    _FINDING_RULES,
    _build_navigator_layer,
)


# ── Data Model Tests ─────────────────────────────────────────────────────────

class TestTactic:
    """Test Tactic dataclass."""

    def test_basic(self):
        t = Tactic("TA0001", "Initial Access", "initial-access", "Trying to get in.")
        assert t.id == "TA0001"
        assert t.name == "Initial Access"
        assert t.short_name == "initial-access"

    def test_to_dict(self):
        t = Tactic("TA0043", "Reconnaissance", "reconnaissance", "Gather info.")
        d = t.to_dict()
        assert d["id"] == "TA0043"
        assert d["name"] == "Reconnaissance"
        assert d["short_name"] == "reconnaissance"
        assert d["description"] == "Gather info."

    def test_defaults(self):
        t = Tactic("TA0099", "Custom", "custom")
        assert t.description == ""


class TestTechnique:
    """Test Technique dataclass."""

    def test_basic(self):
        t = Technique("T1046", "Network Service Scanning", ["TA0007"])
        assert t.id == "T1046"
        assert t.name == "Network Service Scanning"
        assert "TA0007" in t.tactic_ids

    def test_auto_url(self):
        t = Technique("T1046", "Network Service Scanning", ["TA0007"])
        assert t.url == "https://attack.mitre.org/techniques/T1046/"

    def test_subtechnique_url(self):
        t = Technique("T1059.001", "PowerShell", ["TA0002"], is_subtechnique=True, parent_id="T1059")
        assert t.url == "https://attack.mitre.org/techniques/T1059/001/"
        assert t.is_subtechnique
        assert t.parent_id == "T1059"

    def test_explicit_url(self):
        t = Technique("T1046", "NSS", url="https://custom.url/")
        assert t.url == "https://custom.url/"

    def test_to_dict(self):
        t = Technique("T1046", "NSS", ["TA0007"], "desc", False, "", "")
        d = t.to_dict()
        assert d["id"] == "T1046"
        assert d["name"] == "NSS"
        assert d["tactic_ids"] == ["TA0007"]
        assert d["description"] == "desc"
        assert "url" in d

    def test_defaults(self):
        t = Technique("T9999", "Custom")
        assert t.tactic_ids == []
        assert t.description == ""
        assert t.is_subtechnique is False
        assert t.parent_id == ""


class TestTechniqueMapping:
    """Test TechniqueMapping dataclass."""

    def test_defaults(self):
        t = Technique("T1046", "NSS")
        m = TechniqueMapping(technique=t)
        assert m.source == ""
        assert m.confidence == "medium"
        assert m.severity == ""

    def test_to_dict(self):
        t = Technique("T1046", "NSS", ["TA0007"])
        m = TechniqueMapping(
            technique=t,
            source="finding",
            source_name="Open Port 22",
            confidence="high",
            notes="SSH open",
            severity="Medium",
        )
        d = m.to_dict()
        assert d["technique"]["id"] == "T1046"
        assert d["source"] == "finding"
        assert d["source_name"] == "Open Port 22"
        assert d["confidence"] == "high"
        assert d["severity"] == "Medium"


class TestAttackReport:
    """Test AttackReport dataclass."""

    def test_empty_report(self):
        r = AttackReport()
        d = r.to_dict()
        assert d["total_findings"] == 0
        assert d["total_tools"] == 0
        assert d["total_mappings"] == 0
        assert d["unique_techniques"] == 0
        assert d["by_tactic"] == {}

    def test_to_dict_groups_by_tactic(self):
        t1 = Technique("T1046", "NSS", ["TA0007"])
        t2 = Technique("T1190", "Exploit Public-Facing Application", ["TA0001"])
        r = AttackReport(
            mappings=[
                TechniqueMapping(technique=t1, source="tool", source_name="nmap"),
                TechniqueMapping(technique=t2, source="finding", source_name="SQLi"),
            ],
            target="example.com",
            total_findings=1,
            total_tools=1,
        )
        d = r.to_dict()
        assert d["target"] == "example.com"
        assert d["total_mappings"] == 2
        assert d["unique_techniques"] == 2
        assert d["tactics_covered"] == 2
        assert "Discovery" in d["by_tactic"]
        assert "Initial Access" in d["by_tactic"]

    def test_multi_tactic_technique(self):
        """A technique in multiple tactics appears in each."""
        t = Technique("T1059", "Command and Scripting Interpreter", ["TA0002", "TA0005"])
        r = AttackReport(mappings=[TechniqueMapping(technique=t)])
        d = r.to_dict()
        # Same technique should appear in both tactics
        assert "Execution" in d["by_tactic"]
        assert "Defense Evasion" in d["by_tactic"]
        # But unique_techniques count is still 1
        assert d["unique_techniques"] == 1


# ── Tactic/Technique Database Tests ─────────────────────────────────────────

class TestTacticDatabase:
    """Test the TACTICS catalogue."""

    def test_count(self):
        assert len(TACTICS) == 14

    def test_all_have_ids(self):
        for t in TACTICS:
            assert t.id.startswith("TA0")
            assert t.name
            assert t.short_name

    def test_ids_unique(self):
        ids = [t.id for t in TACTICS]
        assert len(ids) == len(set(ids))

    def test_names_unique(self):
        names = [t.name for t in TACTICS]
        assert len(names) == len(set(names))

    def test_tactic_map_matches(self):
        for t in TACTICS:
            assert t.id in TACTIC_MAP
            assert TACTIC_MAP[t.id].name == t.name

    def test_tactic_name_map_matches(self):
        for t in TACTICS:
            assert t.name in TACTIC_NAME_MAP


class TestTechniqueDatabase:
    """Test the TECHNIQUES catalogue."""

    def test_count(self):
        assert len(TECHNIQUES) >= 50

    def test_all_have_ids(self):
        for t in TECHNIQUES:
            assert t.id.startswith("T1")
            assert t.name
            assert len(t.tactic_ids) >= 1

    def test_ids_unique(self):
        ids = [t.id for t in TECHNIQUES]
        assert len(ids) == len(set(ids))

    def test_all_tactic_ids_valid(self):
        """Every tactic_id on a technique must exist in TACTIC_MAP."""
        for t in TECHNIQUES:
            for tid in t.tactic_ids:
                assert tid in TACTIC_MAP, f"Technique {t.id} references unknown tactic {tid}"

    def test_technique_map_matches(self):
        for t in TECHNIQUES:
            assert t.id in TECHNIQUE_MAP


class TestToolTechniqueMap:
    """Test the TOOL_TECHNIQUE_MAP."""

    def test_not_empty(self):
        assert len(TOOL_TECHNIQUE_MAP) >= 20

    def test_all_techniques_valid(self):
        """Every tech_id in tool mappings must exist in TECHNIQUE_MAP."""
        for tool, mappings in TOOL_TECHNIQUE_MAP.items():
            for tech_id, confidence, notes in mappings:
                assert tech_id in TECHNIQUE_MAP, \
                    f"Tool '{tool}' references unknown technique {tech_id}"
                assert confidence in ("high", "medium", "low")

    def test_common_tools_present(self):
        assert "nmap" in TOOL_TECHNIQUE_MAP
        assert "nikto" in TOOL_TECHNIQUE_MAP
        assert "sqlmap" in TOOL_TECHNIQUE_MAP
        assert "hydra" in TOOL_TECHNIQUE_MAP
        assert "gobuster" in TOOL_TECHNIQUE_MAP


class TestFindingRules:
    """Test the _FINDING_RULES regex patterns."""

    def test_not_empty(self):
        assert len(_FINDING_RULES) >= 20

    def test_patterns_compile(self):
        """All patterns should be compiled regex objects."""
        import re
        for pattern, tech_list, notes in _FINDING_RULES:
            assert hasattr(pattern, "search"), f"Pattern should be compiled regex: {pattern}"

    def test_all_technique_ids_valid(self):
        for pattern, tech_list, notes in _FINDING_RULES:
            for tech_id, confidence in tech_list:
                assert tech_id in TECHNIQUE_MAP, \
                    f"Finding rule references unknown technique {tech_id}"
                assert confidence in ("high", "medium", "low")

    def test_sql_injection_matches(self):
        """SQL injection text should match at least one rule."""
        text = "SQL injection vulnerability found in login form"
        matched = False
        for pattern, tech_list, notes in _FINDING_RULES:
            if pattern.search(text):
                matched = True
                break
        assert matched, "SQL injection text should trigger at least one rule"

    def test_xss_matches(self):
        text = "Cross-site scripting (XSS) in search parameter"
        matched = False
        for pattern, tech_list, notes in _FINDING_RULES:
            if pattern.search(text):
                matched = True
                break
        assert matched, "XSS text should trigger at least one rule"

    def test_open_port_matches(self):
        text = "Open port 22 (SSH) detected"
        matched = False
        for pattern, tech_list, notes in _FINDING_RULES:
            if pattern.search(text):
                matched = True
                break
        assert matched, "Open port text should trigger at least one rule"


# ── AttackMapper Tests ───────────────────────────────────────────────────────

class TestAttackMapper:
    """Test AttackMapper class."""

    def test_instantiate(self):
        m = AttackMapper()
        assert m is not None

    def test_map_empty_findings(self):
        m = AttackMapper()
        r = m.map_findings([], target="test")
        assert r.total_findings == 0
        assert r.mappings == []

    def test_map_findings_basic(self):
        m = AttackMapper()
        findings = [
            {
                "title": "SQL Injection in Login",
                "description": "SQL injection vulnerability found",
                "severity": "Critical",
            },
        ]
        r = m.map_findings(findings, target="example.com")
        assert r.total_findings == 1
        assert r.target == "example.com"
        assert len(r.mappings) >= 1

        # Should map to SQL injection technique
        tech_ids = {m.technique.id for m in r.mappings}
        assert any("T1190" in tid or "T1059" in tid for tid in tech_ids), \
            f"SQLi should map to exploitation or injection technique, got: {tech_ids}"

    def test_map_findings_with_tools(self):
        m = AttackMapper()
        findings = [
            {"title": "Open Port 22", "description": "SSH port open", "severity": "Info"},
        ]
        tool_history = [
            {"tool": "nmap", "command": "nmap -sV target"},
            {"tool": "nikto", "command": "nikto -h target"},
        ]
        r = m.map_findings(findings, target="test", tool_history=tool_history)
        assert r.total_tools == 2

        sources = {m.source for m in r.mappings}
        assert "tool" in sources

    def test_deduplication(self):
        """Same tool appearing twice should not duplicate mappings."""
        m = AttackMapper()
        tool_history = [
            {"tool": "nmap", "command": "nmap -sV target1"},
            {"tool": "nmap", "command": "nmap -sV target2"},
        ]
        r = m.map_findings([], target="test", tool_history=tool_history)
        tech_ids = [mp.technique.id for mp in r.mappings]
        # Each technique should appear only once per tool
        assert len(tech_ids) == len(set(tech_ids))

    def test_map_findings_xss(self):
        m = AttackMapper()
        findings = [
            {
                "title": "Cross-Site Scripting",
                "description": "Reflected XSS in search parameter",
                "severity": "High",
            },
        ]
        r = m.map_findings(findings, target="example.com")
        assert len(r.mappings) >= 1
        has_severity = any(mp.severity == "High" for mp in r.mappings)
        assert has_severity

    def test_map_findings_multiple(self):
        m = AttackMapper()
        findings = [
            {"title": "SQL Injection", "description": "SQLi found", "severity": "Critical"},
            {"title": "Open Port 22", "description": "SSH detected", "severity": "Info"},
            {"title": "Weak Password", "description": "Brute force successful", "severity": "High"},
        ]
        r = m.map_findings(findings, target="multi.example.com")
        assert r.total_findings == 3
        assert len(r.mappings) >= 3

    def test_findings_with_empty_text_skipped(self):
        m = AttackMapper()
        findings = [
            {"title": "", "description": "", "severity": "Info"},
        ]
        r = m.map_findings(findings, target="test")
        assert r.total_findings == 1
        # No mappings from an empty finding
        finding_mappings = [mp for mp in r.mappings if mp.source == "finding"]
        assert len(finding_mappings) == 0


# ── Navigator Layer Tests ────────────────────────────────────────────────────

class TestNavigatorLayer:
    """Test ATT&CK Navigator layer generation."""

    def test_empty_layer(self):
        layer = _build_navigator_layer([], name="Test", description="Test layer")
        assert layer["name"] == "Test"
        assert layer["description"] == "Test layer"
        assert layer["domain"] == "enterprise-attack"
        assert layer["versions"]["layer"] == "4.5"
        assert layer["techniques"] == []

    def test_layer_with_mappings(self):
        t = Technique("T1046", "NSS", ["TA0007"])
        mappings = [TechniqueMapping(technique=t, confidence="high", severity="Critical")]
        layer = _build_navigator_layer(mappings)
        assert len(layer["techniques"]) >= 1
        tech = layer["techniques"][0]
        assert tech["techniqueID"] == "T1046"
        assert tech["score"] > 0
        # Navigator layer uses gradient scoring, not per-technique colors
        assert "score" in tech

    def test_layer_json(self):
        m = AttackMapper()
        findings = [
            {"title": "SQL Injection", "description": "SQLi", "severity": "Critical"},
        ]
        r = m.map_findings(findings, target="test")
        json_str = m.generate_navigator_json(r)
        layer = json.loads(json_str)
        assert "name" in layer
        assert "techniques" in layer
        assert layer["domain"] == "enterprise-attack"

    def test_layer_default_name(self):
        m = AttackMapper()
        r = AttackReport(target="example.com")
        layer = m.generate_navigator_layer(r)
        assert "example.com" in layer["name"]

    def test_layer_custom_name(self):
        m = AttackMapper()
        r = AttackReport(target="example.com")
        layer = m.generate_navigator_layer(r, name="Custom Layer", description="Custom desc")
        assert layer["name"] == "Custom Layer"
        assert layer["description"] == "Custom desc"

    def test_layer_gradient(self):
        layer = _build_navigator_layer([])
        grad = layer.get("gradient", {})
        assert "colors" in grad
        assert len(grad["colors"]) >= 2


# ── Report Formatting Tests ──────────────────────────────────────────────────

class TestFormatReport:
    """Test report formatting methods."""

    def test_format_report_empty(self):
        r = AttackReport(target="test")
        md = AttackMapper.format_report(r)
        assert "MITRE ATT&CK Mapping" in md
        assert "test" in md
        assert "0" in md  # zero mappings

    def test_format_report_with_data(self):
        m = AttackMapper()
        findings = [
            {"title": "SQL Injection", "description": "SQLi in login", "severity": "Critical"},
        ]
        r = m.map_findings(findings, target="example.com")
        md = AttackMapper.format_report(r)
        assert "MITRE ATT&CK" in md
        assert "example.com" in md
        assert "Coverage" in md

    def test_format_report_contains_tactics(self):
        m = AttackMapper()
        findings = [
            {"title": "SQL Injection", "description": "SQLi", "severity": "Critical"},
            {"title": "Open Port 22", "description": "SSH open", "severity": "Info"},
        ]
        tool_history = [{"tool": "nmap", "command": "nmap target"}]
        r = m.map_findings(findings, target="test", tool_history=tool_history)
        md = AttackMapper.format_report(r)
        # Should have at least one tactic heading
        assert "##" in md

    def test_format_summary_empty(self):
        r = AttackReport(target="test")
        s = AttackMapper.format_summary(r)
        assert "ATT&CK" in s
        assert "0" in s

    def test_format_summary_with_data(self):
        m = AttackMapper()
        findings = [
            {"title": "SQL Injection", "description": "SQLi", "severity": "Critical"},
        ]
        r = m.map_findings(findings, target="example.com")
        s = AttackMapper.format_summary(r)
        assert "ATT&CK" in s


# ── Static Helper Tests ──────────────────────────────────────────────────────

class TestStaticHelpers:
    """Test AttackMapper static helper methods."""

    def test_list_tactics(self):
        tactics = AttackMapper.list_tactics()
        assert len(tactics) == 14
        assert all("id" in t and "name" in t for t in tactics)

    def test_list_all_techniques(self):
        techs = AttackMapper.list_techniques()
        assert len(techs) >= 50
        assert all("id" in t and "name" in t for t in techs)

    def test_list_techniques_by_tactic(self):
        techs = AttackMapper.list_techniques("TA0007")  # Discovery
        assert len(techs) >= 1
        assert all("TA0007" in t["tactic_ids"] for t in techs)

    def test_list_techniques_unknown_tactic(self):
        techs = AttackMapper.list_techniques("TA9999")
        assert techs == []

    def test_get_technique_found(self):
        tech = AttackMapper.get_technique("T1046")
        assert tech is not None
        assert tech["id"] == "T1046"
        assert "name" in tech

    def test_get_technique_not_found(self):
        tech = AttackMapper.get_technique("T9999")
        assert tech is None

    def test_get_tool_techniques_nmap(self):
        techs = AttackMapper.get_tool_techniques("nmap")
        assert len(techs) >= 1
        assert all("technique" in t and "confidence" in t for t in techs)

    def test_get_tool_techniques_unknown(self):
        techs = AttackMapper.get_tool_techniques("unknown_tool_xyz")
        assert techs == []

    def test_get_tool_techniques_case_insensitive(self):
        techs1 = AttackMapper.get_tool_techniques("nmap")
        techs2 = AttackMapper.get_tool_techniques("NMAP")
        # Both should lowercase to the same key
        assert len(techs1) == len(techs2)


# ── Edge Case Tests ──────────────────────────────────────────────────────────

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_none_findings(self):
        """Passing empty list should not crash."""
        m = AttackMapper()
        r = m.map_findings([], target="")
        assert r.total_findings == 0

    def test_missing_fields_in_finding(self):
        """Findings with missing fields should be handled gracefully."""
        m = AttackMapper()
        findings = [
            {"severity": "High"},  # no title or description
        ]
        r = m.map_findings(findings, target="test")
        assert r.total_findings == 1

    def test_none_tool_history(self):
        m = AttackMapper()
        r = m.map_findings([], target="test", tool_history=None)
        assert r.total_tools == 0

    def test_tool_history_missing_tool_field(self):
        m = AttackMapper()
        r = m.map_findings([], target="test", tool_history=[{"command": "whoami"}])
        # Should not crash, just not match any tool
        assert r.total_tools == 1

    def test_report_to_dict_is_serializable(self):
        """to_dict() output must be JSON-serializable."""
        m = AttackMapper()
        findings = [
            {"title": "SQL Injection", "description": "SQLi", "severity": "Critical"},
        ]
        tool_history = [{"tool": "nmap", "command": "nmap target"}]
        r = m.map_findings(findings, target="example.com", tool_history=tool_history)
        d = r.to_dict()
        # This should not raise
        json_str = json.dumps(d)
        assert isinstance(json_str, str)

    def test_navigator_layer_is_serializable(self):
        m = AttackMapper()
        findings = [
            {"title": "SQL Injection", "description": "SQLi", "severity": "Critical"},
        ]
        r = m.map_findings(findings, target="test")
        layer = m.generate_navigator_layer(r)
        json_str = json.dumps(layer)
        assert isinstance(json_str, str)

    def test_large_findings_set(self):
        """Ensure mapper handles many findings without errors."""
        m = AttackMapper()
        findings = [
            {"title": f"Finding {i}", "description": f"Description {i}", "severity": "Medium"}
            for i in range(100)
        ]
        r = m.map_findings(findings, target="bulk-test")
        assert r.total_findings == 100

    def test_unicode_in_findings(self):
        m = AttackMapper()
        findings = [
            {"title": "SQL 注入漏洞", "description": "Inyección SQL encontrada", "severity": "Critical"},
        ]
        r = m.map_findings(findings, target="test")
        d = r.to_dict()
        json_str = json.dumps(d, ensure_ascii=False)
        assert "test" in json_str


# ── PDF Integration Smoke Test ───────────────────────────────────────────────

class TestPDFIntegration:
    """Smoke-test that attack_data parameter is accepted by PDFReportGenerator."""

    def test_pdf_generator_accepts_attack_data(self):
        """Ensure the generate() signature accepts attack_data kwarg."""
        from hackbot.core.pdf_report import HAS_REPORTLAB
        if not HAS_REPORTLAB:
            pytest.skip("reportlab not installed")

        from hackbot.core.pdf_report import PDFReportGenerator
        import inspect
        sig = inspect.signature(PDFReportGenerator.generate)
        assert "attack_data" in sig.parameters
