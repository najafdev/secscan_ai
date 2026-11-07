# 2. CLI Reference

HackBot's CLI has two layers:
1. **Click commands** — terminal entry points (`hackbot agent`, `hackbot chat`, etc.)
2. **Interactive REPL commands** — slash commands inside the `hackbot` shell (`/agent`, `/chat`, etc.)

---

## Click Entry Points

Run these directly from your terminal:

### `hackbot` — Main Entry Point

```bash
hackbot [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--model` | `-m` | Set AI model |
| `--provider` | `-p` | Set AI provider |
| `--api-key` | `-k` | Set API key |
| `--base-url` | | Custom API endpoint |
| `--no-banner` | | Skip the ASCII banner |
| `--verbose` | `-v` | Enable verbose output |
| `--safe-mode` / `--no-safe-mode` | | Enable/disable safe mode |
| `--gui` | `-g` | Launch GUI instead of REPL |
| `--version` | | Show version |

### `hackbot agent <target>`

Start an autonomous security assessment.

```bash
hackbot agent 10.0.0.1 --scope "Web app on port 443" --instructions "Focus on SQLi"
```

| Option | Short | Description |
|--------|-------|-------------|
| `--scope` | `-s` | Define assessment scope |
| `--instructions` | `-i` | Specific instructions for the agent |

### `hackbot chat`

Start chat mode directly.

```bash
hackbot chat
```

### `hackbot plan [target]`

Generate a pentest plan.

```bash
hackbot plan example.com --type web_pentest
```

