# 5. Intelligence Modules

HackBot includes 10 built-in intelligence modules that extend beyond basic scanning.

---

## 🔬 Zero-Day Discovery Engine

Proactive vulnerability research engine that goes beyond known CVE scanning to find undisclosed vulnerabilities.

### How It Works

The Zero-Day Engine is integrated directly into Agent Mode and runs automatically:
1. **Every tool output** is auto-scanned for anomaly signals (stack traces, error leaks, memory addresses, etc.)
2. The AI agent can invoke **smart fuzzing** against discovered endpoints
3. After collecting findings, the agent can build **exploit chains** combining multiple vulns
4. **Version gap analysis** flags services where the exact version has no known CVE but nearby versions do

### Anomaly Detection Categories

| Category | Severity | What It Detects |
|----------|----------|----------------|
| `stack_trace` | High | Python, Java, PHP, .NET, Node.js, Go stack traces and panics |
| `error_leak` | Medium | SQL errors, database error messages, SQLSTATE codes, protocol errors |
| `path_disclosure` | Medium | Unix/Windows file path leaks, web server config paths, Java webapp internals |
| `debug_info` | High | Debug headers, debug mode flags, phpinfo, framework debuggers (Werkzeug, Django) |
| `memory_address` | Critical | Memory address leaks (defeats ASLR), crash signals, sanitizer output |
| `auth_leak` | Critical | API keys, passwords, private keys, AWS credentials, JWT tokens in responses |
| `injection_signal` | High | Confirmed SQL injection, command injection, /etc/passwd leaks, config file content |

### Smart Fuzz Payload Categories

| Category | Payloads | Purpose |
|----------|----------|--------|
| `buffer_overflow` | 14 | Memory corruption, format string attacks |
| `integer_overflow` | 20 | Integer boundary values and overflow conditions |
| `path_traversal` | 14 | Directory traversal with encoding bypasses and null bytes |
| `template_injection` | 14 | SSTI for Jinja2, FreeMarker, Twig, Handlebars, etc. |
| `ssrf` | 16 | Internal service access, cloud metadata, protocol smuggling |
| `deserialization` | 7 | Java, PHP, Python pickle, Node.js prototype pollution |
| `command_injection` | 20 | OS command injection with various escape techniques |
| `xss` | 12 | Cross-site scripting with filter bypasses |
| `header_injection` | 6 | CRLF injection, response splitting |
| `xxe` | 4 | XML External Entity injection |
| `request_smuggling` | 2 | HTTP request smuggling (CL.TE, TE.CL) |
| `race_condition` | 2 | Concurrent request test markers |

### Agent Action Types

The AI agent can use these actions during assessments:

```json
{"action": "fuzz", "target_url": "http://target.com/api", "parameter": "search", "categories": ["xss","command_injection","template_injection"], "explanation": "Testing search parameter for injection"}
```

```json
{"action": "analyze_anomaly", "response_body": "<suspicious response text>", "context": "Received after sending special chars to login", "explanation": "Analyzing error response for exploitable signals"}
```

```json
{"action": "chain_exploits", "explanation": "Analyze current findings for exploit chains"}
```

### Exploit Chain Types

The engine can identify these attack chains:
- **SSRF → Internal Service Access → RCE** — Use SSRF to reach internal Redis/Docker/etc.
- **SQL Injection → File Write → WebShell** — Write webshell via INTO OUTFILE
- **LFI → Log Poisoning → RCE** — Poison logs then include via LFI
- **XSS → CSRF → Account Takeover** — Chain stored XSS with missing CSRF
- **Info Disclosure → Credential Attack** — Use leaked usernames for brute-force
- **Open Redirect → Phishing** — Abuse trusted domain for credential theft

---

## 🛡 CVE / Exploit Lookup

Search CVE vulnerabilities and find exploit proof-of-concepts.

### CLI Usage
```
/cve CVE-2021-44228                  # Lookup specific CVE
/cve log4j                           # Search by keyword
/cve --nmap <paste nmap output>      # Map nmap services to CVEs
```

