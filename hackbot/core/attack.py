"""
HackBot MITRE ATT&CK Mapping Engine
=====================================
Maps agent actions, tool usage, and security findings to MITRE ATT&CK
techniques and tactics.  Generates ATT&CK Navigator layer JSON for
visualization at https://mitre-attack.github.io/attack-navigator/.

Features:
  - Map findings to ATT&CK techniques via keyword rules
  - Map tool execution history to techniques
  - Generate ATT&CK Navigator layer JSON
  - Formatted Markdown reports
  - Statistics and coverage analysis

Reference: https://attack.mitre.org/

Developed by Yashab Alam
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from hackbot import __version__


# ── ATT&CK Data Models ──────────────────────────────────────────────────────

@dataclass
class Tactic:
    """A MITRE ATT&CK tactic (column in the matrix)."""
    id: str            # e.g. "TA0043"
    name: str          # e.g. "Reconnaissance"
    short_name: str    # e.g. "reconnaissance" (Navigator key)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "short_name": self.short_name,
            "description": self.description,
        }


@dataclass
class Technique:
    """A MITRE ATT&CK technique."""
    id: str            # e.g. "T1046"
    name: str          # e.g. "Network Service Scanning"
    tactic_ids: List[str] = field(default_factory=list)  # parent tactic IDs
    description: str = ""
    is_subtechnique: bool = False
    parent_id: str = ""
    url: str = ""

    def __post_init__(self):
        if not self.url:
            tid = self.id.replace(".", "/")
            self.url = f"https://attack.mitre.org/techniques/{tid}/"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "tactic_ids": self.tactic_ids,
            "description": self.description,
            "is_subtechnique": self.is_subtechnique,
            "parent_id": self.parent_id,
            "url": self.url,
        }


@dataclass
class TechniqueMapping:
    """A mapping from a finding/tool action to an ATT&CK technique."""
    technique: Technique
    source: str = ""       # "finding" | "tool" | "manual"
    source_name: str = ""  # finding title or tool name
    confidence: str = "medium"  # "high" | "medium" | "low"
    notes: str = ""
    severity: str = ""      # from the finding, if applicable

    def to_dict(self) -> Dict[str, Any]:
        return {
            "technique": self.technique.to_dict(),
            "source": self.source,
            "source_name": self.source_name,
            "confidence": self.confidence,
            "notes": self.notes,
            "severity": self.severity,
        }


@dataclass
class AttackReport:
    """Complete ATT&CK mapping report."""
    mappings: List[TechniqueMapping] = field(default_factory=list)
    target: str = ""
    total_findings: int = 0
    total_tools: int = 0

    def to_dict(self) -> Dict[str, Any]:
        by_tactic: Dict[str, List[Dict]] = {}
        unique_techniques: Set[str] = set()

        for m in self.mappings:
            unique_techniques.add(m.technique.id)
            for tac_id in m.technique.tactic_ids:
                tactic_name = TACTIC_MAP.get(tac_id, Tactic(tac_id, tac_id, tac_id)).name
                by_tactic.setdefault(tactic_name, []).append(m.to_dict())

        return {
            "target": self.target,
            "total_findings": self.total_findings,
            "total_tools": self.total_tools,
            "total_mappings": len(self.mappings),
            "unique_techniques": len(unique_techniques),
            "tactics_covered": len(by_tactic),
            "total_tactics": len(TACTICS),
            "by_tactic": by_tactic,
        }


# ── ATT&CK Tactics ──────────────────────────────────────────────────────────
# Full Enterprise ATT&CK tactic list (v15)

TACTICS: List[Tactic] = [
    Tactic("TA0043", "Reconnaissance", "reconnaissance",
           "Gathering information to plan future operations."),
    Tactic("TA0042", "Resource Development", "resource-development",
           "Establishing resources to support operations."),
    Tactic("TA0001", "Initial Access", "initial-access",
           "Trying to get into your network."),
    Tactic("TA0002", "Execution", "execution",
           "Trying to run malicious code."),
    Tactic("TA0003", "Persistence", "persistence",
           "Trying to maintain their foothold."),
    Tactic("TA0004", "Privilege Escalation", "privilege-escalation",
           "Trying to gain higher-level permissions."),
    Tactic("TA0005", "Defense Evasion", "defense-evasion",
           "Trying to avoid being detected."),
    Tactic("TA0006", "Credential Access", "credential-access",
           "Trying to steal account names and passwords."),
    Tactic("TA0007", "Discovery", "discovery",
           "Trying to figure out your environment."),
    Tactic("TA0008", "Lateral Movement", "lateral-movement",
           "Trying to move through your environment."),
    Tactic("TA0009", "Collection", "collection",
           "Trying to gather data of interest."),
    Tactic("TA0011", "Command and Control", "command-and-control",
           "Trying to communicate with compromised systems."),
    Tactic("TA0010", "Exfiltration", "exfiltration",
           "Trying to steal data."),
    Tactic("TA0040", "Impact", "impact",
           "Trying to manipulate, interrupt, or destroy data and systems."),
]

# Quick lookup: tactic_id → Tactic
TACTIC_MAP: Dict[str, Tactic] = {t.id: t for t in TACTICS}
TACTIC_NAME_MAP: Dict[str, Tactic] = {t.name: t for t in TACTICS}


# ── ATT&CK Techniques (curated subset relevant to pentesting) ───────────────
# Each technique includes the tactic IDs it maps to.

TECHNIQUES: List[Technique] = [
    # -- Reconnaissance --
    Technique("T1595", "Active Scanning", ["TA0043"],
              "Scanning infrastructure to gather information."),
    Technique("T1595.001", "Scanning IP Blocks", ["TA0043"],
              "Scanning IP blocks to gather victim network information.",
              is_subtechnique=True, parent_id="T1595"),
    Technique("T1595.002", "Vulnerability Scanning", ["TA0043"],
              "Scanning systems for vulnerabilities.",
              is_subtechnique=True, parent_id="T1595"),
    Technique("T1592", "Gather Victim Host Information", ["TA0043"],
              "Gathering information about victim hosts."),
    Technique("T1592.002", "Software", ["TA0043"],
              "Gathering information about victim host software.",
              is_subtechnique=True, parent_id="T1592"),
    Technique("T1590", "Gather Victim Network Information", ["TA0043"],
              "Gathering information about victim networks."),
    Technique("T1590.004", "Network Topology", ["TA0043"],
              "Gathering victim network topology information.",
              is_subtechnique=True, parent_id="T1590"),
    Technique("T1590.005", "IP Addresses", ["TA0043"],
              "Gathering victim IP address information.",
              is_subtechnique=True, parent_id="T1590"),
    Technique("T1593", "Search Open Websites/Domains", ["TA0043"],
              "Searching freely available websites and domains."),
    Technique("T1596", "Search Open Technical Databases", ["TA0043"],
              "Searching freely available technical databases."),
    Technique("T1589", "Gather Victim Identity Information", ["TA0043"],
              "Gathering identity information."),
    Technique("T1591", "Gather Victim Org Information", ["TA0043"],
              "Gathering organization information."),
    Technique("T1597", "Search Closed Sources", ["TA0043"],
              "Searching closed sources for victim information."),

    # -- Initial Access --
    Technique("T1190", "Exploit Public-Facing Application", ["TA0001"],
              "Exploiting vulnerabilities in internet-facing applications."),
    Technique("T1133", "External Remote Services", ["TA0001", "TA0003"],
              "Leveraging external-facing remote services."),
    Technique("T1078", "Valid Accounts", ["TA0001", "TA0003", "TA0004", "TA0005"],
              "Using legitimate credentials to gain access."),
    Technique("T1189", "Drive-by Compromise", ["TA0001"],
              "Gaining access through a user visiting a website."),
    Technique("T1566", "Phishing", ["TA0001"],
              "Sending phishing messages to gain access."),

    # -- Execution --
    Technique("T1059", "Command and Scripting Interpreter", ["TA0002"],
              "Abusing command and script interpreters to execute commands."),
    Technique("T1059.001", "PowerShell", ["TA0002"],
              "Abusing PowerShell for execution.",
              is_subtechnique=True, parent_id="T1059"),
    Technique("T1059.003", "Windows Command Shell", ["TA0002"],
              "Abusing cmd.exe for execution.",
              is_subtechnique=True, parent_id="T1059"),
    Technique("T1059.004", "Unix Shell", ["TA0002"],
              "Abusing Unix shell for execution.",
              is_subtechnique=True, parent_id="T1059"),
    Technique("T1203", "Exploitation for Client Execution", ["TA0002"],
              "Exploiting software vulnerabilities for code execution."),

    # -- Persistence --
    Technique("T1505", "Server Software Component", ["TA0003"],
              "Abusing server software to establish persistence."),
    Technique("T1505.003", "Web Shell", ["TA0003"],
              "Placing a web shell on a web server.",
              is_subtechnique=True, parent_id="T1505"),
    Technique("T1136", "Create Account", ["TA0003"],
              "Creating accounts for persistence."),
    Technique("T1098", "Account Manipulation", ["TA0003", "TA0004"],
              "Manipulating accounts to maintain or escalate access."),
    Technique("T1053", "Scheduled Task/Job", ["TA0002", "TA0003", "TA0004"],
              "Abusing task scheduling for execution or persistence."),

    # -- Privilege Escalation --
    Technique("T1068", "Exploitation for Privilege Escalation", ["TA0004"],
              "Exploiting software vulnerabilities to escalate privileges."),
    Technique("T1548", "Abuse Elevation Control Mechanism", ["TA0004", "TA0005"],
              "Circumventing elevated access controls."),
    Technique("T1548.001", "Setuid and Setgid", ["TA0004", "TA0005"],
              "Abusing setuid/setgid bits for privilege escalation.",
              is_subtechnique=True, parent_id="T1548"),
    Technique("T1548.003", "Sudo and Sudo Caching", ["TA0004", "TA0005"],
              "Abusing sudo for privilege escalation.",
              is_subtechnique=True, parent_id="T1548"),

    # -- Defense Evasion --
    Technique("T1070", "Indicator Removal", ["TA0005"],
              "Deleting or modifying artifacts such as logs."),
    Technique("T1027", "Obfuscated Files or Information", ["TA0005"],
              "Attempting to make payloads difficult to discover or analyze."),
    Technique("T1562", "Impair Defenses", ["TA0005"],
              "Disabling or modifying security tools."),
    Technique("T1562.001", "Disable or Modify Tools", ["TA0005"],
              "Disabling security software.",
              is_subtechnique=True, parent_id="T1562"),

    # -- Credential Access --
    Technique("T1110", "Brute Force", ["TA0006"],
              "Trying many passwords or keys to discover valid credentials."),
    Technique("T1110.001", "Password Guessing", ["TA0006"],
              "Guessing passwords for user accounts.",
              is_subtechnique=True, parent_id="T1110"),
    Technique("T1110.003", "Password Spraying", ["TA0006"],
              "Using a single password against many accounts.",
              is_subtechnique=True, parent_id="T1110"),
    Technique("T1110.004", "Credential Stuffing", ["TA0006"],
              "Using breached credential pairs.",
              is_subtechnique=True, parent_id="T1110"),
    Technique("T1555", "Credentials from Password Stores", ["TA0006"],
              "Searching password stores for credentials."),
    Technique("T1552", "Unsecured Credentials", ["TA0006"],
              "Searching for insecurely stored credentials."),
    Technique("T1552.001", "Credentials In Files", ["TA0006"],
              "Searching local file systems for credentials.",
              is_subtechnique=True, parent_id="T1552"),
    Technique("T1557", "Adversary-in-the-Middle", ["TA0006", "TA0009"],
              "Positioning between two targets to intercept traffic."),
    Technique("T1040", "Network Sniffing", ["TA0006", "TA0007"],
              "Sniffing network traffic for information."),
    Technique("T1003", "OS Credential Dumping", ["TA0006"],
              "Dumping credentials from the operating system."),
    Technique("T1212", "Exploitation for Credential Access", ["TA0006"],
              "Exploiting software vulnerabilities to collect credentials."),

    # -- Discovery --
    Technique("T1046", "Network Service Discovery", ["TA0007"],
              "Enumerating services running on remote hosts."),
    Technique("T1018", "Remote System Discovery", ["TA0007"],
              "Discovering remote systems on a network."),
    Technique("T1082", "System Information Discovery", ["TA0007"],
              "Getting detailed information about the operating system and hardware."),
    Technique("T1083", "File and Directory Discovery", ["TA0007"],
              "Enumerating files and directories."),
    Technique("T1087", "Account Discovery", ["TA0007"],
              "Getting a listing of accounts on a system or domain."),
    Technique("T1016", "System Network Configuration Discovery", ["TA0007"],
              "Looking at network configuration and settings."),
    Technique("T1049", "System Network Connections Discovery", ["TA0007"],
              "Getting network connections to and from the compromised system."),
    Technique("T1069", "Permission Groups Discovery", ["TA0007"],
              "Enumerating permission groups."),
    Technique("T1518", "Software Discovery", ["TA0007"],
              "Enumerating installed software."),
    Technique("T1580", "Cloud Infrastructure Discovery", ["TA0007"],
              "Discovering cloud infrastructure."),
    Technique("T1135", "Network Share Discovery", ["TA0007"],
              "Looking for shared drives and folders."),
    Technique("T1047", "Windows Management Instrumentation", ["TA0002"],
              "Using WMI to execute commands."),

    # -- Lateral Movement --
    Technique("T1021", "Remote Services", ["TA0008"],
              "Using remote services to move laterally."),
    Technique("T1021.001", "Remote Desktop Protocol", ["TA0008"],
              "Using RDP to move laterally.",
              is_subtechnique=True, parent_id="T1021"),
    Technique("T1021.004", "SSH", ["TA0008"],
              "Using SSH to move laterally.",
              is_subtechnique=True, parent_id="T1021"),
    Technique("T1210", "Exploitation of Remote Services", ["TA0008"],
              "Exploiting remote services for lateral movement."),

    # -- Collection --
    Technique("T1005", "Data from Local System", ["TA0009"],
              "Searching local system sources for data."),
    Technique("T1039", "Data from Network Shared Drive", ["TA0009"],
              "Searching network shares for data."),
    Technique("T1114", "Email Collection", ["TA0009"],
              "Collecting email data."),
    Technique("T1213", "Data from Information Repositories", ["TA0009"],
              "Mining data from information repositories."),

    # -- Command and Control --
    Technique("T1071", "Application Layer Protocol", ["TA0011"],
              "Using application layer protocols for C2 communication."),
    Technique("T1105", "Ingress Tool Transfer", ["TA0011"],
              "Transferring tools from external systems."),
    Technique("T1572", "Protocol Tunneling", ["TA0011"],
              "Tunneling network communications using a protocol."),
    Technique("T1573", "Encrypted Channel", ["TA0011"],
              "Using encrypted channels for C2."),

    # -- Exfiltration --
    Technique("T1048", "Exfiltration Over Alternative Protocol", ["TA0010"],
              "Transferring data via a non-C2 protocol."),
    Technique("T1567", "Exfiltration Over Web Service", ["TA0010"],
              "Exfiltrating data to a web service."),

    # -- Impact --
    Technique("T1499", "Endpoint Denial of Service", ["TA0040"],
              "Performing denial of service to degrade availability."),
    Technique("T1499.002", "Service Exhaustion Flood", ["TA0040"],
              "Performing a DoS via resource exhaustion.",
              is_subtechnique=True, parent_id="T1499"),
    Technique("T1485", "Data Destruction", ["TA0040"],
              "Destroying data and files on specific systems."),
    Technique("T1486", "Data Encrypted for Impact", ["TA0040"],
              "Encrypting data on target systems (ransomware)."),
    Technique("T1491", "Defacement", ["TA0040"],
              "Modifying visual content internally or externally."),
    Technique("T1531", "Account Access Removal", ["TA0040"],
              "Removing access to accounts."),
]

# Quick lookups
TECHNIQUE_MAP: Dict[str, Technique] = {t.id: t for t in TECHNIQUES}


# ── Tool → Technique Mapping ────────────────────────────────────────────────
# Maps HackBot's allowed tools to the ATT&CK techniques they implement.
# Each tool maps to [(technique_id, confidence, notes)].

TOOL_TECHNIQUE_MAP: Dict[str, List[Tuple[str, str, str]]] = {
    "nmap": [
        ("T1046",    "high",   "Network service discovery / port scanning"),
        ("T1595.001","high",   "Active scanning of IP blocks"),
        ("T1592.002","medium", "OS and service version fingerprinting"),
        ("T1082",    "medium", "System information via service banners"),
    ],
    "masscan": [
        ("T1595.001","high",   "High-speed IP block scanning"),
        ("T1046",    "high",   "Network service discovery"),
    ],
    "nikto": [
        ("T1595.002","high",   "Web server vulnerability scanning"),
        ("T1190",    "medium", "Testing for exploitable web vulnerabilities"),
    ],
    "nuclei": [
        ("T1595.002","high",   "Template-based vulnerability scanning"),
        ("T1190",    "medium", "Testing for exploitable vulnerabilities"),
    ],
    "sqlmap": [
        ("T1190",    "high",   "SQL injection exploitation"),
        ("T1059",    "high",   "Command execution via SQL injection"),
        ("T1005",    "medium", "Data extraction via SQL injection"),
    ],
    "gobuster": [
        ("T1083",    "high",   "Directory/file brute-force enumeration"),
        ("T1595",    "medium", "Active scanning for hidden content"),
    ],
    "dirb": [
        ("T1083",    "high",   "Directory brute-force enumeration"),
        ("T1595",    "medium", "Active scanning for hidden directories"),
    ],
    "ffuf": [
        ("T1083",    "high",   "Fuzzing for files and directories"),
        ("T1595",    "medium", "Active content discovery"),
    ],
    "wfuzz": [
        ("T1083",    "high",   "Web fuzzing for parameters and paths"),
        ("T1190",    "medium", "Parameter injection testing"),
    ],
    "subfinder": [
        ("T1590",    "high",   "Subdomain enumeration"),
        ("T1593",    "high",   "Passive subdomain discovery"),
    ],
    "amass": [
        ("T1590",    "high",   "Network mapping and subdomain discovery"),
        ("T1593",    "high",   "Active and passive reconnaissance"),
        ("T1596",    "medium", "Searching technical databases"),
    ],
    "httpx": [
        ("T1595",    "medium", "HTTP probing and fingerprinting"),
        ("T1592.002","medium", "Web technology fingerprinting"),
    ],
    "whatweb": [
        ("T1592.002","high",   "Web technology fingerprinting"),
        ("T1595",    "medium", "Active web scanning"),
    ],
    "hydra": [
        ("T1110",    "high",   "Network brute-force attacks"),
        ("T1110.001","high",   "Password guessing"),
    ],
    "john": [
        ("T1110",    "high",   "Offline password cracking"),
        ("T1003",    "medium", "Credential recovery from hashes"),
    ],
    "hashcat": [
        ("T1110",    "high",   "GPU-accelerated password cracking"),
        ("T1003",    "medium", "Credential recovery from hashes"),
    ],
    "curl": [
        ("T1071",    "low",    "HTTP request crafting"),
        ("T1190",    "low",    "Manual web application testing"),
    ],
    "wget": [
        ("T1105",    "medium", "File download / tool transfer"),
    ],
    "dig": [
        ("T1590",    "high",   "DNS information gathering"),
        ("T1016",    "medium", "Network configuration discovery via DNS"),
    ],
    "whois": [
        ("T1591",    "high",   "Domain/IP owner information gathering"),
        ("T1596",    "high",   "Searching WHOIS databases"),
    ],
    "traceroute": [
        ("T1590.004","high",   "Network topology mapping"),
        ("T1016",    "medium", "Network path discovery"),
    ],
    "ping": [
        ("T1018",    "medium", "Host discovery via ICMP"),
    ],
    "netcat": [
        ("T1046",    "medium", "Banner grabbing / service probing"),
        ("T1071",    "medium", "Network communication"),
    ],
    "openssl": [
        ("T1573",    "low",    "SSL/TLS inspection and testing"),
    ],
    "testssl": [
        ("T1595.002","high",   "TLS/SSL vulnerability scanning"),
    ],
    "sslscan": [
        ("T1595.002","high",   "SSL/TLS configuration scanning"),
    ],
    "ssh": [
        ("T1021.004","medium", "SSH remote access"),
    ],
}


# ── Finding → Technique Rules ────────────────────────────────────────────────
# Each rule: (compiled_regex, list_of_(technique_id, confidence), default_notes)
# Regex matched against finding title + description + evidence (case-insensitive).

def _re(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.IGNORECASE)


_FINDING_RULES: List[Tuple[re.Pattern, List[Tuple[str, str]], str]] = [
    # SQL Injection
    (_re(r"sql\s*injection|sqli|blind.?sql|union.?select|sqlmap"),
     [("T1190", "high"), ("T1059", "medium")],
     "SQL injection enables application exploitation and command execution"),

    # XSS
    (_re(r"cross.?site\s*script|xss|reflected\s*xss|stored\s*xss|dom.?xss"),
     [("T1190", "high"), ("T1189", "medium")],
     "Cross-site scripting can lead to session hijacking"),

    # Command Injection / RCE
    (_re(r"command\s*injection|remote\s*code\s*exec|rce|os\s*command|shell\s*injection"),
     [("T1059", "high"), ("T1190", "high"), ("T1203", "high")],
     "Command injection enables arbitrary code execution"),

    # File Inclusion / Path Traversal
    (_re(r"file\s*inclusion|path\s*traversal|directory\s*traversal|lfi|rfi|\.\./"),
     [("T1083", "high"), ("T1005", "medium")],
     "Path traversal enables file system access"),

    # Authentication issues
    (_re(r"default\s*credential|weak\s*password|default.*password|brute.?forc|credential\s*stuff|password\s*spray"),
     [("T1110", "high"), ("T1078", "high")],
     "Weak authentication enables unauthorized access"),

    # SSRF
    (_re(r"ssrf|server.?side\s*request\s*forgery"),
     [("T1190", "high"), ("T1580", "medium")],
     "SSRF can enable internal network access"),

    # CSRF
    (_re(r"csrf|cross.?site\s*request\s*forgery"),
     [("T1190", "medium")],
     "CSRF enables unauthorized actions"),

    # Open ports / services
    (_re(r"open\s*port|exposed\s*service|unnecessary\s*service|unneeded\s*port"),
     [("T1046", "high"), ("T1133", "medium")],
     "Open ports increase the attack surface"),

    # SSH issues
    (_re(r"ssh.*weak|ssh.*vuln|weak\s*ssh|ssh.*password\s*auth|ssh.*root\s*login"),
     [("T1021.004", "high"), ("T1078", "medium")],
     "Weak SSH configuration enables remote access"),

    # RDP issues
    (_re(r"rdp.*exposed|rdp.*weak|remote\s*desktop.*vuln"),
     [("T1021.001", "high"), ("T1133", "high")],
     "Exposed RDP enables lateral movement"),

    # SSL/TLS issues
    (_re(r"ssl|tls|certificate|cipher.*weak|heartbleed|poodle|beast|drown"),
     [("T1557", "medium"), ("T1040", "low")],
     "Weak encryption enables traffic interception"),

    # Information disclosure
    (_re(r"information\s*disclos|info.*leak|server\s*header|version\s*disclos|banner\s*grab|stack\s*trace|error\s*message.*detail|debug.*mode"),
     [("T1592.002", "medium"), ("T1082", "medium")],
     "Information disclosure aids reconnaissance"),

    # Directory listing
    (_re(r"directory\s*listing|index\s*of|dir.*listing.*enabled"),
     [("T1083", "high"), ("T1213", "medium")],
     "Directory listing exposes file structure"),

    # Subdomain / DNS
    (_re(r"subdomain|dns.*zone.*transfer|dns.*enum|axfr"),
     [("T1590", "high"), ("T1596", "medium")],
     "DNS enumeration reveals infrastructure"),

    # Web shell / backdoor
    (_re(r"web.?shell|backdoor|persist.*shell|reverse.*shell"),
     [("T1505.003", "high"), ("T1059.004", "high")],
     "Web shells provide persistent access"),

    # Privilege escalation
    (_re(r"privil.*escal|priv.*esc|setuid|suid|sudo.*vuln|root.*access|local.*root"),
     [("T1068", "high"), ("T1548", "high")],
     "Privilege escalation grants elevated access"),

    # Misconfiguration
    (_re(r"misconfig|security.*header.*missing|cors.*misconfig|csp.*missing|hsts.*missing|x-frame|clickjack"),
     [("T1190", "medium")],
     "Misconfigurations weaken security posture"),

    # DoS
    (_re(r"denial.?of.?service|dos|ddos|slow.?loris|resource\s*exhaust"),
     [("T1499", "high"), ("T1499.002", "medium")],
     "DoS vulnerabilities impact availability"),

    # LDAP
    (_re(r"ldap.*injection|ldap.*enum|active\s*directory"),
     [("T1087", "medium"), ("T1069", "medium")],
     "LDAP issues enable directory enumeration"),

    # SMB / Network shares
    (_re(r"smb.*vuln|smb.*enum|network\s*share|null\s*session|eternalblue|ms17"),
     [("T1135", "high"), ("T1210", "high"), ("T1039", "medium")],
     "SMB vulnerabilities enable lateral movement"),

    # SNMP
    (_re(r"snmp.*community|snmp.*public|snmp.*enum"),
     [("T1082", "medium"), ("T1046", "medium")],
     "SNMP misconfigurations expose system information"),

    # Phishing
    (_re(r"phish|spear.*phish|social\s*engineer"),
     [("T1566", "high")],
     "Phishing enables initial access"),

    # Credential in files
    (_re(r"credential.*file|password.*file|\.env.*exposed|config.*password|hardcoded.*password|api.?key.*exposed"),
     [("T1552.001", "high"), ("T1552", "high")],
     "Credentials in files enable unauthorized access"),

    # Data exfiltration
    (_re(r"data.*exfil|data.*leak|sensitive.*data.*exposed|pii.*exposed"),
     [("T1048", "medium"), ("T1567", "medium")],
     "Data exposure enables exfiltration"),

    # Ransomware / encryption
    (_re(r"ransomware|encrypt.*impact|data.*destroy"),
     [("T1486", "high"), ("T1485", "high")],
     "Ransomware encrypts data for impact"),

    # Account issues
    (_re(r"account.*lockout.*missing|no.*lockout|session.*fixation|session.*hijack"),
     [("T1078", "medium"), ("T1110", "medium")],
     "Account weaknesses enable unauthorized access"),

    # Log / monitoring
    (_re(r"no.*logging|logging.*disabled|audit.*missing|monitor.*missing"),
     [("T1070", "medium"), ("T1562", "medium")],
     "Missing logging aids defense evasion"),

    # Cloud
    (_re(r"s3.*bucket|cloud.*misconfig|azure.*exposed|gcp.*public|aws.*public"),
     [("T1580", "high"), ("T1190", "medium")],
     "Cloud misconfigurations expose resources"),
]


# ── Navigator Layer Schema ───────────────────────────────────────────────────

# ATT&CK Navigator layer version 4.5
_NAVIGATOR_VERSION = "4.5"
_ATTACK_VERSION = "15"
_NAV_DOMAIN = "enterprise-attack"


def _build_navigator_layer(
    mappings: List[TechniqueMapping],
    name: str = "HackBot Assessment",
    description: str = "",
) -> Dict[str, Any]:
    """Build an ATT&CK Navigator layer JSON from technique mappings.

    The output can be loaded at:
      https://mitre-attack.github.io/attack-navigator/

    Scoring:
      - high confidence → score 4 (red)
      - medium confidence → score 3 (orange)
      - low confidence → score 2 (yellow)
    Severity overlay:
      - Critical → score +1
      - High → score +0.5
    """
    # Aggregate best score per technique
    tech_scores: Dict[str, float] = {}
    tech_comments: Dict[str, List[str]] = {}

    confidence_score = {"high": 4, "medium": 3, "low": 2}
    severity_bonus = {"Critical": 1.0, "High": 0.5, "Medium": 0, "Low": 0, "Info": 0}

    for m in mappings:
        tid = m.technique.id
        base = confidence_score.get(m.confidence, 2)
        bonus = severity_bonus.get(m.severity, 0)
        score = base + bonus

        tech_scores[tid] = max(tech_scores.get(tid, 0), score)

        comment = f"[{m.source}] {m.source_name}"
        if m.notes:
            comment += f" — {m.notes}"
        tech_comments.setdefault(tid, []).append(comment)

    # Build technique entries
    techniques = []
    for tid, score in tech_scores.items():
        tech = TECHNIQUE_MAP.get(tid)
        if not tech:
            continue

        # Tactic references
        tactic_refs = []
        for tac_id in tech.tactic_ids:
            tac = TACTIC_MAP.get(tac_id)
            if tac:
                tactic_refs.append({"tacticName": tac.short_name.replace("-", " ")})

        entry: Dict[str, Any] = {
            "techniqueID": tid,
            "score": score,
            "comment": "\n".join(tech_comments.get(tid, [])),
            "enabled": True,
            "showSubtechniques": tech.is_subtechnique,
        }
        if tactic_refs:
            entry["tactic"] = tactic_refs[0]["tacticName"]  # primary tactic

        techniques.append(entry)

    # Gradient: green(0) → yellow(2) → orange(3) → red(5)
    layer = {
        "name": name,
        "versions": {
            "attack": _ATTACK_VERSION,
            "navigator": _NAVIGATOR_VERSION,
            "layer": "4.5",
        },
        "domain": _NAV_DOMAIN,
        "description": description or f"Generated by HackBot v{__version__}",
        "filters": {"platforms": ["Linux", "macOS", "Windows", "Network"]},
        "sorting": 3,  # Sort by score descending
        "layout": {
            "layout": "side",
            "aggregateFunction": "max",
            "showID": True,
            "showName": True,
            "showAggregateScores": True,
            "countUnscored": False,
        },
        "hideDisabled": False,
        "techniques": techniques,
        "gradient": {
            "colors": ["#a1d99b", "#fee08b", "#fdae61", "#f46d43", "#d73027"],
            "minValue": 0,
            "maxValue": 5,
        },
        "legendItems": [
            {"label": "Not observed", "color": "#a1d99b"},
            {"label": "Low confidence", "color": "#fee08b"},
            {"label": "Medium confidence", "color": "#fdae61"},
            {"label": "High confidence", "color": "#f46d43"},
            {"label": "Critical finding", "color": "#d73027"},
        ],
        "metadata": [
            {"name": "generator", "value": f"HackBot v{__version__}"},
            {"name": "generated_at", "value": time.strftime("%Y-%m-%d %H:%M:%S")},
        ],
        "showTacticRowBackground": True,
        "tacticRowBackground": "#205b8f",
        "selectTechniquesAcrossTactics": True,
        "selectSubtechniquesWithParent": True,
    }

    return layer


# ── ATT&CK Mapper Class ─────────────────────────────────────────────────────

class AttackMapper:
    """Maps HackBot findings and tool usage to MITRE ATT&CK techniques.

    Usage::

        mapper = AttackMapper()
        report = mapper.map_findings(findings_dicts, target="192.168.1.1")
        report = mapper.map_tools(tool_history, report)
        layer_json = mapper.generate_navigator_layer(report)
        markdown = AttackMapper.format_report(report)
    """

    def __init__(self):
        pass

    def map_findings(
        self,
        findings: List[Dict[str, Any]],
        target: str = "",
        tool_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AttackReport:
        """Map findings and tool history to ATT&CK techniques.

        Args:
            findings: List of finding dicts (from Finding.to_dict())
            target: Assessment target
            tool_history: Optional list of tool execution dicts

        Returns:
            AttackReport with all mappings
        """
        report = AttackReport(target=target, total_findings=len(findings))

        seen: Set[str] = set()  # Deduplicate: "source:technique_id:source_name"

        # Map findings
        for finding in findings:
            text = " ".join([
                finding.get("title", ""),
                finding.get("description", ""),
                finding.get("evidence", ""),
                finding.get("recommendation", ""),
            ]).strip()

            if not text:
                continue

            severity = finding.get("severity", "Info")

            for pattern, tech_list, notes in _FINDING_RULES:
                if pattern.search(text):
                    for tech_id, confidence in tech_list:
                        technique = TECHNIQUE_MAP.get(tech_id)
                        if not technique:
                            continue

                        dedup_key = f"finding:{tech_id}:{finding.get('title', '')}"
                        if dedup_key in seen:
                            continue
                        seen.add(dedup_key)

                        report.mappings.append(TechniqueMapping(
                            technique=technique,
                            source="finding",
                            source_name=finding.get("title", "Unknown"),
                            confidence=confidence,
                            notes=notes,
                            severity=severity,
                        ))

        # Map tool history
        if tool_history:
            report.total_tools = len(tool_history)
            for entry in tool_history:
                tool_name = entry.get("tool", "").lower()
                if tool_name not in TOOL_TECHNIQUE_MAP:
                    continue

                for tech_id, confidence, notes in TOOL_TECHNIQUE_MAP[tool_name]:
                    technique = TECHNIQUE_MAP.get(tech_id)
                    if not technique:
                        continue

                    dedup_key = f"tool:{tech_id}:{tool_name}"
                    if dedup_key in seen:
                        continue
                    seen.add(dedup_key)

                    report.mappings.append(TechniqueMapping(
                        technique=technique,
                        source="tool",
                        source_name=tool_name,
                        confidence=confidence,
                        notes=notes,
                    ))

        return report

    def generate_navigator_layer(
        self,
        report: AttackReport,
        name: str = "",
        description: str = "",
    ) -> Dict[str, Any]:
        """Generate an ATT&CK Navigator layer JSON from a report.

        Args:
            report: The ATT&CK mapping report
            name: Layer name (default: "HackBot: <target>")
            description: Layer description

        Returns:
            Navigator layer JSON as dict
        """
        if not name:
            name = f"HackBot: {report.target}" if report.target else "HackBot Assessment"
        if not description:
            description = (
                f"Assessment of {report.target} — "
                f"{len(report.mappings)} technique mappings from "
                f"{report.total_findings} findings and {report.total_tools} tool executions"
            )
        return _build_navigator_layer(report.mappings, name=name, description=description)

    def generate_navigator_json(
        self,
        report: AttackReport,
        name: str = "",
        description: str = "",
    ) -> str:
        """Generate an ATT&CK Navigator layer as a JSON string."""
        layer = self.generate_navigator_layer(report, name, description)
        return json.dumps(layer, indent=2)

    # ── Static helpers ───────────────────────────────────────────────────

    @staticmethod
    def list_tactics() -> List[Dict[str, str]]:
        """List all ATT&CK tactics."""
        return [t.to_dict() for t in TACTICS]

    @staticmethod
    def list_techniques(tactic_id: str = "") -> List[Dict[str, Any]]:
        """List techniques, optionally filtered by tactic."""
        if tactic_id:
            return [
                t.to_dict() for t in TECHNIQUES
                if tactic_id in t.tactic_ids
            ]
        return [t.to_dict() for t in TECHNIQUES]

    @staticmethod
    def get_technique(technique_id: str) -> Optional[Dict[str, Any]]:
        """Get a technique by ID."""
        tech = TECHNIQUE_MAP.get(technique_id)
        return tech.to_dict() if tech else None

    @staticmethod
    def get_tool_techniques(tool_name: str) -> List[Dict[str, Any]]:
        """Get ATT&CK techniques mapped to a specific tool."""
        mappings = TOOL_TECHNIQUE_MAP.get(tool_name.lower(), [])
        result: List[Dict[str, Any]] = []
        for tech_id, confidence, notes in mappings:
            tech = TECHNIQUE_MAP.get(tech_id)
            if tech:
                result.append({
                    "technique": tech.to_dict(),
                    "confidence": confidence,
                    "notes": notes,
                })
        return result

    @staticmethod
    def format_report(report: AttackReport) -> str:
        """Format an ATT&CK report as Markdown."""
        data = report.to_dict()
        lines = [
            "# MITRE ATT&CK Mapping\n",
            f"**Target:** {data['target'] or 'N/A'}",
            f"**Findings analysed:** {data['total_findings']}",
            f"**Tool executions:** {data['total_tools']}",
            f"**Technique mappings:** {data['total_mappings']}",
            f"**Unique techniques:** {data['unique_techniques']}",
            f"**Tactics covered:** {data['tactics_covered']}/{data['total_tactics']}",
            "",
        ]

        # Coverage bar
        covered = data["tactics_covered"]
        total = data["total_tactics"]
        bar_filled = int((covered / max(total, 1)) * 20)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)
        lines.append(f"**Coverage:** [{bar}] {covered}/{total} tactics\n")

        # By tactic
        for tactic in TACTICS:
            tactic_mappings = data["by_tactic"].get(tactic.name, [])
            if not tactic_mappings:
                continue

            lines.append(f"\n## {tactic.name} ({tactic.id})\n")
            lines.append(f"*{tactic.description}*\n")

            seen_techs: Set[str] = set()
            for m in tactic_mappings:
                tech = m["technique"]
                if tech["id"] in seen_techs:
                    continue
                seen_techs.add(tech["id"])

                conf_icon = {"high": "🔴", "medium": "🟠", "low": "🟡"}.get(
                    m["confidence"], "⚪"
                )
                sev_str = f" [{m['severity']}]" if m["severity"] else ""
                source_icon = "🔍" if m["source"] == "finding" else "🔧"

                lines.append(
                    f"- {conf_icon} **{tech['id']}** — {tech['name']}"
                    f"{sev_str} ({source_icon} {m['source_name']})"
                )
                if m["notes"]:
                    lines.append(f"  *{m['notes']}*")

            lines.append("")

        # Legend
        lines.extend([
            "\n---",
            "**Confidence:** 🔴 High | 🟠 Medium | 🟡 Low",
            "**Source:** 🔍 Finding | 🔧 Tool",
            f"\n*Generated by HackBot v{__version__}*",
        ])

        return "\n".join(lines)

    @staticmethod
    def format_summary(report: AttackReport) -> str:
        """Format a short summary of the ATT&CK mapping."""
        data = report.to_dict()
        tactics = list(data["by_tactic"].keys())

        lines = [
            f"📊 **ATT&CK Coverage:** {data['unique_techniques']} techniques, "
            f"{data['tactics_covered']}/{data['total_tactics']} tactics",
        ]
        if tactics:
            lines.append(f"**Tactics:** {', '.join(tactics)}")

        # Count by confidence
        conf_counts: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}
        for m in report.mappings:
            conf_counts[m.confidence] = conf_counts.get(m.confidence, 0) + 1

        parts = []
        if conf_counts["high"]:
            parts.append(f"🔴 {conf_counts['high']} high")
        if conf_counts["medium"]:
            parts.append(f"🟠 {conf_counts['medium']} medium")
        if conf_counts["low"]:
            parts.append(f"🟡 {conf_counts['low']} low")
        if parts:
            lines.append(f"**Confidence:** {' | '.join(parts)}")

        return "\n".join(lines)
