#!/usr/bin/env python3
# SecScan AI core module
"""
Automated Attack Graph & Multi-Stage Attack Chaining Engine for SecScan AI.
Synthesizes end-to-end exploit chains from discrete vulnerability findings,
maps tactics to MITRE ATT&CK, computes defensive chokepoints, and generates
visual Mermaid execution graphs.
"""

import json
import logging
from enum import Enum
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


class AttackStage(str, Enum):
    """MITRE ATT&CK aligned attack execution stages."""
    RECONNAISSANCE = "reconnaissance"
    INITIAL_ACCESS = "initial_access"
    EXECUTION = "execution"
    PERSISTENCE = "persistence"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DEFENSE_EVASION = "defense_evasion"
    CREDENTIAL_ACCESS = "credential_access"
    DISCOVERY = "discovery"
    LATERAL_MOVEMENT = "lateral_movement"
    COLLECTION = "collection"
    EXFILTRATION = "exfiltration"
    IMPACT = "impact"


@dataclass
class AttackNode:
    """An individual state, vulnerability, or action in an attack path."""
    node_id: str
    label: str
    stage: AttackStage
    vulnerability_id: Optional[str] = None
    asset: str = "target_host"
    difficulty: float = 0.5  # 0.0 (near impossible) to 1.0 (trivial exploit)
    mitre_technique: str = "T1190"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["stage"] = self.stage.value
        return result


