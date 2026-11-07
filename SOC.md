# 🛡️ HackBot SOC Analyst Features — Roadmap

> Planned SOC (Security Operations Center) analyst features for HackBot.
> This file tracks what to build and implementation priorities.

---

## Tier 1 — Highest Impact (Daily SOC Workflow)

### 1. IOC Analyzer (`/ioc`)
**Priority: 🔴 High — Build First**

Multi-source threat intelligence for IPs, domains, file hashes, and URLs.

**Capabilities:**
- Auto-extract IOCs from pasted logs/alerts (regex-based: IPs, domains, hashes, URLs, emails)
- VirusTotal lookup (file hashes, URLs, IPs, domains)
- AbuseIPDB reputation check (abuse confidence score, ISP, country, reports)
- Shodan host search (open ports, banners, vulns, geolocation)
- GreyNoise context (classification: benign/malicious/unknown, tags, first/last seen)
- AlienVault OTX pulse search (threat intel pulses, related IOCs)
- IP geolocation and ASN info
- Aggregate risk scoring across all sources
- Bulk IOC analysis (paste multiple IOCs at once)

**CLI Usage:**
```
/ioc 185.220.101.1                    # IP reputation check
/ioc evil.example.com                  # Domain reputation
/ioc 44d88612fea8a8f36de82e1278abb02f  # File hash lookup
/ioc https://malware.example.com/payload.exe  # URL scan
/ioc --extract <paste logs>            # Auto-extract and analyze all IOCs
/ioc --bulk ip1,ip2,ip3               # Bulk lookup
```

**API Keys Needed:**
| Service | Free Tier | Env Variable |
|---------|-----------|-------------|
| VirusTotal | 4 req/min, 500 req/day | `VT_API_KEY` |
| AbuseIPDB | 1000 req/day | `ABUSEIPDB_API_KEY` |
| Shodan | 1 req/sec, limited | `SHODAN_API_KEY` |
| GreyNoise | 50 req/day (Community) | `GREYNOISE_API_KEY` |
| AlienVault OTX | Unlimited (free) | `OTX_API_KEY` |

**Implementation Notes:**
- Create `hackbot/core/ioc.py` — IOCAnalyzer class
- Follow same pattern as `cve.py` (dataclasses, rate limiting, session management)
- Config: add API keys to AgentConfig, env-var overrides
- CLI: `/ioc` command, `/ioc-keys` to manage API keys
- GUI: IOC Analyzer panel with multi-tab layout
- Agent integration: auto-extract IOCs from tool output

---

### 2. Log Analyzer (`/logs`)
**Priority: 🔴 High**

AI-powered log parsing and anomaly detection.

**Capabilities:**
- Parse multiple log formats: syslog, auth.log, Windows Event Logs (EVTX XML), Apache/nginx access/error logs, JSON logs
- Pattern detection: brute-force attempts, privilege escalation, lateral movement, data exfiltration
- Timeline reconstruction — chronological event sequence with anomaly highlighting
- Statistical analysis: failed login counts, top source IPs, unusual hours, spike detection
- AI-powered analysis: natural language summary of what happened
- MITRE ATT&CK mapping of detected patterns

**CLI Usage:**
```
/logs analyze <paste log content>      # Analyze pasted logs
/logs analyze --file /path/to/auth.log # Analyze a log file
/logs timeline <paste>                 # Build event timeline
/logs brute-force <paste auth.log>     # Focused brute-force detection
/logs summary <paste>                  # AI summary of log events
```

**Implementation Notes:**
- Create `hackbot/core/log_analyzer.py`
- Regex-based parsers for each log format
- Statistical anomaly detection (z-score, frequency analysis)
- Feed parsed data to AI for natural language analysis
- Output: structured findings + timeline + AI commentary

---

### 3. Phishing Analyzer (`/phish`)
**Priority: 🔴 High**

Email header analysis and phishing indicator detection.

**Capabilities:**
- Email header parsing (Received chain, SPF, DKIM, DMARC results)
- Sender reputation check (via IOC analyzer integration)
- URL extraction and deobfuscation (base64, URL encoding, redirect chains)
- Attachment hash extraction and VirusTotal lookup
- Homoglyph / typosquatting domain detection
- AI-powered verdict: phishing confidence score with reasoning
- Response suggestions: block sender, quarantine, report

**CLI Usage:**
```
/phish analyze <paste email headers>   # Full header analysis
/phish url https://bit.ly/xyz          # Unshorten + scan URL
/phish domain paypa1.com               # Typosquat detection vs paypal.com
/phish verdict <paste full email>      # AI phishing verdict
```

**Implementation Notes:**
- Create `hackbot/core/phishing.py`
- Python `email` stdlib for header parsing
- SPF/DKIM/DMARC result extraction from Authentication-Results header
- URL deobfuscation chain (follow redirects with `requests`, decode encodings)
- Levenshtein distance for typosquat detection against top 1000 domains
- Integration with IOC analyzer for sender IP/domain reputation

