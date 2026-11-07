# 3. GUI Reference

HackBot includes a full native desktop GUI with dark theme. Launch it with:

```bash
hackbot gui                     # Default: 127.0.0.1:1337
hackbot gui --host 0.0.0.0 --port 8080  # Custom bind
hackbot --gui                   # Shortcut flag
```

The GUI is built with Flask + pywebview and provides every feature available in the CLI.

---

## Sidebar Navigation

The GUI has a left sidebar with **16 panels** organized in 3 sections. Use the sidebar toggle in the logo header to collapse the navigation to an icon rail; the GUI remembers the collapsed/expanded preference.

### Modes
| Panel | Icon | Description |
|-------|------|-------------|
| **Chat** | 💬 | Interactive cybersecurity Q&A with streaming responses |
| **Agent** | 🤖 | Autonomous security testing with real-time output |
| **Plan** | 📋 | Pentest plan generation with templates |

### Tools
| Panel | Icon | Description |
|-------|------|-------------|
| **Tools** | 🔧 | View installed & missing security tools |
| **CVE Lookup** | 🛡 | Search CVEs, lookup by ID, find exploits, parse nmap |
| **OSINT** | 🔍 | Domain reconnaissance (subdomains, DNS, WHOIS, tech stack) |
| **Topology** | 🌐 | Network topology visualization from scan output |
| **Compliance** | 📋 | Map findings to PCI DSS, NIST, OWASP, ISO 27001 |
| **Diff Report** | 📊 | Compare old vs new assessments |
| **Findings** | 🎯 | View all findings with severity badges |
| **Sessions** | 💾 | Browse, restore, delete saved sessions |
| **Campaigns** | 🎯 | Multi-target campaign management |
| **Proxy** | 🔄 | HTTP traffic capture and analysis |

### System
| Panel | Icon | Description |
|-------|------|-------------|
| **Plugins** | 🔌 | Manage custom tool plugins |
| **Settings** | ⚙️ | Provider, model, API key, safe mode, report format |

### Sidebar Footer
Shows connection status, author credit (Yashab Alam), and links to GitHub, LinkedIn, Email, and Donate.

---

## Panel Details

### 💬 Chat Panel

Interactive cybersecurity Q&A with streaming AI responses.

| Element | Function |
|---------|----------|
| Message input | Type your question and press Enter or click Send |
| Response area | Streaming markdown-rendered output |
| Continue button | Appears when response was truncated — click to continue |
| Clear button | Clear conversation history |

**How to use:**
1. Type a cybersecurity question in the input box
2. Press Enter — the AI streams its response in real-time
3. If the response is cut off, click "Continue"
4. Use "Clear" to start a fresh conversation

---

### 🤖 Agent Panel

Autonomous security testing with real tool execution and zero-day discovery.

| Element | Function |
|---------|----------|
| Target input | IP address, domain, or URL to assess |
| Scope field | Define assessment scope (optional) |
| Instructions field | Specific focus areas (optional) |
| Start button | Begin autonomous assessment and auto-run steps until completion, stop, truncation, or error |
| Run command box | Execute a manual tool command |
| Step button | Execute one manual agent step when auto-run is not active |
| Stop button | Halt the assessment and prevent additional auto-run steps |
| Continue button | Appears when an agent response was truncated; click to continue and resume auto-run |
| Findings section | Shows discovered vulnerabilities |
| Export buttons | HTML, Markdown, JSON, PDF report export |
| Remediate button | Generate fix commands for findings |

**Zero-Day Discovery Features (automatic):**
- 🔬 Every tool output is auto-analyzed for anomaly signals (stack traces, error leaks, memory addresses)
- 🧪 AI can invoke smart fuzzing with 150+ payloads across 12 categories
- ⛓️ Exploit chain analysis combines multiple findings into critical attack paths
- 📊 Zero-day candidate signals appear in the Agent Thoughts panel

**How to use:**
1. Enter a target (e.g., `10.0.0.1` or `example.com`)
2. Optionally set scope and instructions
3. Click "Start" — the agent automatically continues through each step without repeated clicks
4. Watch the streaming output as tools execute — zero-day signals auto-appear
5. Click "Stop" to halt auto-run before adding manual guidance or ending the assessment
6. If a response is cut off, click "Continue"; auto-run resumes after the continuation completes
7. Click "Findings" to see discovered vulnerabilities (including zero-day candidates)
8. Click "Export" or "PDF" to generate reports

---

### 📋 Plan Panel

Generates structured penetration testing plans.

| Element | Function |
|---------|----------|
| Target input | Target to plan assessment for |
| Plan type selector | Choose from 8 templates |
| Scope field | Define what's in scope |
| Constraints field | Limitations, rules of engagement |
| Create button | Generate the plan |
| Q&A input | Ask follow-up questions about the plan |
| Clear button | Reset planning session |

**Available plan templates:**

