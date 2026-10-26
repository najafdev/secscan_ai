#!/usr/bin/env python3
# SecScan AI core module
"""
CVE Intelligence and Threat Scoring Engine for SecScan AI.
Enriches vulnerability findings with CVE metadata, CVSS v3.1 metrics,
EPSS (Exploit Prediction Scoring System) probabilities, and CISA KEV status.
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

# Standard CVE identification regular expression
CVE_PATTERN = re.compile(r'\bCVE-\d{4}-\d{4,7}\b', re.IGNORECASE)


@dataclass
class CVEInfo:
    """Detailed CVE Threat Intelligence record."""
    cve_id: str
    title: str
    description: str
    cvss_score: float
    cvss_vector: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    epss_score: float  # Exploit Prediction Scoring System (0.0 to 1.0)
    epss_percentile: float  # EPSS percentile ranking (0.0 to 1.0)
    in_cisa_kev: bool  # Present in CISA Known Exploited Vulnerabilities catalog
    weaponized: bool  # Known public exploit or Metasploit/framework module exists
    affected_components: List[str] = field(default_factory=list)
    mitre_attack_ids: List[str] = field(default_factory=list)
    remediation: str = ""
    references: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert CVEInfo to dictionary representation."""
        result = asdict(self)
        result["prioritized_risk_score"] = self.prioritized_risk_score
        return result

    @property
    def prioritized_risk_score(self) -> float:
        """
        Compute dynamic prioritized risk score (0.0 - 10.0) combining:
        - Base CVSS score (50% weight)
        - EPSS exploit probability (25% weight)
        - CISA KEV active exploitation indicator (15% weight)
        - Public weaponization status (10% weight)
        """
        cvss_component = min(max(self.cvss_score, 0.0), 10.0) * 0.50
        epss_component = (self.epss_score * 10.0) * 0.25
        kev_component = (10.0 if self.in_cisa_kev else 0.0) * 0.15
        weapon_component = (10.0 if self.weaponized else 0.0) * 0.10

        total = cvss_component + epss_component + kev_component + weapon_component
        return round(min(total, 10.0), 2)