---

### 4. Incident Response Playbooks (`/ir`)
**Priority: 🟠 High**

Pre-built step-by-step IR playbooks with AI guidance.

**Capabilities:**
- Pre-built playbooks: ransomware, phishing, data breach, DDoS, insider threat, malware infection, account compromise, web defacement, supply chain attack
- Each playbook has phases: Detection → Containment → Eradication → Recovery → Lessons Learned
- Evidence collection checklists per incident type
- Containment commands (with safe_mode guardrails)
- AI-assisted triage: paste alert details, get customized response steps
- Regulatory notification timelines (GDPR 72hr, HIPAA, PCI-DSS)
- Post-incident report template generation

**CLI Usage:**
```
/ir list                               # List all playbooks
/ir ransomware                         # Show ransomware playbook
/ir phishing                           # Show phishing playbook
/ir triage <paste alert details>       # AI-assisted triage
/ir checklist ransomware               # Evidence collection checklist
/ir report                             # Generate post-incident report
```

**Implementation Notes:**
- Create `hackbot/core/incident.py`
- Playbooks as structured data (dict/dataclass with phases, steps, commands)
- AI integration: use playbook as system prompt context for triage
- PDF report generation using existing `pdf_report.py` infrastructure
- No external APIs needed — mostly structured data + AI prompting

---

## Tier 2 — Advanced SOC (Threat Hunting & Forensics)

### 5. Threat Hunt Mode (`/hunt`)
**Priority: 🟡 Medium**

Hypothesis-driven threat hunting with SIEM query generation.

**Capabilities:**
- Natural language → Sigma rule generation
- Sigma → SIEM query translation (Splunk SPL, Microsoft KQL, Elastic EQL, QRadar AQL)
- Pre-built hunt hypotheses library (lateral movement, C2 beacons, persistence, credential access)
- TTP-based hunting (input ATT&CK technique → get detection queries)
- AI-assisted hypothesis refinement

**CLI Usage:**
```
/hunt "lateral movement via SMB"       # Generate Sigma + SIEM queries
/hunt sigma "failed login brute force" # Generate Sigma rule only
/hunt splunk "DNS tunneling"           # Generate Splunk SPL query
/hunt kql "suspicious PowerShell"      # Generate KQL for Sentinel
/hunt technique T1059.001              # Hunt by ATT&CK technique
/hunt list                             # List pre-built hypotheses
```

**Implementation Notes:**
- Create `hackbot/core/threat_hunt.py`
- Sigma rule YAML generation (structured templates + AI refinement)
- Sigma-to-SIEM transpiler (template-based for each SIEM backend)
- Pre-built hypothesis library (JSON/YAML data)
- Integration with existing ATT&CK mapper for technique-based hunting

---

### 6. PCAP Analyzer (`/pcap`)
**Priority: 🟡 Medium**

Network traffic forensics via tshark integration.

**Capabilities:**
- Parse pcap files using tshark (must be installed)
- Protocol distribution analysis
- DNS query extraction and anomaly detection (tunneling, DGA domains)
- HTTP request/response extraction
- C2 beacon detection (periodic timing analysis)
- Data exfiltration indicators (large outbound transfers, unusual protocols)
- TLS certificate analysis (self-signed, expired, suspicious issuers)
- Conversation summary (top talkers, flow analysis)

**CLI Usage:**
```
/pcap analyze capture.pcap             # Full analysis
/pcap dns capture.pcap                 # DNS-focused analysis
/pcap http capture.pcap                # HTTP request extraction
/pcap c2 capture.pcap                  # C2 beacon detection
/pcap summary capture.pcap             # Quick traffic summary
```

**Implementation Notes:**
- Create `hackbot/core/pcap.py`
- Shell out to `tshark` (add to allowed_tools)
- Parse tshark JSON output for structured analysis
- Statistical timing analysis for beacon detection
- Feed summary data to AI for natural language forensic report

---

### 7. YARA Rule Generator (`/yara`)
**Priority: 🟡 Medium**

AI-assisted YARA rule creation and validation.

**Capabilities:**
- Generate YARA rules from: malware family name, IOCs, file characteristics, description
- Rule validation (syntax check via `yara-python` if installed)
- Template library for common malware families
- String extraction suggestions
- Condition builder (file size, magic bytes, import table, string counts)
- VirusTotal retrohunt-compatible output

**CLI Usage:**
```
/yara generate "Cobalt Strike beacon"  # AI-generated rule
/yara from-iocs hash1,hash2,domain1   # Rule from IOC list
/yara validate <paste rule>            # Syntax validation
/yara templates                        # List templates
```

**Implementation Notes:**
- Create `hackbot/core/yara_gen.py`
- AI-driven rule generation (structured prompting with YARA syntax examples)
- Optional `yara-python` for validation
- Template library as embedded data