| Option | Short | Description |
|--------|-------|-------------|
| `--type` | `-t` | Plan template type (see [Modes](04-modes.md#plan-mode)) |

### `hackbot run <command>`

Execute a security tool directly.

```bash
hackbot run nmap -sV 10.0.0.1
```

### `hackbot tools`

List available security tools (installed vs missing).

### `hackbot gui`

Launch the desktop GUI.

```bash
hackbot gui --host 0.0.0.0 --port 8080
```

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `127.0.0.1` | Server bind address |
| `--port` | `1337` | Server port |

### `hackbot config`

Show current configuration and list all providers.

### `hackbot setup <key>`

Quick setup with API key.

```bash
hackbot setup sk-xxxx --provider anthropic --model claude-sonnet-4-20250514
```

---

## Interactive REPL Commands

Once inside the `hackbot` shell, use these slash commands:

### Mode Commands

| Command | Description |
|---------|-------------|
| `/chat` | Switch to Chat mode — interactive cybersecurity Q&A |
| `/agent <target>` | Start Agent mode — autonomous pentesting against a target |
| `/plan` | Switch to Planning mode — structured pentest plans |

### Agent Commands

| Command | Description |
|---------|-------------|
| `/run <command>` | Execute a security tool manually |
| `/step [input]` | Execute next agent step, with optional guidance |
| `/findings` | Show discovered findings summary |
| `/stop` | Stop current autonomous assessment |

### Session & History

| Command | Description |
|---------|-------------|
| `/save [name]` | Save current session to disk |
| `/load [name]` | Load a previous session (lists available if no arg) |
| `/sessions [mode]` | List all saved sessions, optionally filtered by mode |
| `/clear` | Clear current conversation history |
| `/reset` | Reset HackBot to fresh state |
| `/continue` | Continue a response that was cut off |

### Configuration

| Command | Description |
|---------|-------------|
| `/config` | Show current config (provider, model, key status, safe mode) |
| `/tools` | Show available security tools |
| `/model <name>` | Switch AI model (e.g. `gpt-4o`, `claude-sonnet-4-20250514`) |
| `/key <api_key>` | Set API key (validates immediately) |
| `/provider [id]` | Switch provider (lists all if no arg) |
| `/models [provider]` | List models for current or specified provider |
| `/providers` | List all 10 available AI providers |

### Reporting & Export

| Command | Description |
|---------|-------------|
| `/export [format]` | Export assessment report (html/markdown/json) |
| `/pdf` | Generate professional PDF pentest report |
| `/templates` | List available plan templates (8 types) |
| `/checklist [type]` | Generate assessment checklist |
| `/commands <target>` | Generate specific tool commands for target |

### Intelligence Modules

| Command | Description |
|---------|-------------|
| `/cve <query>` | CVE/exploit lookup (CVE-ID, keyword, or `--nmap <output>`) |
| `/osint <domain>` | OSINT scan with flags: `--subs`, `--dns`, `--whois`, `--tech`, `--emails` |
| `/topology [output]` | Render network topology from nmap/masscan output |
| `/compliance [frameworks]` | Map findings to compliance frameworks (pci, nist, owasp, iso27001) |
| `/diff [old] [new]` | Compare two assessments (new/fixed/persistent findings) |
| `/campaign <sub>` | Multi-target campaign management (see below) |
| `/plugins [sub]` | List, reload, or manage user plugins |
| `/remediate [args]` | Generate fix commands/patches for findings |
| `/proxy <sub>` | HTTP proxy / traffic capture (see below) |

### Other

| Command | Description |
|---------|-------------|
| `/help` | Show all available commands |
| `/manual` | Open the HackBot user manual |
| `/version` | Show version + developer info |
| `/donate` | Show donation/support info |
| `/quit` / `/exit` / `/q` | Exit HackBot |

---

## Campaign Subcommands

Usage: `/campaign <subcommand> [args]`

| Subcommand | Arguments | Description |
|------------|-----------|-------------|
| `new <name> <targets...>` | campaign name + targets | Create a new multi-target campaign |
| `add <targets...>` | target list | Add targets to active campaign |
| `remove <target>` | target | Remove a target |
| `start` | — | Begin campaign (assess first pending target) |
| `next` | — | Complete current target, advance to next |
| `skip [reason]` | optional reason | Skip current target |
| `status` | — | Show campaign progress table |
| `findings` | — | Show all findings across targets |
| `report` | — | Generate campaign report |
| `pause` | — | Pause campaign |
| `resume` | — | Resume paused campaign |
| `abort` | — | Abort campaign |
| `list` | — | List saved campaigns |
| `load <id>` | campaign ID | Load a saved campaign |
| `delete <id>` | campaign ID | Delete a saved campaign |

**Example:**
```
/campaign new webapp_test app1.example.com app2.example.com api.example.com
/campaign start
/campaign next
/campaign status
/campaign report
```

---

## Proxy Subcommands

Usage: `/proxy <subcommand> [args]`

| Subcommand | Arguments | Description |
|------------|-----------|-------------|
| `start [port]` | port (default 8080) | Start intercepting proxy |
| `stop` | — | Stop proxy |
| `status` | — | Show proxy stats |
| `traffic [n]` | optional limit | Show captured traffic |
| `filter <term>` | search string | Filter traffic by URL/header/body |
| `scope <domain>` | domain(s) or `clear` | Restrict or clear capture scope |
| `clear` | — | Clear captured traffic |
| `export [file]` | filename | Export traffic as JSON |
| `replay <id>` | request ID | Replay a captured request |
| `flags` | — | Show flagged security-relevant requests |
| `detail <id>` | request ID | Show full request/response details |

**Example:**
```
/proxy start 8080
/proxy scope example.com
/proxy traffic 20
/proxy flags
/proxy detail 3
/proxy replay 3
/proxy export traffic_dump.json
/proxy stop
```

---

## Remediation Command

Usage: `/remediate [args]`

| Usage | Description |
|-------|-------------|
| `/remediate` | Generate rule-based fixes for ALL findings |
| `/remediate #3` | Generate fix for finding #3 only |
| `/remediate --ai` | Use AI to generate tailored fixes (requires API key) |
| `/remediate #3 --ai` | AI-generated fix for finding #3 |

Each remediation includes:
- One-liner summary
- Shell commands (install, configure, restart)
- Config file patches
- Code snippets (Python, PHP, JS, Java, etc.)
- References (CVE links, CIS benchmarks, OWASP)

---

Next: [GUI Reference →](03-gui-reference.md)