| Type | Description |
|------|-------------|
| `web_pentest` | Web Application Penetration Test (11 phases) |
| `network_pentest` | Network Penetration Test (10 phases) |
| `api_pentest` | API Security Assessment (8 phases) |
| `cloud_audit` | Cloud Security Audit (9 phases) |
| `ad_pentest` | Active Directory Penetration Test (10 phases) |
| `mobile_pentest` | Mobile Application Penetration Test (8 phases) |
| `red_team` | Red Team Engagement (10 phases) |
| `bug_bounty` | Bug Bounty Methodology (7 phases) |

---

### 🔧 Tools Panel

Displays all 26+ security tools with their install status.

| Column | Description |
|--------|-------------|
| Tool name | The security tool (nmap, nikto, sqlmap, etc.) |
| Status | ✅ Installed or ❌ Missing |
| Path | Full path to the executable |

---

### 🛡 CVE Lookup Panel

Search for CVEs and exploits.

| Tab | Input | Description |
|-----|-------|-------------|
| **CVE Lookup** | CVE ID (e.g., `CVE-2021-44228`) | Fetch full CVE details from NVD |
| **Keyword Search** | Keyword + severity filter | Search NVD by keyword (up to 15 results) |
| **Exploit Search** | Search query | Find exploit PoCs via GitHub |
| **Nmap to CVE** | Paste nmap output | Map services to known CVEs (5 per service) |

---

### 🔍 OSINT Panel

Domain reconnaissance and intelligence gathering.

| Tab | Input | Description |
|-----|-------|-------------|
| **Full Scan** | Domain | Runs all OSINT modules with progress indicator |
| **Subdomains** | Domain | Subdomain enumeration |
| **DNS** | Domain | DNS record lookup (A, AAAA, MX, NS, TXT, SOA, CNAME) |
| **WHOIS** | Domain | WHOIS registration data |
| **Tech Stack** | Domain | Server, framework, and technology detection |

---

### 🌐 Topology Panel

Visualize network topology from scan output.

| Input | Description |
|-------|-------------|
| Paste scan output | Paste nmap or masscan output text |
| From Agent button | Auto-parse from current agent scan history |

**Output views:**
- ASCII network map
- Interactive D3.js force-directed graph
- Markdown summary with host/port/service details

---

### 📋 Compliance Panel

Map security findings to compliance frameworks.

| Element | Function |
|---------|----------|
| From Agent button | Auto-map current agent findings |
| Custom findings input | Paste findings text |
| Framework filter | Select: PCI DSS, NIST 800-53, OWASP Top 10, ISO 27001 |
| Controls browser | Browse all controls within a framework |

---

### 📊 Diff Report Panel

Compare two assessments to track remediation progress.

| Element | Function |
|---------|----------|
| Old session selector | Pick the baseline session |
| New session selector | Pick the newer session (or use current agent) |
| Compare button | Generate diff showing new, fixed, and persistent findings |

---

### 🎯 Findings Panel

View all discovered vulnerabilities.

| Column | Description |
|--------|-------------|
| # | Finding number |
| Severity | Critical / High / Medium / Low / Info (color-coded) |
| Title | Finding name |
| Description | Brief description |
| Remediate button | Generate fix commands for that finding |

---

### 💾 Sessions Panel

Manage saved sessions.

| Element | Function |
|---------|----------|
| Session list | Browse all sessions (sorted by date) |
| Mode filter | Filter by chat/agent/plan |
| Restore button | Load session back into the active workspace |
| Delete button | Remove a saved session |

---

### 🎯 Campaigns Panel

Multi-target campaign management.

| Element | Function |
|---------|----------|
| New Campaign form | Name + target list |
| Target management | Add/remove targets |
| Start/Pause/Abort | Campaign lifecycle controls |
| Progress table | Per-target status, findings count, duration |
| Start Target button | Begin assessment of a specific target |
| Complete/Skip buttons | Mark targets as done or skipped |
| Campaign report | Generate aggregate report across all targets |

---

### 🔄 Proxy Panel

HTTP traffic capture and analysis.

| Element | Function |
|---------|----------|
| Start/Stop buttons | Control the intercepting proxy (default port 8080) |
| Port input | Set custom proxy port |
| Status display | Running state, request count, bytes captured |
| Traffic table | Method, URL, status code, size, duration |
| Scope input | Restrict capture to specific domains |
| Filter input | Search traffic by URL, header, or body |
| Flagged tab | Security-relevant requests (auth tokens, errors, SQL patterns, etc.) |
| Detail view | Full request/response with headers and body |
| Replay button | Re-send a captured request |
| Export button | Download traffic as JSON or Markdown |
| Clear button | Wipe captured traffic |

**How to use:**
1. Click "Start" to launch the proxy on port 8080
2. Configure your browser/tool to use `http://127.0.0.1:8080` as proxy
3. Browse or run tools — traffic is captured automatically
4. Use "Flagged" to see security-interesting requests
5. Click a request for full details
6. "Replay" to re-send, "Export" to save

---

### 🔌 Plugins Panel

Manage custom tool plugins.

| Element | Function |
|---------|----------|
| Plugin list | Name, description, version, category, args |
| Reload button | Rediscover plugins from disk |
| Plugin directory | Shows path to `~/.config/hackbot/plugins/` |
| Errors section | Shows any plugin load errors |

---

### ⚙️ Settings Panel

