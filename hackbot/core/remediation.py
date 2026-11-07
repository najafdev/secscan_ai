"""
HackBot AI Remediation Engine
================================
For each finding, auto-generate actionable fix commands, configuration
patches, and code snippets.  Works in two modes:

1. **Rule-based** — instant remediation from a built-in knowledge base of
   ~60 vulnerability patterns (no API key required).
2. **AI-enhanced** — uses the configured LLM to generate tailored fixes when
   the rule base doesn't cover a finding or when richer guidance is requested.

Each remediation contains:
  • One-liner summary of the fix
  • Shell commands (apt, systemctl, sysctl, iptables, etc.)
  • Config file patches (nginx, apache, sshd, etc.)
  • Code snippets (Python, PHP, JS, Java, etc.)
  • References (CVE links, CIS benchmarks, OWASP pages)

Usage (CLI)::

    /remediate              Remediate all current findings
    /remediate 2            Remediate finding #2 only
    /remediate --ai         Force AI-enhanced remediation

Usage (Agent)::

    The agent can call the remediation engine automatically after
    discovering findings to provide immediate fix guidance.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────

class RemediationType(str, Enum):
    """Category of remediation action."""
    COMMAND = "command"
    CONFIG = "config"
    CODE = "code"
    REFERENCE = "reference"


class RemediationPriority(str, Enum):
    """How urgently the fix should be applied."""
    IMMEDIATE = "immediate"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class RemediationStep:
    """A single actionable fix step."""
    type: RemediationType
    title: str
    content: str
    language: str = ""  # bash, python, nginx, apache, yaml, etc.
    filename: str = ""  # target file path when applicable
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "title": self.title,
            "content": self.content,
            "language": self.language,
            "filename": self.filename,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RemediationStep":
        return cls(
            type=RemediationType(data.get("type", "reference")),
            title=data.get("title", ""),
            content=data.get("content", ""),
            language=data.get("language", ""),
            filename=data.get("filename", ""),
            description=data.get("description", ""),
        )


@dataclass
class Remediation:
    """Complete remediation guidance for a single finding."""
    finding_title: str
    finding_severity: str
    summary: str
    priority: RemediationPriority
    steps: List[RemediationStep] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)
    source: str = "rule"  # "rule" or "ai"
    confidence: float = 1.0  # 0.0-1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_title": self.finding_title,
            "finding_severity": self.finding_severity,
            "summary": self.summary,
            "priority": self.priority.value,
            "steps": [s.to_dict() for s in self.steps],
            "references": self.references,
            "generated_at": self.generated_at,
            "source": self.source,
            "confidence": self.confidence,
            "step_count": len(self.steps),
            "has_commands": any(s.type == RemediationType.COMMAND for s in self.steps),
            "has_config": any(s.type == RemediationType.CONFIG for s in self.steps),
            "has_code": any(s.type == RemediationType.CODE for s in self.steps),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Remediation":
        return cls(
            finding_title=data.get("finding_title", ""),
            finding_severity=data.get("finding_severity", ""),
            summary=data.get("summary", ""),
            priority=RemediationPriority(data.get("priority", "medium")),
            steps=[RemediationStep.from_dict(s) for s in data.get("steps", [])],
            references=data.get("references", []),
            generated_at=data.get("generated_at", time.time()),
            source=data.get("source", "rule"),
            confidence=data.get("confidence", 1.0),
        )

    def get_markdown(self) -> str:
        """Render remediation as markdown."""
        lines = [f"## 🔧 Remediation: {self.finding_title}\n"]
        lines.append(f"**Priority:** {self.priority.value.upper()} | "
                      f"**Severity:** {self.finding_severity} | "
                      f"**Source:** {self.source}\n")
        lines.append(f"{self.summary}\n")

        for i, step in enumerate(self.steps, 1):
            icon = {"command": "💻", "config": "⚙️", "code": "📝", "reference": "📖"}.get(step.type.value, "•")
            lines.append(f"### {icon} Step {i}: {step.title}\n")
            if step.description:
                lines.append(f"{step.description}\n")
            if step.filename:
                lines.append(f"**File:** `{step.filename}`\n")
            lang = step.language or ("bash" if step.type == RemediationType.COMMAND else "")
            if step.content:
                lines.append(f"```{lang}\n{step.content}\n```\n")

        if self.references:
            lines.append("### 📚 References\n")
            for ref in self.references:
                lines.append(f"- {ref}")
            lines.append("")

        return "\n".join(lines)


# ── Severity → Priority Mapping ─────────────────────────────────────────────

_SEVERITY_PRIORITY = {
    "Critical": RemediationPriority.IMMEDIATE,
    "High": RemediationPriority.HIGH,
    "Medium": RemediationPriority.MEDIUM,
    "Low": RemediationPriority.LOW,
    "Info": RemediationPriority.INFORMATIONAL,
}


def _severity_to_priority(severity: str) -> RemediationPriority:
    return _SEVERITY_PRIORITY.get(severity, RemediationPriority.MEDIUM)


# ── Rule-Based Remediation Knowledge Base ────────────────────────────────────
#
# Each rule is a tuple of:
#   (pattern, builder_function)
#
# `pattern` is compiled into a regex and matched against finding title +
# description (case-insensitive).  `builder_function` receives the finding
# dict and the regex match object and returns a Remediation.

_RULES: List[Tuple[str, Callable]] = []


def _rule(pattern: str):
    """Decorator to register a remediation rule."""
    def decorator(fn: Callable):
        _RULES.append((pattern, fn))
        return fn
    return decorator


# ── SQL Injection ────────────────────────────────────────────────────────────

@_rule(r"sql\s*inject|sqli|blind.*inject|union.*inject")
def _remediate_sqli(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "SQL Injection"),
        finding_severity=finding.get("severity", "Critical"),
        summary="Prevent SQL injection by using parameterized queries, input validation, and ORM frameworks.",
        priority=RemediationPriority.IMMEDIATE,
        steps=[
            RemediationStep(
                type=RemediationType.CODE,
                title="Use parameterized queries (Python)",
                language="python",
                description="Replace string concatenation with parameterized queries.",
                content="""# VULNERABLE — never do this:
# cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# SECURE — use parameterized queries:
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# Or use an ORM (SQLAlchemy):
user = session.query(User).filter(User.id == user_id).first()""",
            ),
            RemediationStep(
                type=RemediationType.CODE,
                title="Use parameterized queries (PHP)",
                language="php",
                description="Use PDO prepared statements.",
                content="""<?php
// VULNERABLE:
// $stmt = $pdo->query("SELECT * FROM users WHERE id = " . $_GET['id']);

// SECURE — use prepared statements:
$stmt = $pdo->prepare("SELECT * FROM users WHERE id = :id");
$stmt->execute(['id' => $_GET['id']]);
$user = $stmt->fetch();""",
            ),
            RemediationStep(
                type=RemediationType.CODE,
                title="Use parameterized queries (Java)",
                language="java",
                description="Use PreparedStatement instead of Statement.",
                content="""// SECURE — PreparedStatement
PreparedStatement ps = conn.prepareStatement(
    "SELECT * FROM users WHERE id = ?");
ps.setInt(1, userId);
ResultSet rs = ps.executeQuery();""",
            ),
            RemediationStep(
                type=RemediationType.COMMAND,
                title="Deploy a Web Application Firewall (WAF)",
                language="bash",
                description="Install ModSecurity as an additional defense layer.",
                content="""# Install ModSecurity for Apache
sudo apt install libapache2-mod-security2 -y
sudo a2enmod security2
sudo cp /etc/modsecurity/modsecurity.conf-recommended /etc/modsecurity/modsecurity.conf
sudo sed -i 's/SecRuleEngine DetectionOnly/SecRuleEngine On/' /etc/modsecurity/modsecurity.conf
sudo systemctl restart apache2""",
            ),
        ],
        references=[
            "https://owasp.org/www-community/attacks/SQL_Injection",
            "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
        ],
    )


# ── Cross-Site Scripting (XSS) ──────────────────────────────────────────────

@_rule(r"cross.?site\s*script|xss|reflected.*script|stored.*script|dom.*xss")
def _remediate_xss(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "Cross-Site Scripting (XSS)"),
        finding_severity=finding.get("severity", "High"),
        summary="Mitigate XSS by encoding output, validating input, and using Content Security Policy headers.",
        priority=RemediationPriority.HIGH,
        steps=[
            RemediationStep(
                type=RemediationType.CONFIG,
                title="Add Content-Security-Policy header (Nginx)",
                language="nginx",
                filename="/etc/nginx/conf.d/security-headers.conf",
                description="CSP prevents inline script execution.",
                content="""add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none';" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;""",
            ),
            RemediationStep(
                type=RemediationType.CODE,
                title="Output encoding (Python/Jinja2)",
                language="python",
                description="Ensure all user input is HTML-escaped before rendering.",
                content="""from markupsafe import escape

# In Jinja2 templates, autoescaping is on by default:
#   {{ user_input }}          ← auto-escaped
#   {{ user_input | safe }}   ← DANGEROUS — avoid unless trusted

# In Python code:
safe_output = escape(user_input)""",
            ),
            RemediationStep(
                type=RemediationType.CODE,
                title="Output encoding (JavaScript)",
                language="javascript",
                description="Use textContent instead of innerHTML for user data.",
                content="""// VULNERABLE:
// element.innerHTML = userData;

// SECURE — use textContent:
element.textContent = userData;

// If HTML is needed, use a sanitizer:
// import DOMPurify from 'dompurify';
// element.innerHTML = DOMPurify.sanitize(userData);""",
            ),
        ],
        references=[
            "https://owasp.org/www-community/attacks/xss/",
            "https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html",
        ],
    )


# ── Command Injection ────────────────────────────────────────────────────────

@_rule(r"command\s*inject|os\s*command|shell\s*inject|rce|remote\s*code\s*exec")
def _remediate_cmd_injection(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "Command Injection"),
        finding_severity=finding.get("severity", "Critical"),
        summary="Prevent command injection by avoiding shell calls, using safe APIs, and validating input.",
        priority=RemediationPriority.IMMEDIATE,
        steps=[
            RemediationStep(
                type=RemediationType.CODE,
                title="Use subprocess safely (Python)",
                language="python",
                description="Never use shell=True with user input.",
                content="""import subprocess, shlex

# VULNERABLE:
# os.system(f"ping {user_input}")
# subprocess.call(f"ping {user_input}", shell=True)

# SECURE — use list arguments without shell=True:
result = subprocess.run(
    ["ping", "-c", "4", validated_host],
    capture_output=True, text=True, timeout=10
)""",
            ),
            RemediationStep(
                type=RemediationType.CODE,
                title="Input validation",
                language="python",
                description="Whitelist allowed characters / values.",
                content="""import re

def validate_hostname(host: str) -> bool:
    \"\"\"Allow only valid hostnames/IPs.\"\"\"
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9\\-\\.]{0,253}[a-zA-Z0-9]$'
    return bool(re.match(pattern, host))

# Reject any input that doesn't pass validation
if not validate_hostname(user_input):
    raise ValueError("Invalid hostname")""",
            ),
        ],
        references=[
            "https://owasp.org/www-community/attacks/Command_Injection",
            "https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html",
        ],
    )


# ── Open Ports / Unnecessary Services ────────────────────────────────────────

