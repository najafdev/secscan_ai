#!/usr/bin/env python3
"""
Unit tests for Enterprise API Security Scanner & OpenAPI Auditor in SecScan AI.
"""

import pytest
from security.api_scanner import (
    APISecurityScanner,
    OWASPAPICategory,
    APIFinding,
    APISecurityReport,
)


def test_api_scanner_parse_spec_json_and_yaml():
    """Verify parsing of JSON and YAML format OpenAPI definitions."""
    scanner = APISecurityScanner()

    # JSON Spec
    json_spec = '{"openapi": "3.0.0", "info": {"title": "Test JSON", "version": "1.0"}, "paths": {}}'
    parsed_json = scanner.parse_spec(json_spec)
    assert parsed_json["info"]["title"] == "Test JSON"

    # YAML Spec
    yaml_spec = """
openapi: "3.0.0"
info:
  title: Test YAML
  version: "1.0"
paths: {}
"""
    parsed_yaml = scanner.parse_spec(yaml_spec)
    assert parsed_yaml["info"]["title"] == "Test YAML"


def test_api_scanner_detects_bola_and_broken_auth():
    """Verify detection of BOLA / IDOR path parameters and missing authentication."""
    scanner = APISecurityScanner()
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "BOLA API Test", "version": "1.0"},
        "paths": {
            "/api/v1/accounts/{accountId}/transfer": {
                "post": {
                    "summary": "Transfer funds",
                    "security": []  # No authentication!
                }
            }
        }
    }

    report = scanner.scan_spec(spec)
    assert isinstance(report, APISecurityReport)
    assert report.total_findings >= 1

    cats = [f.category for f in report.findings]
    assert OWASPAPICategory.API1_BOLA in cats or OWASPAPICategory.API2_BROKEN_AUTHENTICATION in cats


def test_api_scanner_detects_mass_assignment():
    """Verify detection of Mass Assignment (BOPLA) attributes in request bodies."""
    scanner = APISecurityScanner()
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Mass Assignment Test", "version": "1.0"},
        "paths": {
            "/api/v1/users": {
                "post": {
                    "summary": "Create user",
                    "security": [{"bearerAuth": []}],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "is_admin": {"type": "boolean"},
                                        "role": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    report = scanner.scan_spec(spec)
    bopla_findings = [f for f in report.findings if f.category == OWASPAPICategory.API3_BOPLA]
    assert len(bopla_findings) >= 1
    assert "is_admin" in bopla_findings[0].evidence


def test_api_scanner_mock_benchmark():
    """Verify standard mock benchmark scan produces accurate risk scores and metrics."""
    scanner = APISecurityScanner()
    report = scanner.scan_mock()

    assert isinstance(report, APISecurityReport)
    assert report.endpoints_scanned >= 5
    assert report.total_findings >= 3
    assert report.critical_count >= 1
    assert 0.0 <= report.security_score <= 100.0
    assert report.risk_rating in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert len(report.hardening_recommendations) >= 1

    # Check to_dict serialization
    report_dict = report.to_dict()
    assert "api_title" in report_dict
    assert "findings" in report_dict
    assert isinstance(report_dict["findings"], list)
