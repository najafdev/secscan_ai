"""
Tests for the Compliance Mapping Engine.
"""

import pytest
from hackbot.core.compliance import (
    Framework,
    Control,
    ControlMapping,
    ComplianceReport,
    ComplianceMapper,
    PCI_DSS_CONTROLS,
    NIST_CONTROLS,
    OWASP_CONTROLS,
    ISO_CONTROLS,
)


# ── Data Model Tests ─────────────────────────────────────────────────────────

class TestFramework:
    """Test Framework enum."""

    def test_values(self):
        assert Framework.PCI_DSS.value == "PCI DSS v4.0"
        assert Framework.NIST_800_53.value == "NIST 800-53 Rev 5"
        assert Framework.OWASP_TOP_10.value == "OWASP Top 10 (2021)"
        assert Framework.ISO_27001.value == "ISO 27001:2022"

    def test_member_count(self):
        assert len(Framework) == 4


class TestControl:
    """Test Control dataclass."""

    def test_basic(self):
        c = Control("PCI DSS v4.0", "6.2.4", "Secure coding practices",
                     "Prevent common attacks.", "Secure Development")
        assert c.framework == "PCI DSS v4.0"
        assert c.control_id == "6.2.4"
        assert c.title == "Secure coding practices"
        assert c.family == "Secure Development"

    def test_to_dict(self):
        c = Control("NIST", "AC-2", "Account Management", "Manage accounts", "Access Control")
        d = c.to_dict()
        assert d == {
            "framework": "NIST",
            "control_id": "AC-2",
            "title": "Account Management",
            "description": "Manage accounts",
            "family": "Access Control",
        }

    def test_defaults(self):
        c = Control("fw", "id", "title")
        assert c.description == ""
        assert c.family == ""


class TestControlMapping:
    """Test ControlMapping dataclass."""

    def test_defaults(self):
        c = Control("fw", "id", "title")
        m = ControlMapping(control=c)
        assert m.status == "fail"
        assert m.notes == ""
        assert m.finding_title == ""

    def test_to_dict(self):
        c = Control("fw", "C-1", "Test Control", "desc", "fam")
        m = ControlMapping(control=c, status="warn", notes="Some note", finding_title="SQLi")
        d = m.to_dict()
        assert d["status"] == "warn"
        assert d["notes"] == "Some note"
        assert d["finding_title"] == "SQLi"
        assert d["control"]["control_id"] == "C-1"


class TestComplianceReport:
    """Test ComplianceReport dataclass."""

    def test_empty_report(self):
        r = ComplianceReport()
        d = r.to_dict()
        assert d["total_findings"] == 0
        assert d["mappings"] == {}
        assert d["summary"] == {}
        assert d["frameworks"] == []

    def test_to_dict_groups_by_framework(self):
        c1 = Control("PCI DSS v4.0", "6.2.4", "Secure coding")
        c2 = Control("NIST 800-53 Rev 5", "SI-10", "Input Validation")
        r = ComplianceReport(
            frameworks=["PCI DSS v4.0", "NIST 800-53 Rev 5"],
            mappings=[
                ControlMapping(control=c1, status="fail", finding_title="SQLi"),
                ControlMapping(control=c2, status="warn", finding_title="XSS"),
            ],
            target="example.com",
            total_findings=2,
        )
        d = r.to_dict()
        assert d["target"] == "example.com"
        assert d["total_findings"] == 2
        assert "PCI DSS v4.0" in d["mappings"]
        assert "NIST 800-53 Rev 5" in d["mappings"]
        assert d["summary"]["PCI DSS v4.0"]["fail"] == 1
        assert d["summary"]["NIST 800-53 Rev 5"]["warn"] == 1


# ── Control Database Tests ───────────────────────────────────────────────────