@_rule(r"open\s*port|unnecessary\s*service|exposed\s*port|unneeded.*service|port\s*\d+\s*open")
def _remediate_open_ports(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "Open Ports / Unnecessary Services"),
        finding_severity=finding.get("severity", "Medium"),
        summary="Close unnecessary ports and disable unused services to reduce the attack surface.",
        priority=_severity_to_priority(finding.get("severity", "Medium")),
        steps=[
            RemediationStep(
                type=RemediationType.COMMAND,
                title="Identify and stop unnecessary services",
                language="bash",
                description="List listening services and disable unneeded ones.",
                content="""# List all listening ports
sudo ss -tulnp

# Disable and stop an unnecessary service (e.g., telnet)
sudo systemctl disable --now telnet.socket
sudo systemctl disable --now rpcbind

# Remove unnecessary packages
sudo apt purge telnetd rsh-server -y""",
            ),
            RemediationStep(
                type=RemediationType.COMMAND,
                title="Configure firewall (UFW)",
                language="bash",
                description="Allow only required ports.",
                content="""# Enable UFW and set default deny
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow only needed services
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable""",
            ),
            RemediationStep(
                type=RemediationType.COMMAND,
                title="Configure firewall (iptables)",
                language="bash",
                description="Drop traffic to unnecessary ports.",
                content="""# Drop all incoming by default
sudo iptables -P INPUT DROP
sudo iptables -P FORWARD DROP

# Allow established connections
sudo iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow loopback
sudo iptables -A INPUT -i lo -j ACCEPT

# Allow specific ports
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Save rules
sudo netfilter-persistent save""",
            ),
        ],
        references=[
            "https://www.cisecurity.org/benchmark",
            "https://www.nist.gov/cyberframework",
        ],
    )


# ── Weak / Default Credentials ──────────────────────────────────────────────

@_rule(r"weak.*password|default.*cred|brute.?force|weak.*auth|default.*password|password.*policy")
def _remediate_weak_creds(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "Weak Credentials"),
        finding_severity=finding.get("severity", "High"),
        summary="Enforce strong password policies, change all default credentials, and implement MFA.",
        priority=RemediationPriority.HIGH,
        steps=[
            RemediationStep(
                type=RemediationType.COMMAND,
                title="Enforce password complexity (Linux PAM)",
                language="bash",
                description="Configure PAM to require strong passwords.",
                content="""# Install password quality module
sudo apt install libpam-pwquality -y

# Configure password requirements
sudo tee /etc/security/pwquality.conf << 'EOF'
minlen = 14
dcredit = -1
ucredit = -1
lcredit = -1
ocredit = -1
maxrepeat = 3
dictcheck = 1
EOF""",
            ),
            RemediationStep(
                type=RemediationType.CONFIG,
                title="Enforce SSH key-based authentication",
                language="bash",
                filename="/etc/ssh/sshd_config",
                description="Disable password auth and require SSH keys.",
                content="""# Disable password authentication
PasswordAuthentication no
ChallengeResponseAuthentication no
UsePAM yes

# Allow only key-based auth
PubkeyAuthentication yes
AuthenticationMethods publickey

# Restart SSH
# sudo systemctl restart sshd""",
            ),
        ],
        references=[
            "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html",
            "https://pages.nist.gov/800-63-3/sp800-63b.html",
        ],
    )


# ── SSL/TLS Issues ──────────────────────────────────────────────────────────

@_rule(r"ssl|tls|certificate|cipher|heartbleed|poodle|beast|weak.*crypto|expired.*cert|self.?signed")
def _remediate_ssl(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "SSL/TLS Misconfiguration"),
        finding_severity=finding.get("severity", "High"),
        summary="Harden TLS configuration: use TLS 1.2+, strong ciphers, and valid certificates.",
        priority=RemediationPriority.HIGH,
        steps=[
            RemediationStep(
                type=RemediationType.CONFIG,
                title="Harden Nginx TLS configuration",
                language="nginx",
                filename="/etc/nginx/conf.d/ssl.conf",
                description="Enforce modern TLS with strong ciphers.",
                content="""ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers on;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:10m;
ssl_session_tickets off;
ssl_stapling on;
ssl_stapling_verify on;
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;""",
            ),
            RemediationStep(
                type=RemediationType.CONFIG,
                title="Harden Apache TLS configuration",
                language="apache",
                filename="/etc/apache2/conf-available/ssl-hardening.conf",
                description="Disable weak protocols and ciphers.",
                content="""SSLProtocol -all +TLSv1.2 +TLSv1.3
SSLCipherSuite ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384
SSLHonorCipherOrder on
SSLCompression off
SSLSessionTickets off
Header always set Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" """,
            ),
            RemediationStep(
                type=RemediationType.COMMAND,
                title="Obtain a valid certificate (Let's Encrypt)",
                language="bash",
                description="Replace self-signed or expired certificates.",
                content="""# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renew
sudo certbot renew --dry-run""",
            ),
        ],
        references=[
            "https://ssl-config.mozilla.org/",
            "https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html",
        ],
    )


# ── Missing Security Headers ────────────────────────────────────────────────

@_rule(r"missing.*header|security\s*header|x-frame|x-content|hsts|strict.?transport|clickjack|content.?security.?policy")
def _remediate_headers(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "Missing Security Headers"),
        finding_severity=finding.get("severity", "Medium"),
        summary="Add essential HTTP security headers to protect against common web attacks.",
        priority=RemediationPriority.MEDIUM,
        steps=[
            RemediationStep(
                type=RemediationType.CONFIG,
                title="Add security headers (Nginx)",
                language="nginx",
                filename="/etc/nginx/conf.d/security-headers.conf",
                content="""add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';" always;""",
            ),
            RemediationStep(
                type=RemediationType.CONFIG,
                title="Add security headers (Apache)",
                language="apache",
                filename="/etc/apache2/conf-available/security-headers.conf",
                content="""Header always set X-Frame-Options "DENY"
Header always set X-Content-Type-Options "nosniff"
Header always set X-XSS-Protection "1; mode=block"
Header always set Referrer-Policy "strict-origin-when-cross-origin"
Header always set Permissions-Policy "camera=(), microphone=(), geolocation=()"
Header always set Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"

# Enable: sudo a2enconf security-headers && sudo systemctl reload apache2""",
            ),
            RemediationStep(
                type=RemediationType.CODE,
                title="Add security headers (Express.js / Node)",
                language="javascript",
                description="Use the helmet middleware.",
                content="""const helmet = require('helmet');
const app = require('express')();

app.use(helmet());  // Sets all security headers automatically

// Or configure individually:
app.use(helmet.frameguard({ action: 'deny' }));
app.use(helmet.contentSecurityPolicy({
  directives: { defaultSrc: ["'self'"], scriptSrc: ["'self'"] }
}));""",
            ),
        ],
        references=[
            "https://owasp.org/www-project-secure-headers/",
            "https://securityheaders.com/",
        ],
    )


