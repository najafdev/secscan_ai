<!-- SecScan AI document -->
# SecScan AI SOC Analysis Console & SIEM Integration Guide

This guide details how to configure, query, and use the Security Operations Center (SOC) Analysis Engine and external SIEM connectors within the SecScan AI framework.

---

## 1. Getting Started

The SOC Analysis Engine can be accessed via the interactive command-line interface or directly via CLI arguments.

To launch the SOC Console interactively:

```bash
python advance_secscan_ai.py
```

From the Main Menu, choose Option **`16` (Advanced SOC Analysis)**:

```
SecScan AI Enterprise Main Menu
...
15 | Web            | Launch Web Dashboard
16 | SOC            | Advanced SOC Analysis
0  | System         | Exit Application
```

---

## 2. Ingesting & Analyzing Logs

The SOC engine parses raw unstructured log lines, extracts threat indicators, detects statistical anomalies, maps threats to MITRE ATT&CK techniques, and generates recommended incident response playbooks.

Once inside the SOC Console, you have three primary methods to ingest logs:

### Option 1: Analyze Logs from a File
Prompts for a file path. Reads all lines, auto-detects formats (Syslog, JSON, Firewall, CEF, CSV, Windows Event), and runs the detection pipeline.
* **Example**: `/var/log/syslog` or `/var/log/nginx/access.log`.

### Option 2: Analyze Raw Logs (Pasted Text)
Allows you to paste logs directly into the terminal interface. Press `Enter` then `Ctrl-D` (Linux/macOS) or `Ctrl-Z` (Windows) to run the analysis.

### Option 3: Analyze Built-in Attack Scenario (Sample Logs)
Loads a pre-configured multi-stage corporate network attack scenario, demonstrating:
1. **Credential Access (Brute Force)**: Multiple failed SSH attempts.
2. **Discovery (Port Scan)**: Firewall rejected packets across multiple ports.
3. **Exploitation (SQL Injection)**: Web requests containing SQL payload structures.
4. **Execution (Suspicious Scripts)**: Obfuscated PowerShell execution blocks.
5. **Command & Control (Reverse Shell)**: Netcat callback socket creation.
6. **Impact (Ransomware)**: High-rate directory changes renaming files to `.locked`.

---

## 3. SIEM Integrations (Splunk, QRadar, and Others)

SecScan AI supports active bidirectional SIEM integrations. You can retrieve logs directly via SIEM search APIs and push correlated alerts back to their endpoints.

Choose Option **`5` (Configure SIEM Connections)** in the SOC Console to register and test connections.

### 3.1 Splunk Integration
* **Search / Query Endpoint**: Splunk REST API search job creator (`/services/search/jobs` and `/services/search/jobs/{sid}/results`).
* **Alert Forwarding Endpoint**: Splunk HTTP Event Collector (HEC) (`/services/collector/event`).
* **Configuration Parameters**:
  * **Endpoint URL**: e.g., `https://splunk-server:8089` (REST API management) or `https://splunk-server:8088` (HEC receiver).
  * **HEC Token / API Key**: Splunk Authorization Token.
  * **Simulation Mode**: If enabled, simulates Splunk queries offline.

### 3.2 IBM QRadar Integration
* **Search / Query Endpoint**: QRadar Ariel REST API query engine (`/api/ariel/searches`).
* **Alert Forwarding Endpoint**: Custom API event interface (`/api/custom_events`) to raise offenses.
* **Configuration Parameters**:
  * **Endpoint URL**: QRadar Console Management URL (typically port 443).
  * **SEC Token**: QRadar Security Token.

### 3.3 Elasticsearch Integration
* **Search / Query Endpoint**: Search Query DSL (`/_search`).
* **Alert Forwarding Endpoint**: Document indexer `/secscan_ai-soc-alerts/_doc`.
* **Configuration Parameters**:
  * **Endpoint URL**: e.g., `http://localhost:9200`.
  * **API Key**: Elasticsearch authorization key.

### 3.4 Generic Webhooks (Slack, MS Teams, SOAR)
* **Ingestion**: Webhooks are push-only and do not support pulling logs.
* **Alert Forwarding**: Pushes rich alert blocks to target incoming webhook receivers.
* **Configuration Parameters**:
  * **Webhook URL**: e.g. Slack Webhook `https://hooks.slack.com/services/...` or Teams Connector URL.

---

## 4. Fetching & Analyzing SIEM Logs

To pull logs directly from your SIEM database:
1. Select Option **`6` (Fetch and Analyze Logs from Configured SIEM)**.
2. Select your registered connection ID.
3. Input the search query:
   * **Splunk**: e.g. `index=security sourcetype=syslog failed`
   * **QRadar**: e.g. `SELECT UTF8(payload) FROM events WHERE payload CONTAINS 'failed' LIMIT 50`
   * **Elasticsearch**: e.g. `message:failed`
4. The console pulls the log records, displays ingestion statistics, triggers correlation rules, maps MITRE ATT&CK techniques, and displays recommended playbooks.
5. You can choose to forward the resulting correlated alerts back to your SIEM receivers.

---

## 5. Internals & Correlation Rules

The engine correlates log lines using sliding-time window signatures defined in the `AlertCorrelationEngine`.

### Active Correlation Signatures

| Rule Name | Category | Severity | MITRE Tactic | Target Keywords |
|---|---|---|---|---|
| **Brute Force Attack** | Credential Access | HIGH | T1110 | `failed`, `login`, `invalid password` |
| **Port Scan** | Discovery | MEDIUM | T1046 | `scan`, `syn`, `port refusal` |
| **Suspicious Command** | Execution | HIGH | T1059 | `powershell`, `certutil`, `nc -e` |
| **Data Exfiltration** | Exfiltration | CRITICAL | T1048 | `exfiltrat`, `pastebin`, `mega.nz` |
| **Ransomware / Malware** | Impact | CRITICAL | T1486 | `ransomware`, `locked`, `README_DECRYPT` |
| **Privilege Escalation** | Privilege Escalation | HIGH | T1548 | `sudo`, `getsystem`, `uac bypass` |
| **Lateral Movement** | Lateral Movement | HIGH | T1021 | `psexec`, `wmiexec`, `rdp` |
| **Log Tampering** | Defense Evasion | HIGH | T1070 | `log cleared`, `wevtutil cl`, `history -c` |
| **Credential Dumping** | Credential Access | CRITICAL | T1003 | `mimikatz`, `secretsdump`, `lsass` |
| **C2 Beaconing** | Command & Control | CRITICAL | T1071 | `beacon`, `cobalt strike`, `dns tunnel` |

### Anomaly Tracking Metric Baselines
* **Hourly Event Volume**: Flags spikes where $Z\text{-score} \ge 2.5$.
* **Source IP Diversity**: Triggers alert if unique IP source ratio exceeds $80\%$ with $>20$ distinct addresses.
* **Failure/Error Rate**: Flags anomaly if errors or server failures exceed $30\%$ of total logs.
* **Off-Hours Activity**: Evaluates execution trends between 22:00 and 06:00.
