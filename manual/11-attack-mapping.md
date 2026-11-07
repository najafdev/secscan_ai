# 11. MITRE ATT&CK Mapping

HackBot maps security findings and tool usage to the [MITRE ATT&CK](https://attack.mitre.org/) Enterprise framework — the industry-standard knowledge base of adversary tactics, techniques, and procedures (TTPs). This module helps you understand which adversarial behaviors your assessment covers and generates ATT&CK Navigator layers for visual analysis.

---

## Overview

| Component | Description |
|-----------|-------------|
| **Tactics** | 14 Enterprise ATT&CK tactics (Reconnaissance → Impact) |
| **Techniques** | ~80 curated pentesting-relevant techniques |
| **Finding Rules** | 30 regex-based rules that match finding text to techniques |
| **Tool Mappings** | 26 security tools pre-mapped to techniques |
| **Navigator Export** | ATT&CK Navigator v4.5 layer JSON with gradient scoring |
| **Reports** | Markdown report, summary, PDF section |

---

## How It Works

The ATT&CK mapper analyzes two data sources from your assessment:

### 1. Findings → Techniques (Regex Rules)

Each finding's title, description, evidence, and recommendation are concatenated and matched against 30 regex patterns. A match creates a `TechniqueMapping` with:

- **Technique ID** — e.g. `T1190` (Exploit Public-Facing Application)
- **Source** — `"finding"`
- **Confidence** — `high`, `medium`, or `low`
- **Severity** — inherited from the finding

**Example rules:**

| Pattern | Technique(s) | Confidence |
|---------|-------------|------------|
| `sql.?inject` | T1190 (Exploit Public-Facing App) | high |
| `xss\|cross.?site.?script` | T1059.007 (JavaScript) | high |
| `brute.?force\|password.?spray` | T1110 (Brute Force) | high |
| `open.?port\|service.?detect` | T1046 (Network Service Scanning) | medium |
| `default.?cred` | T1078 (Valid Accounts) | high |
| `dns.?zone.?transfer` | T1590.002 (DNS) | high |

### 2. Tool History → Techniques (Static Map)

Each tool execution is looked up in the `TOOL_TECHNIQUE_MAP`. If the tool name matches, its pre-defined technique mappings are added.

**Example tool mappings:**

| Tool | Techniques |
|------|-----------|
| **nmap** | T1046 (Network Service Scanning), T1595.001 (Active Scanning: IP Blocks) |
| **nikto** | T1595.002 (Vulnerability Scanning) |
| **sqlmap** | T1190 (Exploit Public-Facing App), T1059 (Command Interpreter) |
| **hydra** | T1110 (Brute Force) |
| **gobuster** | T1595.003 (Wordlist Scanning) |
| **nuclei** | T1595.002 (Vulnerability Scanning), T1190 (Exploit Public-Facing App) |
| **subfinder** | T1590.002 (DNS), T1596 (Search Open Websites/Domains) |
| **testssl** | T1557 (Adversary-in-the-Middle), T1040 (Network Sniffing) |
| **hashcat** | T1110.002 (Password Cracking) |
| **ffuf** | T1595.003 (Wordlist Scanning), T1083 (File and Directory Discovery) |

All 26 integrated tools have ATT&CK mappings. Run `/attack tool <name>` to see any tool's mappings.

### 3. Deduplication

Mappings are deduplicated using a composite key: `{source}:{technique_id}:{source_name}`. This prevents the same technique from being listed multiple times for the same finding or tool.

---

## CLI Usage

### `/attack map`

Map current agent findings and tool history to ATT&CK techniques. Displays a full Markdown report.

```
/attack map
```

**Output includes:**
- Coverage bar (`█░` visualization of tactics covered)
- Per-tactic sections with technique listings
- Confidence icons: 🔴 High | 🟠 Medium | 🟡 Low
- Source icons: 🔍 Finding | 🔧 Tool

### `/attack summary`

Short summary suitable for quick review.

```
/attack summary
```

**Output:**
```
📊 ATT&CK Coverage: 12 techniques, 6/14 tactics
Tactics: Reconnaissance, Initial Access, Execution, Discovery, ...
Confidence: 🔴 4 high | 🟠 6 medium | 🟡 2 low
```

### `/attack layer`

Export an ATT&CK Navigator layer JSON file for visualization. The file is saved to the reports directory.

```
/attack layer
```

**Output:**
```
✅ ATT&CK Navigator layer saved: ~/.local/share/hackbot/reports/attack_layer_example_com_20260304_120000.json
Import into https://mitre-attack.github.io/attack-navigator/ to visualize
```

### `/attack tactics`

List all 14 Enterprise ATT&CK tactics.

```
/attack tactics
```

Displays a table with tactic ID, name, and description.

### `/attack techniques [tactic_id]`

List techniques, optionally filtered by tactic ID.

```
/attack techniques             # All ~80 techniques
/attack techniques TA0007      # Discovery techniques only
/attack techniques TA0001      # Initial Access techniques only
```

### `/attack tool <name>`

Show ATT&CK techniques mapped to a specific security tool.

```
/attack tool nmap
/attack tool sqlmap
/attack tool hydra
```

### `/attack lookup <technique_id>`

Look up a specific technique by its ATT&CK ID.

```
/attack lookup T1046
/attack lookup T1190
/attack lookup T1059.001
```

**Output:**
```
T1046 — Network Service Scanning
  Tactics: TA0007
  URL: https://attack.mitre.org/techniques/T1046/
  Adversaries may attempt to get a listing of services running on remote hosts.
```

---

## Agent Integration

When you run an agent assessment and it generates a PDF report (`/pdf` or `/export pdf`), the ATT&CK mapper automatically:

1. Collects all findings and tool execution history
2. Maps them to ATT&CK techniques
3. Includes an **ATT&CK Mapping** section in the PDF report with:
   - Coverage summary (unique techniques, tactics covered)
   - Per-tactic summary table (technique count, confidence breakdown)
   - Per-tactic detail tables (technique ID, name, confidence, source)

This happens alongside the existing compliance mapping — both sections appear in the PDF when data is available.

---

## ATT&CK Navigator Layer

The Navigator layer format (v4.5) is compatible with the [ATT&CK Navigator](https://mitre-attack.github.io/attack-navigator/), MITRE's official web-based tool for visualizing ATT&CK matrices.

### Layer Structure

```json
{
    "name": "HackBot: example.com",
    "versions": { "attack": "15", "navigator": "5.0.1", "layer": "4.5" },
    "domain": "enterprise-attack",
    "description": "Assessment of example.com — 15 technique mappings...",
    "techniques": [
        {
            "techniqueID": "T1046",
            "tactic": "discovery",
            "score": 4.0,
            "comment": "[high] nmap — Network Service Scanning via port scan",
            "enabled": true
        }
    ],
    "gradient": {
        "colors": ["#2d333b", "#f0883e", "#f85149"],
        "minValue": 0,
        "maxValue": 5
    },
    "legendItems": [
        { "label": "High confidence", "color": "#f85149" },
        { "label": "Medium confidence", "color": "#f0883e" },
        { "label": "Low confidence", "color": "#d29922" }
    ]
}
```

### Scoring System

| Factor | Score |
|--------|-------|
| High confidence | 4 |
| Medium confidence | 3 |
| Low confidence | 2 |
| Critical severity bonus | +1.0 |
| High severity bonus | +0.5 |

Maximum score per technique is 5.0. The gradient maps 0→5 using dark→orange→red colors.

### How to Visualize

1. Run `/attack layer` to export the JSON file
2. Open [ATT&CK Navigator](https://mitre-attack.github.io/attack-navigator/)
3. Click **Open Existing Layer** → **Upload from local**
4. Select the exported `.json` file
5. The matrix will display with techniques color-coded by confidence/severity

---

## GUI Usage

The GUI provides 7 REST API endpoints for ATT&CK mapping:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/attack/map` | POST | Map custom findings/tool history to techniques |
| `/api/attack/from-agent` | GET | Map current agent findings to techniques |
| `/api/attack/layer` | GET | Generate Navigator layer JSON from agent data |
| `/api/attack/tactics` | GET | List all 14 ATT&CK tactics |
| `/api/attack/techniques` | GET | List techniques (optional `?tactic_id=TA0007` filter) |
| `/api/attack/technique/<id>` | GET | Get technique details by ID |
| `/api/attack/tool/<name>` | GET | Get technique mappings for a tool |

### POST `/api/attack/map`

```json
{
    "findings": [
        {"title": "SQL Injection", "description": "...", "severity": "Critical"}
    ],
    "tool_history": [
        {"tool": "nmap", "command": "nmap -sV target"}
    ],
    "target": "example.com"
}
```

**Response:** Full `AttackReport.to_dict()` output grouped by tactic.

### GET `/api/attack/from-agent`

Returns both the structured report data and a pre-formatted Markdown string:

```json
{
    "report": { "target": "...", "by_tactic": {...}, ... },
    "markdown": "# MITRE ATT&CK Mapping\n..."
}
```

---

## Telegram Usage

The `/attack` command is available in the Telegram bot:

| Command | Description |
|---------|-------------|
| `/attack` or `/attack map` | Map agent findings — displays summary |
| `/attack full` | Full Markdown ATT&CK report |
| `/attack tactics` | List all tactics |
| `/attack tool <name>` | Show techniques for a tool |
| `/attack lookup <id>` | Look up a technique |

---

## Covered Tactics

| # | ID | Tactic | Description |
|---|-----|--------|-------------|
| 1 | TA0043 | Reconnaissance | Gathering information to plan future operations |
| 2 | TA0042 | Resource Development | Establishing resources to support operations |
| 3 | TA0001 | Initial Access | Trying to get into your network |
| 4 | TA0002 | Execution | Trying to run malicious code |
| 5 | TA0003 | Persistence | Trying to maintain their foothold |
| 6 | TA0004 | Privilege Escalation | Trying to gain higher-level permissions |
| 7 | TA0005 | Defense Evasion | Trying to avoid being detected |
| 8 | TA0006 | Credential Access | Trying to steal account names and passwords |
| 9 | TA0007 | Discovery | Trying to figure out your environment |
| 10 | TA0008 | Lateral Movement | Trying to move through your environment |
| 11 | TA0009 | Collection | Trying to gather data of interest |
| 12 | TA0011 | Command and Control | Trying to communicate with compromised systems |
| 13 | TA0010 | Exfiltration | Trying to steal data |
| 14 | TA0040 | Impact | Trying to manipulate, interrupt, or destroy systems |

---

## Tool-to-Technique Reference

All 26 HackBot-integrated tools and their ATT&CK technique mappings:

| Tool | Technique ID | Technique Name | Confidence |
|------|-------------|----------------|------------|
| nmap | T1046 | Network Service Scanning | high |
| nmap | T1595.001 | Active Scanning: IP Blocks | high |
| nikto | T1595.002 | Vulnerability Scanning | high |
| sqlmap | T1190 | Exploit Public-Facing Application | high |
| sqlmap | T1059 | Command and Scripting Interpreter | medium |
| nuclei | T1595.002 | Vulnerability Scanning | high |
| nuclei | T1190 | Exploit Public-Facing Application | medium |
| hydra | T1110 | Brute Force | high |
| john | T1110.002 | Password Cracking | high |
| hashcat | T1110.002 | Password Cracking | high |
| gobuster | T1595.003 | Wordlist Scanning | high |
| ffuf | T1595.003 | Wordlist Scanning | high |
| ffuf | T1083 | File and Directory Discovery | medium |
| dirb | T1595.003 | Wordlist Scanning | high |
| wfuzz | T1595.003 | Wordlist Scanning | high |
| subfinder | T1590.002 | DNS | high |
| subfinder | T1596 | Search Open Websites/Domains | medium |
| amass | T1590.002 | DNS | high |
| amass | T1596 | Search Open Websites/Domains | medium |
| whois | T1596.002 | WHOIS | medium |
| dig | T1590.002 | DNS | medium |
| whatweb | T1592 | Gather Victim Host Information | medium |
| testssl | T1557 | Adversary-in-the-Middle | medium |
| testssl | T1040 | Network Sniffing | low |
| sslscan | T1557 | Adversary-in-the-Middle | medium |
| masscan | T1046 | Network Service Scanning | high |
| curl | T1071.001 | Web Protocols | low |
| wget | T1071.001 | Web Protocols | low |
| enum4linux | T1087 | Account Discovery | high |

---

## Data Model

### Tactic
```python
@dataclass
class Tactic:
    id: str           # "TA0043"
    name: str         # "Reconnaissance"
    short_name: str   # "reconnaissance" (Navigator key)
    description: str
```

### Technique
```python
@dataclass
class Technique:
    id: str            # "T1046" or "T1059.001" (subtechnique)
    name: str          # "Network Service Scanning"
    tactic_ids: list   # ["TA0007"]
    description: str
    is_subtechnique: bool
    parent_id: str     # "T1059" for subtechniques
    url: str           # Auto-generated: https://attack.mitre.org/techniques/T1046/
```

### TechniqueMapping
```python
@dataclass
class TechniqueMapping:
    technique: Technique
    source: str        # "finding" | "tool" | "manual"
    source_name: str   # finding title or tool name
    confidence: str    # "high" | "medium" | "low"
    notes: str
    severity: str      # from the finding (Critical/High/Medium/Low/Info)
```

### AttackReport
```python
@dataclass
class AttackReport:
    mappings: list     # List[TechniqueMapping]
    target: str
    total_findings: int
    total_tools: int

    def to_dict(self):
        # Returns dict grouped by tactic name with counts
```

---

## Tips

- **Run after agent assessments** — the more findings and tool executions, the richer the ATT&CK mapping.
- **Export Navigator layers** for reports — stakeholders can interactively explore the matrix.
- **Check tool coverage** before an assessment — `/attack tool <name>` shows what ATT&CK techniques each tool maps to, helping you plan assessments that cover more of the matrix.
- **Combine with compliance mapping** — `/compliance` maps to defensive controls, `/attack` maps to offensive techniques. Together they give a complete picture.
- **PDF reports include both** — compliance and ATT&CK sections appear automatically.

---

Next: [Vulnerability Database →](12-vulnerability-database.md)