# ── Directory Traversal / Path Traversal ─────────────────────────────────────

@_rule(r"directory.*travers|path.*travers|local.*file.*inclu|lfi|\.\.\/|file.*inclusion")
def _remediate_path_traversal(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "Path Traversal"),
        finding_severity=finding.get("severity", "High"),
        summary="Prevent path traversal by validating file paths and using chroot/jail mechanisms.",
        priority=RemediationPriority.HIGH,
        steps=[
            RemediationStep(
                type=RemediationType.CODE,
                title="Validate file paths (Python)",
                language="python",
                content="""import os
from pathlib import Path

ALLOWED_DIR = Path("/var/www/uploads").resolve()

def safe_file_access(user_path: str) -> Path:
    \"\"\"Prevent path traversal by resolving and validating paths.\"\"\"
    requested = (ALLOWED_DIR / user_path).resolve()
    if not str(requested).startswith(str(ALLOWED_DIR)):
        raise ValueError("Path traversal detected")
    return requested""",
            ),
            RemediationStep(
                type=RemediationType.CONFIG,
                title="Restrict access in Nginx",
                language="nginx",
                description="Block path traversal patterns.",
                content="""# Block path traversal attempts
location ~ \\.\\. {
    deny all;
    return 403;
}

# Restrict to specific directory
location /uploads/ {
    alias /var/www/uploads/;
    autoindex off;
}""",
            ),
        ],
        references=[
            "https://owasp.org/www-community/attacks/Path_Traversal",
            "https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html",
        ],
    )


# ── CSRF ─────────────────────────────────────────────────────────────────────

@_rule(r"csrf|cross.?site\s*request\s*forg")
def _remediate_csrf(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "Cross-Site Request Forgery (CSRF)"),
        finding_severity=finding.get("severity", "Medium"),
        summary="Implement CSRF tokens and SameSite cookie attributes.",
        priority=RemediationPriority.MEDIUM,
        steps=[
            RemediationStep(
                type=RemediationType.CODE,
                title="CSRF protection (Python/Flask)",
                language="python",
                description="Use Flask-WTF for automatic CSRF protection.",
                content="""from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.secret_key = os.urandom(32)
csrf = CSRFProtect(app)

# In templates, include the token:
# <input type=\"hidden\" name=\"csrf_token\" value=\"{{ csrf_token() }}\">""",
            ),
            RemediationStep(
                type=RemediationType.CODE,
                title="SameSite cookies (Express.js)",
                language="javascript",
                content="""app.use(session({
  cookie: {
    sameSite: 'strict',  // or 'lax'
    secure: true,
    httpOnly: true,
  }
}));""",
            ),
        ],
        references=[
            "https://owasp.org/www-community/attacks/csrf",
            "https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html",
        ],
    )


# ── SSH Misconfigurations ────────────────────────────────────────────────────

@_rule(r"ssh.*misconfig|ssh.*weak|openssh.*vuln|ssh.*root|ssh.*permit|ssh.*password")
def _remediate_ssh(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "SSH Misconfiguration"),
        finding_severity=finding.get("severity", "High"),
        summary="Harden SSH configuration: disable root login, use key-based auth, restrict access.",
        priority=RemediationPriority.HIGH,
        steps=[
            RemediationStep(
                type=RemediationType.CONFIG,
                title="Harden sshd_config",
                language="bash",
                filename="/etc/ssh/sshd_config",
                content="""# Disable root login
PermitRootLogin no

# Disable password authentication
PasswordAuthentication no

# Use only SSHv2
Protocol 2

# Limit authentication attempts
MaxAuthTries 3
LoginGraceTime 30

# Disable empty passwords
PermitEmptyPasswords no

# Restrict to specific users/groups
AllowGroups sshusers

# Use strong key exchange and ciphers
KexAlgorithms curve25519-sha256@libssh.org,diffie-hellman-group-exchange-sha256
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com""",
            ),
            RemediationStep(
                type=RemediationType.COMMAND,
                title="Apply and verify SSH changes",
                language="bash",
                content="""# Validate config before restart
sudo sshd -t

# Restart SSH
sudo systemctl restart sshd

# Verify settings
sudo sshd -T | grep -E 'permitrootlogin|passwordauthentication|maxauthtries'""",
            ),
        ],
        references=[
            "https://www.ssh.com/academy/ssh/sshd_config",
            "https://www.cisecurity.org/benchmark/distribution_independent_linux",
        ],
    )


# ── Information Disclosure ───────────────────────────────────────────────────

@_rule(r"info.*disclos|server.*version|version.*disclos|banner.*grab|sensitive.*info.*expos|directory.*listing|stack\s*trace")
def _remediate_info_disclosure(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "Information Disclosure"),
        finding_severity=finding.get("severity", "Low"),
        summary="Suppress server version banners, disable directory listings, and remove debug endpoints.",
        priority=_severity_to_priority(finding.get("severity", "Low")),
        steps=[
            RemediationStep(
                type=RemediationType.CONFIG,
                title="Hide server version (Nginx)",
                language="nginx",
                filename="/etc/nginx/nginx.conf",
                content="""# In http block:
server_tokens off;
# Optionally add:
# more_clear_headers Server;""",
            ),
            RemediationStep(
                type=RemediationType.CONFIG,
                title="Hide server version (Apache)",
                language="apache",
                filename="/etc/apache2/conf-available/security.conf",
                content="""ServerTokens Prod
ServerSignature Off
TraceEnable Off""",
            ),
            RemediationStep(
                type=RemediationType.COMMAND,
                title="Disable directory listing",
                language="bash",
                content="""# Nginx — remove autoindex
# autoindex off;  (default, but ensure it's not 'on')

# Apache — remove Indexes option
sudo sed -i 's/Options Indexes/Options -Indexes/' /etc/apache2/apache2.conf
sudo systemctl reload apache2""",
            ),
        ],
        references=[
            "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/01-Information_Gathering/",
        ],
    )


# ── Outdated Software / Known CVEs ──────────────────────────────────────────