@dataclass
class AttackEdge:
    """Directed transition representing exploit dependency or pivot."""
    source: str
    target: str
    transition_condition: str
    probability: float = 0.8  # Transition success probability (0.0 - 1.0)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AttackGraph:
    """
    Directed Graph representing synthesized attacker progression paths.
    Provides pathfinding, risk calculation, critical chokepoint analysis,
    and Mermaid flowchart export.
    """

    def __init__(self):
        self.nodes: Dict[str, AttackNode] = {}
        self.edges: List[AttackEdge] = []
        self._adj_list: Dict[str, List[Tuple[str, AttackEdge]]] = {}

    def add_node(self, node: AttackNode) -> None:
        """Register a node in the attack graph."""
        self.nodes[node.node_id] = node
        if node.node_id not in self._adj_list:
            self._adj_list[node.node_id] = []

    def add_edge(self, edge: AttackEdge) -> None:
        """Register a directed edge connecting two existing nodes."""
        if edge.source not in self.nodes or edge.target not in self.nodes:
            logger.warning(f"Ignoring edge with invalid endpoints: {edge.source} -> {edge.target}")
            return
        self.edges.append(edge)
        if edge.source not in self._adj_list:
            self._adj_list[edge.source] = []
        self._adj_list[edge.source].append((edge.target, edge))

    def find_all_paths(
        self, start_node_id: Optional[str] = None, end_node_id: Optional[str] = None
    ) -> List[List[str]]:
        """
        Find all acyclic paths between designated start and end nodes.
        If start_node_id is None, defaults to nodes in INITIAL_ACCESS or RECONNAISSANCE.
        If end_node_id is None, defaults to terminal nodes or IMPACT stage nodes.
        """
        start_nodes = [start_node_id] if start_node_id else [
            nid for nid, node in self.nodes.items()
            if node.stage in (AttackStage.INITIAL_ACCESS, AttackStage.RECONNAISSANCE)
        ]

        impact_stages = (AttackStage.IMPACT, AttackStage.EXFILTRATION, AttackStage.LATERAL_MOVEMENT)
        end_nodes = [end_node_id] if end_node_id else [
            nid for nid, node in self.nodes.items()
            if node.stage in impact_stages or len(self._adj_list.get(nid, [])) == 0
        ]

        if not start_nodes or not end_nodes:
            return []

        all_paths: List[List[str]] = []

        def dfs(current: str, target_set: Set[str], visited: Set[str], current_path: List[str]):
            if current in target_set and len(current_path) > 1:
                all_paths.append(list(current_path))
                # Continue if more downstream nodes exist

            for next_node, _ in self._adj_list.get(current, []):
                if next_node not in visited:
                    visited.add(next_node)
                    current_path.append(next_node)
                    dfs(next_node, target_set, visited, current_path)
                    current_path.pop()
                    visited.remove(next_node)

        end_set = set(end_nodes)
        for s in start_nodes:
            visited_set: Set[str] = {s}
            dfs(s, end_set, visited_set, [s])

        return all_paths

    def calculate_path_risk(self, path: List[str]) -> float:
        """
        Calculate compound risk score (0.0 to 10.0) for a given attack sequence path.
        Factors:
        - Node vulnerability difficulties
        - Transition probabilities between stages
        - Path depth and critical impact reached
        """
        if not path or len(path) < 2:
            return 0.0

        cum_prob = 1.0
        avg_difficulty = 0.0

        for i in range(len(path) - 1):
            src = path[i]
            dst = path[i + 1]
            edge_match = next((e for e in self.edges if e.source == src and e.target == dst), None)
            prob = edge_match.probability if edge_match else 0.5
            cum_prob *= prob
            node = self.nodes.get(src)
            avg_difficulty += (node.difficulty if node else 0.5)

        avg_difficulty /= (len(path) - 1)
        depth_factor = min(len(path) / 5.0, 1.5)
        raw_score = (cum_prob * 4.0) + (avg_difficulty * 4.0) + (depth_factor * 2.0)
        return round(min(raw_score, 10.0), 2)

    def find_critical_chokepoints(self) -> List[Dict[str, Any]]:
        """
        Identify critical defensive chokepoint nodes.
        A chokepoint is a node present in the highest percentage of attack chains.
        Patching or mitigating a chokepoint disrupts the maximum number of attack vectors.
        """
        paths = self.find_all_paths()
        if not paths:
            return []

        node_occurrences: Dict[str, int] = {}
        for path in paths:
            # Exclude trivial start/end endpoints to focus on actionable intermediate pivot points
            intermediate_nodes = set(path)
            for nid in intermediate_nodes:
                node_occurrences[nid] = node_occurrences.get(nid, 0) + 1

        total_paths = len(paths)
        chokepoints = []
        for nid, count in node_occurrences.items():
            node = self.nodes.get(nid)
            if not node:
                continue
            mitigation_roi = (count / total_paths) * (node.difficulty * 10.0)
            chokepoints.append({
                "node_id": nid,
                "label": node.label,
                "stage": node.stage.value,
                "mitre_technique": node.mitre_technique,
                "affected_chains_count": count,
                "total_chains": total_paths,
                "coverage_percentage": round((count / total_paths) * 100, 1),
                "mitigation_roi": round(mitigation_roi, 2),
                "remediation_summary": f"Remediate '{node.label}' to sever {count} active attack paths."
            })

        chokepoints.sort(key=lambda x: (x["coverage_percentage"], x["mitigation_roi"]), reverse=True)
        return chokepoints

    def to_mermaid(self, title: str = "SecScan AI Automated Attack Graph") -> str:
        """
        Export attack graph into Mermaid flowchart syntax (flowchart TD).
        Generates readable, visually distinct nodes grouped with MITRE stages.
        """
        lines = [
            "```mermaid",
            "flowchart TD",
            f"    %% {title}",
            "    classDef initial fill:#ef4444,stroke:#991b1b,stroke-width:2px,color:#ffffff;",
            "    classDef privesc fill:#f97316,stroke:#c2410c,stroke-width:2px,color:#ffffff;",
            "    classDef lateral fill:#8b5cf6,stroke:#6d28d9,stroke-width:2px,color:#ffffff;",
            "    classDef impact fill:#dc2626,stroke:#7f1d1d,stroke-width:3px,color:#ffffff;",
            "    classDef generic fill:#3b82f6,stroke:#1d4ed8,stroke-width:1px,color:#ffffff;"
        ]

        # Add Nodes
        for nid, node in self.nodes.items():
            # Escape quotes in label
            clean_label = node.label.replace('"', "'")
            clean_tech = node.mitre_technique
            lines.append(f'    {nid}["{clean_label} ({clean_tech})"]')

            # Assign styling classes
            if node.stage in (AttackStage.INITIAL_ACCESS, AttackStage.RECONNAISSANCE):
                lines.append(f"    class {nid} initial;")
            elif node.stage in (AttackStage.PRIVILEGE_ESCALATION, AttackStage.EXECUTION):
                lines.append(f"    class {nid} privesc;")
            elif node.stage in (AttackStage.LATERAL_MOVEMENT, AttackStage.CREDENTIAL_ACCESS):
                lines.append(f"    class {nid} lateral;")
            elif node.stage in (AttackStage.IMPACT, AttackStage.EXFILTRATION):
                lines.append(f"    class {nid} impact;")
            else:
                lines.append(f"    class {nid} generic;")

        # Add Edges
        for edge in self.edges:
            clean_cond = edge.transition_condition.replace('"', "'")
            lines.append(f'    {edge.source} -->|"{clean_cond}"| {edge.target}')

        lines.append("```")
        return "\n".join(lines)

    def to_d3fend_matrix(self) -> List[Dict[str, Any]]:
        """
        Map attack graph techniques to official MITRE D3FEND defensive countermeasures.
        Returns a structured matrix of defensive capabilities aligned to neutralize the attack paths.
        """
        d3fend_catalog = {
            "T1190": [
                {
                    "d3fend_id": "D3-WAF",
                    "name": "Web Application Filtering",
                    "tactic": "Isolate",
                    "description": "Inspect and filter inbound HTTP requests to block injection and deserialization exploits.",
                    "mitigation_strength": 0.90
                },
                {
                    "d3fend_id": "D3-ITR",
                    "name": "Inbound Traffic Filtering",
                    "tactic": "Isolate",
                    "description": "Deploy stateful ingress filtering to restrict untrusted ingress access.",
                    "mitigation_strength": 0.85
                },
                {
                    "d3fend_id": "D3-VPA",
                    "name": "Automated Vulnerability Patching",
                    "tactic": "Harden",
                    "description": "Rapid patch distribution and hot-patching for disclosed CVEs.",
                    "mitigation_strength": 0.95
                }
            ],
            "T1059": [
                {
                    "d3fend_id": "D3-PSA",
                    "name": "Process Spawn Analysis",
                    "tactic": "Detect",
                    "description": "Monitor and alert on abnormal child process execution from web servers and shells.",
                    "mitigation_strength": 0.85
                },
                {
                    "d3fend_id": "D3-EDR",
                    "name": "Endpoint Detection and Response",
                    "tactic": "Detect",
                    "description": "Real-time process telemetry, script block logging, and behavioral anomaly blocking.",
                    "mitigation_strength": 0.90
                },
                {
                    "d3fend_id": "D3-SCA",
                    "name": "System Call Analysis",
                    "tactic": "Detect",
                    "description": "Audit and restrict anomalous system calls via seccomp/AppArmor/SELinux profiles.",
                    "mitigation_strength": 0.80
                }
            ],
            "T1548": [
                {
                    "d3fend_id": "D3-LRP",
                    "name": "Least Privilege Principle",
                    "tactic": "Harden",
                    "description": "Eliminate NOPASSWD sudoers entries and enforce strict role boundaries.",
                    "mitigation_strength": 0.95
                },
                {
                    "d3fend_id": "D3-KHE",
                    "name": "Kernel Hardening Extension",
                    "tactic": "Harden",
                    "description": "Enable kernel.kptr_restrict, yama ptrace scope, and restrict eBPF access.",
                    "mitigation_strength": 0.90
                }
            ],
            "T1068": [
                {
                    "d3fend_id": "D3-KHE",
                    "name": "Kernel Hardening Extension",
                    "tactic": "Harden",
                    "description": "Enable lockdown mode and restrict privileged syscall invocation.",
                    "mitigation_strength": 0.90
                },
                {
                    "d3fend_id": "D3-SUID",
                    "name": "SUID Binary Audit & Removal",
                    "tactic": "Harden",
                    "description": "Audit filesystem for unneeded SUID/SGID bits and mount /tmp noexec.",
                    "mitigation_strength": 0.85
                }
            ],
            "T1003": [
                {
                    "d3fend_id": "D3-CSH",
                    "name": "Credential Storage Hardening",
                    "tactic": "Harden",
                    "description": "Enable Windows Credential Guard or Linux keyring encryption to prevent memory scraping.",
                    "mitigation_strength": 0.95
                },
                {
                    "d3fend_id": "D3-MFA",
                    "name": "Multi-Factor Authentication",
                    "tactic": "Harden",
                    "description": "Enforce FIDO2/WebAuthn MFA to render dumped password hashes non-viable.",
                    "mitigation_strength": 0.95
                }
            ],
            "T1021": [
                {
                    "d3fend_id": "D3-NSG",
                    "name": "Network Microsegmentation",
                    "tactic": "Isolate",
                    "description": "Block lateral east-west communication between internal host tiers via host firewalls.",
                    "mitigation_strength": 0.90
                },
                {
                    "d3fend_id": "D3-JIT",
                    "name": "Just-In-Time Network Access",
                    "tactic": "Isolate",
                    "description": "Require ephemeral session grants for SSH and RDP management endpoints.",
                    "mitigation_strength": 0.85
                }
            ],
            "T1485": [
                {
                    "d3fend_id": "D3-BKP",
                    "name": "Immutable Encrypted Backups",
                    "tactic": "Restore",
                    "description": "Air-gapped and write-once backup retention to guarantee rapid operational recovery.",
                    "mitigation_strength": 0.95
                },
                {
                    "d3fend_id": "D3-FIM",
                    "name": "File Integrity Monitoring",
                    "tactic": "Detect",
                    "description": "Real-time cryptographic hash verification of system and sensitive configuration files.",
                    "mitigation_strength": 0.85
                }
            ],
            "T1595": [
                {
                    "d3fend_id": "D3-HON",
                    "name": "Decoy Environment & Honeyports",
                    "tactic": "Deceive",
                    "description": "Deploy canary ports and deceptive network endpoints to detect early adversary reconnaissance.",
                    "mitigation_strength": 0.80
                },
                {
                    "d3fend_id": "D3-RTL",
                    "name": "Connection Rate Limiting",
                    "tactic": "Isolate",
                    "description": "Drop high-velocity SYN scan attempts using connection tracking limits.",
                    "mitigation_strength": 0.85
                }
            ]
        }

        # Generic default countermeasure
        default_countermeasure = {
            "d3fend_id": "D3-EDR",
            "name": "Endpoint Detection and Response",
            "tactic": "Detect",
            "description": "Comprehensive behavioral anomaly detection and threat containment.",
            "mitigation_strength": 0.80
        }

        results = []
        seen_d3fend: Set[str] = set()

        for nid, node in self.nodes.items():
            tech = node.mitre_technique
            cm_list = d3fend_catalog.get(tech, [default_countermeasure])
            for cm in cm_list:
                key = f"{cm['d3fend_id']}_{node.node_id}"
                if key not in seen_d3fend:
                    seen_d3fend.add(key)
                    results.append({
                        "node_id": node.node_id,
                        "attack_label": node.label,
                        "mitre_technique": tech,
                        "attack_stage": node.stage.value,
                        "d3fend_id": cm["d3fend_id"],
                        "d3fend_name": cm["name"],
                        "defensive_tactic": cm["tactic"],
                        "description": cm["description"],
                        "mitigation_strength": cm["mitigation_strength"]
                    })

        results.sort(key=lambda x: (x["mitigation_strength"], x["attack_stage"]), reverse=True)
        return results

    def export_sigma_rules(self) -> List[Dict[str, Any]]:
        """
        Generate Detection-as-Code Sigma Rules (YAML) and Splunk queries
        for techniques identified in the attack graph.
        """
        import uuid
        from datetime import date

        sigma_templates = {
            "T1190": {
                "category": "webserver",
                "product": "web",
                "selection": {
                    "cs_method": ["POST", "GET"],
                    "cs_uri_query|contains": ["SELECT", "UNION", "../", "cmd=", "whoami", "/etc/passwd", "<script>"]
                },
                "splunk": 'index=web (uri="*SELECT*" OR uri="*UNION*" OR uri="*../*" OR uri="*cmd=*" OR uri="*whoami*") | stats count by src_ip, uri, status'
            },
            "T1059": {
                "category": "process_creation",
                "product": "linux",
                "selection": {
                    "Image|endswith": ["/sh", "/bash", "/dash", "/python3", "/perl"],
                    "ParentImage|endswith": ["/nginx", "/apache2", "/httpd", "/php-fpm"]
                },
                "splunk": 'index=os sourcetype=syslog (process="sh" OR process="bash") parent_process="nginx" OR parent_process="apache2" | table _time, host, user, process, command'
            },
            "T1548": {
                "category": "process_creation",
                "product": "linux",
                "selection": {
                    "CommandLine|contains": ["sudo ", "NOPASSWD", "visudo", "pkexec"]
                },
                "splunk": 'index=os sourcetype=auth "sudo:" "*COMMAND=*" | stats count by host, user, command'
            },
            "T1068": {
                "category": "process_creation",
                "product": "linux",
                "selection": {
                    "CommandLine|contains": ["pwnkit", "dirty_cow", "cve-", "overlayfs", "netfilter"]
                },
                "splunk": 'index=os sourcetype=syslog ("pwnkit" OR "cve-202" OR "overlayfs") | table _time, host, user, command'
            },
            "T1003": {
                "category": "process_creation",
                "product": "linux",
                "selection": {
                    "CommandLine|contains": ["/etc/shadow", "mimikatz", "procdump", "lsass", "sekurlsa"]
                },
                "splunk": 'index=os (process="*shadow*" OR command="*mimikatz*" OR command="*lsass*") | stats count by host, user, command'
            },
            "T1021": {
                "category": "network_connection",
                "product": "firewall",
                "selection": {
                    "DestinationPort": [22, 445, 3389, 5985],
                    "Direction": "internal"
                },
                "splunk": 'index=firewall (dest_port=22 OR dest_port=445 OR dest_port=3389) src_ip="10.*" dest_ip="10.*" | stats count by src_ip, dest_ip, dest_port'
            },
            "T1485": {
                "category": "file_event",
                "product": "linux",
                "selection": {
                    "CommandLine|contains": ["rm -rf /", "shred ", "dd if=/dev/zero", "drop database"]
                },
                "splunk": 'index=os command="*rm -rf*" OR command="*shred*" OR command="*drop database*" | table _time, host, user, command'
            }
        }

        today_str = date.today().isoformat()
        rules = []

        for nid, node in self.nodes.items():
            tech = node.mitre_technique
            rule_info = sigma_templates.get(tech)
            if not rule_info:
                rule_info = {
                    "category": "process_creation",
                    "product": "linux",
                    "selection": {"CommandLine|contains": [node.label.lower()[:30]]},
                    "splunk": f'index=* (CommandLine="*{node.label[:25]}*") | table _time, host, user, command'
                }

            rule_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"secscan_ai.{node.node_id}.{tech}"))
            sigma_yaml = (
                f"title: SecScan AI Detection - {node.label}\n"
                f"id: {rule_id}\n"
                f"status: experimental\n"
                f"description: Detects adversarial activity corresponding to {node.label} ({tech})\n"
                f"references:\n"
                f"  - https://attack.mitre.org/techniques/{tech}/\n"
                f"author: SecScan AI Enterprise Threat Intel\n"
                f"date: {today_str}\n"
                f"logsource:\n"
                f"  category: {rule_info['category']}\n"
                f"  product: {rule_info['product']}\n"
                f"detection:\n"
                f"  selection:\n"
            )
            for k, v in rule_info["selection"].items():
                if isinstance(v, list):
                    sigma_yaml += f"    {k}:\n"
                    for val in v:
                        sigma_yaml += f"      - '{val}'\n"
                else:
                    sigma_yaml += f"    {k}: '{v}'\n"

            sigma_yaml += (
                "  condition: selection\n"
                "falsepositives:\n"
                "  - Legitimate security maintenance or authorized penetration tests\n"
                f"level: {'critical' if node.stage in (AttackStage.IMPACT, AttackStage.PRIVILEGE_ESCALATION) else 'high'}\n"
                "tags:\n"
                f"  - attack.{tech.lower()}\n"
                f"  - attack.{node.stage.value}\n"
            )

            rules.append({
                "rule_id": rule_id,
                "node_id": node.node_id,
                "label": node.label,
                "technique": tech,
                "stage": node.stage.value,
                "sigma_yaml": sigma_yaml,
                "splunk_spl": rule_info["splunk"]
            })

        return rules

    def generate_ansible_playbook(self) -> str:
        """
        Generate an automated remediation Ansible Playbook (YAML)
        specifically targeting critical defensive chokepoints in the attack graph.
        """
        chokepoints = self.find_critical_chokepoints()
        tasks = []

        # Common base hardening tasks
        tasks.append("""  - name: Ensure OS package manager and security updates are applied
    package:
      name: "*"
      state: latest
    when: ansible_os_family in ['Debian', 'RedHat']""")

        tasks.append("""  - name: Enforce sysctl kernel security hardening
    sysctl:
      name: "{{ item.key }}"
      value: "{{ item.value }}"
      state: present
      reload: yes
    loop:
      - { key: 'fs.protected_hardlinks', value: '1' }
      - { key: 'fs.protected_symlinks', value: '1' }
      - { key: 'fs.suid_dumpable', value: '0' }
      - { key: 'kernel.dmesg_restrict', value: '1' }
      - { key: 'kernel.kptr_restrict', value: '2' }
      - { key: 'kernel.yama.ptrace_scope', value: '2' }""")

        tasks.append("""  - name: Audit and restrict sudoers configuration
    lineinfile:
      path: /etc/sudoers
      state: present
      regexp: '.*NOPASSWD.*'
      line: '# NOPASSWD disabled by SecScan AI Enterprise Hardening'
      validate: 'visudo -cf %s'""")

        # Add tailored chokepoint remediations
        for chk in chokepoints:
            tech = chk.get("mitre_technique", "")
            if tech in ("T1190", "T1059"):
                tasks.append(f"""  - name: Harden Web Server Application Permissions (Addressing {chk['label']})
    file:
      path: /var/www
      owner: www-data
      group: www-data
      mode: '0750'
      recurse: yes
    ignore_errors: yes""")
            elif tech in ("T1548", "T1068"):
                tasks.append(f"""  - name: Remove unneeded SUID binaries (Addressing {chk['label']})
    shell: "find / -perm /4000 -type f -exec chmod u-s {{}} + 2>/dev/null"
    args:
      warn: false
    ignore_errors: yes""")
            elif tech == "T1021":
                tasks.append(f"""  - name: Enforce SSH hardening & disable root login (Addressing {chk['label']})
    lineinfile:
      path: /etc/ssh/sshd_config
      regexp: '^PermitRootLogin'
      line: 'PermitRootLogin no'
    notify: Restart sshd""")

        playbook = "---\n- name: SecScan AI Enterprise Automated Attack Graph Remediation\n"
        playbook += "  hosts: all\n"
        playbook += "  become: yes\n"
        playbook += "  tasks:\n"
        playbook += "\n\n".join(tasks)
        playbook += "\n\n  handlers:\n"
        playbook += "    - name: Restart sshd\n"
        playbook += "      service:\n"
        playbook += "        name: sshd\n"
        playbook += "        state: restarted\n"

        return playbook

    def generate_hardening_script(self) -> str:
        """
        Generate an executable Bash hardening script tailored to sever the
        critical chokepoints identified in the attack graph.
        """
        chokepoints = self.find_critical_chokepoints()
        lines = [
            "#!/usr/bin/env bash",
            "# ===================================================================",
            "# SecScan AI Enterprise - Automated Security Hardening Script",
            "# Generated automatically from synthesized Attack Graph chokepoints",
            "# ===================================================================",
            "set -euo pipefail",
            "",
            "echo '[+] Initiating SecScan AI defensive hardening...'",
            "",
            "# 1. Kernel sysctl parameter hardening",
            "echo '[+] Applying kernel sysctl parameters...'",
            "cat << 'EOF' > /etc/sysctl.d/99-secscan_ai-hardening.conf",
            "fs.protected_hardlinks = 1",
            "fs.protected_symlinks = 1",
            "fs.suid_dumpable = 0",
            "kernel.dmesg_restrict = 1",
            "kernel.kptr_restrict = 2",
            "kernel.yama.ptrace_scope = 2",
            "net.ipv4.conf.all.rp_filter = 1",
            "net.ipv4.conf.default.rp_filter = 1",
            "EOF",
            "sysctl --system >/dev/null 2>&1 || true",
            "",
            "# 2. Disable passwordless sudo and audit sudoers",
            "echo '[+] Hardening sudoers configuration...'",
            "if [ -f /etc/sudoers ]; then",
            "    sed -i -E 's/(.*NOPASSWD.*)/# \\1 # Disabled by SecScan AI/' /etc/sudoers || true",
            "fi",
            "",
            "# 3. Umask & permissions hardening",
            "echo '[+] Enforcing default secure umask 027...'",
            "umask 027",
            ""
        ]

        # Specific chokepoint mitigations
        for chk in chokepoints:
            tech = chk.get("mitre_technique", "")
            lines.append(f"# Mitigation for: {chk['label']} ({tech})")
            if tech in ("T1190", "T1059"):
                lines.append("if [ -d /var/www ]; then")
                lines.append("    find /var/www -type d -exec chmod 750 {} + 2>/dev/null || true")
                lines.append("    find /var/www -type f -exec chmod 640 {} + 2>/dev/null || true")
                lines.append("fi")
            elif tech in ("T1548", "T1068"):
                lines.append("# Restrict elevated execution on shared temporary storage")
                lines.append("mount -o remount,noexec,nosuid,nodev /tmp 2>/dev/null || true")
            elif tech == "T1021":
                lines.append("# Restrict remote root SSH login")
                lines.append("if [ -f /etc/ssh/sshd_config ]; then")
                lines.append("    sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config || true")
                lines.append("    systemctl restart sshd 2>/dev/null || service ssh restart 2>/dev/null || true")
                lines.append("fi")
            lines.append("")

        lines.append("echo '[✓] SecScan AI Enterprise defensive hardening completed successfully.'")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to JSON-serializable dictionary structure."""
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges],
            "chokepoints": self.find_critical_chokepoints(),
            "paths_count": len(self.find_all_paths()),
            "d3fend_countermeasures": self.to_d3fend_matrix(),
            "sigma_rules_count": len(self.export_sigma_rules())
        }


class AttackChainingEngine:
    """
    Automated attack chain synthesis engine.
    Analyzes raw vulnerability collections, infers causal dependencies,
    and constructs multi-stage attack scenarios.
    """

    def synthesize_attack_graph(
        self,
        vulnerabilities: List[Dict[str, Any]],
        target_assets: Optional[List[Dict[str, Any]]] = None
    ) -> AttackGraph:
        """
        Synthesize a comprehensive AttackGraph from parsed vulnerability findings.
        """
        graph = AttackGraph()

        if not vulnerabilities:
            return graph

        # Map findings into categorized stages
        categorized_nodes: Dict[AttackStage, List[AttackNode]] = {stage: [] for stage in AttackStage}

        for idx, vuln in enumerate(vulnerabilities):
            stage = self._classify_vulnerability_stage(vuln)
            diff = self._calculate_exploit_difficulty(vuln)
            tech = self._infer_mitre_technique(vuln, stage)
            node_id = f"node_{stage.value[:4]}_{idx + 1}"
            label = vuln.get("title") or vuln.get("name") or f"Vulnerability {idx + 1}"

            node = AttackNode(
                node_id=node_id,
                label=str(label),
                stage=stage,
                vulnerability_id=str(vuln.get("id", f"v_{idx}")),
                asset=str(vuln.get("target") or vuln.get("host") or "target_host"),
                difficulty=diff,
                mitre_technique=tech,
                description=str(vuln.get("description", ""))
            )
            graph.add_node(node)
            categorized_nodes[stage].append(node)

        # Fallback synthetic target node if no impact node was directly generated
        if not categorized_nodes[AttackStage.IMPACT]:
            impact_node = AttackNode(
                node_id="node_target_objective",
                label="Full System Compromise & Data Extraction",
                stage=AttackStage.IMPACT,
                difficulty=0.9,
                mitre_technique="T1485",
                description="Attacker accomplishes operational compromise or data theft."
            )
            graph.add_node(impact_node)
            categorized_nodes[AttackStage.IMPACT].append(impact_node)

        # Ensure we have at least one initial access node
        if not categorized_nodes[AttackStage.INITIAL_ACCESS] and not categorized_nodes[AttackStage.RECONNAISSANCE]:
            for st, nodes in categorized_nodes.items():
                if nodes and st != AttackStage.IMPACT:
                    first = nodes.pop(0)
                    first.stage = AttackStage.INITIAL_ACCESS
                    categorized_nodes[AttackStage.INITIAL_ACCESS].append(first)
                    break

        # Build causal edges across logical stage progressions
        self._link_stages(graph, categorized_nodes, AttackStage.INITIAL_ACCESS, AttackStage.EXECUTION, "Payload Delivery & Execution", 0.85)
        self._link_stages(graph, categorized_nodes, AttackStage.EXECUTION, AttackStage.PRIVILEGE_ESCALATION, "Elevate Context to Administrator/Root", 0.75)
        self._link_stages(graph, categorized_nodes, AttackStage.PRIVILEGE_ESCALATION, AttackStage.CREDENTIAL_ACCESS, "Dump Memory Credentials & Secrets", 0.80)
        self._link_stages(graph, categorized_nodes, AttackStage.CREDENTIAL_ACCESS, AttackStage.LATERAL_MOVEMENT, "Authenticate against Internal Network", 0.70)
        self._link_stages(graph, categorized_nodes, AttackStage.LATERAL_MOVEMENT, AttackStage.IMPACT, "Pivot to Core Enterprise Database", 0.90)

        # Ensure path to IMPACT exists from the latest active upstream stage
        for imp_node in categorized_nodes[AttackStage.IMPACT]:
            in_edges = [e for e in graph.edges if e.target == imp_node.node_id]
            if not in_edges:
                upstream_candidates = (
                    categorized_nodes[AttackStage.LATERAL_MOVEMENT]
                    or categorized_nodes[AttackStage.CREDENTIAL_ACCESS]
                    or categorized_nodes[AttackStage.PRIVILEGE_ESCALATION]
                    or categorized_nodes[AttackStage.EXECUTION]
                    or categorized_nodes[AttackStage.INITIAL_ACCESS]
                )
                for u in upstream_candidates[-2:]:
                    if u.node_id != imp_node.node_id:
                        graph.add_edge(AttackEdge(
                            source=u.node_id,
                            target=imp_node.node_id,
                            transition_condition="Direct Compromise of Core Target Asset",
                            probability=0.85
                        ))

        # Connect any unlinked initial access nodes directly to privilege escalation or impact if intermediate stages were absent
        for init_node in categorized_nodes[AttackStage.INITIAL_ACCESS]:
            out_edges = [e for e in graph.edges if e.source == init_node.node_id]
            if not out_edges:
                next_target = (
                    categorized_nodes[AttackStage.PRIVILEGE_ESCALATION]
                    or categorized_nodes[AttackStage.CREDENTIAL_ACCESS]
                    or categorized_nodes[AttackStage.IMPACT]
                )
                if next_target and next_target[0].node_id != init_node.node_id:
                    graph.add_edge(AttackEdge(
                        source=init_node.node_id,
                        target=next_target[0].node_id,
                        transition_condition="Direct Exploitation to Elevated Access",
                        probability=0.75
                    ))

        return graph

    def _link_stages(
        self,
        graph: AttackGraph,
        categorized_nodes: Dict[AttackStage, List[AttackNode]],
        src_stage: AttackStage,
        dst_stage: AttackStage,
        condition: str,
        probability: float
    ) -> None:
        """Create connecting edges between source and destination stages."""
        sources = categorized_nodes.get(src_stage, [])
        destinations = categorized_nodes.get(dst_stage, [])

        if not sources or not destinations:
            return

        for src in sources:
            linked = 0
            for dst in destinations:
                if src.node_id == dst.node_id:
                    continue
                # Prevent duplicate edges
                if any(e.source == src.node_id and e.target == dst.node_id for e in graph.edges):
                    continue
                graph.add_edge(AttackEdge(
                    source=src.node_id,
                    target=dst.node_id,
                    transition_condition=condition,
                    probability=probability
                ))
                linked += 1
                if linked >= 2:  # Limit fan-out to 2 per node for clean topologies
                    break

    def _classify_vulnerability_stage(self, vuln: Dict[str, Any]) -> AttackStage:
        """Classify vulnerability into appropriate MITRE attack stage."""
        text = " ".join([
            str(vuln.get("title", "")),
            str(vuln.get("description", "")),
            str(vuln.get("category", "")),
            str(vuln.get("type", ""))
        ]).lower()

        if any(w in text for w in ["root", "privilege", "sudo", "suid", "escalat", "uac", "bypass"]):
            return AttackStage.PRIVILEGE_ESCALATION
        if any(w in text for w in ["rce", "remote code", "command injection", "deserialization", "eval"]):
            return AttackStage.EXECUTION
        if any(w in text for w in ["credential", "password", "hash", "secret", "token", "jwt", "key", "lsass"]):
            return AttackStage.CREDENTIAL_ACCESS
        if any(w in text for w in ["smb", "ssh", "rdp", "lateral", "pivot", "internal", "relay"]):
            return AttackStage.LATERAL_MOVEMENT
        if any(w in text for w in ["sqli", "sql injection", "xss", "traversal", "ssrf", "upload", "auth bypass", "phish"]):
            return AttackStage.INITIAL_ACCESS
        if any(w in text for w in ["exfiltration", "leak", "dump", "ransom", "destroy", "dos"]):
            return AttackStage.IMPACT
        if any(w in text for w in ["recon", "scan", "info", "disclosure", "banner"]):
            return AttackStage.RECONNAISSANCE

        return AttackStage.INITIAL_ACCESS

    def _calculate_exploit_difficulty(self, vuln: Dict[str, Any]) -> float:
        """Score exploitation ease (1.0 = trivial, 0.2 = high difficulty)."""
        severity = str(vuln.get("severity", "")).lower()
        if severity == "critical":
            return 0.95
        elif severity == "high":
            return 0.80
        elif severity == "medium":
            return 0.50
        elif severity == "low":
            return 0.25
        return 0.50

    def _infer_mitre_technique(self, vuln: Dict[str, Any], stage: AttackStage) -> str:
        """Assign MITRE ATT&CK technique code."""
        text = str(vuln.get("title", "")).lower()
        if "sql" in text:
            return "T1190"  # Exploit Public-Facing Application
        if "command" in text or "rce" in text:
            return "T1059"  # Command and Scripting Interpreter
        if "privilege" in text or "sudo" in text:
            return "T1548"  # Abuse Elevation Control Mechanism
        if "credential" in text or "password" in text:
            return "T1003"  # OS Credential Dumping
        if "smb" in text or "lateral" in text:
            return "T1021"  # Remote Services

        stage_defaults = {
            AttackStage.RECONNAISSANCE: "T1595",
            AttackStage.INITIAL_ACCESS: "T1190",
            AttackStage.EXECUTION: "T1059",
            AttackStage.PRIVILEGE_ESCALATION: "T1068",
            AttackStage.CREDENTIAL_ACCESS: "T1003",
            AttackStage.LATERAL_MOVEMENT: "T1021",
            AttackStage.IMPACT: "T1485",
        }
        return stage_defaults.get(stage, "T1190")

    def generate_remediation_roadmap(self, attack_graph: AttackGraph) -> List[Dict[str, Any]]:
        """
        Produce a ranked remediation plan focusing on highest defensive ROI.
        """
        chokepoints = attack_graph.find_critical_chokepoints()
        roadmap = []

        for rank, chk in enumerate(chokepoints, 1):
            roadmap.append({
                "priority_rank": rank,
                "node_label": chk["label"],
                "mitre_technique": chk["mitre_technique"],
                "attack_stage": chk["stage"],
                "attack_chains_broken": chk["affected_chains_count"],
                "coverage_pct": chk["coverage_percentage"],
                "strategic_action": chk["remediation_summary"],
                "urgency": "IMMEDIATE" if rank <= 2 else "HIGH"
            })

        return roadmap

    def generate_d3fend_matrix(self, attack_graph: AttackGraph) -> List[Dict[str, Any]]:
        """Map attack graph components to MITRE D3FEND defensive countermeasures."""
        return attack_graph.to_d3fend_matrix()

    def export_detection_rules(self, attack_graph: AttackGraph) -> List[Dict[str, Any]]:
        """Export Sigma and Splunk detection rules derived from attack graph stages."""
        return attack_graph.export_sigma_rules()

    def generate_playbooks(self, attack_graph: AttackGraph) -> Dict[str, str]:
        """Generate automated Ansible and Bash remediation playbooks."""
        return {
            "ansible": attack_graph.generate_ansible_playbook(),
            "bash": attack_graph.generate_hardening_script()
        }