# Curated offline threat intelligence database for high-profile security vulnerabilities
KNOWN_CVE_DATABASE: Dict[str, Dict[str, Any]] = {
    "CVE-2021-44228": {
        "title": "Apache Log4j2 JNDI Remote Code Execution (Log4Shell)",
        "description": "Apache Log4j2 <=2.14.1 JNDI features used in configuration, log messages, and parameters do not protect against attacker controlled LDAP and other JNDI related endpoints.",
        "cvss_score": 10.0,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
        "severity": "CRITICAL",
        "epss_score": 0.975,
        "epss_percentile": 0.999,
        "in_cisa_kev": True,
        "weaponized": True,
        "affected_components": ["Apache Log4j", "Java Runtime", "Spring Boot", "Elasticsearch"],
        "mitre_attack_ids": ["T1190", "T1059.005", "T1071"],
        "remediation": "Upgrade Apache Log4j to version 2.17.1 or later, or set log4j2.formatMsgNoLookups=true.",
        "references": ["https://nvd.nist.gov/vuln/detail/CVE-2021-44228", "https://cisa.gov/known-exploited-vulnerabilities-catalog"]
    },
    "CVE-2017-0144": {
        "title": "Microsoft Windows SMB Remote Code Execution (EternalBlue)",
        "description": "The SMBv1 server in Microsoft Windows allows remote attackers to execute arbitrary code via crafted packets (EternalBlue / MS17-010).",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "severity": "CRITICAL",
        "epss_score": 0.974,
        "epss_percentile": 0.998,
        "in_cisa_kev": True,
        "weaponized": True,
        "affected_components": ["Microsoft Windows SMBv1", "Windows 7", "Windows Server 2008", "Windows 10"],
        "mitre_attack_ids": ["T1210", "T1021.002"],
        "remediation": "Apply Microsoft security bulletin MS17-010 and disable SMBv1 across all hosts.",
        "references": ["https://nvd.nist.gov/vuln/detail/CVE-2017-0144"]
    },
    "CVE-2022-22965": {
        "title": "Spring Framework RCE via Data Binding on JDK 9+ (Spring4Shell)",
        "description": "A Spring MVC or Spring WebFlux application running on JDK 9+ may be vulnerable to remote code execution via data binding to AccessLogValve.",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "severity": "CRITICAL",
        "epss_score": 0.968,
        "epss_percentile": 0.995,
        "in_cisa_kev": True,
        "weaponized": True,
        "affected_components": ["Spring Framework", "Apache Tomcat", "Java JDK 9+"],
        "mitre_attack_ids": ["T1190", "T1505.003"],
        "remediation": "Upgrade Spring Framework to versions 5.3.18+, 5.2.20+, or upgrade Tomcat.",
        "references": ["https://tanzu.vmware.com/security/cve-2022-22965"]
    },
    "CVE-2021-26855": {
        "title": "Microsoft Exchange Server SSRF Vulnerability (ProxyLogon)",
        "description": "Microsoft Exchange Server Remote Code Execution Vulnerability allows unauthenticated attacker to bypass authentication and impersonate Exchange administrator.",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "severity": "CRITICAL",
        "epss_score": 0.971,
        "epss_percentile": 0.997,
        "in_cisa_kev": True,
        "weaponized": True,
        "affected_components": ["Microsoft Exchange Server 2013", "Exchange Server 2016", "Exchange Server 2019"],
        "mitre_attack_ids": ["T1190", "T1078", "T1505.003"],
        "remediation": "Install Microsoft Exchange Server Cumulative Updates (KB5000871).",
        "references": ["https://msrc.microsoft.com/update-guide/vulnerability/CVE-2021-26855"]
    },
    "CVE-2022-0847": {
        "title": "Linux Kernel Local Privilege Escalation (Dirty Pipe)",
        "description": "A vulnerability in the Linux kernel allows overwriting data in arbitrary read-only files, leading to privilege escalation to root.",
        "cvss_score": 7.8,
        "cvss_vector": "CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H",
        "severity": "HIGH",
        "epss_score": 0.892,
        "epss_percentile": 0.985,
        "in_cisa_kev": True,
        "weaponized": True,
        "affected_components": ["Linux Kernel 5.8 through 5.16.11", "Android OS"],
        "mitre_attack_ids": ["T1068", "T1548.001"],
        "remediation": "Upgrade Linux kernel to 5.16.11, 5.15.25, 5.10.102 or later.",
        "references": ["https://dirtypipe.cm4all.com/"]
    },
    "CVE-2021-4034": {
        "title": "Polkit pkexec Local Privilege Escalation (PwnKit)",
        "description": "Memory corruption vulnerability in Polkit's pkexec utility allows unprivileged local users to gain full root privileges.",
        "cvss_score": 7.8,
        "cvss_vector": "CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H",
        "severity": "HIGH",
        "epss_score": 0.923,
        "epss_percentile": 0.991,
        "in_cisa_kev": True,
        "weaponized": True,
        "affected_components": ["Polkit pkexec", "Ubuntu", "Debian", "RHEL", "CentOS"],
        "mitre_attack_ids": ["T1068", "T1548.001"],
        "remediation": "Update polkit package via OS package manager or remove SUID bit with chmod 0755 /usr/bin/pkexec.",
        "references": ["https://www.qualys.com/2022/01/25/cve-2021-4034/pwnkit.txt"]
    },
    "CVE-2021-41773": {
        "title": "Apache HTTP Server Path Traversal and RCE",
        "description": "A flaw was found in a change made to path normalization in Apache HTTP Server 2.4.49. An attacker could map URLs to files outside the expected document root.",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "severity": "HIGH",
        "epss_score": 0.972,
        "epss_percentile": 0.998,
        "in_cisa_kev": True,
        "weaponized": True,
        "affected_components": ["Apache HTTP Server 2.4.49"],
        "mitre_attack_ids": ["T1190", "T1083"],
        "remediation": "Upgrade Apache HTTP Server to version 2.4.51 or later.",
        "references": ["https://httpd.apache.org/security/vulnerabilities_24.html"]
    },
    "CVE-2022-26134": {
        "title": "Atlassian Confluence OGNL Injection Remote Code Execution",
        "description": "Unauthenticated OGNL injection in Atlassian Confluence Server and Data Center allows an attacker to execute arbitrary code.",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "severity": "CRITICAL",
        "epss_score": 0.974,
        "epss_percentile": 0.998,
        "in_cisa_kev": True,
        "weaponized": True,
        "affected_components": ["Atlassian Confluence Server", "Atlassian Confluence Data Center"],
        "mitre_attack_ids": ["T1190", "T1059"],
        "remediation": "Upgrade Confluence to fixed versions 7.4.17, 7.13.7, 7.14.3, 7.15.2, 7.16.4, 7.17.4, or 7.18.1.",
        "references": ["https://confluence.atlassian.com/doc/confluence-security-advisory-2022-06-02-1130377146.html"]
    },
    "CVE-2023-34362": {
        "title": "Progress MOVEit Transfer SQL Injection to RCE",
        "description": "SQL injection vulnerability in the MOVEit Transfer web application that could allow an unauthenticated attacker to gain unauthorized access and execute commands.",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "severity": "CRITICAL",
        "epss_score": 0.975,
        "epss_percentile": 0.999,
        "in_cisa_kev": True,
        "weaponized": True,
        "affected_components": ["Progress Software MOVEit Transfer"],
        "mitre_attack_ids": ["T1190", "T1078", "T1505.003"],
        "remediation": "Apply vendor security patches released June 2023 and disable HTTP/HTTPS traffic on ports 80/443 pending upgrade.",
        "references": ["https://www.progress.com/security/moveit-transfer-and-moveit-cloud-vulnerability"]
    },
    "CVE-2014-0160": {
        "title": "OpenSSL TLS Heartbeat Information Disclosure (Heartbleed)",
        "description": "The (1) TLS and (2) DTLS implementations in OpenSSL 1.0.1 before 1.0.1g do not properly handle Heartbeat Extension packets, allowing remote attackers to read server memory.",
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "severity": "HIGH",
        "epss_score": 0.950,
        "epss_percentile": 0.992,
        "in_cisa_kev": True,
        "weaponized": True,
        "affected_components": ["OpenSSL 1.0.1 through 1.0.1f"],
        "mitre_attack_ids": ["T1552", "T1040"],
        "remediation": "Upgrade to OpenSSL 1.0.1g or rebuild OpenSSL with -DOPENSSL_NO_HEARTBEATS.",
        "references": ["https://heartbleed.com/"]
    }
}