class TestControlDatabases:
    """Test that control databases are well-formed."""

    def test_pci_dss_controls_count(self):
        assert len(PCI_DSS_CONTROLS) >= 20

    def test_nist_controls_count(self):
        assert len(NIST_CONTROLS) >= 20

    def test_owasp_controls_count(self):
        assert len(OWASP_CONTROLS) == 10

    def test_iso_controls_count(self):
        assert len(ISO_CONTROLS) >= 19

    def test_all_controls_have_ids(self):
        for clist in [PCI_DSS_CONTROLS, NIST_CONTROLS, OWASP_CONTROLS, ISO_CONTROLS]:
            for c in clist:
                assert c.control_id
                assert c.title
                assert c.framework

    def test_pci_ids_unique(self):
        ids = [c.control_id for c in PCI_DSS_CONTROLS]
        assert len(ids) == len(set(ids))

    def test_nist_ids_unique(self):
        ids = [c.control_id for c in NIST_CONTROLS]
        assert len(ids) == len(set(ids))

    def test_owasp_ids_unique(self):
        ids = [c.control_id for c in OWASP_CONTROLS]
        assert len(ids) == len(set(ids))

    def test_iso_ids_unique(self):
        ids = [c.control_id for c in ISO_CONTROLS]
        assert len(ids) == len(set(ids))


# ── ComplianceMapper Tests ───────────────────────────────────────────────────

