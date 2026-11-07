"""
Tests for the Professional PDF Report Generator.
"""

import os
import time
import pytest
from unittest.mock import patch, MagicMock

from hackbot.core.pdf_report import (
    PDFReportGenerator,
    HAS_REPORTLAB,
    HAS_MATPLOTLIB,
    SEVERITY_COLORS,
    SEVERITY_COLORS_MPL,
    SEVERITY_ORDER,
    LIKELIHOOD_LEVELS,
    _severity_bar_chart,
    _severity_pie_chart,
    _risk_matrix_chart,
    _build_styles,
)


# Skip entire module if reportlab not installed
pytestmark = pytest.mark.skipif(not HAS_REPORTLAB, reason="reportlab not installed")


# ── Sample Data ──────────────────────────────────────────────────────────────

SAMPLE_FINDINGS = [
    {
        "title": "SQL Injection in login form",
        "severity": "Critical",
        "description": "Parameter 'user' is vulnerable to blind SQL injection.",
        "evidence": "sqlmap --url http://example.com/login --data user=test",
        "recommendation": "Use parameterized queries",
        "tool": "sqlmap",
    },
    {
        "title": "Weak TLS Configuration",
        "severity": "High",
        "description": "Server supports TLS 1.0 and weak ciphers.",
        "evidence": "",
        "recommendation": "Upgrade to TLS 1.2+",
        "tool": "sslscan",
    },
    {
        "title": "Directory Listing Enabled",
        "severity": "Medium",
        "description": "Open directory listing on /images/",
        "recommendation": "Disable directory listing in web server config",
    },
    {
        "title": "Missing X-Frame-Options",
        "severity": "Low",
        "description": "X-Frame-Options header not set.",
        "recommendation": "Add X-Frame-Options: DENY header",
    },
    {
        "title": "Server Version Disclosure",
        "severity": "Info",
        "description": "Apache/2.4.49 disclosed in server header.",
        "recommendation": "Remove server version from HTTP headers",
    },
]

SAMPLE_TOOL_HISTORY = [
    {
        "command": "nmap -sV example.com",
        "success": True,
        "duration": 12.5,
        "return_code": 0,
        "stdout": "Nmap scan results...",
    },
    {
        "command": "nikto -h example.com",
        "success": True,
        "duration": 45.2,
        "return_code": 0,
        "stdout": "Nikto scan complete...",
    },
    {
        "command": "hydra -l admin -P pass.txt ssh://example.com",
        "success": False,
        "duration": 120.0,
        "return_code": 1,
        "stdout": "",
    },
]

SAMPLE_COMPLIANCE = {
    "target": "example.com",
    "total_findings": 3,
    "frameworks": ["PCI DSS v4.0", "OWASP Top 10 (2021)"],
    "summary": {
        "PCI DSS v4.0": {"fail": 3, "warn": 1, "pass": 0, "not_tested": 0},
        "OWASP Top 10 (2021)": {"fail": 2, "warn": 0, "pass": 0, "not_tested": 0},
    },
    "mappings": {
        "PCI DSS v4.0": [
            {
                "control": {"framework": "PCI DSS v4.0", "control_id": "6.2.4",
                            "title": "Secure coding", "description": "", "family": "Secure Development"},
                "status": "fail",
                "notes": "Finding...",
                "finding_title": "SQL Injection in login form",
            },
        ],
        "OWASP Top 10 (2021)": [
            {
                "control": {"framework": "OWASP Top 10 (2021)", "control_id": "A03:2021",
                            "title": "Injection", "description": "", "family": "Injection"},
                "status": "fail",
                "notes": "Finding...",
                "finding_title": "SQL Injection in login form",
            },
        ],
    },
}


# ── Constants Tests ──────────────────────────────────────────────────────────

class TestConstants:
    """Test module-level constants."""

    def test_severity_order(self):
        assert SEVERITY_ORDER == ["Critical", "High", "Medium", "Low", "Info"]

    def test_severity_colors_keys(self):
        for sev in SEVERITY_ORDER:
            assert sev in SEVERITY_COLORS
            assert sev in SEVERITY_COLORS_MPL

    def test_likelihood_levels(self):
        assert len(LIKELIHOOD_LEVELS) == 5
        assert "Very Low" in LIKELIHOOD_LEVELS
        assert "Very High" in LIKELIHOOD_LEVELS


