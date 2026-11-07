"""
Tests for HackBot AI Remediation Engine
=========================================
Covers rule-based matching, AI-enhanced fallback, data models,
serialization, markdown rendering, and batch operations.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from hackbot.core.remediation import (
    Remediation,
    RemediationEngine,
    RemediationPriority,
    RemediationStep,
    RemediationType,
    _compile_rules,
    _COMPILED_RULES,
    _RULES,
    _severity_to_priority,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

FINDING_SQLI = {
    "title": "SQL Injection in Login Form",
    "severity": "Critical",
    "description": "The login endpoint is vulnerable to SQL injection via the username parameter.",
    "evidence": "' OR 1=1 -- returned all users",
    "recommendation": "Use parameterized queries",
    "tool": "sqlmap",
    "timestamp": "2025-01-01T00:00:00",
}

FINDING_XSS = {
    "title": "Reflected Cross-Site Scripting (XSS)",
    "severity": "High",
    "description": "User input is reflected without encoding in the search results page.",
    "evidence": "<script>alert(1)</script> was executed",
    "recommendation": "Encode all user output",
    "tool": "zap",
}

FINDING_OPEN_PORT = {
    "title": "Unnecessary Open Port 23 (Telnet)",
    "severity": "Medium",
    "description": "Port 23 open with Telnet service running, which transmits data in cleartext.",
    "evidence": "nmap: 23/tcp open telnet",
    "recommendation": "Disable Telnet and use SSH instead",
    "tool": "nmap",
}

FINDING_WEAK_PASS = {
    "title": "Default credentials on admin panel",
    "severity": "High",
    "description": "The web admin panel uses default password admin/admin.",
    "evidence": "Login successful with admin:admin",
    "recommendation": "Change default credentials immediately",
    "tool": "hydra",
}

FINDING_SSL = {
    "title": "Weak TLS Configuration — TLSv1.0 Supported",
    "severity": "High",
    "description": "Server supports TLS 1.0 which has known vulnerabilities.",
    "evidence": "sslscan: TLSv1.0 enabled",
    "recommendation": "Disable TLS 1.0 and 1.1",
    "tool": "sslscan",
}

FINDING_HEADERS = {
    "title": "Missing Security Headers",
    "severity": "Medium",
    "description": "Several security headers are missing from HTTP responses.",
    "evidence": "Missing: X-Frame-Options, Content-Security-Policy, HSTS",
    "recommendation": "Add security headers",
    "tool": "nikto",
}

FINDING_CMD_INJECTION = {
    "title": "OS Command Injection in ping utility",
    "severity": "Critical",
    "description": "The ping utility passes user input directly to system shell.",
    "evidence": "; cat /etc/passwd returned file contents",
    "recommendation": "Sanitize input and avoid shell execution",
    "tool": "manual",
}

FINDING_PATH_TRAVERSAL = {
    "title": "Directory Traversal in File Download",
    "severity": "High",
    "description": "LFI allows reading arbitrary files via path traversal.",
    "evidence": "../../etc/passwd returned /etc/passwd content",
    "recommendation": "Validate and restrict file paths",
    "tool": "burp",
}

FINDING_CSRF = {
    "title": "Cross-Site Request Forgery on Profile Update",
    "severity": "Medium",
    "description": "No CSRF protection on state-changing requests.",
    "evidence": "Profile updated via cross-origin form submission",
    "recommendation": "Implement CSRF tokens",
    "tool": "burp",
}

FINDING_SSH = {
    "title": "SSH Root Login Permitted",
    "severity": "High",
    "description": "SSH allows root login with password authentication.",
    "evidence": "sshd_config: PermitRootLogin yes",
    "recommendation": "Disable SSH root login",
    "tool": "nmap-scripts",
}

FINDING_INFO_DISCLOSURE = {
    "title": "Server Version Information Disclosure",
    "severity": "Low",
    "description": "HTTP response headers expose server version details.",
    "evidence": "Server: Apache/2.4.49 (Ubuntu)",
    "recommendation": "Hide server version banners",
    "tool": "nikto",
}

FINDING_OUTDATED = {
    "title": "Outdated Apache 2.4.49 — CVE-2021-41773",
    "severity": "Critical",
    "description": "Apache version 2.4.49 is end-of-life and has known security vulnerabilities.",
    "evidence": "Version: 2.4.49",
    "recommendation": "Update to latest Apache version",
    "tool": "nmap",
}

FINDING_CORS = {
    "title": "CORS Misconfiguration — Wildcard Origin",
    "severity": "Medium",
    "description": "Access-Control-Allow-Origin is set to * allowing any origin.",
    "evidence": "Access-Control-Allow-Origin: *",
    "recommendation": "Restrict CORS to trusted origins",
    "tool": "burp",
}

FINDING_IDOR = {
    "title": "Insecure Direct Object Reference in API",
    "severity": "High",
    "description": "User can access other users' data by changing the ID parameter.",
    "evidence": "/api/users/123 accessible with user 456 token",
    "recommendation": "Implement proper authorization checks",
    "tool": "burp",
}

FINDING_UPLOAD = {
    "title": "Unrestricted File Upload",
    "severity": "High",
    "description": "Application allows uploading PHP files disguised as images.",
    "evidence": "Uploaded shell.php.jpg — executed as PHP",
    "recommendation": "Validate file types and store outside webroot",
    "tool": "manual",
}

FINDING_XXE = {
    "title": "XML External Entity (XXE) in API",
    "severity": "High",
    "description": "XML parser processes external entities allowing file reading.",
    "evidence": "<!ENTITY xxe SYSTEM 'file:///etc/passwd'>",
    "recommendation": "Disable external entities in XML parser",
    "tool": "burp",
}

FINDING_SSRF = {
    "title": "Server-Side Request Forgery via URL Fetch",
    "severity": "High",
    "description": "Application fetches user-supplied URLs without restriction.",
    "evidence": "http://169.254.169.254/latest/meta-data/ returned AWS metadata",
    "recommendation": "Validate and restrict outbound URLs",
    "tool": "manual",
}

FINDING_DESERIALIZATION = {
    "title": "Insecure Deserialization in Session Cookie",
    "severity": "Critical",
    "description": "Application uses pickle to deserialize session data.",
    "evidence": "Modified pickle payload executed code on server",
    "recommendation": "Use JSON instead of pickle for serialization",
    "tool": "manual",
}

FINDING_DNS = {
    "title": "DNS Zone Transfer Allowed (AXFR)",
    "severity": "Medium",
    "description": "DNS server allows zone transfer revealing all records.",
    "evidence": "dig axfr example.com @ns1.example.com succeeded",
    "recommendation": "Restrict zone transfers to authorized servers",
    "tool": "dig",
}

FINDING_SNMP = {
    "title": "SNMP Default Community String 'public'",
    "severity": "High",
    "description": "SNMP service uses default 'public' community string.",
    "evidence": "snmpwalk -c public returned system info",
    "recommendation": "Change community strings and use SNMPv3",
    "tool": "nmap",
}

FINDING_ADMIN = {
    "title": "Exposed phpMyAdmin Panel",
    "severity": "High",
    "description": "phpMyAdmin interface publicly accessible without IP restriction.",
    "evidence": "http://target/phpmyadmin/ accessible from internet",
    "recommendation": "Restrict admin panel access to internal networks",
    "tool": "dirb",
}

FINDING_UNKNOWN = {
    "title": "Obscure Custom Vulnerability X42",
    "severity": "Medium",
    "description": "A very specific misconfiguration in custom software.",
    "evidence": "Custom check detected issue",
    "recommendation": "Review custom software configuration",
    "tool": "custom",
}

ALL_FINDINGS = [
    FINDING_SQLI, FINDING_XSS, FINDING_OPEN_PORT, FINDING_WEAK_PASS,
    FINDING_SSL, FINDING_HEADERS, FINDING_CMD_INJECTION, FINDING_PATH_TRAVERSAL,
    FINDING_CSRF, FINDING_SSH, FINDING_INFO_DISCLOSURE, FINDING_OUTDATED,
    FINDING_CORS, FINDING_IDOR, FINDING_UPLOAD, FINDING_XXE, FINDING_SSRF,
    FINDING_DESERIALIZATION, FINDING_DNS, FINDING_SNMP, FINDING_ADMIN,
]


# ── RemediationType Tests ────────────────────────────────────────────────────

class TestRemediationType:
    def test_values(self):
        assert RemediationType.COMMAND.value == "command"
        assert RemediationType.CONFIG.value == "config"
        assert RemediationType.CODE.value == "code"
        assert RemediationType.REFERENCE.value == "reference"

    def test_string_enum(self):
        assert isinstance(RemediationType.COMMAND, str)
        assert RemediationType.COMMAND == "command"


class TestRemediationPriority:
    def test_values(self):
        assert RemediationPriority.IMMEDIATE.value == "immediate"
        assert RemediationPriority.HIGH.value == "high"
        assert RemediationPriority.MEDIUM.value == "medium"
        assert RemediationPriority.LOW.value == "low"
        assert RemediationPriority.INFORMATIONAL.value == "informational"


# ── RemediationStep Tests ────────────────────────────────────────────────────

class TestRemediationStep:
    def test_create_step(self):
        step = RemediationStep(
            type=RemediationType.COMMAND,
            title="Install patch",
            content="sudo apt update",
            language="bash",
            filename="",
            description="Update packages",
        )
        assert step.type == RemediationType.COMMAND
        assert step.title == "Install patch"
        assert step.content == "sudo apt update"
        assert step.language == "bash"

    def test_to_dict(self):
        step = RemediationStep(
            type=RemediationType.CODE,
            title="Fix code",
            content="x = 1",
            language="python",
            filename="app.py",
            description="Set variable",
        )
        d = step.to_dict()
        assert d["type"] == "code"
        assert d["title"] == "Fix code"
        assert d["content"] == "x = 1"
        assert d["language"] == "python"
        assert d["filename"] == "app.py"
        assert d["description"] == "Set variable"

    def test_from_dict(self):
        data = {
            "type": "config",
            "title": "Fix nginx",
            "content": "server_tokens off;",
            "language": "nginx",
            "filename": "/etc/nginx/nginx.conf",
            "description": "Hide version",
        }
        step = RemediationStep.from_dict(data)
        assert step.type == RemediationType.CONFIG
        assert step.title == "Fix nginx"
        assert step.filename == "/etc/nginx/nginx.conf"

    def test_from_dict_defaults(self):
        step = RemediationStep.from_dict({})
        assert step.type == RemediationType.REFERENCE
        assert step.title == ""
        assert step.content == ""

    def test_round_trip(self):
        step = RemediationStep(
            type=RemediationType.COMMAND,
            title="Test",
            content="echo hello",
            language="bash",
            filename="/tmp/test.sh",
            description="Test step",
        )
        step2 = RemediationStep.from_dict(step.to_dict())
        assert step2.type == step.type
        assert step2.title == step.title
        assert step2.content == step.content
        assert step2.language == step.language
        assert step2.filename == step.filename
        assert step2.description == step.description


# ── Remediation Tests ────────────────────────────────────────────────────────

class TestRemediation:
    def test_create(self):
        r = Remediation(
            finding_title="SQL Injection",
            finding_severity="Critical",
            summary="Use parameterized queries",
            priority=RemediationPriority.IMMEDIATE,
            steps=[
                RemediationStep(
                    type=RemediationType.CODE,
                    title="Fix query",
                    content="cursor.execute('SELECT * FROM users WHERE id = %s', (uid,))",
                    language="python",
                ),
            ],
            references=["https://owasp.org"],
            source="rule",
        )
        assert r.finding_title == "SQL Injection"
        assert r.priority == RemediationPriority.IMMEDIATE
        assert len(r.steps) == 1
        assert r.source == "rule"

    def test_to_dict(self):
        r = Remediation(
            finding_title="Test",
            finding_severity="High",
            summary="Fix it",
            priority=RemediationPriority.HIGH,
            steps=[
                RemediationStep(type=RemediationType.COMMAND, title="Cmd", content="echo fix"),
                RemediationStep(type=RemediationType.CONFIG, title="Cfg", content="x=1"),
                RemediationStep(type=RemediationType.CODE, title="Code", content="pass"),
            ],
            references=["https://example.com"],
        )
        d = r.to_dict()
        assert d["finding_title"] == "Test"
        assert d["finding_severity"] == "High"
        assert d["priority"] == "high"
        assert d["step_count"] == 3
        assert d["has_commands"] is True
        assert d["has_config"] is True
        assert d["has_code"] is True
        assert len(d["steps"]) == 3
        assert len(d["references"]) == 1
        assert d["source"] == "rule"

    def test_from_dict(self):
        data = {
            "finding_title": "XSS",
            "finding_severity": "High",
            "summary": "Encode output",
            "priority": "high",
            "steps": [{"type": "code", "title": "Fix", "content": "escape(x)"}],
            "references": ["https://owasp.org"],
            "source": "ai",
            "confidence": 0.9,
        }
        r = Remediation.from_dict(data)
        assert r.finding_title == "XSS"
        assert r.priority == RemediationPriority.HIGH
        assert len(r.steps) == 1
        assert r.source == "ai"
        assert r.confidence == 0.9

    def test_from_dict_defaults(self):
        r = Remediation.from_dict({})
        assert r.finding_title == ""
        assert r.priority == RemediationPriority.MEDIUM
        assert r.source == "rule"
        assert r.confidence == 1.0

    def test_round_trip(self):
        r = Remediation(
            finding_title="Original",
            finding_severity="Critical",
            summary="Test round trip",
            priority=RemediationPriority.IMMEDIATE,
            steps=[
                RemediationStep(type=RemediationType.COMMAND, title="Step 1", content="cmd1"),
                RemediationStep(type=RemediationType.CODE, title="Step 2", content="code1"),
            ],
            references=["https://a.com", "https://b.com"],
            source="rule",
            confidence=0.95,
        )
        r2 = Remediation.from_dict(r.to_dict())
        assert r2.finding_title == r.finding_title
        assert r2.finding_severity == r.finding_severity
        assert r2.priority == r.priority
        assert len(r2.steps) == len(r.steps)
        assert r2.references == r.references
        assert r2.source == r.source

    def test_get_markdown(self):
        r = Remediation(
            finding_title="SQL Injection",
            finding_severity="Critical",
            summary="Use parameterized queries.",
            priority=RemediationPriority.IMMEDIATE,
            steps=[
                RemediationStep(type=RemediationType.COMMAND, title="Update server", content="apt update", language="bash", description="System update"),
                RemediationStep(type=RemediationType.CONFIG, title="Fix config", content="key=val", filename="/etc/conf.d/x"),
                RemediationStep(type=RemediationType.CODE, title="Fix code", content="x = safe(y)", language="python"),
                RemediationStep(type=RemediationType.REFERENCE, title="Read docs", content="Check OWASP"),
            ],
            references=["https://owasp.org"],
        )
        md = r.get_markdown()
        assert "SQL Injection" in md
        assert "IMMEDIATE" in md
        assert "Critical" in md
        assert "apt update" in md
        assert "/etc/conf.d/x" in md
        assert "x = safe(y)" in md
        assert "https://owasp.org" in md
        assert "Step 1" in md
        assert "Step 4" in md
        assert "💻" in md  # command icon
        assert "📝" in md  # code icon

    def test_get_markdown_no_steps(self):
        r = Remediation(
            finding_title="Empty",
            finding_severity="Info",
            summary="Nothing",
            priority=RemediationPriority.INFORMATIONAL,
        )
        md = r.get_markdown()
        assert "Empty" in md
        assert "Nothing" in md


# ── Severity → Priority Mapping ─────────────────────────────────────────────

class TestSeverityPriority:
    def test_critical(self):
        assert _severity_to_priority("Critical") == RemediationPriority.IMMEDIATE

    def test_high(self):
        assert _severity_to_priority("High") == RemediationPriority.HIGH

    def test_medium(self):
        assert _severity_to_priority("Medium") == RemediationPriority.MEDIUM

    def test_low(self):
        assert _severity_to_priority("Low") == RemediationPriority.LOW

    def test_info(self):
        assert _severity_to_priority("Info") == RemediationPriority.INFORMATIONAL

    def test_unknown(self):
        assert _severity_to_priority("Unknown") == RemediationPriority.MEDIUM


# ── Rule Registry ────────────────────────────────────────────────────────────

class TestRuleRegistry:
    def test_rules_exist(self):
        assert len(_RULES) > 15, f"Expected 15+ rules, got {len(_RULES)}"

    def test_compile_rules(self):
        _compile_rules()
        assert len(_COMPILED_RULES) >= len(_RULES)

    def test_rule_count(self):
        engine = RemediationEngine()
        assert engine.get_rule_count() > 15

    def test_rule_patterns(self):
        engine = RemediationEngine()
        patterns = engine.get_rule_patterns()
        assert len(patterns) == engine.get_rule_count()
        assert all(isinstance(p, str) for p in patterns)


# ── Rule-Based Remediation ───────────────────────────────────────────────────

class TestRuleBasedRemediation:
    def setup_method(self):
        self.engine = RemediationEngine()

    # SQL Injection
    def test_sqli(self):
        r = self.engine.remediate_finding(FINDING_SQLI)
        assert r.source == "rule"
        assert r.priority == RemediationPriority.IMMEDIATE
        assert r.finding_title == "SQL Injection in Login Form"
        assert len(r.steps) >= 3
        assert any(s.type == RemediationType.CODE for s in r.steps)
        assert any("parameterized" in s.content.lower() for s in r.steps)

    def test_sqli_variations(self):
        for title in ["Blind SQL Injection", "Union-based SQLi", "SQL injection detected"]:
            f = {"title": title, "severity": "Critical", "description": title}
            r = self.engine.remediate_finding(f)
            assert r.source == "rule"

    # XSS
    def test_xss(self):
        r = self.engine.remediate_finding(FINDING_XSS)
        assert r.source == "rule"
        assert r.priority == RemediationPriority.HIGH
        assert any(s.type == RemediationType.CONFIG for s in r.steps)
        assert any("content-security-policy" in s.content.lower() for s in r.steps)

    def test_xss_variations(self):
        for title in ["Stored XSS", "DOM-based XSS", "Reflected Script Injection"]:
            f = {"title": title, "severity": "High", "description": title}
            r = self.engine.remediate_finding(f)
            assert r.source == "rule"

    # Command Injection
    def test_command_injection(self):
        r = self.engine.remediate_finding(FINDING_CMD_INJECTION)
        assert r.source == "rule"
        assert r.priority == RemediationPriority.IMMEDIATE
        assert any("subprocess" in s.content for s in r.steps)

    def test_rce(self):
        f = {"title": "Remote Code Execution", "severity": "Critical", "description": "RCE via eval"}
        r = self.engine.remediate_finding(f)
        assert r.source == "rule"

    # Open Ports
    def test_open_ports(self):
        r = self.engine.remediate_finding(FINDING_OPEN_PORT)
        assert r.source == "rule"
        assert any(s.type == RemediationType.COMMAND for s in r.steps)
        assert any("ufw" in s.content.lower() or "iptables" in s.content.lower() for s in r.steps)

    # Weak Credentials
    def test_weak_creds(self):
        r = self.engine.remediate_finding(FINDING_WEAK_PASS)
        assert r.source == "rule"
        assert r.priority == RemediationPriority.HIGH
        assert any("password" in s.content.lower() or "pam" in s.content.lower() for s in r.steps)

    # SSL/TLS
    def test_ssl(self):
        r = self.engine.remediate_finding(FINDING_SSL)
        assert r.source == "rule"
        assert any("TLSv1.2" in s.content or "TLSv1.3" in s.content for s in r.steps)

    def test_ssl_variations(self):
        for title in ["Expired SSL Certificate", "Self-signed certificate", "Weak cipher suite", "POODLE vulnerability"]:
            f = {"title": title, "severity": "High", "description": title}
            r = self.engine.remediate_finding(f)
            assert r.source == "rule"

    # Security Headers
    def test_headers(self):
        r = self.engine.remediate_finding(FINDING_HEADERS)
        assert r.source == "rule"
        assert any("X-Frame-Options" in s.content for s in r.steps)

    def test_clickjacking(self):
        f = {"title": "Clickjacking - X-Frame-Options Missing", "severity": "Medium", "description": "No X-Frame-Options"}
        r = self.engine.remediate_finding(f)
        assert r.source == "rule"

    # Path Traversal
    def test_path_traversal(self):
        r = self.engine.remediate_finding(FINDING_PATH_TRAVERSAL)
        assert r.source == "rule"
        assert any("resolve" in s.content.lower() or "traversal" in s.content.lower() for s in r.steps)

    # CSRF
    def test_csrf(self):
        r = self.engine.remediate_finding(FINDING_CSRF)
        assert r.source == "rule"
        assert any("csrf" in s.content.lower() for s in r.steps)

    # SSH
    def test_ssh(self):
        r = self.engine.remediate_finding(FINDING_SSH)
        assert r.source == "rule"
        assert any("PermitRootLogin" in s.content for s in r.steps)

    # Info Disclosure
    def test_info_disclosure(self):
        r = self.engine.remediate_finding(FINDING_INFO_DISCLOSURE)
        assert r.source == "rule"
        assert any("server_tokens" in s.content for s in r.steps)

    # Outdated Software
    def test_outdated(self):
        r = self.engine.remediate_finding(FINDING_OUTDATED)
        assert r.source == "rule"
        assert any("apt" in s.content for s in r.steps)

    # CORS
    def test_cors(self):
        r = self.engine.remediate_finding(FINDING_CORS)
        assert r.source == "rule"
        assert any("cors" in s.content.lower() or "origin" in s.content.lower() for s in r.steps)

    # IDOR
    def test_idor(self):
        r = self.engine.remediate_finding(FINDING_IDOR)
        assert r.source == "rule"
        assert any("authorization" in s.content.lower() or "owner" in s.content.lower() for s in r.steps)

    # File Upload
    def test_upload(self):
        r = self.engine.remediate_finding(FINDING_UPLOAD)
        assert r.source == "rule"
        assert any("mime" in s.content.lower() or "validate" in s.content.lower() for s in r.steps)

    # XXE
    def test_xxe(self):
        r = self.engine.remediate_finding(FINDING_XXE)
        assert r.source == "rule"
        assert any("defuse" in s.content.lower() or "entity" in s.content.lower() or "external" in s.content.lower() for s in r.steps)

    # SSRF
    def test_ssrf(self):
        r = self.engine.remediate_finding(FINDING_SSRF)
        assert r.source == "rule"
        assert any("ip_network" in s.content or "ipaddress" in s.content for s in r.steps)

    # Deserialization
    def test_deserialization(self):
        r = self.engine.remediate_finding(FINDING_DESERIALIZATION)
        assert r.source == "rule"
        assert any("json" in s.content.lower() or "pickle" in s.content.lower() for s in r.steps)

    # DNS
    def test_dns(self):
        r = self.engine.remediate_finding(FINDING_DNS)
        assert r.source == "rule"
        assert any("zone" in s.content.lower() or "transfer" in s.content.lower() for s in r.steps)

    # SNMP
    def test_snmp(self):
        r = self.engine.remediate_finding(FINDING_SNMP)
        assert r.source == "rule"
        assert any("snmp" in s.content.lower() for s in r.steps)

    # Admin Panel
    def test_admin(self):
        r = self.engine.remediate_finding(FINDING_ADMIN)
        assert r.source == "rule"
        assert any("deny" in s.content.lower() or "allow" in s.content.lower() for s in r.steps)

    # All findings produce valid remediations
    def test_all_findings_produce_results(self):
        for finding in ALL_FINDINGS:
            r = self.engine.remediate_finding(finding)
            assert isinstance(r, Remediation)
            assert r.finding_title
            assert r.summary
            assert r.priority in RemediationPriority
            assert len(r.steps) >= 1


# ── Generic Fallback ─────────────────────────────────────────────────────────

class TestGenericFallback:
    def setup_method(self):
        self.engine = RemediationEngine()

    def test_unknown_finding(self):
        r = self.engine.remediate_finding(FINDING_UNKNOWN)
        assert r.source == "generic"
        assert r.confidence == 0.3
        assert r.finding_title == "Obscure Custom Vulnerability X42"
        assert len(r.steps) >= 1

    def test_unknown_with_recommendation(self):
        r = self.engine.remediate_finding(FINDING_UNKNOWN)
        # Should include the original recommendation
        has_recommendation = any(
            "Review custom software" in s.content for s in r.steps
        )
        assert has_recommendation

    def test_empty_finding(self):
        r = self.engine.remediate_finding({})
        assert r.source == "generic"
        assert r.finding_title == "Security Finding"


# ── Batch Remediation ────────────────────────────────────────────────────────

class TestBatchRemediation:
    def setup_method(self):
        self.engine = RemediationEngine()

    def test_remediate_findings(self):
        results = self.engine.remediate_findings(ALL_FINDINGS)
        assert len(results) == len(ALL_FINDINGS)
        assert all(isinstance(r, Remediation) for r in results)

    def test_remediate_empty_list(self):
        results = self.engine.remediate_findings([])
        assert results == []

    def test_summary_markdown(self):
        results = self.engine.remediate_findings(ALL_FINDINGS)
        md = RemediationEngine.get_summary_markdown(results)
        assert "# 🔧 Remediation Report" in md
        assert "Priority Summary" in md
        assert "IMMEDIATE" in md
        assert "HIGH" in md
        assert "Total:" in md

    def test_summary_empty(self):
        md = RemediationEngine.get_summary_markdown([])
        assert "No remediations" in md

    def test_priority_distribution(self):
        results = self.engine.remediate_findings(ALL_FINDINGS)
        priorities = [r.priority for r in results]
        assert RemediationPriority.IMMEDIATE in priorities
        assert RemediationPriority.HIGH in priorities
        assert RemediationPriority.MEDIUM in priorities


# ── AI-Enhanced Remediation ──────────────────────────────────────────────────

class TestAIRemediation:
    def test_ai_prompt_generation(self):
        prompt = RemediationEngine._build_ai_prompt(FINDING_SQLI)
        assert "SQL Injection" in prompt
        assert "Critical" in prompt
        assert "sqlmap" in prompt
        assert "SUMMARY:" in prompt
        assert "COMMAND:" in prompt
        assert "CODE:" in prompt

    def test_ai_response_parsing(self):
        mock_response = """SUMMARY: Apply parameterized queries to prevent SQL injection.