class TestComplianceMapper:
    """Test the ComplianceMapper engine."""

    def test_init_all_frameworks(self):
        m = ComplianceMapper()
        assert sorted(m.frameworks) == ["iso", "nist", "owasp", "pci"]

    def test_init_specific_frameworks(self):
        m = ComplianceMapper(frameworks=["pci", "owasp"])
        assert sorted(m.frameworks) == ["owasp", "pci"]

    def test_init_alias_normalization(self):
        m = ComplianceMapper(frameworks=["PCI-DSS", "NIST-800-53", "OWASP-Top-10", "ISO-27001"])
        assert sorted(m.frameworks) == ["iso", "nist", "owasp", "pci"]

    def test_init_alias_pcidss(self):
        m = ComplianceMapper(frameworks=["pcidss"])
        assert "pci" in m.frameworks

    def test_init_alias_top10(self):
        m = ComplianceMapper(frameworks=["top10"])
        assert "owasp" in m.frameworks

    def test_init_alias_iso27k(self):
        m = ComplianceMapper(frameworks=["iso27k"])
        assert "iso" in m.frameworks

    def test_map_empty_findings(self):
        m = ComplianceMapper()
        report = m.map_findings([], target="test.com")
        assert report.total_findings == 0
        assert len(report.mappings) == 0

    def test_map_sql_injection(self):
        m = ComplianceMapper()
        findings = [{
            "title": "SQL Injection in login form",
            "description": "Parameter 'user' is vulnerable to blind SQL injection.",
            "severity": "Critical",
            "evidence": "sqlmap found injectable parameter",
            "recommendation": "Use parameterized queries",
        }]
        report = m.map_findings(findings, target="example.com")
        assert report.total_findings == 1
        assert len(report.mappings) > 0

        # Should map to OWASP A03:2021 (Injection)
        ctrl_ids = [m.control.control_id for m in report.mappings]
        assert "A03:2021" in ctrl_ids

        # Should map to PCI DSS 6.2.4
        assert "6.2.4" in ctrl_ids

        # All should be fail status for Critical severity
        for mapping in report.mappings:
            assert mapping.status == "fail"

    def test_map_xss(self):
        m = ComplianceMapper()
        findings = [{
            "title": "Reflected XSS in search",
            "description": "Cross-site scripting vulnerability",
            "severity": "High",
        }]
        report = m.map_findings(findings)
        ctrl_ids = [m.control.control_id for m in report.mappings]
        assert "A03:2021" in ctrl_ids  # OWASP Injection
        assert "6.2.4" in ctrl_ids      # PCI Secure Coding

    def test_map_ssl_tls(self):
        m = ComplianceMapper()
        findings = [{
            "title": "Expired SSL Certificate",
            "description": "The TLS certificate has expired",
            "severity": "High",
        }]
        report = m.map_findings(findings)
        ctrl_ids = [m.control.control_id for m in report.mappings]
        assert "A02:2021" in ctrl_ids  # OWASP Cryptographic Failures
        assert "4.2.1" in ctrl_ids      # PCI Strong Cryptography

    def test_map_auth_weakness(self):
        m = ComplianceMapper()
        findings = [{
            "title": "Weak Password Policy",
            "description": "Brute force attack succeeded with default credentials",
            "severity": "Critical",
        }]
        report = m.map_findings(findings)
        ctrl_ids = [m.control.control_id for m in report.mappings]
        assert "A07:2021" in ctrl_ids  # OWASP Auth Failures
        assert "8.3.1" in ctrl_ids      # PCI Strong Auth

    def test_map_access_control(self):
        m = ComplianceMapper()
        findings = [{
            "title": "Broken Access Control - IDOR",
            "description": "Insecure Direct Object Reference allows unauthorized access",
            "severity": "High",
        }]
        report = m.map_findings(findings)
        ctrl_ids = [m.control.control_id for m in report.mappings]
        assert "A01:2021" in ctrl_ids  # OWASP Broken Access Control

    def test_map_outdated_components(self):
        m = ComplianceMapper()
        findings = [{
            "title": "Outdated Apache version CVE-2023-1234",
            "description": "Server running end-of-life software with known vulnerabilities",
            "severity": "Medium",
        }]
        report = m.map_findings(findings)
        ctrl_ids = [m.control.control_id for m in report.mappings]
        assert "A06:2021" in ctrl_ids  # OWASP Vulnerable Components

    def test_map_misconfiguration(self):
        m = ComplianceMapper()
        findings = [{
            "title": "Directory Listing Enabled",
            "description": "Information disclosure via directory listing misconfiguration",
            "severity": "Low",
        }]
        report = m.map_findings(findings)
        ctrl_ids = [m.control.control_id for m in report.mappings]
        assert "A05:2021" in ctrl_ids  # OWASP Security Misconfig

        # Low severity should be warn
        for mapping in report.mappings:
            assert mapping.status == "warn"

    def test_map_ssrf(self):
        m = ComplianceMapper()
        findings = [{
            "title": "SSRF via image upload",
            "description": "Server-Side Request Forgery",
            "severity": "High",
        }]
        report = m.map_findings(findings)
        ctrl_ids = [m.control.control_id for m in report.mappings]
        assert "A10:2021" in ctrl_ids  # OWASP SSRF

    def test_map_missing_logging(self):
        m = ComplianceMapper()
        findings = [{
            "title": "No logging configured",
            "description": "Insufficient logging and audit monitoring",
            "severity": "Medium",
        }]
        report = m.map_findings(findings)
        ctrl_ids = [m.control.control_id for m in report.mappings]
        assert "A09:2021" in ctrl_ids  # OWASP Logging Failures

    def test_severity_mapping_critical(self):
        m = ComplianceMapper(frameworks=["owasp"])
        findings = [{"title": "SQL Injection", "severity": "Critical"}]
        report = m.map_findings(findings)
        assert all(m.status == "fail" for m in report.mappings)

    def test_severity_mapping_low(self):
        m = ComplianceMapper(frameworks=["owasp"])
        findings = [{"title": "SQL Injection", "severity": "Low"}]
        report = m.map_findings(findings)
        assert all(m.status == "warn" for m in report.mappings)

    def test_severity_mapping_info(self):
        m = ComplianceMapper(frameworks=["owasp"])
        findings = [{"title": "SQL Injection", "severity": "Info"}]
        report = m.map_findings(findings)
        assert all(m.status == "warn" for m in report.mappings)

    def test_framework_filtering(self):
        m = ComplianceMapper(frameworks=["owasp"])
        findings = [{
            "title": "SQL Injection",
            "description": "sqli found",
            "severity": "High",
        }]
        report = m.map_findings(findings)
        # Only OWASP controls should appear
        for mapping in report.mappings:
            assert mapping.control.framework == Framework.OWASP_TOP_10.value

    def test_deduplication(self):
        m = ComplianceMapper(frameworks=["owasp"])
        findings = [
            {"title": "SQL Injection in param A", "severity": "High"},
            {"title": "SQL Injection in param B", "severity": "High"},
        ]
        report = m.map_findings(findings)
        # A03:2021 should appear twice (once per finding), not more
        a03_count = sum(1 for mp in report.mappings if mp.control.control_id == "A03:2021")
        assert a03_count == 2  # One per finding, deduplicated by finding_title

    def test_multiple_findings_multiple_frameworks(self):
        m = ComplianceMapper()
        findings = [
            {"title": "SQL Injection", "severity": "Critical"},
            {"title": "Weak Password Policy", "severity": "High"},
            {"title": "Expired SSL Certificate", "severity": "Medium"},
        ]
        report = m.map_findings(findings, target="target.com")
        assert report.total_findings == 3
        assert len(report.mappings) > 5  # Should produce many mappings

        # Check all 4 frameworks are represented
        frameworks_seen = set(m.control.framework for m in report.mappings)
        assert len(frameworks_seen) >= 3  # At least 3 frameworks should be hit

    def test_no_match_findings(self):
        m = ComplianceMapper()
        findings = [{"title": "System uptime is 99.9%", "severity": "Info"}]
        report = m.map_findings(findings)
        assert len(report.mappings) == 0

    def test_report_target(self):
        m = ComplianceMapper()
        report = m.map_findings([], target="192.168.1.1")
        assert report.target == "192.168.1.1"

    def test_report_frameworks_list(self):
        m = ComplianceMapper(frameworks=["pci", "nist"])
        report = m.map_findings([])
        assert Framework.PCI_DSS.value in report.frameworks
        assert Framework.NIST_800_53.value in report.frameworks
        assert Framework.OWASP_TOP_10.value not in report.frameworks