Configure HackBot.

| Setting | Options | Description |
|---------|---------|-------------|
| Provider | 10 providers (dropdown) | Select AI provider |
| Model | Provider-specific (dropdown) | Select AI model |
| API Key | Text input + Validate button | Set and validate API key |
| Temperature | Slider (0.0 — 1.0) | LLM creativity/randomness |
| Max Tokens | Slider (256 — 16384) | Max response length |
| Safe Mode | Toggle | Prevent destructive/aggressive scans |
| Auto-confirm | Toggle | Skip risky command confirmations |
| Report Format | html / markdown / json | Default report format |

---

## API Endpoints

The GUI communicates with the backend via REST API. All endpoints are prefixed with `/api/`.

### Status & Config
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | App status (version, mode, provider, model) |
| `/api/providers` | GET | All provider definitions + models |
| `/api/tools` | GET | Security tools status |
| `/api/config` | GET | Get current config |
| `/api/config` | POST | Update config |
| `/api/validate-key` | POST | Validate API key |
| `/api/mode` | POST | Switch mode |

### Chat
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send message (SSE stream) |
| `/api/chat/clear` | POST | Clear history |
| `/api/chat/continue` | POST | Continue truncated response |
| `/api/chat/truncated` | GET | Check truncation status |

### Agent
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agent/start` | POST | Start assessment (SSE stream) |
| `/api/agent/step` | POST | Next step (SSE stream) |
| `/api/agent/run` | POST | Manual command |
| `/api/agent/continue` | POST | Continue truncated response |
| `/api/agent/truncated` | GET | Check truncation |
| `/api/agent/findings` | GET | Get findings |
| `/api/agent/stop` | POST | Stop assessment |
| `/api/agent/remediate` | POST | Generate remediation |
| `/api/agent/export` | POST | Export report |
| `/api/agent/export-pdf` | POST | Generate PDF |

### Plan
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/plan/templates` | GET | List templates |
| `/api/plan/create` | POST | Create plan (SSE) |
| `/api/plan/ask` | POST | Ask question (SSE) |
| `/api/plan/clear` | POST | Reset plan |

### Sessions
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sessions` | GET | List sessions |
| `/api/sessions/<id>` | GET | Load session |
| `/api/sessions/<id>` | DELETE | Delete session |
| `/api/sessions/restore/<id>` | POST | Restore session |

### CVE
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/cve/lookup` | POST | CVE by ID |
| `/api/cve/search` | POST | Keyword search |
| `/api/cve/exploits` | POST | Exploit search |
| `/api/cve/nmap` | POST | Nmap-to-CVE mapping |

### OSINT
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/osint/scan` | POST | Full OSINT scan (SSE) |
| `/api/osint/subdomains` | POST | Subdomains |
| `/api/osint/dns` | POST | DNS records |
| `/api/osint/whois` | POST | WHOIS lookup |
| `/api/osint/techstack` | POST | Tech stack |

### Topology
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/topology/parse` | POST | Parse scan output |
| `/api/topology/from-agent` | GET | Build from agent |

### Compliance
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/compliance/map` | POST | Map findings |
| `/api/compliance/from-agent` | GET | Map from agent |
| `/api/compliance/frameworks` | GET | List frameworks |
| `/api/compliance/controls/<fw>` | GET | Controls for framework |

### Diff
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/diff/sessions` | GET | Sessions with findings |
| `/api/diff/compare` | POST | Compare sessions |

### Plugins
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/plugins` | GET | List plugins |
| `/api/plugins/reload` | POST | Reload plugins |
| `/api/plugins/execute` | POST | Execute plugin |

### Campaigns
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/campaigns` | GET | List campaigns |
| `/api/campaigns` | POST | Create campaign |
| `/api/campaigns/<id>` | GET | Get campaign |
| `/api/campaigns/<id>` | DELETE | Delete campaign |
| `/api/campaigns/<id>/activate` | POST | Activate |
| `/api/campaigns/active` | GET | Active campaign |
| `/api/campaigns/active/start` | POST | Start campaign |
| `/api/campaigns/active/start-target` | POST | Start target (SSE) |
| `/api/campaigns/active/complete-target` | POST | Complete target |
| `/api/campaigns/active/skip-target` | POST | Skip target |
| `/api/campaigns/active/pause` | POST | Pause |
| `/api/campaigns/active/abort` | POST | Abort |
| `/api/campaigns/active/findings` | GET | All findings |
| `/api/campaigns/active/report` | POST | Generate report |

### Proxy
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/proxy/start` | POST | Start proxy |
| `/api/proxy/stop` | POST | Stop proxy |
| `/api/proxy/status` | GET | Proxy stats |
| `/api/proxy/traffic` | GET | Get traffic |
| `/api/proxy/traffic/<id>` | GET | Request details |
| `/api/proxy/flags` | GET | Flagged requests |
| `/api/proxy/scope` | POST | Set/clear scope |
| `/api/proxy/clear` | POST | Clear traffic |
| `/api/proxy/replay` | POST | Replay request |
| `/api/proxy/export` | GET | Export traffic |

---

Next: [Modes →](04-modes.md)