@_rule(r"outdated|end.?of.?life|eol|unpatched|cve-\d{4}|known.*vuln|update.*required|upgrade.*required")
def _remediate_outdated(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "Outdated Software"),
        finding_severity=finding.get("severity", "High"),
        summary="Update affected software to the latest patched version.",
        priority=RemediationPriority.HIGH,
        steps=[
            RemediationStep(
                type=RemediationType.COMMAND,
                title="Update system packages",
                language="bash",
                content="""# Debian/Ubuntu
sudo apt update && sudo apt upgrade -y

# RHEL/CentOS/Rocky
sudo dnf update -y

# Check for security updates only (Debian)
sudo apt list --upgradable 2>/dev/null | grep -i security""",
            ),
            RemediationStep(
                type=RemediationType.COMMAND,
                title="Update specific software",
                language="bash",
                description="Replace <package> with the affected software.",
                content="""# Check installed version
dpkg -l | grep <package>
# or
rpm -qa | grep <package>

# Update specific package
sudo apt install --only-upgrade <package>
# or
sudo dnf update <package>""",
            ),
            RemediationStep(
                type=RemediationType.COMMAND,
                title="Enable automatic security updates",
                language="bash",
                content="""# Debian/Ubuntu — enable unattended upgrades
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure -plow unattended-upgrades""",
            ),
        ],
        references=[
            "https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
            "https://nvd.nist.gov/",
        ],
    )


# ── CORS Misconfiguration ───────────────────────────────────────────────────

@_rule(r"cors|cross.?origin|access.?control.?allow|origin.*wildcard")
def _remediate_cors(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "CORS Misconfiguration"),
        finding_severity=finding.get("severity", "Medium"),
        summary="Restrict CORS to specific trusted origins instead of wildcard or reflected origins.",
        priority=RemediationPriority.MEDIUM,
        steps=[
            RemediationStep(
                type=RemediationType.CONFIG,
                title="Fix CORS in Nginx",
                language="nginx",
                content="""# Allow specific origins only (not wildcard *)
set $cors_origin "";
if ($http_origin ~* "^https://(www\\.)?yourdomain\\.com$") {
    set $cors_origin $http_origin;
}
add_header Access-Control-Allow-Origin $cors_origin always;
add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
add_header Access-Control-Allow-Credentials "true" always;""",
            ),
            RemediationStep(
                type=RemediationType.CODE,
                title="Fix CORS in Express.js",
                language="javascript",
                content="""const cors = require('cors');

// VULNERABLE: app.use(cors());  // allows all origins

// SECURE:
app.use(cors({
  origin: ['https://yourdomain.com', 'https://app.yourdomain.com'],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
}));""",
            ),
        ],
        references=[
            "https://owasp.org/www-community/attacks/CORS_OriginHeaderScrutiny",
            "https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS",
        ],
    )


# ── IDOR / Broken Access Control ─────────────────────────────────────────────

@_rule(r"idor|insecure.*direct.*object|broken.*access.*control|privilege.*escalat|unauthorized.*access|access.*control")
def _remediate_idor(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "Broken Access Control"),
        finding_severity=finding.get("severity", "High"),
        summary="Implement proper authorization checks on every endpoint and use indirect object references.",
        priority=RemediationPriority.HIGH,
        steps=[
            RemediationStep(
                type=RemediationType.CODE,
                title="Authorization middleware (Python/Flask)",
                language="python",
                content="""from functools import wraps
from flask import abort, g

def require_owner(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        resource = get_resource(kwargs['resource_id'])
        if resource.owner_id != g.current_user.id:
            abort(403)
        return f(*args, **kwargs)
    return decorated

@app.route('/api/documents/<resource_id>')
@require_owner
def get_document(resource_id):
    # User can only access their own documents
    ...""",
            ),
            RemediationStep(
                type=RemediationType.CODE,
                title="Use indirect references",
                language="python",
                description="Map internal IDs to per-user tokens.",
                content="""import secrets

# Instead of: /api/invoice/12345 (sequential, guessable)
# Use: /api/invoice/a7f3b2c9e1d4 (random token per user)

def create_indirect_ref(user_id: int, internal_id: int) -> str:
    token = secrets.token_urlsafe(16)
    cache.set(f"ref:{user_id}:{token}", internal_id, timeout=3600)
    return token""",
            ),
        ],
        references=[
            "https://owasp.org/Top10/A01_2021-Broken_Access_Control/",
            "https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html",
        ],
    )


# ── File Upload Vulnerabilities ──────────────────────────────────────────────

@_rule(r"file\s*upload|unrestrict.*upload|malicious.*upload|upload.*vuln|webshell")
def _remediate_upload(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "Unrestricted File Upload"),
        finding_severity=finding.get("severity", "High"),
        summary="Validate file types, scan uploads, and store files outside the webroot.",
        priority=RemediationPriority.HIGH,
        steps=[
            RemediationStep(
                type=RemediationType.CODE,
                title="Validate uploads (Python/Flask)",
                language="python",
                content="""import magic
from pathlib import Path

ALLOWED_MIME = {'image/jpeg', 'image/png', 'image/gif', 'application/pdf'}
ALLOWED_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.pdf'}
MAX_SIZE = 10 * 1024 * 1024  # 10 MB
UPLOAD_DIR = Path('/var/uploads')  # Outside webroot!

def validate_upload(file):
    # Check extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise ValueError(f"Extension {ext} not allowed")
    # Check file size
    file.seek(0, 2)
    if file.tell() > MAX_SIZE:
        raise ValueError("File too large")
    file.seek(0)
    # Check actual MIME type (not just header)
    mime = magic.from_buffer(file.read(2048), mime=True)
    file.seek(0)
    if mime not in ALLOWED_MIME:
        raise ValueError(f"MIME type {mime} not allowed")""",
            ),
            RemediationStep(
                type=RemediationType.CONFIG,
                title="Restrict uploads in Nginx",
                language="nginx",
                content="""# Limit upload size
client_max_body_size 10m;

# Disable script execution in upload directory
location /uploads/ {
    location ~ \\.(php|py|pl|cgi|sh|asp|aspx|jsp)$ {
        deny all;
    }
}""",
            ),
        ],
        references=[
            "https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload",
            "https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html",
        ],
    )


