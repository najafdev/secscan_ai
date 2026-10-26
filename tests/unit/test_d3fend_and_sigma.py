#!/usr/bin/env python3
"""
Unit tests for MITRE D3FEND Countermeasure Mapping, Detection-as-Code (Sigma),
and Automated Playbook Generation in SecScan AI Enterprise.
"""

import pytest
from ai_engine.attack_chainer import (
    AttackGraph,
    AttackNode,
    AttackEdge,
    AttackStage,
    AttackChainingEngine,
)
from ai_engine.advanced_engine import AdvancedAIEngine


def test_d3fend_countermeasures_mapping():
    """Verify mapping of attack nodes to official MITRE D3FEND countermeasures."""
    graph = AttackGraph()
    n1 = AttackNode(
        node_id="node_init_1",
        label="Public SQL Injection",
        stage=AttackStage.INITIAL_ACCESS,
        mitre_technique="T1190"
    )
    n2 = AttackNode(
        node_id="node_exec_1",
        label="Web Shell Execution",
        stage=AttackStage.EXECUTION,
        mitre_technique="T1059"
    )
    n3 = AttackNode(
        node_id="node_priv_1",
        label="Sudoers NOPASSWD Escalation",
        stage=AttackStage.PRIVILEGE_ESCALATION,
        mitre_technique="T1548"
    )
    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)

    d3fend_matrix = graph.to_d3fend_matrix()
    assert isinstance(d3fend_matrix, list)
    assert len(d3fend_matrix) >= 3

    d3_ids = [item["d3fend_id"] for item in d3fend_matrix]
    assert "D3-WAF" in d3_ids  # Web App Filtering for T1190
    assert "D3-PSA" in d3_ids  # Process Spawn Analysis for T1059
    assert "D3-LRP" in d3_ids  # Least Privilege Principle for T1548

    for entry in d3fend_matrix:
        assert "node_id" in entry
        assert "d3fend_name" in entry
        assert "defensive_tactic" in entry
        assert "mitigation_strength" in entry
        assert 0.0 <= entry["mitigation_strength"] <= 1.0


def test_sigma_rules_export():
    """Verify Detection-as-Code Sigma YAML and Splunk query generation."""
    graph = AttackGraph()
    n1 = AttackNode(
        node_id="node_init_1",
        label="Log4j RCE Exploitation",
        stage=AttackStage.INITIAL_ACCESS,
        mitre_technique="T1190"
    )
    n2 = AttackNode(
        node_id="node_cred_1",
        label="Dump LSASS Secrets",
        stage=AttackStage.CREDENTIAL_ACCESS,
        mitre_technique="T1003"
    )
    graph.add_node(n1)
    graph.add_node(n2)

    sigma_rules = graph.export_sigma_rules()
    assert isinstance(sigma_rules, list)
    assert len(sigma_rules) == 2

    for rule in sigma_rules:
        assert "rule_id" in rule
        assert "sigma_yaml" in rule
        assert "splunk_spl" in rule
        yaml_text = rule["sigma_yaml"]
        assert "title: SecScan AI Detection" in yaml_text
        assert "author: SecScan AI Enterprise" in yaml_text
        assert "logsource:" in yaml_text
        assert "detection:" in yaml_text
        assert "level:" in yaml_text
        assert "tags:" in yaml_text
        assert "index=" in rule["splunk_spl"]


def test_automated_remediation_playbooks():
    """Verify Ansible Playbook and Bash Hardening Script generation."""
    chainer = AttackChainingEngine()
    sample_vulns = [
        {"id": "v1", "title": "SQL Injection in User Portal", "severity": "critical", "type": "sqli"},
        {"id": "v2", "title": "NOPASSWD Sudoers Misconfiguration", "severity": "high", "type": "privesc"},
        {"id": "v3", "title": "Insecure SSH Root Login Enabled", "severity": "medium", "type": "smb"}
    ]
    graph = chainer.synthesize_attack_graph(sample_vulns)
    playbooks = chainer.generate_playbooks(graph)

    assert "ansible" in playbooks
    assert "bash" in playbooks

    ansible_yaml = playbooks["ansible"]
    assert "---" in ansible_yaml
    assert "SecScan AI Enterprise Automated Attack Graph Remediation" in ansible_yaml
    assert "fs.protected_hardlinks" in ansible_yaml
    assert "NOPASSWD" in ansible_yaml

    bash_script = playbooks["bash"]
    assert "#!/usr/bin/env bash" in bash_script
    assert "fs.protected_hardlinks = 1" in bash_script
    assert "umask 027" in bash_script
    assert "SecScan AI Enterprise defensive hardening completed" in bash_script


def test_advanced_ai_engine_d3fend_and_playbook_integration():
    """Verify AdvancedAIEngine wrapper methods for D3FEND, Sigma, and Playbooks."""
    ai = AdvancedAIEngine()
    sample_vulns = [
        {"id": "v1", "title": "Web Shell Upload", "severity": "critical", "category": "web"},
        {"id": "v2", "title": "Polkit PwnKit Privilege Escalation", "severity": "high", "category": "system"}
    ]

    # D3FEND Countermeasures
    d3fend = ai.get_d3fend_countermeasures(sample_vulns)
    assert isinstance(d3fend, list)
    assert len(d3fend) >= 2

    # Sigma Rules
    sigma = ai.export_sigma_rules(sample_vulns)
    assert isinstance(sigma, list)
    assert len(sigma) >= 2
    assert "sigma_yaml" in sigma[0]

    # Playbooks
    playbooks = ai.generate_remediation_playbooks(sample_vulns)
    assert isinstance(playbooks, dict)
    assert "ansible" in playbooks
    assert "bash" in playbooks
    assert len(playbooks["ansible"]) > 50
    assert len(playbooks["bash"]) > 50