COMMAND:
<title>: Install WAF
<description>: Deploy ModSecurity
<language>: bash
```
sudo apt install libapache2-mod-security2 -y
```

CODE:
<title>: Fix Python query
<language>: python
```
cursor.execute("SELECT * FROM users WHERE id = %s", (uid,))
```

REFERENCES:
- https://owasp.org/sqli
- https://example.com/fix"""

        r = RemediationEngine._parse_ai_response(FINDING_SQLI, mock_response)
        assert r.source == "ai"
        assert r.confidence == 0.8
        assert "parameterized" in r.summary.lower()
        assert len(r.steps) >= 2
        assert len(r.references) >= 1

    def test_ai_remediation_with_mock_engine(self):
        mock_engine = MagicMock()
        mock_engine.chat.return_value = """SUMMARY: Fix the vulnerability.

COMMAND:
<title>: Apply patch
<language>: bash
```
sudo apt update
```"""

        engine = RemediationEngine(ai_engine=mock_engine)
        r = engine.remediate_finding(FINDING_UNKNOWN, use_ai=True)
        assert r.source == "ai"
        mock_engine.chat.assert_called_once()

    def test_ai_fallback_on_error(self):
        mock_engine = MagicMock()
        mock_engine.chat.side_effect = Exception("API error")

        engine = RemediationEngine(ai_engine=mock_engine)
        r = engine.remediate_finding(FINDING_UNKNOWN, use_ai=True)
        assert r.source == "generic"  # Falls back to generic

    def test_use_ai_skips_rules(self):
        """When use_ai=True, should skip rule matching and go to AI."""
        mock_engine = MagicMock()
        mock_engine.chat.return_value = "SUMMARY: AI fix\n\nCOMMAND:\n<title>: AI step\n<language>: bash\n```\necho ai\n```"

        engine = RemediationEngine(ai_engine=mock_engine)
        r = engine.remediate_finding(FINDING_SQLI, use_ai=True)
        assert r.source == "ai"
        mock_engine.chat.assert_called_once()

    def test_ai_empty_response(self):
        r = RemediationEngine._parse_ai_response(FINDING_SQLI, "")
        assert r.source == "ai"
        assert len(r.steps) >= 1  # Should still have at least a reference step

    def test_ai_malformed_response(self):
        r = RemediationEngine._parse_ai_response(FINDING_SQLI, "random text without any structure")
        assert r.source == "ai"
        assert r.summary  # Should have generated a summary


