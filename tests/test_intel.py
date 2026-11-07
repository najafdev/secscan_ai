"""
Tests for CVE Lookup, OSINT, and Network Topology modules.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

# ── CVE Module Tests ─────────────────────────────────────────────────────────

from hackbot.core.cve import CVELookup, CVEEntry, ExploitEntry


class TestCVEEntry:
    """Test CVEEntry data model."""

    def test_severity_color_critical(self):
        entry = CVEEntry(cve_id="CVE-2021-44228", description="Log4Shell", cvss_score=10.0)
        assert entry.severity_color == "Critical"

    def test_severity_color_high(self):
        entry = CVEEntry(cve_id="CVE-2023-0001", description="Test", cvss_score=8.5)
        assert entry.severity_color == "High"

    def test_severity_color_medium(self):
        entry = CVEEntry(cve_id="CVE-2023-0002", description="Test", cvss_score=5.0)
        assert entry.severity_color == "Medium"

    def test_severity_color_low(self):
        entry = CVEEntry(cve_id="CVE-2023-0003", description="Test", cvss_score=2.5)
        assert entry.severity_color == "Low"

    def test_severity_color_info(self):
        entry = CVEEntry(cve_id="CVE-2023-0004", description="Test", cvss_score=0.0)
        assert entry.severity_color == "Info"

    def test_to_dict(self):
        entry = CVEEntry(
            cve_id="CVE-2021-44228",
            description="Log4Shell RCE",
            severity="CRITICAL",
            cvss_score=10.0,
            published="2021-12-10",
        )
        d = entry.to_dict()
        assert d["cve_id"] == "CVE-2021-44228"
        assert d["cvss_score"] == 10.0
        assert d["published"] == "2021-12-10"
        assert d["severity"] == "CRITICAL"

    def test_summary(self):
        entry = CVEEntry(cve_id="CVE-2021-44228", description="Log4Shell", cvss_score=10.0)
        s = entry.summary()
        assert "CVE-2021-44228" in s
        assert "10.0" in s
        assert "Critical" in s


class TestExploitEntry:
    def test_to_dict(self):
        entry = ExploitEntry(
            title="poc/log4shell",
            source="GitHub",
            url="https://github.com/test/poc",
            cve_id="CVE-2021-44228",
        )
        d = entry.to_dict()
        assert d["title"] == "poc/log4shell"
        assert d["source"] == "GitHub"
        assert d["url"].startswith("https://")


class TestCVELookup:
    """Test CVELookup engine."""

    def test_init_default(self):
        engine = CVELookup()
        assert engine.timeout == 20
        assert engine.nvd_api_key == ""

    def test_init_with_key(self):
        engine = CVELookup(nvd_api_key="test-key")
        assert engine.nvd_api_key == "test-key"
        assert engine._session.headers.get("apiKey") == "test-key"

    def test_rate_limit_value_no_key(self):
        """Without API key, rate limit should be slower."""
        from hackbot.core.cve import _NVD_RATE_LIMIT_NO_KEY, _NVD_RATE_LIMIT_WITH_KEY
        assert _NVD_RATE_LIMIT_NO_KEY > _NVD_RATE_LIMIT_WITH_KEY
        assert _NVD_RATE_LIMIT_NO_KEY >= 6.0
        assert _NVD_RATE_LIMIT_WITH_KEY <= 1.0

    def test_lookup_invalid_cve_id(self):
        engine = CVELookup()
        result = engine.lookup_cve("NOT-A-CVE")
        assert result is None

    def test_lookup_cve_format_validation(self):
        engine = CVELookup()
        # Valid format but won't hit API
        result = engine.lookup_cve("")
        assert result is None

    @patch("hackbot.core.cve.requests.Session.get")
    def test_search_cve_empty_keyword(self, mock_get):
        engine = CVELookup()
        result = engine.search_cve("")
        assert result == []
        mock_get.assert_not_called()

    def test_format_cve_report_empty(self):
        report = CVELookup.format_cve_report([])
        assert "No CVEs found" in report

    def test_format_cve_report_with_entries(self):
        entries = [
            CVEEntry(
                cve_id="CVE-2021-44228",
                description="Apache Log4j2 RCE vulnerability",
                severity="CRITICAL",
                cvss_score=10.0,
                published="2021-12-10",
            ),
            CVEEntry(
                cve_id="CVE-2023-0001",
                description="Test vuln",
                severity="HIGH",
                cvss_score=8.0,
            ),
        ]
        report = CVELookup.format_cve_report(entries, title="Test Results")
        assert "Test Results" in report
        assert "CVE-2021-44228" in report
        assert "2 vulnerabilities" in report

    def test_format_nmap_cve_report_empty(self):
        report = CVELookup.format_nmap_cve_report({})
        assert "No vulnerabilities found" in report

    def test_format_nmap_cve_report(self):
        results = {
            "80/tcp http (Apache 2.4.49)": [
                CVEEntry(cve_id="CVE-2021-41773", description="Path traversal", cvss_score=7.5),
            ],
        }
        report = CVELookup.format_nmap_cve_report(results)
        assert "Apache 2.4.49" in report
        assert "CVE-2021-41773" in report

    @patch("hackbot.core.cve.requests.Session.get")
    def test_parse_nvd_item(self, mock_get):
        engine = CVELookup()
        item = {
            "cve": {
                "id": "CVE-2021-44228",
                "descriptions": [
                    {"lang": "en", "value": "Log4Shell RCE"}
                ],
                "metrics": {
                    "cvssMetricV31": [{
                        "cvssData": {"baseScore": 10.0, "vectorString": "CVSS:3.1/AV:N"},
                        "baseSeverity": "CRITICAL",
                    }]
                },
                "published": "2021-12-10T00:00:00",
                "lastModified": "2023-01-01T00:00:00",
                "references": [{"url": "https://example.com"}],
                "weaknesses": [{"description": [{"value": "CWE-502"}]}],
                "configurations": [],
            }
        }
        entry = engine._parse_nvd_item(item)
        assert entry.cve_id == "CVE-2021-44228"
        assert entry.cvss_score == 10.0
        assert entry.severity == "CRITICAL"
        assert "CWE-502" in entry.weaknesses


# ── OSINT Module Tests ───────────────────────────────────────────────────────

from hackbot.core.osint import (
    OSINTEngine,
    SubdomainResult,
    WHOISResult,
    DNSRecord,
    TechStackResult,
    OSINTReport,
)


class TestSubdomainResult:
    def test_to_dict(self):
        s = SubdomainResult(subdomain="mail.example.com", ip="1.2.3.4", source="crt.sh")
        d = s.to_dict()
        assert d["subdomain"] == "mail.example.com"
        assert d["ip"] == "1.2.3.4"


class TestDNSRecord:
    def test_to_dict(self):
        r = DNSRecord(record_type="A", value="1.2.3.4", ttl=300)
        d = r.to_dict()
        assert d["type"] == "A"
        assert d["value"] == "1.2.3.4"
        assert d["ttl"] == 300


class TestWHOISResult:
    def test_to_dict(self):
        w = WHOISResult(
            domain="example.com",
            registrar="GoDaddy",
            creation_date="2020-01-01",
            name_servers=["ns1.example.com", "ns2.example.com"],
        )
        d = w.to_dict()
        assert d["domain"] == "example.com"
        assert d["registrar"] == "GoDaddy"
        assert len(d["name_servers"]) == 2


class TestTechStackResult:
    def test_to_dict(self):
        ts = TechStackResult(
            url="https://example.com",
            server="nginx/1.21",
            technologies=[{"name": "Nginx", "category": "Web Server"}],
        )
        d = ts.to_dict()
        assert d["server"] == "nginx/1.21"
        assert len(d["technologies"]) == 1


class TestOSINTReport:
    def test_to_dict(self):
        report = OSINTReport(
            domain="example.com",
            subdomains=[SubdomainResult("www.example.com", "1.2.3.4", "crt.sh")],
            dns_records=[DNSRecord("A", "1.2.3.4", 300)],
            emails=["admin@example.com"],
        )
        d = report.to_dict()
        assert d["domain"] == "example.com"
        assert len(d["subdomains"]) == 1
        assert len(d["dns_records"]) == 1
        assert "admin@example.com" in d["emails"]


class TestOSINTEngine:
    def test_clean_domain(self):
        assert OSINTEngine._clean_domain("https://www.example.com/path") == "example.com"
        assert OSINTEngine._clean_domain("http://test.io:8080") == "test.io"
        assert OSINTEngine._clean_domain("EXAMPLE.COM") == "example.com"

    def test_normalize_url(self):
        assert OSINTEngine._normalize_url("example.com") == "https://example.com"
        assert OSINTEngine._normalize_url("http://example.com") == "http://example.com"

    def test_is_valid_subdomain(self):
        assert OSINTEngine._is_valid_subdomain("www.example.com") is True
        assert OSINTEngine._is_valid_subdomain("mail.example.com") is True
        assert OSINTEngine._is_valid_subdomain("") is False
        assert OSINTEngine._is_valid_subdomain("-invalid.com") is False

    def test_format_report(self):
        report = OSINTReport(
            domain="example.com",
            subdomains=[
                SubdomainResult("www.example.com", "1.2.3.4", "crt.sh"),
                SubdomainResult("mail.example.com", "1.2.3.5", "brute"),
            ],
            dns_records=[DNSRecord("A", "1.2.3.4", 300)],
            emails=["admin@example.com"],
        )
        md = OSINTEngine.format_report(report)
        assert "example.com" in md
        assert "www.example.com" in md
        assert "admin@example.com" in md
        assert "Subdomains" in md

    def test_format_report_empty(self):
        report = OSINTReport(domain="empty.com")
        md = OSINTEngine.format_report(report)
        assert "empty.com" in md
        assert "Summary" in md


# ── Topology Module Tests ────────────────────────────────────────────────────

from hackbot.core.topology import (
    TopologyParser,
    NetworkTopology,
    TopoNode,
    TopoEdge,
)


SAMPLE_NMAP_OUTPUT = """Starting Nmap 7.94 ( https://nmap.org ) at 2024-01-15 10:00 UTC
Nmap scan report for scanme.nmap.org (45.33.32.156)
Host is up (0.065s latency).

PORT     STATE SERVICE     VERSION
22/tcp   open  ssh         OpenSSH 6.6.1p1 Ubuntu 2ubuntu2.13
80/tcp   open  http        Apache httpd 2.4.7
9929/tcp open  nping-echo  Nping echo
31337/tcp open  tcpwrapped

Nmap scan report for 192.168.1.1
Host is up (0.001s latency).

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 8.2p1
80/tcp open  http    nginx 1.18.0
443/tcp open  https   nginx 1.18.0

Nmap done: 2 IP addresses (2 hosts up) scanned in 12.34 seconds
"""

SAMPLE_MASSCAN_OUTPUT = """Starting masscan 1.3.2
Discovered open port 80/tcp on 10.0.0.1
Discovered open port 443/tcp on 10.0.0.1
Discovered open port 22/tcp on 10.0.0.2
Discovered open port 3306/tcp on 10.0.0.3
Discovered open port 80/tcp on 10.0.0.3
"""


class TestTopoNode:
    def test_to_dict(self):
        node = TopoNode(
            id="host_192_168_1_1",
            label="192.168.1.1 (3 ports)",
            node_type="host",
            ip="192.168.1.1",
            ports=[{"port": 80, "protocol": "tcp", "state": "open"}],
            status="up",
        )
        d = node.to_dict()
        assert d["id"] == "host_192_168_1_1"
        assert d["type"] == "host"
        assert d["ip"] == "192.168.1.1"
        assert len(d["ports"]) == 1


class TestTopoEdge:
    def test_to_dict(self):
        edge = TopoEdge(source="scanner", target="host_1", edge_type="scan")
        d = edge.to_dict()
        assert d["source"] == "scanner"
        assert d["target"] == "host_1"
        assert d["type"] == "scan"


class TestNetworkTopology:
    def test_to_dict(self):
        topo = NetworkTopology(
            nodes=[
                TopoNode(id="scanner", label="Scanner", node_type="scanner"),
                TopoNode(id="host_1", label="192.168.1.1", node_type="host", ports=[
                    {"port": 80, "state": "open"},
                ]),
            ],
            edges=[TopoEdge(source="scanner", target="host_1")],
        )
        d = topo.to_dict()
        assert d["stats"]["total_hosts"] == 1
        assert d["stats"]["total_services"] == 1
        assert len(d["nodes"]) == 2
        assert len(d["edges"]) == 1

    def test_to_json(self):
        topo = NetworkTopology()
        j = topo.to_json()
        data = json.loads(j)
        assert "nodes" in data
        assert "edges" in data


class TestTopologyParser:
    def test_parse_nmap_text(self):
        parser = TopologyParser()
        topo = parser.parse_nmap_text(SAMPLE_NMAP_OUTPUT)
        assert len(topo.nodes) > 1  # scanner + at least 1 host
        hosts = [n for n in topo.nodes if n.node_type == "host"]
        assert len(hosts) == 2
        assert any(h.ip == "45.33.32.156" for h in hosts)
        assert any(h.ip == "192.168.1.1" for h in hosts)

    def test_nmap_ports_parsed(self):
        parser = TopologyParser()
        topo = parser.parse_nmap_text(SAMPLE_NMAP_OUTPUT)
        hosts = [n for n in topo.nodes if n.node_type == "host"]
        scanme = next(h for h in hosts if h.ip == "45.33.32.156")
        assert len(scanme.ports) == 4
        assert any(p["port"] == 22 for p in scanme.ports)
        assert any(p["port"] == 80 for p in scanme.ports)

    def test_parse_masscan(self):
        parser = TopologyParser()
        topo = parser.parse_masscan_output(SAMPLE_MASSCAN_OUTPUT)
        hosts = [n for n in topo.nodes if n.node_type == "host"]
        assert len(hosts) == 3
        host1 = next(h for h in hosts if h.ip == "10.0.0.1")
        assert len(host1.ports) == 2

    def test_auto_parse_nmap(self):
        parser = TopologyParser()
        topo = parser.auto_parse(SAMPLE_NMAP_OUTPUT)
        hosts = [n for n in topo.nodes if n.node_type == "host"]
        assert len(hosts) >= 1

    def test_auto_parse_masscan(self):
        parser = TopologyParser()
        topo = parser.auto_parse(SAMPLE_MASSCAN_OUTPUT)
        hosts = [n for n in topo.nodes if n.node_type == "host"]
        assert len(hosts) == 3

    def test_render_ascii(self):
        parser = TopologyParser()
        topo = parser.parse_nmap_text(SAMPLE_NMAP_OUTPUT)
        ascii_art = TopologyParser.render_ascii(topo)
        assert "NETWORK TOPOLOGY MAP" in ascii_art
        assert "45.33.32.156" in ascii_art or "scanme" in ascii_art
        assert "Hosts:" in ascii_art

    def test_format_markdown(self):
        parser = TopologyParser()
        topo = parser.parse_nmap_text(SAMPLE_NMAP_OUTPUT)
        md = TopologyParser.format_markdown(topo)
        assert "Network Topology" in md
        assert "Discovered Hosts" in md
        assert "45.33.32.156" in md

    def test_get_subnet(self):
        assert TopologyParser._get_subnet("192.168.1.100") == "192.168.1.0/24"
        assert TopologyParser._get_subnet("10.0.0.5") == "10.0.0.0/24"
        assert TopologyParser._get_subnet("invalid") == ""

    def test_empty_output(self):
        parser = TopologyParser()
        topo = parser.parse_nmap_text("")
        hosts = [n for n in topo.nodes if n.node_type == "host"]
        assert len(hosts) == 0

    def test_render_ascii_empty(self):
        topo = NetworkTopology(
            nodes=[TopoNode(id="scanner", label="Scanner", node_type="scanner")],
        )
        ascii_art = TopologyParser.render_ascii(topo)
        assert "No hosts discovered" in ascii_art

    def test_nmap_xml_fallback(self):
        """If XML parsing fails, should fall back to text parsing."""
        parser = TopologyParser()
        # Invalid XML should trigger text fallback
        topo = parser.parse_nmap_xml("not xml at all\n" + SAMPLE_NMAP_OUTPUT)
        hosts = [n for n in topo.nodes if n.node_type == "host"]
        # Should still parse hosts via text fallback
        assert len(hosts) >= 1

    def test_subnet_grouping(self):
        parser = TopologyParser()
        topo = parser.parse_nmap_text(SAMPLE_NMAP_OUTPUT)
        subnets = [n for n in topo.nodes if n.node_type == "subnet"]
        # Hosts are on different subnets
        assert len(subnets) >= 1

    def test_parse_nmap_xml_valid(self):
        """Test with minimal valid nmap XML."""
        xml = """<?xml version="1.0"?>
<nmaprun scanner="nmap" args="-sV" startstr="2024-01-15">
  <host>
    <status state="up"/>
    <address addr="192.168.1.10" addrtype="ipv4"/>
    <hostnames><hostname name="fileserver.local"/></hostnames>
    <ports>
      <port protocol="tcp" portid="22">
        <state state="open"/>
        <service name="ssh" product="OpenSSH" version="8.9"/>
      </port>
      <port protocol="tcp" portid="445">
        <state state="open"/>
        <service name="microsoft-ds" product="Samba"/>
      </port>
    </ports>
    <os><osmatch name="Linux 5.x"/></os>
  </host>
</nmaprun>"""
        parser = TopologyParser()
        topo = parser.parse_nmap_xml(xml)
        hosts = [n for n in topo.nodes if n.node_type == "host"]
        assert len(hosts) == 1
        assert hosts[0].ip == "192.168.1.10"
        assert hosts[0].hostname == "fileserver.local"
        assert hosts[0].os == "Linux 5.x"
        assert len(hosts[0].ports) == 2

    def test_render_mermaid(self):
        """Test Mermaid graph rendering."""
        parser = TopologyParser()
        topo = parser.parse_nmap_text(SAMPLE_NMAP_OUTPUT)
        mermaid = parser.render_mermaid(topo)
        assert mermaid.startswith("```mermaid")
        assert "graph TD" in mermaid
        assert "classDef scanner" in mermaid
        assert "classDef host" in mermaid
        assert "scanner -->" in mermaid
        assert "192.168.1.1" in mermaid
        assert topo.to_mermaid() == mermaid

    def test_mermaid_empty_topology(self):
        from hackbot.core.topology import NetworkTopology
        topo = NetworkTopology()
        mermaid = TopologyParser.render_mermaid(topo)
        assert "```mermaid" in mermaid
        assert "(No hosts discovered)" in mermaid


class TestCVSSCalculator:
    """Tests for FIRST CVSS v3.1 calculator and vector parser."""

    def test_critical_base_score(self):
        from hackbot.core.cve import CVSSCalculator

        vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
        res = CVSSCalculator.calculate(vector)
        assert res.base_score == 9.8
        assert res.severity == "Critical"
        assert res.metrics["AV"] == "N"
        assert res.metrics["S"] == "U"
        assert res.impact_subscore == 5.9
        assert res.exploitability_subscore == 3.9

    def test_scope_changed_base_score(self):
        from hackbot.core.cve import CVSSCalculator

        vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H"
        res = CVSSCalculator.calculate(vector)
        assert res.base_score == 10.0
        assert res.severity == "Critical"

    def test_vector_without_prefix(self):
        from hackbot.core.cve import CVSSCalculator

        vector = "AV:L/AC:H/PR:H/UI:R/S:U/C:L/I:N/A:N"
        res = CVSSCalculator.calculate(vector)
        assert res.base_score < 4.0
        assert res.severity == "Low"
        assert "Attack Vector: Local" in res.descriptions["AV"]

    def test_missing_metrics_raises_error(self):
        from hackbot.core.cve import CVSSCalculator

        with pytest.raises(ValueError, match="Missing required CVSS v3.1 metrics"):
            CVSSCalculator.calculate("CVSS:3.1/AV:N/AC:L/PR:N")

    def test_invalid_metric_value_raises_error(self):
        from hackbot.core.cve import CVSSCalculator

        with pytest.raises(ValueError, match="Invalid value 'X' for CVSS metric AV"):
            CVSSCalculator.calculate("CVSS:3.1/AV:X/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")

    def test_result_to_dict_and_summary(self):
        from hackbot.core.cve import CVSSCalculator

        vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
        res = CVSSCalculator.calculate(vector)
        d = res.to_dict()
        assert d["base_score"] == 9.8
        assert d["severity"] == "Critical"
        summary = res.summary()
        assert "9.8 (Critical)" in summary
        assert "Attack Vector" in summary