class TestComplianceMapperStatic:
    """Test static methods of ComplianceMapper."""

    def test_list_frameworks(self):
        fws = ComplianceMapper.list_frameworks()
        assert len(fws) == 4
        keys = [f["key"] for f in fws]
        assert "pci" in keys
        assert "nist" in keys
        assert "owasp" in keys
        assert "iso" in keys
        for f in fws:
            assert "name" in f
            assert "controls" in f
            assert f["controls"] > 0

    def test_get_framework_controls_pci(self):
        controls = ComplianceMapper.get_framework_controls("pci")
        assert len(controls) == len(PCI_DSS_CONTROLS)

    def test_get_framework_controls_nist(self):
        controls = ComplianceMapper.get_framework_controls("nist")
        assert len(controls) == len(NIST_CONTROLS)

    def test_get_framework_controls_owasp(self):
        controls = ComplianceMapper.get_framework_controls("owasp")
        assert len(controls) == len(OWASP_CONTROLS)

    def test_get_framework_controls_iso(self):
        controls = ComplianceMapper.get_framework_controls("iso")
        assert len(controls) == len(ISO_CONTROLS)

    def test_get_framework_controls_alias(self):
        controls = ComplianceMapper.get_framework_controls("pcidss")
        assert len(controls) == len(PCI_DSS_CONTROLS)

    def test_get_framework_controls_unknown(self):
        controls = ComplianceMapper.get_framework_controls("unknown_fw")
        assert controls == []

    def test_format_report_empty(self):
        report = ComplianceReport()
        md = ComplianceMapper.format_report(report)
        assert "# 📋 Compliance Mapping Report" in md
        assert "No compliance gaps identified" in md

    def test_format_report_with_mappings(self):
        c1 = Control("PCI DSS v4.0", "6.2.4", "Secure coding", "", "Secure Development")
        c2 = Control("OWASP Top 10 (2021)", "A03:2021", "Injection", "", "Injection")
        report = ComplianceReport(
            frameworks=["PCI DSS v4.0", "OWASP Top 10 (2021)"],
            mappings=[
                ControlMapping(control=c1, status="fail", finding_title="SQLi"),
                ControlMapping(control=c2, status="fail", finding_title="SQLi"),
            ],
            target="example.com",
            total_findings=1,
        )
        md = ComplianceMapper.format_report(report)
        assert "example.com" in md
        assert "Executive Summary" in md
        assert "6.2.4" in md
        assert "A03:2021" in md
        assert "🔴 FAIL" in md
        assert "Gap Analysis" in md
        assert "2** controls failing" in md
        assert "Top Failing Control Families" in md
        assert "HackBot Compliance Mapper" in md

    def test_format_report_status_icons(self):
        c = Control("fw", "C-1", "Test")
        for status, icon in [("fail", "🔴"), ("warn", "🟡"), ("pass", "🟢"), ("not_tested", "⚪")]:
            report = ComplianceReport(
                frameworks=["fw"],
                mappings=[ControlMapping(control=c, status=status, finding_title="f")],
                total_findings=1,
            )
            md = ComplianceMapper.format_report(report)
            assert icon in md