# ── Remediation Content Quality ──────────────────────────────────────────────

class TestContentQuality:
    def setup_method(self):
        self.engine = RemediationEngine()

    def test_sqli_has_multiple_languages(self):
        r = self.engine.remediate_finding(FINDING_SQLI)
        languages = {s.language for s in r.steps if s.language}
        assert len(languages) >= 2, f"Expected multi-language coverage, got: {languages}"

    def test_ssl_has_nginx_and_apache(self):
        r = self.engine.remediate_finding(FINDING_SSL)
        content = " ".join(s.content for s in r.steps)
        assert "nginx" in content.lower() or "apache" in content.lower()
        assert "TLSv1.2" in content or "TLSv1.3" in content

    def test_headers_have_multiple_steps(self):
        r = self.engine.remediate_finding(FINDING_HEADERS)
        assert len(r.steps) >= 2

    def test_open_ports_has_firewall_commands(self):
        r = self.engine.remediate_finding(FINDING_OPEN_PORT)
        content = " ".join(s.content for s in r.steps)
        assert "ufw" in content or "iptables" in content

    def test_references_are_urls(self):
        """All references should be valid URLs."""
        for finding in ALL_FINDINGS:
            r = self.engine.remediate_finding(finding)
            for ref in r.references:
                assert ref.startswith("http"), f"Invalid reference: {ref}"

    def test_all_steps_have_content(self):
        """Every step should have non-empty content."""
        for finding in ALL_FINDINGS:
            r = self.engine.remediate_finding(finding)
            for step in r.steps:
                assert step.content, f"Empty content in step '{step.title}' for '{r.finding_title}'"

    def test_all_steps_have_titles(self):
        """Every step should have a title."""
        for finding in ALL_FINDINGS:
            r = self.engine.remediate_finding(finding)
            for step in r.steps:
                assert step.title, f"Empty title in step for '{r.finding_title}'"

    def test_command_steps_have_bash_language(self):
        """Command steps should default to bash."""
        for finding in ALL_FINDINGS:
            r = self.engine.remediate_finding(finding)
            for step in r.steps:
                if step.type == RemediationType.COMMAND:
                    assert step.language == "bash", f"Expected bash, got '{step.language}' for '{step.title}'"


