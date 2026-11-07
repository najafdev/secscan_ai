# Security Policy

<div align="center">

**HackBot is an offensive security tool designed for authorized penetration testing.**

This document outlines HackBot's security model, built-in safeguards, responsible usage policy, and vulnerability disclosure process.

</div>

---

## ⚠️ Responsible Usage

HackBot is a **dual-use cybersecurity tool**. It is built for legitimate security professionals to perform authorized penetration testing, vulnerability assessments, and security research.

### Legal Requirements

> **You are solely responsible for how you use HackBot.**

Before using HackBot against any target, you **MUST** have:

| Requirement | Description |
|-------------|-------------|
| ✅ **Written authorization** | A signed scope agreement or contract from the target owner |
| ✅ **Defined scope** | A clear list of in-scope targets, IP ranges, and domains |
| ✅ **Rules of engagement** | Agreed limitations on testing (hours, intensity, off-limits systems) |
| ✅ **Legal compliance** | Compliance with all applicable laws (CFAA, Computer Misuse Act, etc.) |
| ✅ **Incident plan** | A procedure for handling any unintended damage or data exposure |

### Prohibited Uses

HackBot **must NOT** be used for:

- 🚫 Unauthorized access to systems, networks, or data
- 🚫 Attacking targets without explicit written permission
- 🚫 Launching denial-of-service attacks against production systems
- 🚫 Exfiltrating sensitive data from systems you do not own
- 🚫 Creating, distributing, or deploying malware
- 🚫 Violating any local, national, or international laws

**Violation of these terms may result in criminal prosecution.** The HackBot developers assume no liability for misuse.

---

## 🛡️ Built-in Security Safeguards

HackBot includes multiple layers of protection to prevent accidental damage and misuse.

### Command Validation & Blocking

| Safeguard | Description |
|-----------|-------------|
| **Blocked Commands** | Destructive system commands are permanently blocked: `rm -rf /`, `mkfs`, `dd if=/dev/zero`, fork bombs, `shutdown`, `reboot`, etc. |
| **Risky Command Warnings** | Patterns like `rm -rf`, `exploit`, `payload`, `reverse_tcp`, `meterpreter`, `nc -e` trigger confirmation prompts before execution |
| **Safe Mode** | Enabled by default — prevents highly aggressive or destructive scans without explicit user confirmation |
| **Tool Allowlist** | Only pre-approved security tools can be executed — arbitrary binaries are rejected |
| **Sudo Control** | Sudo is handled by the system, not by the AI — prevents privilege escalation from AI hallucination |

### Agent Guardrails

