# SecScan AI unit test
"""Unit tests for Automated Attack Graph and Attack Chaining Engine."""

import pytest
from ai_engine.attack_chainer import (
    AttackStage,
    AttackNode,
    AttackEdge,
    AttackGraph,
    AttackChainingEngine,
)
from ai_engine.advanced_engine import AdvancedAIEngine, VulnerabilityCorrelator


def test_attack_node_and_edge_creation():
    """Verify AttackNode and AttackEdge properties and serialization."""
    node = AttackNode(
        node_id="n1",
        label="SQL Injection on Login",
        stage=AttackStage.INITIAL_ACCESS,
        vulnerability_id="vuln-01",
        difficulty=0.8,
        mitre_technique="T1190"
    )
    assert node.node_id == "n1"
    assert node.stage == AttackStage.INITIAL_ACCESS
    d = node.to_dict()
    assert d["stage"] == "initial_access"
    assert d["difficulty"] == 0.8

    edge = AttackEdge(
        source="n1",
        target="n2",
        transition_condition="Execute web shell",
        probability=0.85
    )
    assert edge.source == "n1"
    assert edge.target == "n2"
    assert edge.to_dict()["probability"] == 0.85


def test_attack_graph_paths_and_chokepoints():
    """Verify graph path traversal and critical chokepoint identification."""
    graph = AttackGraph()

    n1 = AttackNode("init_1", "Public Web SQLi", AttackStage.INITIAL_ACCESS, difficulty=0.8)
    n2 = AttackNode("init_2", "Exposed Jenkins RCE", AttackStage.INITIAL_ACCESS, difficulty=0.9)
    # Intermediate chokepoint node
    n3 = AttackNode("priv_root", "Kernel Dirty Pipe Exploit", AttackStage.PRIVILEGE_ESCALATION, difficulty=0.85)
    n4 = AttackNode("cred_lsass", "Dump Domain Credentials", AttackStage.CREDENTIAL_ACCESS, difficulty=0.7)
    n5 = AttackNode("obj_db", "Exfiltrate Crown Jewel Database", AttackStage.IMPACT, difficulty=0.9)

    for n in [n1, n2, n3, n4, n5]:
        graph.add_node(n)

    # Both initial access vectors converge on n3 (priv_root)
    graph.add_edge(AttackEdge("init_1", "priv_root", "Local shell obtained", 0.9))
    graph.add_edge(AttackEdge("init_2", "priv_root", "Command execution obtained", 0.9))
    graph.add_edge(AttackEdge("priv_root", "cred_lsass", "Root privilege acquired", 0.85))
    graph.add_edge(AttackEdge("cred_lsass", "obj_db", "Domain admin access", 0.8))

    paths = graph.find_all_paths()
    assert len(paths) == 2

    # Check path risk calculation
    risk = graph.calculate_path_risk(paths[0])
    assert 0.0 < risk <= 10.0

    # Chokepoint analysis: 'priv_root' and 'cred_lsass' should appear in 100% of paths
    chokepoints = graph.find_critical_chokepoints()
    assert len(chokepoints) >= 2
    top_chokepoint = chokepoints[0]
    assert top_chokepoint["coverage_percentage"] == 100.0
    assert top_chokepoint["affected_chains_count"] == 2


def test_attack_graph_mermaid_export():
    """Verify that Mermaid export generates valid diagram syntax."""
    graph = AttackGraph()
    n1 = AttackNode("node_init", "Web RCE", AttackStage.INITIAL_ACCESS, mitre_technique="T1190")
    n2 = AttackNode("node_imp", "Data Loss", AttackStage.IMPACT, mitre_technique="T1485")
    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_edge(AttackEdge("node_init", "node_imp", "Direct compromise", 0.8))

    mermaid_str = graph.to_mermaid("Test Graph")
    assert "```mermaid" in mermaid_str
    assert "flowchart TD" in mermaid_str
    assert "node_init" in mermaid_str
    assert "node_imp" in mermaid_str
    assert "T1190" in mermaid_str
    assert "-->|" in mermaid_str


def test_attack_chaining_engine_synthesis():
    """Verify automatic attack graph synthesis from raw vulnerabilities."""
    chainer = AttackChainingEngine()
    findings = [
        {
            "id": "v1",
            "title": "SQL Injection in User Search",
            "category": "web",
            "severity": "high"
        },
        {
            "id": "v2",
            "title": "Local SUID Privilege Escalation",
            "category": "system",
            "severity": "high"
        },
        {
            "id": "v3",
            "title": "Plaintext Database Credentials in Config",
            "category": "system",
            "severity": "medium"
        }
    ]

    graph = chainer.synthesize_attack_graph(findings)
    assert len(graph.nodes) >= 3
    assert len(graph.edges) >= 1

    # Verify remediation roadmap generation
    roadmap = chainer.generate_remediation_roadmap(graph)
    assert isinstance(roadmap, list)
    if roadmap:
        assert "priority_rank" in roadmap[0]
        assert "strategic_action" in roadmap[0]


def test_vulnerability_correlator_enhanced_output():
    """Verify VulnerabilityCorrelator produces graph, chokepoints, and KEV metrics."""
    correlator = VulnerabilityCorrelator()
    sample_vulns = [
        {
            "id": "vuln-log4j",
            "title": "Apache Log4j2 JNDI RCE (CVE-2021-44228)",
            "severity": "critical",
            "category": "web"
        },
        {
            "id": "vuln-pwnkit",
            "title": "Polkit PwnKit Privilege Escalation (CVE-2021-4034)",
            "severity": "high",
            "category": "system"
        }
    ]

    results = correlator.correlate_findings(session_id="test-session-001", vulnerabilities=sample_vulns)
    assert "attack_chains" in results
    assert "attack_graph" in results
    assert "critical_chokepoints" in results
    assert "remediation_roadmap" in results
    assert "mermaid_diagram" in results
    assert "cisa_kev_summary" in results

    # Verify CISA KEV detected from CVEs
    kev_summary = results["cisa_kev_summary"]
    assert kev_summary["total_kev_count"] >= 1
    assert kev_summary["requires_immediate_action"] is True


def test_ai_engine_attack_chain_methods():
    """Verify attack chaining helper methods on AdvancedAIEngine."""
    ai = AdvancedAIEngine()
    sample_vulns = [
        {"id": "v1", "title": "Web Shell Upload", "severity": "critical", "category": "web"},
        {"id": "v2", "title": "Sudoers NOPASSWD root", "severity": "critical", "category": "system"}
    ]

    graph = ai.build_attack_graph(sample_vulns)
    assert graph is not None
    assert len(graph.nodes) >= 2

    mermaid = ai.generate_attack_mermaid(sample_vulns)
    assert "flowchart TD" in mermaid

    chokepoints = ai.get_defensive_chokepoints(sample_vulns)
    assert isinstance(chokepoints, list)