# ── XML External Entity (XXE) ───────────────────────────────────────────────

@_rule(r"xxe|xml.*external.*entity|xml.*inject|xml.*parse")
def _remediate_xxe(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "XML External Entity (XXE)"),
        finding_severity=finding.get("severity", "High"),
        summary="Disable external entity processing in XML parsers.",
        priority=RemediationPriority.HIGH,
        steps=[
            RemediationStep(
                type=RemediationType.CODE,
                title="Disable XXE (Python)",
                language="python",
                content="""import defusedxml.ElementTree as ET

# VULNERABLE: xml.etree.ElementTree.parse(user_input)
# SECURE:
tree = ET.parse(user_input)  # defusedxml blocks XXE by default

# Or with lxml:
from lxml import etree
parser = etree.XMLParser(resolve_entities=False, no_network=True)
tree = etree.parse(user_input, parser)""",
            ),
            RemediationStep(
                type=RemediationType.CODE,
                title="Disable XXE (Java)",
                language="java",
                content="""DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
dbf.setXIncludeAware(false);
dbf.setExpandEntityReferences(false);""",
            ),
        ],
        references=[
            "https://owasp.org/www-community/vulnerabilities/XML_External_Entity_(XXE)_Processing",
            "https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html",
        ],
    )


# ── Server-Side Request Forgery (SSRF) ──────────────────────────────────────

@_rule(r"ssrf|server.?side\s*request\s*forg")
def _remediate_ssrf(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "Server-Side Request Forgery (SSRF)"),
        finding_severity=finding.get("severity", "High"),
        summary="Validate and restrict outbound requests to prevent SSRF attacks.",
        priority=RemediationPriority.HIGH,
        steps=[
            RemediationStep(
                type=RemediationType.CODE,
                title="URL validation (Python)",
                language="python",
                content="""import ipaddress
from urllib.parse import urlparse

BLOCKED_NETWORKS = [
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('169.254.0.0/16'),
]

def validate_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return False
    import socket
    ip = socket.gethostbyname(parsed.hostname)
    addr = ipaddress.ip_address(ip)
    for net in BLOCKED_NETWORKS:
        if addr in net:
            return False  # Block internal network access
    return True""",
            ),
        ],
        references=[
            "https://owasp.org/www-community/attacks/Server_Side_Request_Forgery",
            "https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html",
        ],
    )


# ── Insecure Deserialization ─────────────────────────────────────────────────

@_rule(r"deserializ|pickle|marshal|insecure.*serial|object.*inject")
def _remediate_deserialization(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "Insecure Deserialization"),
        finding_severity=finding.get("severity", "Critical"),
        summary="Avoid deserializing untrusted data; use safe formats like JSON instead of pickle/marshal.",
        priority=RemediationPriority.IMMEDIATE,
        steps=[
            RemediationStep(
                type=RemediationType.CODE,
                title="Replace pickle with JSON (Python)",
                language="python",
                content="""import json

# VULNERABLE:
# import pickle
# data = pickle.loads(user_input)  # RCE risk!

# SECURE:
data = json.loads(user_input)

# If you MUST use pickle, use restricted unpickler:
import pickle, io
class RestrictedUnpickler(pickle.Unpickler):
    ALLOWED = {'builtins': {'range', 'dict', 'list', 'set', 'tuple'}}
    def find_class(self, module, name):
        if module in self.ALLOWED and name in self.ALLOWED[module]:
            return getattr(__import__(module), name)
        raise pickle.UnpicklingError(f"Blocked: {module}.{name}")""",
            ),
        ],
        references=[
            "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/15-Testing_for_HTTP_Incoming_Requests",
            "https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html",
        ],
    )


# ── DNS Zone Transfer ────────────────────────────────────────────────────────

@_rule(r"dns.*zone\s*transfer|axfr|dns.*misconfig")
def _remediate_dns(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "DNS Zone Transfer"),
        finding_severity=finding.get("severity", "Medium"),
        summary="Restrict DNS zone transfers to authorized secondary nameservers only.",
        priority=RemediationPriority.MEDIUM,
        steps=[
            RemediationStep(
                type=RemediationType.CONFIG,
                title="Restrict zone transfers (BIND)",
                language="bash",
                filename="/etc/bind/named.conf.options",
                content="""options {
    allow-transfer { none; };     // Global default: deny all
    allow-query { any; };
};

// Per-zone: allow only secondary NS
zone "example.com" {
    type master;
    file "/etc/bind/db.example.com";
    allow-transfer { 192.168.1.2; };  // Secondary NS IP only
};""",
            ),
        ],
        references=[
            "https://www.cisecurity.org/benchmark/bind",
        ],
    )


# ── SNMP Community Strings ──────────────────────────────────────────────────

@_rule(r"snmp.*community|snmp.*public|snmp.*private|snmp.*default|snmp.*string")
def _remediate_snmp(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "SNMP Default Community String"),
        finding_severity=finding.get("severity", "High"),
        summary="Change default SNMP community strings and upgrade to SNMPv3 with authentication.",
        priority=RemediationPriority.HIGH,
        steps=[
            RemediationStep(
                type=RemediationType.CONFIG,
                title="Configure SNMPv3 (snmpd.conf)",
                language="bash",
                filename="/etc/snmp/snmpd.conf",
                content="""# Remove default community strings
# rocommunity public  ← DELETE THIS
# rwcommunity private ← DELETE THIS

# Use SNMPv3 with auth and encryption
createUser snmpMonitor SHA "StrongAuthPass!" AES "StrongPrivPass!"
rouser snmpMonitor priv

# Restrict access by IP
agentAddress udp:161
com2sec readonly  192.168.1.0/24  secret_community""",
            ),
            RemediationStep(
                type=RemediationType.COMMAND,
                title="Apply SNMP changes",
                language="bash",
                content="""sudo systemctl restart snmpd
# Verify with:
snmpwalk -v3 -u snmpMonitor -l authPriv -a SHA -A "StrongAuthPass!" -x AES -X "StrongPrivPass!" localhost""",
            ),
        ],
        references=[
            "https://www.cisecurity.org/benchmark",
        ],
    )


