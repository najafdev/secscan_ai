"""Tests for HackBot Zero-Day Discovery Engine and Anomaly Detection."""

import pytest
from hackbot.core.zeroday import (
    ZeroDayEngine,
    AnomalySignal,
    ExploitChain,
    VersionGapResult,
    ANOMALY_PATTERNS,
)


class TestZeroDayAnomalyDetection:
    """Test response anomaly pattern matching and signal generation."""

    def setup_method(self):
        self.engine = ZeroDayEngine()

    def test_ssti_template_injection_pattern(self):
        response_body = "Server error: jinja2.exceptions.TemplateSyntaxError: unexpected char '{' at line 2"
        anomalies = self.engine.analyze_response(
            response_body=response_body,
            response_headers="HTTP/1.1 500 Internal Server Error",
            response_code=500,
        )
        categories = [a.category for a in anomalies]
        assert "template_injection" in categories
        ssti = next(a for a in anomalies if a.category == "template_injection")
        assert ssti.severity == "High"
        assert "SSTI" in ssti.indicator or "template" in ssti.indicator.lower()
        assert "Remote Code Execution" in ssti.exploit_potential or "RCE" in ssti.exploit_potential

    def test_ssrf_cloud_metadata_pattern(self):
        response_body = '{"instance-id": "i-0abcd1234ef567890", "security-credentials/": "admin-role"}'
        anomalies = self.engine.analyze_response(
            response_body=response_body,
            response_headers="HTTP/1.1 200 OK",
            response_code=200,
        )
        categories = [a.category for a in anomalies]
        assert "ssrf_cloud_metadata" in categories
        ssrf = next(a for a in anomalies if a.category == "ssrf_cloud_metadata")
        assert ssrf.severity == "Critical"
        assert "AWS" in ssrf.indicator or "metadata" in ssrf.indicator.lower()
        assert "IAM" in ssrf.exploit_potential or "credentials" in ssrf.exploit_potential

    def test_prototype_pollution_pattern(self):
        response_body = 'Error: Cannot assign to read only property \'polluted\' of object \'[object Object]\' prototype'
        anomalies = self.engine.analyze_response(
            response_body=response_body,
            response_headers="HTTP/1.1 500 Internal Server Error",
            response_code=500,
        )
        categories = [a.category for a in anomalies]
        assert "prototype_pollution" in categories
        pp = next(a for a in anomalies if a.category == "prototype_pollution")
        assert pp.severity == "High"
        assert "prototype" in pp.indicator.lower()

    def test_timing_anomaly(self):
        anomalies = self.engine.analyze_response(
            response_body="Hello World",
            response_headers="HTTP/1.1 200 OK",
            response_time=5.2,
            baseline_time=0.4,
            response_code=200,
        )
        categories = [a.category for a in anomalies]
        assert "timing" in categories
        timing = next(a for a in anomalies if a.category == "timing")
        assert timing.severity == "High"

    def test_new_patterns_in_anomaly_patterns_dict(self):
        assert "template_injection" in ANOMALY_PATTERNS
        assert "ssrf_cloud_metadata" in ANOMALY_PATTERNS
        assert "prototype_pollution" in ANOMALY_PATTERNS
