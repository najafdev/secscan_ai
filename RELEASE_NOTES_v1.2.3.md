## HackBot v1.2.3

### 🔬 Zero-Day Discovery Engine (NEW)

A brand-new intelligence module that turns HackBot from a "known-CVE scanner" into a proactive vulnerability researcher:

- **Response Anomaly Detection** — 40+ regex patterns across 7 categories automatically scan every tool output for stack traces, error leaks, path disclosures, debug info, memory addresses, auth leaks, and injection signals
- **Smart Fuzz Payload Generator** — 150+ payloads across 12 categories: buffer overflow, integer overflow, path traversal, SSTI, SSRF, deserialization, command injection, XSS, header injection, XXE, request smuggling, race conditions
- **Exploit Chain Builder** — Analyzes multiple findings to propose high-impact attack chains (SSRF→RCE, SQLi→WebShell, LFI→Log Poisoning→RCE, XSS→CSRF→Account Takeover, and more)
- **Version Gap Analysis** — Flags services where the exact version has no known CVE but nearby versions do — zero-day candidates
- **Auto-Enrichment** — Every tool execution output is automatically analyzed for zero-day signals with no extra configuration needed
- **New Agent Actions** — AI can now invoke `fuzz`, `analyze_anomaly`, and `chain_exploits` actions autonomously during assessments

### 🛠️ Expanded Tool Support (+20 tools)

New tools added to the default allowed list (56 → 76 total):
- **Web Security**: `wpscan`, `dalfox`, `commix`, `tplmap`, `ghauri`, `crlfuzz`, `jwt_tool`, `xxeinjector`
- **Recon/Discovery**: `arjun`, `paramspider`, `katana`, `gau`, `waybackurls`
- **Exploitation**: `ysoserial`
- **Scripting/Compilation**: `python3`, `ruby`, `perl`, `php`, `gcc`, `go`

### 🐛 Bug Fixes

- **Fixed**: "Cannot read property 'appendChild' of null" error when stopping the agent — all 7 references to non-existent `agentMessages` element replaced with the existing `agentThoughts` container
- **Fixed**: `startCampaignTarget` null pointer crash when starting campaign targets
- **Fixed**: Incorrect CSS class names in campaign target message rendering (now uses `msg msg-assistant`)
- **Added**: Null guards for all DOM manipulation in agent panel functions

### 📖 Documentation

- New manual chapter: `15-zeroday-engine.md` — comprehensive guide with architecture, all payload categories, exploit chains, and API reference
- Updated: `README.md` — features table, agent mode description, GUI features, new intelligence module section
- Updated: `05-intelligence-modules.md` — Zero-Day Engine as first module (9 → 10 modules)
- Updated: `04-modes.md` — Agent methodology now includes zero-day analysis phases
- Updated: `03-gui-reference.md` — Agent panel docs with zero-day features
- Updated: `09-configuration.md` — Expanded tools list (56 → 76)

### Files Changed

| File | Change |
|------|--------|
| `hackbot/core/zeroday.py` | **NEW** — Zero-Day Discovery Engine module |
| `hackbot/core/engine.py` | Enhanced agent system prompt with zero-day hunting protocol |
| `hackbot/modes/agent.py` | Integrated ZeroDayEngine — 3 new action handlers, auto-enrichment |
| `hackbot/config.py` | 20 new tools in default allowed list |
| `hackbot/core/__init__.py` | Export ZeroDayEngine |
| `hackbot/gui/templates/index.html` | Fixed agent DOM errors + updated descriptions |
| `manual/15-zeroday-engine.md` | **NEW** — Dedicated manual chapter |
| `manual/README.md` | Added chapter 15 to table of contents |
| `manual/03-gui-reference.md` | Zero-day features in agent panel |
| `manual/04-modes.md` | Zero-day phases in agent methodology |
| `manual/05-intelligence-modules.md` | Full zero-day engine documentation |
| `manual/09-configuration.md` | Updated tools count and list |
| `README.md` | Feature table, agent mode, GUI features, intelligence section |
| `website/index.html` | Version bump |

---

**Full Changelog**: https://github.com/yashab-cyber/hackbot/compare/v1.2.2...v1.2.3
