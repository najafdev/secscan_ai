# 4. Modes

HackBot has three core operating modes, each designed for a different workflow.

---

## 💬 Chat Mode

Interactive cybersecurity Q&A powered by AI.

### When to use
- Learning about security concepts
- Getting advice on tools and techniques
- Asking for code review or vulnerability analysis
- Quick security questions

### How it works
1. Type any cybersecurity question
2. The AI streams a response with markdown formatting
3. Conversation context is maintained (the AI remembers previous messages)
4. Sessions auto-save after each exchange

### Entering Chat Mode
```
/chat                  # In REPL
hackbot chat           # From terminal
```

### Features
- **Streaming responses** — see the answer as it's generated
- **Conversation memory** — context is preserved across messages
- **Auto-save** — conversations are saved automatically
- **`/continue`** — resume if a response gets cut off
- **Summarization** — when conversation exceeds 40 messages, older messages are summarized to maintain context window

### Example
```
HackBot> /chat
💬 Chat Mode — Interactive cybersecurity Q&A

HackBot [chat]> How do I detect SQL injection vulnerabilities?
AI: SQL injection can be detected through several approaches...

HackBot [chat]> What tools can automate this?
AI: Here are the top tools for SQL injection detection...
```

---

## 🤖 Agent Mode

Autonomous penetration testing — the AI plans, executes tools, analyzes results, and adapts its strategy.

### When to use
- Security assessments against authorized targets
- Automated vulnerability scanning and analysis
- Penetration testing with AI-guided methodology

### How it works
1. You provide a target (IP, domain, URL)
2. The agent follows a structured methodology:
   - **Reconnaissance** → Gather information
   - **Scanning** → Port/service discovery
   - **Enumeration** → Detailed service probing
   - **Zero-Day Analysis** → Anomaly detection, smart fuzzing, version gap analysis
   - **Exploitation** → Vulnerability verification
   - **Post-Exploitation** → Impact assessment
   - **Exploit Chaining** → Combine findings into high-impact attack paths
   - **Reporting** → Generate findings report
3. At each step, the AI decides which tool to run, executes it, and analyzes the output
4. Every tool output is auto-scanned for zero-day signals (stack traces, error leaks, memory addresses)
5. Findings are tracked with severity ratings

### Starting Agent Mode
```
/agent 10.0.0.1                                        # Basic
/agent example.com --scope "Web app on port 443"        # With scope
hackbot agent 10.0.0.1 -s "DMZ network" -i "Focus on web apps"  # From terminal
```

### Agent Controls
| Command | Description |
|---------|-------------|
| `/step [input]` | Execute next step with optional guidance |
| `/run <cmd>` | Manually run a tool |
| `/findings` | View discovered findings |
| `/stop` | Stop the assessment |
| `/export html` | Export report |
| `/pdf` | Generate PDF report |
| `/remediate` | Generate fixes for findings |
| `/compliance` | Map findings to compliance frameworks |

### Safe Mode
When `safe_mode` is enabled (default), the agent:
- Avoids destructive scans (no exploit payloads, no DoS)
- Blocks dangerous commands
- Prompts for confirmation on risky operations

Disable with `/config` or `--no-safe-mode`.

### Findings
Each finding includes:
- **Severity**: Critical, High, Medium, Low, or Info
- **Title**: Short description
- **Description**: Detailed explanation
- **Evidence**: Raw tool output proving the finding
- **Recommendation**: How to fix it

### Example
```
HackBot> /agent 10.0.0.1
🤖 Agent Mode — Starting assessment of 10.0.0.1

[Agent] Running: nmap -sV -sC 10.0.0.1
[Agent] Found 5 open ports. Analyzing services...
[Agent] Running: nikto -h http://10.0.0.1
[Agent] ⚠️ Finding: Outdated Apache 2.4.29 (HIGH)
[Agent] Running: sqlmap -u "http://10.0.0.1/search?q=test" --batch
...

HackBot> /findings
3 findings discovered:
  #1 [HIGH] Outdated Apache 2.4.29
  #2 [CRITICAL] SQL Injection in /search endpoint
  #3 [MEDIUM] Missing security headers
```

---

## 📋 Plan Mode

Generates structured penetration testing plans, checklists, and methodologies.

### When to use
- Planning an engagement before starting
- Creating pentest proposals for clients
- Generating checklists for specific assessment types
- Getting tool recommendations for a target

### How it works
1. Provide a target and optionally select a plan template
2. The AI generates a comprehensive plan with phases, tools, techniques, and timelines
3. You can ask follow-up questions to refine the plan

### Entering Plan Mode
```
/plan                                        # Interactive
hackbot plan example.com --type web_pentest  # From terminal
```

### Plan Templates (8 types)

| Template | Phases | Focus |
|----------|--------|-------|
| `web_pentest` | 11 | Web application security (OWASP, injection, auth, etc.) |
| `network_pentest` | 10 | Network infrastructure (ports, services, protocols) |
| `api_pentest` | 8 | API security (REST, GraphQL, auth, rate limiting) |
| `cloud_audit` | 9 | Cloud security (AWS/Azure/GCP, IAM, storage, network) |
| `ad_pentest` | 10 | Active Directory (Kerberos, LDAP, GPO, lateral movement) |
| `mobile_pentest` | 8 | Mobile apps (iOS/Android, API, storage, crypto) |
| `red_team` | 10 | Full red team engagement (OSINT, phishing, persistence) |
| `bug_bounty` | 7 | Bug bounty program methodology |

### Plan Commands
| Command | Description |
|---------|-------------|
| `/templates` | List all 8 plan templates with details |
| `/checklist [type]` | Generate a checklist for a specific assessment type |
| `/commands <target>` | Generate specific tool commands for a target |

### Example
```
HackBot> /plan
📋 Planning Mode

HackBot [plan]> Plan a web pentest for shop.example.com
AI: # Web Application Penetration Test Plan
## Target: shop.example.com

### Phase 1: Reconnaissance
- Objective: Map the application surface
- Tools: whatweb, wappalyzer, subfinder
- Duration: 2 hours
...

HackBot [plan]> What about API endpoints?
AI: Great question. Here's how to enumerate and test the API...
```

---

## Switching Modes

You can switch between modes at any time:

```
/chat       # Switch to Chat
/agent X    # Switch to Agent
/plan       # Switch to Plan
```

Each mode maintains its own conversation history. Switching modes does not lose your progress.

---

Next: [Intelligence Modules →](05-intelligence-modules.md)