# ── Edge Cases ───────────────────────────────────────────────────────────────

class TestEdgeCases:
    def setup_method(self):
        self.engine = RemediationEngine()

    def test_finding_with_empty_title(self):
        r = self.engine.remediate_finding({"title": "", "severity": "Low"})
        assert isinstance(r, Remediation)

    def test_finding_with_long_description(self):
        r = self.engine.remediate_finding({
            "title": "SQL Injection",
            "severity": "High",
            "description": "x" * 10000,
        })
        assert isinstance(r, Remediation)

    def test_finding_with_special_chars(self):
        r = self.engine.remediate_finding({
            "title": "XSS <script>alert('test')</script>",
            "severity": "High",
            "description": "Input: <img onerror='alert(1)' src=x>",
        })
        assert isinstance(r, Remediation)

    def test_case_insensitive_matching(self):
        """Rules should match regardless of case."""
        for title in ["SQL INJECTION", "sql injection", "Sql Injection"]:
            r = self.engine.remediate_finding({"title": title, "severity": "High"})
            assert r.source == "rule", f"Failed for: {title}"

    def test_description_matching(self):
        """Rules should also match against description."""
        f = {
            "title": "Custom Check Failed",
            "severity": "High",
            "description": "SQL injection vulnerability found in user input handling",
        }
        r = self.engine.remediate_finding(f)
        assert r.source == "rule"

    def test_no_ai_engine(self):
        """Without AI engine, should fall back to generic."""
        engine = RemediationEngine(ai_engine=None)
        r = engine.remediate_finding(FINDING_UNKNOWN, use_ai=True)
        assert r.source == "generic"

    def test_ai_remediate_success(self):
        """When AI engine is provided and returns structured text, it should parse correctly."""
        from hackbot.core.engine import AIEngine, Conversation
        ai_engine = MagicMock(spec=AIEngine)
        ai_engine.chat.return_value = """SUMMARY: Fix for custom vulnerability
COMMAND:
<title>: Update configuration
<description>: Secure the app configuration
<language>: bash
```
secure_mode = true
```

REFERENCES:
- https://example.com/fix
"""
        engine = RemediationEngine(ai_engine=ai_engine)
        r = engine.remediate_finding(FINDING_UNKNOWN, use_ai=True)
        assert r.source == "ai"
        assert r.summary == "Fix for custom vulnerability"
        assert len(r.steps) == 1
        assert r.steps[0].content == "secure_mode = true"
        assert "https://example.com/fix" in r.references
        ai_engine.chat.assert_called_once()
        call_args, call_kwargs = ai_engine.chat.call_args
        assert isinstance(call_args[0], Conversation)
        assert call_kwargs.get("stream") is False

    def test_ai_remediate_exception_fallback(self):
        """When AI engine raises an exception, should gracefully fall back to generic."""
        from hackbot.core.engine import AIEngine
        ai_engine = MagicMock(spec=AIEngine)
        ai_engine.chat.side_effect = RuntimeError("API error")
        engine = RemediationEngine(ai_engine=ai_engine)
        r = engine.remediate_finding(FINDING_UNKNOWN, use_ai=True)
        assert r.source == "generic"

    def test_concurrent_usage(self):
        """Engine should be safe for concurrent use."""
        import threading
        results = []
        def worker(finding):
            r = self.engine.remediate_finding(finding)
            results.append(r)

        threads = [threading.Thread(target=worker, args=(f,)) for f in ALL_FINDINGS]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(results) == len(ALL_FINDINGS)


# ── Summary Report ───────────────────────────────────────────────────────────

class TestSummaryReport:
    def test_report_structure(self):
        engine = RemediationEngine()
        results = engine.remediate_findings(ALL_FINDINGS[:5])
        md = RemediationEngine.get_summary_markdown(results)
        assert "# 🔧 Remediation Report" in md
        assert "Priority Summary" in md
        assert "Total:" in md
        assert "commands" in md
        assert "configs" in md
        assert "code snippets" in md

    def test_report_has_all_findings(self):
        engine = RemediationEngine()
        results = engine.remediate_findings(ALL_FINDINGS[:5])
        md = RemediationEngine.get_summary_markdown(results)
        for r in results:
            assert r.finding_title in md

    def test_report_empty(self):
        md = RemediationEngine.get_summary_markdown([])
        assert "No remediations" in md

    def test_single_finding_report(self):
        engine = RemediationEngine()
        r = engine.remediate_finding(FINDING_SQLI)
        md = RemediationEngine.get_summary_markdown([r])
        assert "SQL Injection" in md
        assert "IMMEDIATE" in md
