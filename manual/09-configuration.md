# 9. Configuration

HackBot is configured via `~/.config/hackbot/config.yaml`, environment variables, CLI flags, or the GUI Settings panel.

---

## Config File Location

```
~/.config/hackbot/config.yaml
```

Created automatically on first run with sensible defaults.

---

## All Configuration Options

### AI Settings (`ai` section)

| Field | Type | Default | Env Variable | Description |
|-------|------|---------|-------------|-------------|
| `provider` | string | `openai` | `HACKBOT_PROVIDER` | AI provider ID |
| `model` | string | `gpt-4o` | `HACKBOT_MODEL` | Model ID |
| `api_key` | string | `""` | `HACKBOT_API_KEY` | API key (provider-specific env vars also work) |
| `base_url` | string | `""` | `HACKBOT_BASE_URL` | Custom API endpoint URL |
| `temperature` | float | `0.2` | — | Creativity/randomness (0.0 = deterministic, 1.0 = creative) |
| `max_tokens` | int | `4096` | — | Maximum response length in tokens |

### Provider-Specific API Key Variables

| Provider | Environment Variable |
|----------|---------------------|
| OpenAI | `OPENAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| Gemini | `GEMINI_API_KEY` or `GOOGLE_API_KEY` |
| Groq | `GROQ_API_KEY` |
| Mistral | `MISTRAL_API_KEY` |
| DeepSeek | `DEEPSEEK_API_KEY` |
| Together | `TOGETHER_API_KEY` |
| OpenRouter | `OPENROUTER_API_KEY` |
| Ollama | Not required |
| Local | Not required |

### Agent Settings (`agent` section)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `auto_confirm` | bool | `false` | Skip confirmation prompts for risky commands |
| `max_steps` | int | `50` | Maximum steps per assessment |
| `timeout` | int | `300` | Tool execution timeout in seconds |
| `safe_mode` | bool | `true` | Prevent destructive/aggressive operations |
| `sudo_password` | string | `""` | `SUDO_PASSWORD` | Password for non-interactive sudo (avoids TTY hangs) |
| `nvd_api_key` | string | `""` | `NVD_API_KEY` | NVD API key for faster CVE lookups (50 req/30s vs 5) |
| `allowed_tools` | list | 76 tools | Whitelist of tools the agent can use |

### Allowed Tools (Default 76)

```
nmap, nikto, gobuster, sqlmap, wfuzz, ffuf, nuclei, subfinder, httpx,
amass, masscan, feroxbuster, dnsrecon, dnsenum, whatweb, dirb, searchsploit,
msfconsole, msfvenom, hydra, john, hashcat, wifite, aircrack-ng, airodump-ng,
aireplay-ng, airbase-ng, reaver, wash, hcxdumptool, hcxpcapngtool, bettercap,
ettercap, responder, nxc, crackmapexec, smbclient, enum4linux, enum4linux-ng,
ldapsearch, nbtscan, onesixtyone, snmpwalk, curl, wget, tcpdump, tshark, dig,
whois, traceroute, ping, fping, arp-scan, netdiscover, netcat, openssl,
testssl, sslscan, thc-ipv6, wpscan, dalfox, commix, tplmap, ghauri, arjun,
paramspider, katana, gau, waybackurls, crlfuzz, jwt_tool, xxeinjector,
ysoserial, python3, ruby, perl, php, gcc, go
```

### Reporting Settings (`reporting` section)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `format` | string | `html` | Default report format (`html`, `markdown`, `json`) |
| `auto_save` | bool | `true` | Auto-save reports after assessments |
| `include_raw_output` | bool | `true` | Include raw tool output in reports |

### UI Settings (`ui` section)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `theme` | string | `dark` | UI theme |
| `show_banner` | bool | `true` | Show ASCII banner on startup |
| `verbose` | bool | `false` | Show verbose error output |

---

## Viewing Configuration

### CLI
```
/config                       # Show current config in REPL
hackbot config                # Show config from terminal
```

### GUI
The **Settings** panel shows all configurable options.

---

## Modifying Configuration

### Interactive REPL
```
/provider openai              # Set provider
/model gpt-4o                 # Set model
/key YOUR_API_KEY             # Set API key (validates immediately)
```

### Terminal
```bash
hackbot setup YOUR_KEY --provider anthropic --model claude-sonnet-4-20250514
```

### CLI Flags
```bash
hackbot --provider groq --model llama-3.3-70b-versatile -k YOUR_KEY
```

### Environment Variables
```bash
export HACKBOT_PROVIDER=openai
export HACKBOT_MODEL=gpt-4o
export HACKBOT_API_KEY=sk-...
```

### Direct File Edit
```yaml
# ~/.config/hackbot/config.yaml
ai:
  provider: openai
  model: gpt-4o
  api_key: sk-...
  temperature: 0.2
  max_tokens: 4096

agent:
  auto_confirm: false
  max_steps: 50
  timeout: 300
  safe_mode: true

reporting:
  format: html
  auto_save: true
  include_raw_output: true

ui:
  show_banner: true
  verbose: false
```

---

## Data Directories

| Purpose | Path |
|---------|------|
| Configuration | `~/.config/hackbot/` |
| Config file | `~/.config/hackbot/config.yaml` |
| Sessions | `~/.local/share/hackbot/sessions/` |
| Reports | `~/.local/share/hackbot/reports/` |
| Logs | `~/.local/share/hackbot/logs/` |
| Plugins | `~/.config/hackbot/plugins/` |
| Campaigns | `~/.local/share/hackbot/campaigns/` |

Paths follow the [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html) via the `platformdirs` library.

---

## API Key Validation

When you set or change an API key (via `/key`, `/provider`, `hackbot setup`, or GUI Settings), it is **validated immediately** by making a minimal test request (`max_tokens=1`) to the provider. You'll see:

- ✅ **Valid** — key works, you're ready
- ❌ **Invalid** — wrong key, expired, or provider issue

Validation is skipped for `ollama` and `local` providers.

---

Next: [Troubleshooting →](10-troubleshooting.md)