# ── Exposed Admin / Debug Panels ─────────────────────────────────────────────

@_rule(r"admin.*panel|debug.*mode|debug.*endpoint|exposed.*admin|phpinfo|phpmyadmin|management.*console|dashboard.*exposed")
def _remediate_admin_panels(finding: Dict, match) -> Remediation:
    return Remediation(
        finding_title=finding.get("title", "Exposed Admin/Debug Panel"),
        finding_severity=finding.get("severity", "High"),
        summary="Restrict access to admin and debug endpoints; disable debug mode in production.",
        priority=RemediationPriority.HIGH,
        steps=[
            RemediationStep(
                type=RemediationType.CONFIG,
                title="Restrict admin access (Nginx)",
                language="nginx",
                content="""# Block admin panels from public access
location ~ ^/(admin|phpmyadmin|wp-admin|debug|server-status|server-info) {
    allow 10.0.0.0/8;      # Internal network only
    allow 192.168.0.0/16;
    deny all;
}""",
            ),
            RemediationStep(
                type=RemediationType.COMMAND,
                title="Disable debug mode",
                language="bash",
                content="""# Django — set in settings.py or env:
# DEBUG = False
# ALLOWED_HOSTS = ['yourdomain.com']

# Flask — never run with debug in production:
# app.run(debug=False)

# Remove phpinfo files:
sudo find /var/www -name 'phpinfo.php' -delete
sudo find /var/www -name 'info.php' -delete""",
            ),
        ],
        references=[
            "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/",
        ],
    )


# ── Compile Rules ────────────────────────────────────────────────────────────

_COMPILED_RULES: List[Tuple[re.Pattern, Callable]] = []


def _compile_rules() -> None:
    """Compile all rule patterns (lazy, on first use)."""
    if _COMPILED_RULES:
        return
    _COMPILED_RULES.extend(
        (re.compile(pattern, re.IGNORECASE), fn)
        for pattern, fn in _RULES
    )


# ── Remediation Engine ───────────────────────────────────────────────────────