### Features
- **CVE Lookup**: Fetch full details from NVD (description, severity, CVSS score, references)
- **Keyword Search**: Search NVD by keyword with optional severity filter (up to 15 results)
- **Nmap-to-CVE Mapping**: Parses nmap service output, maps each service to known CVEs (5 per service)
- **Exploit Search**: Find PoC exploits via GitHub
- **Agent Auto-Enrichment**: Agent automatically maps nmap results to CVEs after every scan
- **NVD API Key**: Configure with `/nvd-key` for 10× faster rate limits (see [NVD API Integration](13-nvd-api-integration.md))

### GUI
Use the **CVE Lookup** panel with 4 tabs: CVE Lookup, Keyword Search, Exploit Search, Nmap to CVE.

---

## 🔍 OSINT Module

Open-source intelligence gathering for domains.

### CLI Usage
```
/osint example.com                  # Full scan (all modules)
/osint example.com --subs           # Subdomains only
/osint example.com --dns            # DNS records only
/osint example.com --whois          # WHOIS data only
/osint example.com --tech           # Technology stack only
/osint example.com --emails         # Email harvesting only
```

### Capabilities
| Module | What it discovers |
|--------|------------------|
| **Subdomains** | Enumerate subdomains using multiple techniques |
| **DNS** | A, AAAA, MX, NS, TXT, SOA, CNAME records |
| **WHOIS** | Registrar, creation/expiry dates, contact info |
| **Tech Stack** | Web server, framework, programming language, CMS |
| **Emails** | Email addresses associated with the domain |

### GUI
Use the **OSINT** panel — enter a domain and pick a scan type. Full scan shows real-time progress via SSE.

---

## 🌐 Network Topology Visualizer

Visualize network structure from scan results.

### CLI Usage
```
/topology                           # Auto-detect from agent scan history
/topology <paste nmap output>       # Parse specific output
```

### Output
- **ASCII network map** — terminal-friendly topology diagram
- **Markdown summary** — host details with ports, services, and states
- **Graph data** — JSON structure for GUI visualization

### GUI
Use the **Topology** panel:
- Paste scan output or click "From Agent" to auto-parse
- View as ASCII, interactive D3.js graph, or markdown

---

## 📋 Compliance Mapping

Map security findings to industry compliance frameworks.

### CLI Usage
```
/compliance                         # Map agent findings to all frameworks
/compliance pci nist                # Map to specific frameworks only
```

### Supported Frameworks

| Framework | Full Name | Controls |
|-----------|-----------|----------|
| `pci` | PCI DSS v4.0 | Payment card security requirements |
| `nist` | NIST 800-53 | Federal information security controls |
| `owasp` | OWASP Top 10 | Web application security risks |
| `iso27001` | ISO/IEC 27001 | Information security management |

### Output
For each finding, shows:
- Mapped control IDs and names
- Control descriptions
- Compliance status
- Framework-specific recommendations

### GUI
Use the **Compliance** panel:
- "From Agent" to auto-map current findings
- Or paste custom findings text
- Filter by framework
- Browse all controls within a framework

---

## 📊 Diff Reports

Compare two assessments to track remediation progress.

### CLI Usage
```
/diff                               # Lists available sessions to compare
/diff session1_id session2_id       # Compare specific sessions
```

### Output Categories
| Category | Meaning |
|----------|---------|
| 🆕 **New** | Findings in the new session that weren't in the old one |
| ✅ **Fixed** | Findings from the old session that are no longer present |
| ⏳ **Persistent** | Findings that exist in both sessions |

### GUI
Use the **Diff Report** panel — select two sessions from dropdowns and click Compare.

---

## 🎯 Multi-Target Campaigns

Manage coordinated assessments across multiple targets.

### CLI Usage
```
/campaign new webapp_audit app1.com app2.com api.internal.com
/campaign start
/campaign status
/campaign next
/campaign findings
/campaign report
```

### Campaign Lifecycle
1. **Create** — define campaign name and targets
2. **Start** — begin assessing first target
3. **Next** — mark current target complete, move to next
4. **Skip** — skip a target with optional reason
5. **Pause/Resume** — temporarily halt
6. **Abort** — cancel entire campaign

### Campaign States
| State | Description |
|-------|-------------|
| `draft` | Created but not started |
| `running` | Active assessment in progress |
| `paused` | Temporarily halted |
| `completed` | All targets assessed |
| `aborted` | Cancelled |