# ── Chart Tests ──────────────────────────────────────────────────────────────

class TestCharts:
    """Test chart generation functions."""

    @pytest.mark.skipif(not HAS_MATPLOTLIB, reason="matplotlib not installed")
    def test_bar_chart_returns_png(self):
        counts = {"Critical": 2, "High": 3, "Medium": 1}
        result = _severity_bar_chart(counts)
        assert result is not None
        assert isinstance(result, bytes)
        assert result[:4] == b"\x89PNG"  # PNG magic bytes

    @pytest.mark.skipif(not HAS_MATPLOTLIB, reason="matplotlib not installed")
    def test_bar_chart_empty(self):
        result = _severity_bar_chart({})
        assert result is None

    @pytest.mark.skipif(not HAS_MATPLOTLIB, reason="matplotlib not installed")
    def test_pie_chart_returns_png(self):
        counts = {"Critical": 1, "High": 2, "Low": 3}
        result = _severity_pie_chart(counts)
        assert result is not None
        assert isinstance(result, bytes)
        assert result[:4] == b"\x89PNG"

    @pytest.mark.skipif(not HAS_MATPLOTLIB, reason="matplotlib not installed")
    def test_pie_chart_empty(self):
        result = _severity_pie_chart({})
        assert result is None

    @pytest.mark.skipif(not HAS_MATPLOTLIB, reason="matplotlib not installed")
    def test_risk_matrix_returns_png(self):
        counts = {"Critical": 1, "High": 1}
        result = _risk_matrix_chart(counts)
        assert result is not None
        assert isinstance(result, bytes)
        assert result[:4] == b"\x89PNG"


# ── Styles Tests ─────────────────────────────────────────────────────────────

class TestStyles:
    """Test style builder."""

    def test_build_styles_returns_dict(self):
        styles = _build_styles()
        assert isinstance(styles, dict)
        assert "cover_title" in styles
        assert "h1" in styles
        assert "body" in styles
        assert "evidence" in styles
        assert "finding_title" in styles
        assert "recommendation" in styles

    def test_all_expected_styles(self):
        expected = [
            "cover_title", "cover_subtitle", "cover_meta",
            "h1", "h2", "h3", "body", "body_dim",
            "finding_title", "evidence", "recommendation",
            "toc", "footer",
        ]
        styles = _build_styles()
        for name in expected:
            assert name in styles, f"Missing style: {name}"


# ── PDFReportGenerator Tests ────────────────────────────────────────────────