---

### 8. Alert Enrichment Pipeline (`/alert`)
**Priority: 🟡 Medium**

SIEM alert triage automation.

**Capabilities:**
- Paste raw SIEM alert → auto-extract all observables (IPs, domains, hashes, users, hosts)
- Enrich each observable via IOC analyzer
- Score overall alert priority (critical/high/medium/low/false positive)
- Suggest response actions based on alert type
- Map to MITRE ATT&CK techniques
- Generate triage notes for ticketing system

**CLI Usage:**
```
/alert triage <paste raw alert>        # Full triage pipeline
/alert enrich <paste alert>            # Enrich observables only
/alert priority <paste alert>          # Quick priority scoring
/alert notes <paste alert>             # Generate ticket notes
```

**Implementation Notes:**
- Create `hackbot/core/alert_triage.py`
- Depends on IOC analyzer (#1) — build that first
- Observable extraction: regex patterns for all indicator types
- Priority scoring: weighted formula based on IOC reputations + alert context
- Integration with ATT&CK mapper for technique tagging

---

## Tier 3 — SOC Operations

### 9. Shift Handoff Reports (`/shift`)
**Priority: 🟢 Low**

Auto-generate SOC shift summaries.

**Capabilities:**
- Aggregate all activities from current session
- List: investigations performed, IOCs analyzed, findings discovered, actions taken
- Open incident summary with status and next steps
- Escalation log
- Export as Markdown/PDF

**CLI Usage:**
```
/shift report                          # Generate shift summary
/shift export pdf                      # Export as PDF
```

**Implementation Notes:**
- Create `hackbot/core/shift_report.py`
- Pull data from session memory, findings, tool history
- AI-generated narrative summary
- Reuse existing PDF/report infrastructure

---

### 10. STIX/TAXII Export (`/stix`)
**Priority: 🟢 Low**

Threat intelligence sharing in standard format.

**Capabilities:**
- Package IOCs as STIX 2.1 bundles (indicators, observables, relationships)
- Package findings as STIX attack patterns
- TAXII 2.1 client for pushing to threat intel platforms
- TLP marking (WHITE, GREEN, AMBER, RED)

**CLI Usage:**
```
/stix export                           # Export session IOCs as STIX bundle
/stix export --tlp amber               # With TLP marking
/stix push --server https://taxii.example.com  # Push to TAXII server
```

**Implementation Notes:**
- Create `hackbot/core/stix_export.py`
- Use `stix2` Python library
- Map CVE/IOC/finding data to STIX SDOs
- Optional TAXII client (`taxii2-client`)

---

## Implementation Order

| Phase | Features | Effort | Dependencies |
|-------|----------|--------|-------------|
| **Phase 1** | #1 IOC Analyzer | ~2 days | Free API keys |
| **Phase 2** | #4 IR Playbooks | ~1 day | None (data + AI) |
| **Phase 3** | #3 Phishing Analyzer | ~1 day | IOC Analyzer |
| **Phase 4** | #2 Log Analyzer | ~2 days | None |
| **Phase 5** | #8 Alert Enrichment | ~1 day | IOC Analyzer |
| **Phase 6** | #5 Threat Hunt Mode | ~2 days | ATT&CK Mapper |
| **Phase 7** | #7 YARA Generator | ~1 day | None |
| **Phase 8** | #6 PCAP Analyzer | ~1 day | tshark |
| **Phase 9** | #9 Shift Reports | ~0.5 day | Session memory |
| **Phase 10** | #10 STIX/TAXII | ~1 day | stix2 library |

---

## File Structure (Planned)

```
hackbot/
  core/
    ioc.py              # IOC Analyzer (#1)
    log_analyzer.py     # Log Analyzer (#2)
    phishing.py         # Phishing Analyzer (#3)
    incident.py         # IR Playbooks (#4)
    threat_hunt.py      # Threat Hunt Mode (#5)
    pcap.py             # PCAP Analyzer (#6)
    yara_gen.py         # YARA Rule Generator (#7)
    alert_triage.py     # Alert Enrichment (#8)
    shift_report.py     # Shift Handoff Reports (#9)
    stix_export.py      # STIX/TAXII Export (#10)
manual/
    14-soc-features.md  # SOC manual page (after implementation)
```

---

## Config Keys (Planned)

```yaml
agent:
  vt_api_key: ""           # VirusTotal
  abuseipdb_api_key: ""    # AbuseIPDB
  shodan_api_key: ""       # Shodan
  greynoise_api_key: ""    # GreyNoise
  otx_api_key: ""          # AlienVault OTX
```

Environment variable overrides:
```
VT_API_KEY, ABUSEIPDB_API_KEY, SHODAN_API_KEY, GREYNOISE_API_KEY, OTX_API_KEY
```

---

> **Status**: Planning complete. Start with Phase 1 (IOC Analyzer) when ready.
