# 13. NVD API Integration

HackBot integrates with the [National Vulnerability Database (NVD)](https://nvd.nist.gov/) API v2.0 to provide real-time CVE intelligence. With an NVD API key configured, the agent automatically enriches nmap scan results with known vulnerabilities, giving you instant visibility into exploitable services.

---

## Overview

| Component | Description |
|-----------|-------------|
| **API** | NVD REST API v2.0 (`services.nvd.nist.gov/rest/json/cves/2.0`) |
| **Rate Limit (no key)** | 5 requests / 30 seconds (6.5s interval) |
| **Rate Limit (with key)** | 50 requests / 30 seconds (0.6s interval) — **10× faster** |
| **Auto Enrichment** | Agent auto-maps nmap services to CVEs after every scan |
| **Finding Ingest** | High/critical CVEs (CVSS ≥ 7.0) auto-recorded to VulnDB |
| **Data** | CVSS v3.1/v3.0/v2.0 scores, CWE weaknesses, CPE matches, references, PoC exploits |
| **Exploit Sources** | GitHub PoC repositories (sorted by stars) |

---

## Getting an API Key

NVD API keys are **free** and take about 30 seconds to obtain:

1. Go to [https://nvd.nist.gov/developers/request-an-api-key](https://nvd.nist.gov/developers/request-an-api-key)
2. Enter your email address and organization (optional)
3. Check your email for the confirmation link
4. Click the link to activate — your key is displayed once
5. Save the key securely

> ⚠️ The key is shown only once. If you lose it, you must request a new one.

---

## Configuration

### Method 1: CLI Command (Recommended)

```
/nvd-key YOUR_NVD_API_KEY
```

This saves the key to your config file and immediately activates it for all CVE lookups.

To check current status:
```
/nvd-key
```

**Output (key configured):**
```
ℹ NVD API key is set: 89bd****c371
ℹ Rate limit: 50 requests / 30 seconds

Usage: /nvd-key <key>
Get a free key at: https://nvd.nist.gov/developers/request-an-api-key
```

### Method 2: CLI Flag

```bash
hackbot --nvd-key YOUR_NVD_API_KEY
hackbot agent 192.168.1.1 --nvd-key YOUR_NVD_API_KEY
```

### Method 3: Environment Variable

```bash
export NVD_API_KEY=YOUR_NVD_API_KEY
hackbot
```

Add to your shell profile (`~/.bashrc`, `~/.zshrc`) for persistence:
```bash
echo 'export NVD_API_KEY=YOUR_NVD_API_KEY' >> ~/.bashrc
```

### Method 4: Config File

Edit `~/.config/hackbot/config.yaml`:
```yaml
agent:
  nvd_api_key: YOUR_NVD_API_KEY
```

### Method 5: GUI Settings

Open the GUI (`hackbot --gui`) → Settings panel → enter your NVD API key and save.

---

## How It Works

### Manual CVE Lookup (`/cve`)

The `/cve` command uses the NVD API key automatically when configured:

```
/cve CVE-2021-44228                  # Lookup specific CVE by ID
/cve Apache 2.4.49                   # Search by keyword
/cve --severity critical log4j       # Filter by severity
/cve --nmap <paste nmap output>      # Map nmap services to CVEs
```

**Example output:**
```
## CVE Results

**5 vulnerabilities found**

| CVE ID | CVSS | Severity | Description |
|--------|------|----------|-------------|
| CVE-2021-44228 | 10.0 | Critical | Apache Log4j2 RCE via JNDI... |
| CVE-2021-45046 | 9.0 | Critical | Apache Log4j2 Thread Context... |
| CVE-2021-45105 | 7.5 | High | Apache Log4j2 DoS via... |

### CVE-2021-44228 — CVSS 10.0 (Critical)

Apache Log4j2 2.0-beta9 through 2.15.0 JNDI features do not protect
against attacker controlled LDAP and other JNDI related endpoints...

**Weaknesses:** CWE-502, CWE-400
**Published:** 2021-12-10

**Known Exploits:**
- kozmer/log4j-shell-poc ⭐ 1542
- fullhunt/log4j-scan ⭐ 3201
```

### Agent Auto CVE Enrichment

This is the key feature. When the agent runs an `nmap` scan during an assessment, HackBot **automatically**:

1. **Parses** the nmap output for open ports with service/version banners
2. **Queries NVD** for each unique service+version combination (up to 5 CVEs per service)
3. **Appends** the CVE intelligence report to the tool result, so the AI sees it
4. **Records** high-severity CVEs (CVSS ≥ 7.0) as findings in the local VulnDB
5. **Feeds** the enriched data back to the AI for smarter follow-up decisions

**What the agent sees after nmap:**

```
**[nmap]** SUCCESS (exit=0, 12.3s)
Command: `nmap -sV -sC 192.168.1.100`

PORT     STATE SERVICE     VERSION
22/tcp   open  ssh         OpenSSH 8.2p1 Ubuntu 4ubuntu0.5
80/tcp   open  http        Apache httpd 2.4.49
443/tcp  open  ssl/https   Apache httpd 2.4.49
3306/tcp open  mysql       MySQL 5.7.38

## Nmap Service → CVE Mapping

**12 vulnerabilities** across **3 services**

### 🔓 80/tcp http (Apache httpd 2.4.49)

- 🔴 **CVE-2021-41773** (CVSS 7.5) — Path traversal in Apache 2.4.49...
- 🔴 **CVE-2021-42013** (CVSS 9.8) — Path traversal and RCE in Apache 2.4.49/2.4.50...
- 🟠 **CVE-2021-44790** (CVSS 7.5) — Buffer overflow in mod_lua...

### 🔓 22/tcp ssh (OpenSSH 8.2p1)

- 🟡 **CVE-2021-41617** (CVSS 5.5) — Privilege escalation via AuthorizedKeysCommand...

### 🔓 3306/tcp mysql (MySQL 5.7.38)

- 🟠 **CVE-2022-21589** (CVSS 7.1) — MySQL Server optimizer vulnerability...
```

The AI then uses this CVE data to:
- Prioritize high-severity vulnerabilities for further exploitation
- Reference specific CVE IDs in findings
- Suggest targeted remediation steps
- Skip further enumeration on already-documented vulnerabilities

### Automatic Finding Recording

CVEs with CVSS ≥ 7.0 are automatically saved to the local VulnDB:

| Field | Value |
|-------|-------|
| **Title** | `CVE-2021-42013 — 80/tcp http (Apache httpd 2.4.49)` |
| **Severity** | Critical (CVSS ≥ 9.0) or High (CVSS ≥ 7.0) |
| **Description** | Full CVE description from NVD |
| **Evidence** | `CVSS 9.8 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)` |
| **Recommendation** | `Patch or mitigate CVE-2021-42013. See: <NVD reference>` |
| **Tool** | `nmap+nvd` |

These findings appear in:
- `/findings` summary
- `/vulndb search` results
- PDF/HTML/Markdown reports
- Risk trend snapshots

---

## Rate Limiting

HackBot enforces NVD rate limits to avoid API bans:

| Configuration | Limit | Interval | Throughput |
|--------------|-------|----------|------------|
| **No API key** | 5 req / 30s | 6.5 seconds | ~9 lookups/min |
| **With API key** | 50 req / 30s | 0.6 seconds | ~100 lookups/min |

Rate limiting is global — all CVE operations (manual `/cve`, agent auto-enrichment, Telegram `/cve`) share the same throttle.

**Practical impact:**

- Without key: An nmap scan finding 5 services takes ~32 seconds for CVE lookups
- With key: The same scan takes ~3 seconds

For assessments with many ports open, the API key makes a significant difference.

---

## Data Returned per CVE

Each CVE lookup returns:

| Field | Description |
|-------|-------------|
| `cve_id` | CVE identifier (e.g. `CVE-2021-44228`) |
| `description` | Full English description from NVD |
| `cvss_score` | Base score (0.0 – 10.0), preferring CVSS v3.1 |
| `cvss_vector` | Vector string (e.g. `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`) |
| `severity` | CRITICAL, HIGH, MEDIUM, LOW, or Unknown |
| `published` | Publication date |
| `modified` | Last modified date |
| `references` | Up to 10 reference URLs (advisories, patches, etc.) |
| `cpe_matches` | Up to 20 CPE identifiers (affected products) |
| `weaknesses` | CWE identifiers (e.g. CWE-502, CWE-79) |
| `exploits` | GitHub PoC repositories with star counts |

---

## Integration Points

The NVD API key is used across the entire HackBot ecosystem:

| Component | How NVD Key Is Used |
|-----------|-------------------|
| **Agent Mode** | Auto CVE enrichment after every nmap scan |
| **CLI `/cve`** | Manual CVE lookup, keyword search, nmap mapping |
| **GUI CVE Panel** | All 4 tabs (Lookup, Search, Exploits, Nmap-to-CVE) |
| **Telegram Bot** | `/cve` command in the Telegram interface |
| **PDF Reports** | CVE data included in findings section |
| **VulnDB** | High-severity CVEs auto-ingested as findings |

---

## Telegram Bot

The Telegram bot's `/cve` command also respects the configured NVD API key:

```
/cve CVE-2021-44228       → Full CVE details with exploits
/cve log4j               → Keyword search (top results by CVSS)
```

---

## Troubleshooting

### "CVE lookups are slow"

You likely don't have an API key configured. Check with:
```
/nvd-key
```
Get a free key at [nvd.nist.gov/developers/request-an-api-key](https://nvd.nist.gov/developers/request-an-api-key).

### "No CVEs found for service"

NVD keyword search depends on accurate service banners. If nmap shows a generic banner (e.g., just `http` without a product name), CVE mapping may return no results. Use `-sV` with nmap for version detection:
```
nmap -sV -sC <target>
```

### "NVD API request failed"

- Check your internet connection
- NVD may be temporarily down — try again in a few minutes
- If using a key, ensure it hasn't expired (keys don't expire, but can be revoked)
- Rate limit may be exceeded if you're running multiple HackBot instances

### "Agent doesn't show CVE data after nmap"

Auto CVE enrichment triggers only when:
1. The executed tool is identified as `nmap`
2. The nmap command completed successfully (exit code 0)
3. The output contains parseable port/service lines

Ensure your nmap command includes `-sV` for version detection.

---

## Security Notes

- The NVD API key is stored in `~/.config/hackbot/config.yaml` (plaintext)
- Use environment variables (`NVD_API_KEY`) for CI/CD or shared environments
- The key grants read-only access to public NVD data — it cannot modify anything
- HackBot sends only the `apiKey` header to NVD; no other credentials are transmitted
- The GUI settings endpoint returns `has_nvd_api_key: true/false` (never the actual key)
