# SecScan AI unit test
"""Unit tests for CVE Intelligence and Threat Scoring Engine."""

import pytest
from ai_engine.cve_intelligence import (
    CVEIntelligenceEngine,
    CVEInfo,
    KNOWN_CVE_DATABASE,
)
from ai_engine.advanced_engine import AdvancedAIEngine


def test_cve_info_prioritized_risk_score():
    """Verify prioritized risk score calculation."""
    info = CVEInfo(
        cve_id="CVE-2021-44228",
        title="Log4Shell",
        description="RCE vulnerability",
        cvss_score=10.0,
        cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
        severity="CRITICAL",
        epss_score=0.975,
        epss_percentile=0.999,
        in_cisa_kev=True,
        weaponized=True,
    )
    score = info.prioritized_risk_score
    # Max possible score components: 5.0 + 2.4375 + 1.5 + 1.0 = ~9.94
    assert 9.0 <= score <= 10.0
    d = info.to_dict()
    assert d["cve_id"] == "CVE-2021-44228"
    assert d["in_cisa_kev"] is True


def test_cve_extraction_regex():
    """Verify extraction and deduplication of CVE identifiers."""
    engine = CVEIntelligenceEngine()
    sample_text = (
        "Server is vulnerable to cve-2021-44228 and CVE-2021-44228 (duplicate). "
        "Also found traces of CVE-2017-0144 and CVE-2022-0847."
    )
    cves = engine.extract_cves(sample_text)
    assert len(cves) == 3
    assert "CVE-2021-44228" in cves
    assert "CVE-2017-0144" in cves
    assert "CVE-2022-0847" in cves

    # Empty and invalid cases
    assert engine.extract_cves("") == []
    assert engine.extract_cves(None) == []
    assert engine.extract_cves("No vulnerabilities here") == []


def test_known_cve_lookup():
    """Verify lookup of curated high-profile vulnerabilities."""
    engine = CVEIntelligenceEngine()
    log4shell = engine.lookup_cve("cve-2021-44228")
    assert log4shell is not None
    assert log4shell.cve_id == "CVE-2021-44228"
    assert log4shell.cvss_score == 10.0
    assert log4shell.severity == "CRITICAL"
    assert log4shell.in_cisa_kev is True
    assert log4shell.weaponized is True
    assert "Log4j" in log4shell.title

    dirty_pipe = engine.lookup_cve("CVE-2022-0847")
    assert dirty_pipe is not None
    assert "Dirty Pipe" in dirty_pipe.title
    assert dirty_pipe.severity == "HIGH"


def test_heuristic_cve_fallback():
    """Verify fallback behavior for unrecognized but well-formed CVEs."""
    engine = CVEIntelligenceEngine()
    unknown_cve = engine.lookup_cve("CVE-2099-99999")
    assert unknown_cve is not None
    assert unknown_cve.cve_id == "CVE-2099-99999"
    assert unknown_cve.cvss_score == 6.5
    assert unknown_cve.severity == "MEDIUM"

    # Non-CVE strings return None
    assert engine.lookup_cve("not-a-cve") is None
    assert engine.lookup_cve("") is None


def test_enrich_findings():
    """Verify enrichment of vulnerability finding dictionaries."""
    engine = CVEIntelligenceEngine()
    findings = [
        {
            "id": "f-1",
            "title": "Apache Log4j2 JNDI Exploit Detected",
            "description": "Exploitation attempted via CVE-2021-44228",
            "severity": "critical"
        },
        {
            "id": "f-2",
            "title": "Informational banner grab",
            "description": "Nginx 1.18.0 detected",
            "severity": "low"
        }
    ]
    enriched = engine.enrich_findings(findings)
    assert len(enriched) == 2

    first = enriched[0]
    assert "CVE-2021-44228" in first["cves_detected"]
    assert len(first["cve_intelligence"]) == 1
    assert first["has_cisa_kev"] is True
    assert first["is_weaponized"] is True
    assert first["prioritized_risk_score"] >= 9.0

    second = enriched[1]
    assert second["cves_detected"] == []
    assert second["cve_intelligence"] == []


def test_cisa_kev_summary():
    """Verify CISA KEV aggregation summary."""
    engine = CVEIntelligenceEngine()
    findings = [
        {
            "title": "Log4Shell issue",
            "description": "CVE-2021-44228"
        },
        {
            "title": "Dirty Pipe issue",
            "description": "CVE-2022-0847"
        }
    ]
    enriched = engine.enrich_findings(findings)
    summary = engine.get_cisa_kev_summary(enriched)
    assert summary["total_kev_count"] == 2
    assert summary["requires_immediate_action"] is True
    assert len(summary["vulnerabilities"]) == 2


def test_ai_engine_cve_integration():
    """Verify CVE threat intelligence methods on AdvancedAIEngine."""
    ai = AdvancedAIEngine()
    assert hasattr(ai, "lookup_cve")
    assert hasattr(ai, "extract_cves")
    assert hasattr(ai, "enrich_with_cve_intelligence")

    cves = ai.extract_cves("Found CVE-2021-44228 in logs")
    assert "CVE-2021-44228" in cves

    info = ai.lookup_cve("CVE-2021-44228")
    assert info is not None
    assert info.cvss_score == 10.0
