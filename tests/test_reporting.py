"""Tests for generic (HTML/Markdown/JSON) report generation."""

import json
from pathlib import Path
from unittest.mock import patch

from hackbot.reporting import ReportGenerator


SAMPLE_FINDINGS = [
    {
        "title": "Missing Security Header",
        "severity": "Low",
        "description": "X-Frame-Options not set.",
    }
]


def test_normalize_tool_history_fills_missing_tool_and_command():
    raw = [
        {"command": "nmap -sV example.com", "success": True, "duration": 2.1, "return_code": 0},
        {"tool": "nikto", "command": "", "success": False, "duration": 4.2, "return_code": 1},
        {"success": True},
    ]

    normalized = ReportGenerator._normalize_tool_history(raw)

    assert normalized[0]["tool"] == "nmap"
    assert normalized[0]["command"] == "nmap -sV example.com"
    assert normalized[1]["tool"] == "nikto"
    assert normalized[1]["command"] == "(no command)"
    assert normalized[2]["tool"] == "unknown"
    assert normalized[2]["command"] == "(no command)"


def test_markdown_report_contains_tool_and_command(tmp_path):
    with patch("hackbot.reporting.REPORTS_DIR", tmp_path):
        rg = ReportGenerator(report_format="markdown")
        path = rg.generate(
            target="example.com",
            findings=SAMPLE_FINDINGS,
            tool_history=[{
                "command": "sudo nmap -sV example.com",
                "success": True,
                "duration": 1.2,
                "return_code": 0,
                "stdout": "scan output",
            }],
        )

        text = Path(path).read_text(encoding="utf-8")
        assert "## 4. List of Commands Executed" in text
        assert "## 5. Technical Annex (Agent Output)" in text
        assert "[sudo]" in text
        assert "sudo nmap -sV example.com" in text
        assert "sudo=yes" in text


def test_json_report_contains_normalized_tool_history(tmp_path):
    with patch("hackbot.reporting.REPORTS_DIR", tmp_path):
        rg = ReportGenerator(report_format="json")
        path = rg.generate(
            target="example.com",
            findings=SAMPLE_FINDINGS,
            tool_history=[{"command": "curl -I https://example.com", "success": True}],
        )

        data = json.loads(Path(path).read_text(encoding="utf-8"))
        assert data["tool_history"][0]["tool"] == "curl"
        assert data["tool_history"][0]["command"] == "curl -I https://example.com"
        assert "commands_executed" in data
        assert "technical_annex" in data


def test_html_report_contains_numbered_sections(tmp_path):
    with patch("hackbot.reporting.REPORTS_DIR", tmp_path):
        rg = ReportGenerator(report_format="html")
        path = rg.generate(
            target="example.com",
            findings=SAMPLE_FINDINGS,
            summary="Test summary",
        )

        text = Path(path).read_text(encoding="utf-8")
        assert "1. Executive Summary" in text
        assert "2. Risk Assessment Charts" in text
        assert "3. Detailed Findings" in text


def test_markdown_report_contains_numbered_sections(tmp_path):
    with patch("hackbot.reporting.REPORTS_DIR", tmp_path):
        rg = ReportGenerator(report_format="markdown")
        path = rg.generate(
            target="example.com",
            findings=SAMPLE_FINDINGS,
            summary="Test summary",
        )

        text = Path(path).read_text(encoding="utf-8")
        assert "## 1. Executive Summary" in text
        assert "## 2. Risk Assessment Charts" in text
        assert "## 3. Detailed Findings" in text
        assert "| Severity | Count | Percentage |" in text


def test_json_report_contains_risk_assessment(tmp_path):
    with patch("hackbot.reporting.REPORTS_DIR", tmp_path):
        rg = ReportGenerator(report_format="json")
        path = rg.generate(
            target="example.com",
            findings=SAMPLE_FINDINGS,
        )

        data = json.loads(Path(path).read_text(encoding="utf-8"))
        assert "risk_assessment" in data
        assert len(data["risk_assessment"]) > 0
        assert data["risk_assessment"][0]["severity"] == "Low"
        assert data["risk_assessment"][0]["count"] == 1
        assert "security_posture" in data
        assert data["security_posture"]["score"] == 99
        assert data["security_posture"]["grade"] == "A+"


def test_calculate_security_posture():
    from hackbot.reporting import calculate_security_posture

    findings = [
        {"severity": "Critical", "title": "RCE"},
        {"severity": "High", "title": "SQLi"},
        {"severity": "Medium", "title": "CSRF"},
        {"severity": "Low", "title": "Banner leak"},
    ]
    posture = calculate_security_posture(findings)
    # 100 - (25 + 12 + 5 + 1) = 57 -> grade 'F', risk 'Critical'
    assert posture["score"] == 57
    assert posture["grade"] == "F"
    assert posture["risk_level"] == "Critical"
    assert posture["remediation_hours"] == 16 + 8 + 4 + 1
    assert posture["counts"]["Critical"] == 1


def test_sarif_report_generation(tmp_path):
    with patch("hackbot.reporting.REPORTS_DIR", tmp_path):
        rg = ReportGenerator(report_format="sarif")
        path = rg.generate(
            target="example.com",
            findings=[
                {
                    "title": "SQL Injection",
                    "severity": "Critical",
                    "description": "Union-based SQL injection on id param.",
                    "evidence": "SELECT * FROM users",
                    "recommendation": "Use parameterized queries.",
                }
            ],
        )

        assert path.endswith(".sarif")
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        assert data["version"] == "2.1.0"
        assert "https://raw.githubusercontent.com/oasis-tcs/sarif-spec" in data["$schema"]
        assert len(data["runs"]) == 1
        driver = data["runs"][0]["tool"]["driver"]
        assert driver["name"] == "HackBot"
        assert len(driver["rules"]) == 1
        assert driver["rules"][0]["shortDescription"]["text"] == "SQL Injection"
        results = data["runs"][0]["results"]
        assert len(results) == 1
        assert results[0]["level"] == "error"
        assert "SQL Injection" in results[0]["message"]["text"]


def test_csv_report_generation(tmp_path):
    import csv

    with patch("hackbot.reporting.REPORTS_DIR", tmp_path):
        rg = ReportGenerator(report_format="csv")
        path = rg.generate(
            target="example.com",
            findings=[
                {
                    "title": "Cross-Site Scripting",
                    "severity": "High",
                    "cvss": "7.5",
                    "tool": "nuclei",
                    "description": "Reflected XSS in search query.",
                    "evidence": "<script>alert(1)</script>",
                    "recommendation": "Encode HTML output.",
                }
            ],
        )

        assert path.endswith(".csv")
        with open(path, "r", encoding="utf-8") as f:
            reader = list(csv.reader(f))
            assert reader[0] == ["Title", "Severity", "CVSS", "Tool", "Description", "Evidence", "Recommendation"]
            assert reader[1][0] == "Cross-Site Scripting"
            assert reader[1][1] == "High"
            assert reader[1][2] == "7.5"
            assert reader[1][3] == "nuclei"