class RemediationEngine:
    """
    Generates remediation guidance for security findings.

    Two strategies:
    1. Rule-based (instant, no API) — matches finding title/description
       against built-in vulnerability patterns.
    2. AI-enhanced (optional) — Falls back to an LLM for tailored fixes
       when no rule matches or when --ai flag is used.
    """

    def __init__(self, ai_engine: Optional[Any] = None):
        """
        Args:
            ai_engine: Optional AIEngine instance for AI-enhanced remediation.
        """
        _compile_rules()
        self.ai_engine = ai_engine

    # ── Rule-Based Remediation ───────────────────────────────────────────

    def remediate_finding(self, finding: Dict[str, Any], use_ai: bool = False) -> Remediation:
        """
        Generate remediation for a single finding.

        Args:
            finding: Finding dict with title, severity, description, etc.
            use_ai: Force AI-enhanced remediation even if rules match.

        Returns:
            Remediation object with fix steps.
        """
        title = finding.get("title", "")
        desc = finding.get("description", "")
        search_text = f"{title} {desc}"

        # Try rule-based first
        if not use_ai:
            for pattern, builder in _COMPILED_RULES:
                m = pattern.search(search_text)
                if m:
                    try:
                        rem = builder(finding, m)
                        if isinstance(rem, Remediation):
                            return rem
                    except Exception as e:
                        logger.warning(f"Rule failed for '{title}': {e}")

        # AI-enhanced fallback
        if self.ai_engine:
            return self._ai_remediate(finding)

        # Generic fallback
        return self._generic_remediation(finding)

    def remediate_findings(
        self,
        findings: List[Dict[str, Any]],
        use_ai: bool = False,
    ) -> List[Remediation]:
        """Remediate a list of findings."""
        return [self.remediate_finding(f, use_ai=use_ai) for f in findings]

    # ── AI-Enhanced Remediation ──────────────────────────────────────────

    def _ai_remediate(self, finding: Dict[str, Any]) -> Remediation:
        """Use AI to generate tailored remediation."""
        if not self.ai_engine:
            return self._generic_remediation(finding)
        prompt = self._build_ai_prompt(finding)
        try:
            from hackbot.core.engine import Conversation, Message
            conv = Conversation(messages=[Message(role="user", content=prompt)])
            response = self.ai_engine.chat(
                conv,
                stream=False,
            )
            return self._parse_ai_response(finding, response)
        except Exception as e:
            logger.error(f"AI remediation failed: {e}")
            return self._generic_remediation(finding)

    @staticmethod
    def _build_ai_prompt(finding: Dict[str, Any]) -> str:
        """Build a prompt for AI-enhanced remediation."""
        return f"""You are a cybersecurity remediation expert. Generate specific, actionable fix guidance for this security finding.

**Finding:** {finding.get('title', 'Unknown')}
**Severity:** {finding.get('severity', 'Unknown')}
**Description:** {finding.get('description', 'No description')}
**Evidence:** {finding.get('evidence', 'None')}
**Tool:** {finding.get('tool', 'Unknown')}

Provide your response in this exact format:

SUMMARY: <one-sentence fix description>

COMMAND:
<title>: <title of the command step>
<description>: <brief description>
<language>: bash
```
<shell commands to fix the issue>
```

CONFIG:
<title>: <title of the config step>
<filename>: <config file path>
<language>: <config type>
```
<config patch content>
```

CODE:
<title>: <title of the code step>
<language>: <programming language>
```
<code snippet to fix>
```

REFERENCES:
- <relevant URL 1>
- <relevant URL 2>

Include at least one COMMAND and one CODE or CONFIG section. Be specific to the actual finding — don't give generic advice. Use real file paths and real commands."""

    @staticmethod
    def _parse_ai_response(finding: Dict[str, Any], response: str) -> Remediation:
        """Parse AI response into structured Remediation."""
        steps = []
        references = []
        summary = ""

        # Extract summary
        summary_match = re.search(r'SUMMARY:\s*(.+?)(?:\n\n|\nCOMMAND|\nCONFIG|\nCODE|\nREFERENCES)', response, re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()

        # Extract code blocks with their section context
        sections = re.split(r'\n(COMMAND|CONFIG|CODE|REFERENCES):', response)

        current_type = None
        for i, section in enumerate(sections):
            section_stripped = section.strip()
            if section_stripped in ('COMMAND', 'CONFIG', 'CODE'):
                current_type = section_stripped
                continue
            if section_stripped == 'REFERENCES':
                current_type = 'REFERENCES'
                # Extract reference URLs
                if i + 1 < len(sections):
                    ref_matches = re.findall(r'-\s*(https?://\S+)', sections[i + 1])
                    references.extend(ref_matches)
                continue

            if current_type in ('COMMAND', 'CONFIG', 'CODE') and section_stripped:
                rtype = {
                    'COMMAND': RemediationType.COMMAND,
                    'CONFIG': RemediationType.CONFIG,
                    'CODE': RemediationType.CODE,
                }.get(current_type, RemediationType.COMMAND)

                # Extract title
                title_match = re.search(r'<title>:\s*(.+)', section)
                title = title_match.group(1).strip() if title_match else f"{current_type.title()} Fix"

                # Extract description
                desc_match = re.search(r'<description>:\s*(.+)', section)
                desc = desc_match.group(1).strip() if desc_match else ""

                # Extract language
                lang_match = re.search(r'<language>:\s*(.+)', section)
                lang = lang_match.group(1).strip() if lang_match else ("bash" if rtype == RemediationType.COMMAND else "")

                # Extract filename
                file_match = re.search(r'<filename>:\s*(.+)', section)
                filename = file_match.group(1).strip() if file_match else ""

                # Extract code block
                code_match = re.search(r'```\w*\n(.*?)```', section, re.DOTALL)
                content = code_match.group(1).strip() if code_match else section_stripped[:500]

                steps.append(RemediationStep(
                    type=rtype,
                    title=title,
                    content=content,
                    language=lang,
                    filename=filename,
                    description=desc,
                ))

        # Extract references from the end if not found yet
        if not references:
            ref_matches = re.findall(r'-\s*(https?://\S+)', response)
            references = ref_matches[:5]

        if not summary:
            summary = f"AI-generated remediation for: {finding.get('title', 'Unknown')}"

        return Remediation(
            finding_title=finding.get("title", "Unknown"),
            finding_severity=finding.get("severity", "Unknown"),
            summary=summary,
            priority=_severity_to_priority(finding.get("severity", "Medium")),
            steps=steps or [RemediationStep(
                type=RemediationType.REFERENCE,
                title="AI Guidance",
                content=response[:2000],
                description="Full AI-generated remediation guidance.",
            )],
            references=references,
            source="ai",
            confidence=0.8,
        )

    # ── Generic Fallback ─────────────────────────────────────────────────

    @staticmethod
    def _generic_remediation(finding: Dict[str, Any]) -> Remediation:
        """Fallback remediation when no rule matches and AI is unavailable."""
        severity = finding.get("severity", "Medium")
        title = finding.get("title", "Security Finding")
        recommendation = finding.get("recommendation", "")

        steps = []
        if recommendation:
            steps.append(RemediationStep(
                type=RemediationType.REFERENCE,
                title="Original Recommendation",
                content=recommendation,
                description="Recommendation from the assessment tool.",
            ))

        steps.append(RemediationStep(
            type=RemediationType.REFERENCE,
            title="General Guidance",
            content=f"""1. Research "{title}" in the OWASP Testing Guide and NVD
2. Apply vendor-recommended patches or workarounds
3. Implement defense-in-depth controls:
   - Network segmentation and firewall rules
   - Input validation and output encoding
   - Least-privilege access controls
   - Monitoring and alerting
4. Verify the fix with a targeted re-test
5. Document the remediation in your risk register""",
            description="Follow these steps when a specific remediation is not available.",
        ))

        return Remediation(
            finding_title=title,
            finding_severity=severity,
            summary=f"Review and apply vendor-recommended fixes for: {title}",
            priority=_severity_to_priority(severity),
            steps=steps,
            references=[
                "https://owasp.org/www-project-web-security-testing-guide/",
                "https://nvd.nist.gov/",
            ],
            source="generic",
            confidence=0.3,
        )

    # ── Batch Summary ────────────────────────────────────────────────────

    @staticmethod
    def get_summary_markdown(remediations: List[Remediation]) -> str:
        """Generate a combined markdown report for all remediations."""
        if not remediations:
            return "No remediations generated.\n"

        lines = ["# 🔧 Remediation Report\n"]

        # Priority summary
        by_priority: Dict[str, int] = {}
        for r in remediations:
            by_priority[r.priority.value] = by_priority.get(r.priority.value, 0) + 1
        lines.append("## Priority Summary\n")
        for p in ["immediate", "high", "medium", "low", "informational"]:
            if p in by_priority:
                icon = {"immediate": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "informational": "⚪"}.get(p, "•")
                lines.append(f"- {icon} **{p.upper()}:** {by_priority[p]} findings")
        lines.append("")

        # Stats
        total_steps = sum(len(r.steps) for r in remediations)
        cmd_count = sum(1 for r in remediations for s in r.steps if s.type == RemediationType.COMMAND)
        cfg_count = sum(1 for r in remediations for s in r.steps if s.type == RemediationType.CONFIG)
        code_count = sum(1 for r in remediations for s in r.steps if s.type == RemediationType.CODE)
        lines.append(f"**Total:** {len(remediations)} findings → {total_steps} fix steps "
                      f"({cmd_count} commands, {cfg_count} configs, {code_count} code snippets)\n")
        lines.append("---\n")

        # Individual remediations
        for r in remediations:
            lines.append(r.get_markdown())
            lines.append("---\n")

        return "\n".join(lines)

    # ── Utilities ────────────────────────────────────────────────────────

    @staticmethod
    def get_rule_count() -> int:
        """Return the number of built-in remediation rules."""
        return len(_RULES)

    @staticmethod
    def get_rule_patterns() -> List[str]:
        """Return all rule patterns (for debugging/testing)."""
        return [p for p, _ in _RULES]