class CVEIntelligenceEngine:
    """
    Threat intelligence engine providing automated CVE extraction,
    EPSS probability assessment, CISA KEV lookups, and risk prioritization.
    """

    def __init__(self, custom_database: Optional[Dict[str, Dict[str, Any]]] = None):
        self.database: Dict[str, Dict[str, Any]] = dict(KNOWN_CVE_DATABASE)
        if custom_database:
            self.database.update(custom_database)
        self.cache: Dict[str, CVEInfo] = {}

    def extract_cves(self, text: str) -> List[str]:
        """
        Extract unique CVE identifiers from arbitrary text or log output.
        Normalizes IDs to uppercase standard format (e.g. 'CVE-2021-44228').
        """
        if not text or not isinstance(text, str):
            return []
        matches = CVE_PATTERN.findall(text)
        # Normalize and preserve appearance order while deduplicating
        seen: Set[str] = set()
        unique_cves: List[str] = []
        for match in matches:
            normalized = match.upper()
            if normalized not in seen:
                seen.add(normalized)
                unique_cves.append(normalized)
        return unique_cves

    def lookup_cve(self, cve_id: str) -> Optional[CVEInfo]:
        """
        Look up comprehensive CVE intelligence by CVE ID.
        Checks local fast cache, curated database, and falls back to
        heuristic estimation for unrecognized CVEs.
        """
        if not cve_id:
            return None

        normalized_id = cve_id.strip().upper()

        if normalized_id in self.cache:
            return self.cache[normalized_id]

        if normalized_id in self.database:
            raw = self.database[normalized_id]
            info = CVEInfo(
                cve_id=normalized_id,
                title=raw.get("title", normalized_id),
                description=raw.get("description", ""),
                cvss_score=float(raw.get("cvss_score", 5.0)),
                cvss_vector=raw.get("cvss_vector", "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:L"),
                severity=raw.get("severity", "MEDIUM"),
                epss_score=float(raw.get("epss_score", 0.05)),
                epss_percentile=float(raw.get("epss_percentile", 0.50)),
                in_cisa_kev=bool(raw.get("in_cisa_kev", False)),
                weaponized=bool(raw.get("weaponized", False)),
                affected_components=raw.get("affected_components", []),
                mitre_attack_ids=raw.get("mitre_attack_ids", []),
                remediation=raw.get("remediation", "Apply vendor security patches."),
                references=raw.get("references", []),
            )
            self.cache[normalized_id] = info
            return info

        # Dynamic fallback for valid CVE format not in local knowledge base
        if CVE_PATTERN.match(normalized_id):
            info = self._generate_heuristic_cve_info(normalized_id)
            self.cache[normalized_id] = info
            return info

        return None

    def _generate_heuristic_cve_info(self, cve_id: str) -> CVEInfo:
        """Generate baseline heuristic estimate for known valid CVE format."""
        return CVEInfo(
            cve_id=cve_id,
            title=f"Vulnerability {cve_id}",
            description=f"Security advisory details for {cve_id}. Verify through official advisory channels.",
            cvss_score=6.5,
            cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:M/I:M/A:N",
            severity="MEDIUM",
            epss_score=0.10,
            epss_percentile=0.65,
            in_cisa_kev=False,
            weaponized=False,
            affected_components=["Generic Component"],
            mitre_attack_ids=["T1190"],
            remediation="Review vendor security bulletins and apply recommended updates.",
            references=[f"https://nvd.nist.gov/vuln/detail/{cve_id}"]
        )

    def enrich_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich a list of vulnerability findings with CVE intelligence.
        Extracts CVEs from descriptions, titles, and proof-of-concept fields.
        """
        enriched: List[Dict[str, Any]] = []

        for item in findings:
            item_copy = dict(item)
            # Combine fields to search for CVE IDs
            search_text = " ".join([
                str(item_copy.get("title", "")),
                str(item_copy.get("description", "")),
                str(item_copy.get("proof_of_concept", "")),
                str(item_copy.get("details", "")),
                str(item_copy.get("cve", ""))
            ])

            cve_ids = self.extract_cves(search_text)
            cve_intel_list: List[Dict[str, Any]] = []

            for cve_id in cve_ids:
                info = self.lookup_cve(cve_id)
                if info:
                    cve_intel_list.append(info.to_dict())

            item_copy["cves_detected"] = cve_ids
            item_copy["cve_intelligence"] = cve_intel_list

            # If CVEs were detected, upgrade finding metadata with highest prioritized risk
            if cve_intel_list:
                item_copy["prioritized_risk_score"] = max(c.get("prioritized_risk_score", 0.0) for c in cve_intel_list)
                # Check for CISA KEV presence
                item_copy["has_cisa_kev"] = any(c.get("in_cisa_kev", False) for c in cve_intel_list)
                item_copy["is_weaponized"] = any(c.get("weaponized", False) for c in cve_intel_list)

            enriched.append(item_copy)

        return enriched

    def get_cisa_kev_summary(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate summary of vulnerabilities present in CISA KEV catalog."""
        kev_vulnerabilities = []
        for finding in findings:
            intel_list = finding.get("cve_intelligence", [])
            for intel in intel_list:
                if intel.get("in_cisa_kev", False):
                    kev_vulnerabilities.append({
                        "finding_title": finding.get("title", "Unknown"),
                        "cve_id": intel.get("cve_id"),
                        "cvss_score": intel.get("cvss_score"),
                        "epss_score": intel.get("epss_score"),
                        "remediation": intel.get("remediation"),
                    })

        return {
            "total_kev_count": len(kev_vulnerabilities),
            "requires_immediate_action": len(kev_vulnerabilities) > 0,
            "vulnerabilities": kev_vulnerabilities,
        }
