"""
HackBot Compliance Mapping Engine
===================================
Automatically maps security findings to compliance framework controls:
  • PCI DSS v4.0
  • NIST SP 800-53 Rev 5
  • OWASP Top 10 (2021)
  • ISO 27001:2022

Each finding's title, description, severity, and evidence are matched against
a keyword-rule database to produce control-level mappings with gap analysis.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# ── Data Models ──────────────────────────────────────────────────────────────

class Framework(str, Enum):
    PCI_DSS = "PCI DSS v4.0"
    NIST_800_53 = "NIST 800-53 Rev 5"
    OWASP_TOP_10 = "OWASP Top 10 (2021)"
    ISO_27001 = "ISO 27001:2022"


@dataclass
class Control:
    """A single compliance control."""
    framework: str
    control_id: str
    title: str
    description: str = ""
    family: str = ""          # control family / category

    def to_dict(self) -> Dict[str, Any]:
        return {
            "framework": self.framework,
            "control_id": self.control_id,
            "title": self.title,
            "description": self.description,
            "family": self.family,
        }


@dataclass
class ControlMapping:
    """A mapping from a finding to a compliance control."""
    control: Control
    status: str = "fail"      # "fail" | "warn" | "pass" | "not_tested"
    notes: str = ""           # how the finding relates to the control
    finding_title: str = ""   # originating finding

    def to_dict(self) -> Dict[str, Any]:
        return {
            "control": self.control.to_dict(),
            "status": self.status,
            "notes": self.notes,
            "finding_title": self.finding_title,
        }


@dataclass
class ComplianceReport:
    """Full compliance mapping report."""
    frameworks: List[str] = field(default_factory=list)
    mappings: List[ControlMapping] = field(default_factory=list)
    target: str = ""
    total_findings: int = 0

    def to_dict(self) -> Dict[str, Any]:
        by_framework: Dict[str, List[Dict]] = {}
        for m in self.mappings:
            fw = m.control.framework
            by_framework.setdefault(fw, []).append(m.to_dict())

        summary: Dict[str, Dict[str, int]] = {}
        for fw, maps in by_framework.items():
            counts = {"fail": 0, "warn": 0, "pass": 0, "not_tested": 0}
            for item in maps:
                counts[item["status"]] = counts.get(item["status"], 0) + 1
            summary[fw] = counts

        return {
            "target": self.target,
            "total_findings": self.total_findings,
            "frameworks": self.frameworks,
            "summary": summary,
            "mappings": by_framework,
        }


# ── Keyword → Control Rules ─────────────────────────────────────────────────
# Each rule: (compiled_regex, list_of_controls, status)
# The regex is matched against finding title + description (case-insensitive).

def _re(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.IGNORECASE)


# ---------- PCI DSS v4.0 Controls ----------

PCI_DSS_CONTROLS: List[Control] = [
    Control(Framework.PCI_DSS.value, "1.2.1",  "Network security controls", "Install and maintain network security controls.", "Network Security"),
    Control(Framework.PCI_DSS.value, "1.3.1",  "Inbound traffic restriction", "Restrict inbound traffic to only that which is necessary.", "Network Security"),
    Control(Framework.PCI_DSS.value, "1.3.2",  "Outbound traffic restriction", "Restrict outbound traffic to only that which is necessary.", "Network Security"),
    Control(Framework.PCI_DSS.value, "2.2.1",  "System hardening standards", "Develop configuration standards for all system components.", "Secure Configuration"),
    Control(Framework.PCI_DSS.value, "2.2.7",  "Encrypt non-console admin access", "Encrypt all non-console administrative access using strong cryptography.", "Secure Configuration"),
    Control(Framework.PCI_DSS.value, "4.2.1",  "Strong cryptography for transmission", "Strong cryptography is used during transmission of PAN.", "Encryption"),
    Control(Framework.PCI_DSS.value, "4.2.2",  "PAN secured with strong crypto", "PAN is secured with strong cryptography whenever sent via end-user messaging.", "Encryption"),
    Control(Framework.PCI_DSS.value, "6.2.4",  "Secure coding practices", "Software engineering techniques prevent or mitigate common software attacks.", "Secure Development"),
    Control(Framework.PCI_DSS.value, "6.3.1",  "Vulnerability identification", "Security vulnerabilities are identified and managed.", "Vulnerability Management"),
    Control(Framework.PCI_DSS.value, "6.3.3",  "Patch management", "Critical security patches are installed within one month of release.", "Vulnerability Management"),
    Control(Framework.PCI_DSS.value, "6.4.1",  "Web app attack protection", "Public-facing web applications are protected against attacks.", "Secure Development"),
    Control(Framework.PCI_DSS.value, "6.4.2",  "WAF for web applications", "Public-facing web applications use an automated technical solution to detect and prevent web-based attacks.", "Secure Development"),
    Control(Framework.PCI_DSS.value, "7.2.1",  "Access control system", "An access control system(s) is implemented for systems components.", "Access Control"),
    Control(Framework.PCI_DSS.value, "7.2.2",  "Appropriate user access", "Access is assigned based on job classification and function.", "Access Control"),
    Control(Framework.PCI_DSS.value, "8.3.1",  "Strong authentication", "All user access to system components is authenticated by at least one factor.", "Authentication"),
    Control(Framework.PCI_DSS.value, "8.3.6",  "Password complexity", "Passwords/passphrases meet minimum complexity requirements.", "Authentication"),
    Control(Framework.PCI_DSS.value, "8.3.9",  "Password rotation", "Passwords/passphrases are changed at least once every 90 days.", "Authentication"),
    Control(Framework.PCI_DSS.value, "10.2.1", "Audit logging", "Audit logs are enabled and active for all system components.", "Logging & Monitoring"),
    Control(Framework.PCI_DSS.value, "10.4.1", "Audit log review", "Audit logs are reviewed at least once daily.", "Logging & Monitoring"),
    Control(Framework.PCI_DSS.value, "11.3.1", "Vulnerability scanning", "Internal vulnerability scans performed at least quarterly.", "Security Testing"),
    Control(Framework.PCI_DSS.value, "11.4.1", "Penetration testing", "External and internal penetration testing performed at least annually.", "Security Testing"),
    Control(Framework.PCI_DSS.value, "12.3.1", "Risk assessment", "Risk assessment is performed at least annually.", "Information Security Policy"),
]

# ---------- NIST 800-53 Rev 5 Controls ----------

NIST_CONTROLS: List[Control] = [
    Control(Framework.NIST_800_53.value, "AC-2",  "Account Management", "Manage system accounts, including establishing, activating, modifying, reviewing, disabling, and removing accounts.", "Access Control"),
    Control(Framework.NIST_800_53.value, "AC-3",  "Access Enforcement", "Enforce approved authorizations for logical access.", "Access Control"),
    Control(Framework.NIST_800_53.value, "AC-7",  "Unsuccessful Logon Attempts", "Limit consecutive invalid logon attempts.", "Access Control"),
    Control(Framework.NIST_800_53.value, "AC-17", "Remote Access", "Establish and document usage restrictions for remote access.", "Access Control"),
    Control(Framework.NIST_800_53.value, "AU-2",  "Event Logging", "Identify events that the system is capable of logging.", "Audit and Accountability"),
    Control(Framework.NIST_800_53.value, "AU-6",  "Audit Record Review", "Review and analyze system audit records.", "Audit and Accountability"),
    Control(Framework.NIST_800_53.value, "CA-8",  "Penetration Testing", "Conduct penetration testing on systems and networks.", "Assessment, Authorization, and Monitoring"),
    Control(Framework.NIST_800_53.value, "CM-6",  "Configuration Settings", "Establish and document mandatory configuration settings.", "Configuration Management"),
    Control(Framework.NIST_800_53.value, "CM-7",  "Least Functionality", "Configure the system to provide only essential capabilities.", "Configuration Management"),
    Control(Framework.NIST_800_53.value, "IA-2",  "Identification and Authentication", "Uniquely identify and authenticate organizational users.", "Identification and Authentication"),
    Control(Framework.NIST_800_53.value, "IA-5",  "Authenticator Management", "Manage system authenticators (passwords, tokens, biometrics, PKI).", "Identification and Authentication"),
    Control(Framework.NIST_800_53.value, "IR-4",  "Incident Handling", "Implement an incident handling capability.", "Incident Response"),
    Control(Framework.NIST_800_53.value, "RA-5",  "Vulnerability Monitoring and Scanning", "Monitor and scan for vulnerabilities in the system.", "Risk Assessment"),
    Control(Framework.NIST_800_53.value, "SC-7",  "Boundary Protection", "Monitor and control communications at the external managed interfaces.", "System and Communications Protection"),
    Control(Framework.NIST_800_53.value, "SC-8",  "Transmission Confidentiality and Integrity", "Protect the confidentiality and integrity of transmitted information.", "System and Communications Protection"),
    Control(Framework.NIST_800_53.value, "SC-12", "Cryptographic Key Establishment and Management", "Establish and manage cryptographic keys.", "System and Communications Protection"),
    Control(Framework.NIST_800_53.value, "SC-13", "Cryptographic Protection", "Implement cryptographic mechanisms to prevent unauthorized disclosure.", "System and Communications Protection"),
    Control(Framework.NIST_800_53.value, "SC-28", "Protection of Information at Rest", "Protect the confidentiality and integrity of information at rest.", "System and Communications Protection"),
    Control(Framework.NIST_800_53.value, "SI-2",  "Flaw Remediation", "Identify, report, and correct system flaws.", "System and Information Integrity"),
    Control(Framework.NIST_800_53.value, "SI-3",  "Malicious Code Protection", "Implement malicious code protection mechanisms.", "System and Information Integrity"),
    Control(Framework.NIST_800_53.value, "SI-4",  "System Monitoring", "Monitor the system to detect attacks and indicators of potential attacks.", "System and Information Integrity"),
    Control(Framework.NIST_800_53.value, "SI-10", "Information Input Validation", "Check the validity of information inputs.", "System and Information Integrity"),
]

# ---------- OWASP Top 10 (2021) ----------

OWASP_CONTROLS: List[Control] = [
    Control(Framework.OWASP_TOP_10.value, "A01:2021", "Broken Access Control", "Access control enforces policy such that users cannot act outside their intended permissions.", "Access Control"),
    Control(Framework.OWASP_TOP_10.value, "A02:2021", "Cryptographic Failures", "Failures related to cryptography (or lack thereof) that lead to exposure of sensitive data.", "Cryptography"),
    Control(Framework.OWASP_TOP_10.value, "A03:2021", "Injection", "SQL, NoSQL, OS, LDAP injection — untrusted data sent to an interpreter as part of a command or query.", "Injection"),
    Control(Framework.OWASP_TOP_10.value, "A04:2021", "Insecure Design", "Risks related to design and architectural flaws.", "Design"),
    Control(Framework.OWASP_TOP_10.value, "A05:2021", "Security Misconfiguration", "Missing or improper security hardening across the application stack.", "Configuration"),
    Control(Framework.OWASP_TOP_10.value, "A06:2021", "Vulnerable and Outdated Components", "Using components with known vulnerabilities.", "Components"),
    Control(Framework.OWASP_TOP_10.value, "A07:2021", "Identification and Authentication Failures", "Confirmation of the user's identity, authentication, and session management.", "Authentication"),
    Control(Framework.OWASP_TOP_10.value, "A08:2021", "Software and Data Integrity Failures", "Code and infrastructure that does not protect against integrity violations.", "Integrity"),
    Control(Framework.OWASP_TOP_10.value, "A09:2021", "Security Logging and Monitoring Failures", "Insufficient logging, detection, monitoring, and active response.", "Logging"),
    Control(Framework.OWASP_TOP_10.value, "A10:2021", "Server-Side Request Forgery (SSRF)", "SSRF flaws occur when a web application fetches a remote resource without validating the user-supplied URL.", "SSRF"),
]

# ---------- ISO 27001:2022 Controls (Annex A) ----------

ISO_CONTROLS: List[Control] = [
    Control(Framework.ISO_27001.value, "A.5.1",  "Policies for information security", "Management direction for information security shall be established.", "Organizational Controls"),
    Control(Framework.ISO_27001.value, "A.5.15", "Access control", "Rules to control physical and logical access to information shall be established.", "Organizational Controls"),
    Control(Framework.ISO_27001.value, "A.5.23", "Information security for use of cloud services", "Processes for acquisition and management of cloud services shall be established.", "Organizational Controls"),
    Control(Framework.ISO_27001.value, "A.5.36", "Compliance with policies and standards", "Compliance with the organization's information security policy shall be reviewed.", "Organizational Controls"),
    Control(Framework.ISO_27001.value, "A.6.8",  "Information security event reporting", "Personnel shall report observed or suspected information security events.", "People Controls"),
    Control(Framework.ISO_27001.value, "A.7.1",  "Physical security perimeters", "Security perimeters shall be defined and used to protect areas with sensitive information.", "Physical Controls"),
    Control(Framework.ISO_27001.value, "A.8.1",  "User endpoint devices", "Information stored on, processed by, or accessible via user endpoint devices shall be protected.", "Technological Controls"),
    Control(Framework.ISO_27001.value, "A.8.5",  "Secure authentication", "Secure authentication technologies and procedures shall be established.", "Technological Controls"),
    Control(Framework.ISO_27001.value, "A.8.7",  "Protection against malware", "Protection against malware shall be implemented.", "Technological Controls"),
    Control(Framework.ISO_27001.value, "A.8.8",  "Management of technical vulnerabilities", "Information about technical vulnerabilities shall be obtained, evaluated, and addressed.", "Technological Controls"),
    Control(Framework.ISO_27001.value, "A.8.9",  "Configuration management", "Configurations, including security configurations, of hardware, software, services and networks shall be established.", "Technological Controls"),
    Control(Framework.ISO_27001.value, "A.8.10", "Information deletion", "Information stored in systems and devices shall be deleted when no longer required.", "Technological Controls"),
    Control(Framework.ISO_27001.value, "A.8.12", "Data leakage prevention", "Data leakage prevention measures shall be applied.", "Technological Controls"),
    Control(Framework.ISO_27001.value, "A.8.15", "Logging", "Logs that record activities, exceptions, faults and other relevant events shall be produced and stored.", "Technological Controls"),
    Control(Framework.ISO_27001.value, "A.8.20", "Networks security", "Networks and network devices shall be secured, managed and controlled.", "Technological Controls"),
    Control(Framework.ISO_27001.value, "A.8.21", "Security of network services", "Security mechanisms, service levels and requirements of network services shall be identified.", "Technological Controls"),
    Control(Framework.ISO_27001.value, "A.8.24", "Use of cryptography", "Rules for the effective use of cryptography shall be defined and implemented.", "Technological Controls"),
    Control(Framework.ISO_27001.value, "A.8.25", "Secure development life cycle", "Rules for the secure development of software and systems shall be established.", "Technological Controls"),
    Control(Framework.ISO_27001.value, "A.8.26", "Application security requirements", "Information security requirements shall be identified when developing or acquiring applications.", "Technological Controls"),
    Control(Framework.ISO_27001.value, "A.8.28", "Secure coding", "Secure coding principles shall be applied to software development.", "Technological Controls"),
]


# ── Mapping Rules (keyword → controls) ───────────────────────────────────────
# Each tuple: (regex_pattern, list of (framework_controls, control_id), status_default)

_RULES: List[tuple] = [
    # ── SQL Injection ──
    (_re(r"sql.?inject|sqli|union.?select|blind.?inject"), [
        ("pci",   "6.2.4"), ("pci",   "6.4.1"),
        ("nist",  "SI-10"), ("nist",  "SI-2"),
        ("owasp", "A03:2021"),
        ("iso",   "A.8.28"), ("iso",   "A.8.26"),
    ], "fail"),

    # ── XSS ──
    (_re(r"cross.?site.?script|xss|reflected.?script|stored.?xss|dom.?xss"), [
        ("pci",   "6.2.4"), ("pci",   "6.4.1"), ("pci",   "6.4.2"),
        ("nist",  "SI-10"),
        ("owasp", "A03:2021"),
        ("iso",   "A.8.28"),
    ], "fail"),

    # ── Command/OS Injection ──
    (_re(r"command.?inject|os.?inject|rce|remote.?code.?exec"), [
        ("pci",   "6.2.4"),
        ("nist",  "SI-10"), ("nist",  "SI-2"),
        ("owasp", "A03:2021"),
        ("iso",   "A.8.28"),
    ], "fail"),

    # ── SSRF ──
    (_re(r"ssrf|server.?side.?request"), [
        ("pci",   "6.2.4"),
        ("nist",  "SI-10"), ("nist",  "SC-7"),
        ("owasp", "A10:2021"),
        ("iso",   "A.8.20"),
    ], "fail"),

    # ── Access Control / Authorization ──
    (_re(r"broken.?access|unauthorized|idor|privilege.?escalat|insecure.?direct.?object|access.?control"), [
        ("pci",   "7.2.1"), ("pci",   "7.2.2"),
        ("nist",  "AC-3"),  ("nist",  "AC-2"),
        ("owasp", "A01:2021"),
        ("iso",   "A.5.15"),
    ], "fail"),

    # ── Authentication Weaknesses ──
    (_re(r"brute.?force|weak.?password|default.?cred|credential|login.?bypass|password.?policy|auth.?bypass|authentication.?fail"), [
        ("pci",   "8.3.1"), ("pci",   "8.3.6"), ("pci",   "8.3.9"),
        ("nist",  "IA-2"),  ("nist",  "IA-5"),  ("nist",  "AC-7"),
        ("owasp", "A07:2021"),
        ("iso",   "A.8.5"),
    ], "fail"),

    # ── SSL/TLS / Crypto ──
    (_re(r"ssl|tls|cert|cipher|crypto|cleartext|plaintext.?transmit|http(?!s)|weak.?encrypt|expired.?cert"), [
        ("pci",   "4.2.1"), ("pci",   "2.2.7"),
        ("nist",  "SC-8"),  ("nist",  "SC-12"), ("nist",  "SC-13"),
        ("owasp", "A02:2021"),
        ("iso",   "A.8.24"),
    ], "fail"),

    # ── Outdated / Vulnerable Components ──
    (_re(r"outdated|eol|end.?of.?life|known.?vuln|cve-\d|unpatched|obsolete|version"), [
        ("pci",   "6.3.1"), ("pci",   "6.3.3"),
        ("nist",  "SI-2"),  ("nist",  "RA-5"),
        ("owasp", "A06:2021"),
        ("iso",   "A.8.8"),
    ], "fail"),

    # ── Misconfiguration ──
    (_re(r"mis.?config|default.?config|directory.?list|open.?port|information.?disclos|server.?header|debug.?mode|verbose.?error|stack.?trace"), [
        ("pci",   "2.2.1"),
        ("nist",  "CM-6"),  ("nist",  "CM-7"),
        ("owasp", "A05:2021"),
        ("iso",   "A.8.9"),
    ], "fail"),

    # ── Missing Logging / Monitoring ──
    (_re(r"no.?log|missing.?log|insufficient.?log|audit|monitoring.?fail"), [
        ("pci",   "10.2.1"), ("pci",  "10.4.1"),
        ("nist",  "AU-2"),   ("nist", "AU-6"), ("nist", "SI-4"),
        ("owasp", "A09:2021"),
        ("iso",   "A.8.15"),
    ], "fail"),

    # ── Network / Firewall ──
    (_re(r"firewall|open.?port|network.?segm|exposed.?service|unnecessary.?port|ingress|egress"), [
        ("pci",   "1.2.1"), ("pci",   "1.3.1"), ("pci",   "1.3.2"),
        ("nist",  "SC-7"),
        ("owasp", "A05:2021"),
        ("iso",   "A.8.20"), ("iso",   "A.8.21"),
    ], "warn"),

    # ── Data Exposure / Leakage ──
    (_re(r"data.?leak|sensitive.?data|expos|personal.?data|pii|pan|card.?number|ssn"), [
        ("pci",   "4.2.2"),
        ("nist",  "SC-28"),
        ("owasp", "A02:2021"),
        ("iso",   "A.8.10"), ("iso",   "A.8.12"),
    ], "fail"),

    # ── Malware / Integrity ──
    (_re(r"malware|trojan|backdoor|web.?shell|integrity|supply.?chain|tamper"), [
        ("nist",  "SI-3"),
        ("owasp", "A08:2021"),
        ("iso",   "A.8.7"),
    ], "fail"),

    # ── Insecure Design / Architecture ──
    (_re(r"insecure.?design|architecture|threat.?model|security.?by.?design"), [
        ("owasp", "A04:2021"),
        ("iso",   "A.8.25"), ("iso",   "A.8.26"),
    ], "warn"),

    # ── Remote Access / SSH ──
    (_re(r"ssh|remote.?access|rdp|telnet|vnc"), [
        ("pci",   "2.2.7"),
        ("nist",  "AC-17"),
        ("iso",   "A.8.20"),
    ], "warn"),
]


# Build framework lookup
_FRAMEWORK_MAP = {
    "pci":   {c.control_id: c for c in PCI_DSS_CONTROLS},
    "nist":  {c.control_id: c for c in NIST_CONTROLS},
    "owasp": {c.control_id: c for c in OWASP_CONTROLS},
    "iso":   {c.control_id: c for c in ISO_CONTROLS},
}

ALL_FRAMEWORKS = {
    "pci":   Framework.PCI_DSS,
    "nist":  Framework.NIST_800_53,
    "owasp": Framework.OWASP_TOP_10,
    "iso":   Framework.ISO_27001,
}


# ── Compliance Mapper Engine ─────────────────────────────────────────────────

class ComplianceMapper:
    """
    Maps security findings to compliance framework controls.

    Accepts a list of findings (dicts with title, description, severity, evidence)
    and produces a ComplianceReport with per-framework control mappings.
    """

    def __init__(self, frameworks: Optional[List[str]] = None):
        """
        Args:
            frameworks: list of framework keys to include ("pci", "nist", "owasp", "iso").
                        Defaults to all four frameworks.
        """
        if frameworks:
            self.frameworks = [fw.lower().replace(" ", "").replace("-", "").replace("_", "")
                               for fw in frameworks]
            # normalise aliases
            aliases = {
                "pcidss": "pci", "pci": "pci", "pcidssv4": "pci", "pciv4": "pci",
                "nist": "nist", "nist80053": "nist", "nist800": "nist", "sp80053": "nist",
                "owasp": "owasp", "owasptop10": "owasp", "owasp2021": "owasp", "top10": "owasp",
                "iso": "iso", "iso27001": "iso", "iso27k": "iso", "27001": "iso",
            }
            self.frameworks = list(set(aliases.get(f, f) for f in self.frameworks))
        else:
            self.frameworks = ["pci", "nist", "owasp", "iso"]

    def map_findings(
        self,
        findings: List[Dict[str, Any]],
        target: str = "",
    ) -> ComplianceReport:
        """
        Map a list of findings to compliance controls.

        Args:
            findings: list of dicts with keys: title, description, severity, evidence, recommendation
            target: the assessment target for the report header
        Returns:
            ComplianceReport with all mapped controls
        """
        report = ComplianceReport(
            frameworks=[ALL_FRAMEWORKS[f].value for f in self.frameworks if f in ALL_FRAMEWORKS],
            target=target,
            total_findings=len(findings),
        )

        # Track which controls have already been mapped to avoid duplicate entries
        seen: Set[str] = set()

        for finding in findings:
            text = " ".join([
                finding.get("title", ""),
                finding.get("description", ""),
                finding.get("evidence", ""),
                finding.get("recommendation", ""),
            ])

            for pattern, control_refs, default_status in _RULES:
                if not pattern.search(text):
                    continue

                # Determine status based on finding severity
                severity = finding.get("severity", "Info").lower()
                if severity in ("critical", "high"):
                    status = "fail"
                elif severity in ("medium",):
                    status = default_status
                elif severity in ("low",):
                    status = "warn"
                else:
                    status = "warn"

                for fw_key, ctrl_id in control_refs:
                    if fw_key not in self.frameworks:
                        continue
                    ctrl = _FRAMEWORK_MAP.get(fw_key, {}).get(ctrl_id)
                    if not ctrl:
                        continue

                    dedup_key = f"{ctrl.framework}:{ctrl.control_id}:{finding.get('title', '')}"
                    if dedup_key in seen:
                        continue
                    seen.add(dedup_key)

                    report.mappings.append(ControlMapping(
                        control=ctrl,
                        status=status,
                        notes=f"Finding '{finding.get('title', '')}' ({finding.get('severity', 'Info')}) indicates a gap in {ctrl.control_id}.",
                        finding_title=finding.get("title", ""),
                    ))

        return report

    @staticmethod
    def get_framework_controls(framework: str) -> List[Control]:
        """Get all controls for a given framework."""
        key = framework.lower().replace(" ", "").replace("-", "").replace("_", "")
        aliases = {
            "pcidss": "pci", "pci": "pci", "nist": "nist", "nist80053": "nist",
            "owasp": "owasp", "owasptop10": "owasp", "top10": "owasp",
            "iso": "iso", "iso27001": "iso",
        }
        key = aliases.get(key, key)
        return list(_FRAMEWORK_MAP.get(key, {}).values())

    @staticmethod
    def list_frameworks() -> List[Dict[str, Any]]:
        """List available frameworks."""
        return [
            {"key": "pci",   "name": Framework.PCI_DSS.value,     "controls": len(PCI_DSS_CONTROLS)},
            {"key": "nist",  "name": Framework.NIST_800_53.value, "controls": len(NIST_CONTROLS)},
            {"key": "owasp", "name": Framework.OWASP_TOP_10.value, "controls": len(OWASP_CONTROLS)},
            {"key": "iso",   "name": Framework.ISO_27001.value,   "controls": len(ISO_CONTROLS)},
        ]

    @staticmethod
    def format_report(report: ComplianceReport) -> str:
        """Format a ComplianceReport as rich Markdown."""
        lines = [
            "# 📋 Compliance Mapping Report",
            "",
            f"**Target:** {report.target or 'N/A'}",
            f"**Findings Analyzed:** {report.total_findings}",
            f"**Frameworks:** {', '.join(report.frameworks)}",
            "",
        ]

        data = report.to_dict()

        # ── Executive Summary ──
        lines.append("## Executive Summary\n")
        lines.append("| Framework | Fail | Warn | Pass | Not Tested |")
        lines.append("|-----------|------|------|------|------------|")
        for fw, counts in data.get("summary", {}).items():
            lines.append(
                f"| {fw} | {counts.get('fail', 0)} | {counts.get('warn', 0)} | "
                f"{counts.get('pass', 0)} | {counts.get('not_tested', 0)} |"
            )
        lines.append("")

        # ── Per-Framework Detail ──
        for fw, mappings in data.get("mappings", {}).items():
            lines.append(f"## {fw}\n")
            lines.append("| Status | Control | Title | Finding |")
            lines.append("|--------|---------|-------|---------|")
            for m in mappings:
                ctrl = m["control"]
                status_icon = {
                    "fail": "🔴 FAIL",
                    "warn": "🟡 WARN",
                    "pass": "🟢 PASS",
                    "not_tested": "⚪ N/T",
                }.get(m["status"], m["status"])
                lines.append(
                    f"| {status_icon} | {ctrl['control_id']} | {ctrl['title']} | {m.get('finding_title', '')} |"
                )
            lines.append("")

        # ── Gap Analysis ──
        lines.append("## Gap Analysis\n")
        fail_count = sum(1 for m in report.mappings if m.status == "fail")
        warn_count = sum(1 for m in report.mappings if m.status == "warn")
        total = len(report.mappings)

        if total == 0:
            lines.append("No compliance gaps identified from the current findings.\n")
        else:
            pct_fail = (fail_count / total * 100) if total else 0
            lines.append(f"- **{fail_count}** controls failing ({pct_fail:.0f}% of mapped controls)")
            lines.append(f"- **{warn_count}** controls with warnings")
            lines.append(f"- **{total}** total control mappings generated from {report.total_findings} findings")
            lines.append("")

            # Top failing areas
            family_fails: Dict[str, int] = {}
            for m in report.mappings:
                if m.status == "fail":
                    fam = m.control.family
                    family_fails[fam] = family_fails.get(fam, 0) + 1

            if family_fails:
                lines.append("### Top Failing Control Families\n")
                for fam, count in sorted(family_fails.items(), key=lambda x: -x[1])[:10]:
                    lines.append(f"- **{fam}**: {count} failing control(s)")
                lines.append("")

        lines.append("---")
        lines.append("*Generated by HackBot Compliance Mapper*")

        return "\n".join(lines)