class TestPDFReportGenerator:
    """Test main PDF report generation."""

    def test_init(self):
        gen = PDFReportGenerator()
        assert gen.include_raw is True
        assert gen.styles is not None

    def test_init_no_raw(self):
        gen = PDFReportGenerator(include_raw=False)
        assert gen.include_raw is False

    def test_generate_creates_file(self, tmp_path):
        with patch("hackbot.core.pdf_report.REPORTS_DIR", tmp_path):
            gen = PDFReportGenerator()
            path = gen.generate(
                target="test.example.com",
                findings=SAMPLE_FINDINGS,
                scope="Full assessment",
            )
            assert os.path.exists(path)
            assert path.endswith(".pdf")
            assert os.path.getsize(path) > 1000

    def test_generate_with_tool_history(self, tmp_path):
        with patch("hackbot.core.pdf_report.REPORTS_DIR", tmp_path):
            gen = PDFReportGenerator()
            path = gen.generate(
                target="test.example.com",
                findings=SAMPLE_FINDINGS,
                tool_history=SAMPLE_TOOL_HISTORY,
            )
            assert os.path.exists(path)
            assert os.path.getsize(path) > 1000

    def test_tool_history_normalization(self):
        gen = PDFReportGenerator()
        rows = gen._normalize_tool_history([
            {"command": "sudo nmap -sV example.com", "success": True, "stdout": "ok"},
            {"tool": "nikto", "command": "", "success": False},
            {},
        ])
        assert rows[0]["tool"] == "nmap"
        assert rows[0]["command"] == "sudo nmap -sV example.com"
        assert rows[0]["sudo_used"] is True
        assert rows[0]["annex_output"] == "ok"
        assert rows[1]["tool"] == "nikto"
        assert rows[1]["command"] == "(no command)"
        assert rows[2]["tool"] == "unknown"
        assert rows[2]["command"] == "(no command)"

    def test_generate_with_compliance(self, tmp_path):
        with patch("hackbot.core.pdf_report.REPORTS_DIR", tmp_path):
            gen = PDFReportGenerator()
            path = gen.generate(
                target="test.example.com",
                findings=SAMPLE_FINDINGS,
                compliance_data=SAMPLE_COMPLIANCE,
            )
            assert os.path.exists(path)
            assert os.path.getsize(path) > 1000

    def test_generate_full_report(self, tmp_path):
        with patch("hackbot.core.pdf_report.REPORTS_DIR", tmp_path):
            gen = PDFReportGenerator()
            path = gen.generate(
                target="example.com",
                findings=SAMPLE_FINDINGS,
                tool_history=SAMPLE_TOOL_HISTORY,
                scope="External penetration test",
                summary="The assessment found 5 vulnerabilities.",
                start_time=time.time() - 3600,
                compliance_data=SAMPLE_COMPLIANCE,
            )
            assert os.path.exists(path)
            size = os.path.getsize(path)
            assert size > 5000  # Should have charts + tables + content

    def test_generate_empty_findings(self, tmp_path):
        with patch("hackbot.core.pdf_report.REPORTS_DIR", tmp_path):
            gen = PDFReportGenerator()
            path = gen.generate(target="empty.com", findings=[])
            assert os.path.exists(path)

    def test_generate_single_finding(self, tmp_path):
        with patch("hackbot.core.pdf_report.REPORTS_DIR", tmp_path):
            gen = PDFReportGenerator()
            path = gen.generate(
                target="single.com",
                findings=[SAMPLE_FINDINGS[0]],
            )
            assert os.path.exists(path)

    def test_filename_format(self, tmp_path):
        with patch("hackbot.core.pdf_report.REPORTS_DIR", tmp_path):
            gen = PDFReportGenerator()
            path = gen.generate(target="10.0.0.1:8080", findings=[])
            filename = os.path.basename(path)
            assert filename.startswith("report_10.0.0.1_8080_")
            assert filename.endswith(".pdf")

    def test_safe_escaping(self):
        result = PDFReportGenerator._safe("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_risk_label(self):
        assert "immediate" in PDFReportGenerator._risk_label("Critical").lower()
        assert "30 days" in PDFReportGenerator._risk_label("High")
        assert "90 days" in PDFReportGenerator._risk_label("Medium")
        assert "next opportunity" in PDFReportGenerator._risk_label("Low").lower()
        assert "informational" in PDFReportGenerator._risk_label("Info").lower()

    def test_count_severities(self):
        counts = PDFReportGenerator._count_severities(SAMPLE_FINDINGS)
        assert counts["Critical"] == 1
        assert counts["High"] == 1
        assert counts["Medium"] == 1
        assert counts["Low"] == 1
        assert counts["Info"] == 1

    def test_count_severities_empty(self):
        counts = PDFReportGenerator._count_severities([])
        assert counts == {}

    def test_special_characters_in_findings(self, tmp_path):
        """Test that findings with XML-special characters don't crash the PDF."""
        with patch("hackbot.core.pdf_report.REPORTS_DIR", tmp_path):
            weird_findings = [
                {
                    "title": 'XSS <script>alert("test")</script>',
                    "severity": "High",
                    "description": "Chars: < > & \" '",
                    "evidence": '<img src=x onerror="alert(1)">',
                    "recommendation": "Filter & encode output",
                },
            ]
            gen = PDFReportGenerator()
            path = gen.generate(target="xss-test.com", findings=weird_findings)
            assert os.path.exists(path)


class TestPDFReportGeneratorNoReportlab:
    """Test error handling when reportlab is not installed."""

    def test_raises_without_reportlab(self):
        with patch("hackbot.core.pdf_report.HAS_REPORTLAB", False):
            # The class checks HAS_REPORTLAB at init time
            with pytest.raises(ImportError, match="reportlab"):
                PDFReportGenerator()