### Target States
| State | Description |
|-------|-------------|
| `pending` | Not yet assessed |
| `running` | Currently being assessed |
| `completed` | Assessment finished |
| `failed` | Assessment failed |
| `skipped` | Skipped by user |

### Intelligence Sharing
Campaign context is shared between targets — findings from one target inform the assessment of the next.

### GUI
Use the **Campaigns** panel — create campaigns, manage targets, track progress, generate aggregate reports.

---

## Custom Plugins

Extend HackBot with your own Python tools.

Plugin files are loaded from the user config plugins directory. On Linux this is:

```text
~/.config/hackbot/plugins/
```

You can always print the active path with:

```text
/plugins dir
```

Supported registration methods:

1. `@hackbot_plugin(...)` decorator on a callable.
2. `register()` function that returns a `PluginDefinition`.

Plugin runtime command format:

```text
hackbot-plugin <name> --arg1 value1 --arg2 value2
```

CLI management commands:

```text
/plugins
/plugins reload
/plugins dir
```

For complete step-by-step plugin authoring instructions, examples, and troubleshooting, see:

[Plugin Creation Guide ->](14-plugin-creation.md)

---

## 🔧 AI Remediation Engine

Generate fix commands and patches for security findings.

### CLI Usage
```
/remediate                # Rule-based fixes for ALL findings
/remediate #3             # Fix for finding #3 only
/remediate --ai           # AI-enhanced fixes (uses API key)
/remediate #3 --ai        # AI fix for finding #3
```

### Two Modes

| Mode | Speed | Requires API Key | Description |
|------|-------|-----------------|-------------|
| **Rule-based** | Instant | No | ~60 built-in vulnerability patterns |
| **AI-enhanced** | Seconds | Yes | LLM generates tailored fixes |

### Remediation Output
Each fix includes:
- **Summary** — one-liner description
- **Shell commands** — apt install, systemctl, sysctl, iptables, etc.
- **Config patches** — nginx.conf, sshd_config, apache, etc.
- **Code snippets** — Python, PHP, JavaScript, Java, etc.
- **References** — CVE links, CIS benchmarks, OWASP pages

### Priority Levels
| Priority | Action needed |
|----------|--------------|
| `immediate` | Fix now — active exploitation risk |
| `high` | Fix within 24 hours |
| `medium` | Fix within 1 week |
| `low` | Fix in next maintenance window |
| `informational` | Best practice improvement |

### GUI
In the **Agent** panel or **Findings** panel, click "Remediate" for any finding.

---

## 🔌 HTTP Proxy / Traffic Capture

Built-in intercepting proxy for capturing and analyzing web traffic.

### CLI Usage
```
/proxy start 8080         # Start proxy on port 8080
/proxy status             # Show proxy stats
/proxy scope example.com  # Capture only this domain
/proxy traffic 20         # Show last 20 requests
/proxy flags              # Show security-interesting requests
/proxy detail 5           # Full details for request #5
/proxy replay 5           # Replay request #5
/proxy filter login       # Filter traffic containing "login"
/proxy export dump.json   # Export traffic to file
/proxy clear              # Clear captured traffic
/proxy stop               # Stop proxy
```

### Auto-Flagged Patterns
The proxy automatically flags requests matching these patterns:

| Flag | Description |
|------|-------------|
| `auth_token` | Authorization headers, Bearer tokens |
| `cookie` | Cookie headers |
| `credentials` | Username/password in body |
| `error_response` | 4xx/5xx status codes |
| `redirect` | 3xx redirect responses |
| `sensitive_data` | SSN, credit card patterns |
| `sql_pattern` | SQL injection indicators |
| `file_upload` | File upload requests |
| `api_key` | API key parameters |
| `cors_header` | CORS headers |

### Using with Tools
```bash
# Use HackBot proxy with curl
curl -x http://127.0.0.1:8080 http://target.com/api/login

# Use with sqlmap
sqlmap -u "http://target.com/search?q=test" --proxy="http://127.0.0.1:8080"
```

### GUI
Use the **Proxy** panel — start/stop, view traffic table, filter, inspect details, replay requests, export.

---

Next: [ATT&CK Mapping →](11-attack-mapping.md) · [Vulnerability Database →](12-vulnerability-database.md) · [AI Providers →](06-ai-providers.md)