| Safeguard | Description |
|-----------|-------------|
| **Command normalization** | AI-generated commands are cleaned and validated before execution |
| **Double-sudo prevention** | Strips any AI-injected `sudo` prefix — sudo is applied only by the system layer |
| **Output truncation** | Command output is capped at 100KB to prevent memory exhaustion |
| **Timeout enforcement** | All tool executions have a configurable timeout (default: 300s) with process kill on expiry |
| **Environment sanitization** | API keys (`HACKBOT_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) are stripped from subprocess environments |

### Zero-Day Engine Safeguards

| Safeguard | Description |
|-----------|-------------|
| **Same-domain crawling** | Target mapper is restricted to the initial target domain by default |
| **Crawl limits** | Maximum 100 pages and depth of 3 by default |
| **Concurrency cap** | Parallel executor limited to 10 threads to avoid overwhelming targets |
| **Request delays** | Configurable delay between requests (default: 100ms) to avoid triggering rate limits |
| **Iteration limits** | Active scan loop capped at 20 iterations by default |
| **Fuzz limits** | Maximum 50 payloads per parameter by default |
| **Stop mechanism** | Active scans can be stopped immediately via `stop()` method or GUI button |

---

## 🔐 API Key & Credential Security

### Storage

| Item | Location | Protection |
|------|----------|------------|
| API keys | `~/.config/hackbot/config.yaml` | File-system permissions only |
| Session data | `~/.config/hackbot/sessions/` | File-system permissions only |
| Vulnerability DB | `~/.config/hackbot/vulndb.sqlite` | File-system permissions only |
| Execution logs | `~/.config/hackbot/logs/` | File-system permissions only |

### Recommendations

1. **Never commit API keys** to version control — use environment variables or the config file
2. **Restrict config permissions**: `chmod 600 ~/.config/hackbot/config.yaml`
3. **Rotate API keys** regularly, especially after shared-machine usage
4. **Use separate API keys** for HackBot vs. production applications
5. **Docker deployments**: pass keys via `-e` flags, not Dockerfiles

### What HackBot Does NOT Do

- ❌ Does **not** send API keys to any server other than the configured AI provider
- ❌ Does **not** collect telemetry, analytics, or usage data
- ❌ Does **not** phone home or check for updates automatically
- ❌ Does **not** store credentials from target systems (intercepted creds appear only in session output)
- ❌ Does **not** exfiltrate any data from targets

---

## 🔒 Network Security

### HTTP Proxy / Traffic Capture

HackBot includes a built-in intercepting proxy. When active:

- Proxy binds to `127.0.0.1` only (localhost) — not externally accessible
- Intercepted traffic is stored in memory only (not persisted to disk unless explicitly exported)
- Auto-detects and flags sensitive data patterns (credentials, API keys, tokens)
- Domain scoping restricts capture to specified domains

### Zero-Day Active Scanner

The active scanning engine makes real HTTP requests:

- All requests include a `User-Agent: HackBot/2.0 ZeroDay-Scanner` header for identification
- SSL certificate verification is disabled by default (pentest context: self-signed certs are common)
- Proxy support allows routing all traffic through Burp Suite or similar tools for inspection
- Request rate limiting and delay controls prevent accidental DoS

---

## 🔍 Vulnerability Disclosure

### Reporting Security Issues in HackBot Itself

If you discover a security vulnerability **in HackBot's code**, please report it responsibly:

| Channel | Contact |
|---------|---------|
| 📧 **Email** (preferred) | [yashabalam707@gmail.com](mailto:yashabalam707@gmail.com) |
| 📧 **Alternate email** | [yashabalam9@gmail.com](mailto:yashabalam9@gmail.com) |
| 🐙 **GitHub Security Advisory** | [Create a private advisory](https://github.com/yashab-cyber/hackbot/security/advisories/new) |

### Disclosure Guidelines

1. **Do NOT open a public GitHub issue** for security vulnerabilities
2. Include a detailed description with steps to reproduce
3. Provide any proof-of-concept code if applicable
4. Allow **90 days** for the maintainer to develop and release a fix before public disclosure
5. Credit will be given to reporters in the release notes (unless anonymity is requested)

### Scope

The following are in scope for security reports:

| In Scope | Examples |
|----------|---------|
| ✅ Command injection via AI prompt manipulation | Adversarial prompts that bypass command validation |
| ✅ API key leakage | Keys exposed in logs, error messages, or subprocess environments |
| ✅ Arbitrary file read/write | Path traversal in report generation, session handling, or plugins |
| ✅ Privilege escalation | Bypassing safe_mode, sudo controls, or tool allowlist |
| ✅ Dependency vulnerabilities | Critical CVEs in direct dependencies |

The following are **out of scope**:

| Out of Scope | Reason |
|-------------|--------|
| ❌ Vulnerabilities in targets being tested | That's HackBot's purpose — report to the target owner |
| ❌ Social engineering of HackBot users | User responsibility |
| ❌ Attacks requiring physical access | Out of threat model |
| ❌ Denial of service against HackBot itself | Local tool, not a service |

---

## 🏗️ Security Architecture

### Execution Isolation

```
┌─────────────────────────────────────────────────────┐
│                   HackBot Process                    │
│                                                      │
│  ┌──────────────┐   ┌────────────────────────────┐  │
│  │  AI Engine   │   │    Tool Runner              │  │
│  │  (LLM calls) │──▶│  • Command validation      │  │
│  │              │   │  • Blocked command check    │  │
│  │  Generates   │   │  • Allowlist enforcement    │  │
│  │  action JSON │   │  • Safe mode checks        │  │
│  └──────────────┘   │  • User confirmation       │  │
│                      │           │                 │  │
│                      │           ▼                 │  │
│                      │  ┌────────────────────┐    │  │
│                      │  │ subprocess.Popen   │    │  │
│                      │  │ • Sanitized env    │    │  │
│                      │  │ • Timeout enforced │    │  │
│                      │  │ • Output capped    │    │  │
│                      │  └────────────────────┘    │  │
│                      └────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### Trust Boundaries

| Layer | Trusts | Does NOT Trust |
|-------|--------|----------------|
| **User** | HackBot CLI/GUI, config file | AI-generated commands (confirmation required) |
| **AI Engine** | API provider, system prompt | User-supplied targets (needs authorization) |
| **Tool Runner** | Allowlisted tools, validated commands | AI output (validates before execution) |
| **Subprocess** | OS kernel, installed tools | HackBot process (sanitized environment) |

---

## 📋 Dependencies & Supply Chain

### Key Dependencies

| Package | Purpose | Risk Mitigation |
|---------|---------|-----------------|
| `openai` | LLM API client | Pinned to stable versions |
| `requests` | HTTP client (CVE lookup, OSINT, active scanner) | Uses `Session` with retry/timeout |
| `flask` | GUI backend | Binds to localhost only |
| `pywebview` | Desktop GUI | Native OS webview sandboxing |
| `reportlab` | PDF generation | No network access |
| `dnspython` | DNS resolution (OSINT) | Read-only queries |

### Recommendations for Users

1. **Pin your dependencies**: Use `pip freeze > requirements.txt` in production
2. **Run in a virtual environment**: Isolate HackBot from system Python
3. **Use Docker** for maximum isolation in shared environments
4. **Audit plugins**: Third-party plugins execute arbitrary code — review before installing
5. **Keep updated**: Run `pip install --upgrade` regularly to get security patches

---

## 📜 License & Liability

HackBot is released under the [MIT License](LICENSE).

**THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.** The authors and contributors are **not responsible** for any damage, legal consequences, or misuse arising from the use of this software.

By using HackBot, you agree to:
- Use it only for **authorized security testing**
- Comply with all applicable **laws and regulations**
- Accept **full responsibility** for your actions

---

## 📞 Contact

| Channel | Contact |
|---------|---------|
| **Security issues** | [yashabalam707@gmail.com](mailto:yashabalam707@gmail.com) |
| **General questions** | [GitHub Discussions](https://github.com/yashab-cyber/hackbot/discussions) |
| **Bug reports** | [GitHub Issues](https://github.com/yashab-cyber/hackbot/issues) |
| **Community** | [Discord](https://discord.gg/X2tgYHXYq) |

---

*Last updated: April 2026 — HackBot v1.2.4*
