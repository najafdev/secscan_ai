<!-- SecScan AI document -->
# 📖 SecScan AI Enterprise User & Command Guide

Welcome to the official user manual for **SecScan AI Enterprise**, the state-of-the-art AI-powered penetration testing, vulnerability assessment, and Security Operations Center (SOC) platform.

---

## 📌 Table of Contents
1. [System Prerequisites & Installation](#1-system-prerequisites--installation)
2. [Configuration Settings](#2-configuration-settings)
3. [Command Line Interface (CLI) Reference](#3-command-line-interface-cli-reference)
4. [Interactive Console Options (0–16)](#4-interactive-console-options-016)
5. [Enterprise Web Dashboard GUI](#5-enterprise-web-dashboard-gui)
6. [Advanced SOC & SIEM Correlation Engine](#6-advanced-soc--siem-correlation-engine)
7. [Compliance & Threat Model Frameworks](#7-compliance--threat-model-frameworks)

---

## 1. System Prerequisites & Installation

### Prerequisites
* **Operating System**: Kali Linux, Debian/Ubuntu, macOS, or Windows WSL2 (Ubuntu 20.04+).
* **Python Version**: Python 3.8+ (Python 3.10+ recommended).
* **Docker & Docker-Compose**: For containerized deployment, database, and Redis.
* **Hardware Requirements**: Minimum 4GB RAM, 20GB free space.

### Installation Options

#### Option A: Local Virtual Environment (Recommended for Development)
```bash
# Clone the repository
git clone https://github.com/najafdev/secscan_ai.git
cd SecScan AI

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -r requirements-dev.txt

# Run installation check
python3 test_installation.py
```

#### Option B: Docker Containers (Recommended for Production)
```bash
# Build the container stack
docker-compose build

# Start services (App, Worker, Postgres, Redis, Prometheus, Grafana, ELK)
docker-compose up -d
```

---

## 2. Configuration Settings

SecScan AI settings can be controlled via environment variables (in `.env`) and the configuration file (`config.ini`).

### 1. Environment File (`.env`)
Copy the `.env.example` to `.env` and fill in active keys:
```ini
# AI Provider Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIzaSy...
DEEPSEEK_API_KEY=sk-ds-...
GLM_API_KEY=...
OPENROUTER_API_KEY=sk-or-...
ORCAROUTER_API_KEY=sk-orca-...

# Database Settings
DATABASE_URL=postgresql://secscan_ai:secscan_ai_secure_pass@localhost:5432/secscan_ai

# Platform Config
SECSCAN_AI_MODEL=gpt-5
SECRET_KEY=supersecretjwtkey123!
```

### 2. Config File (`config.ini`)
Contains service configurations, performance tuning, and threshold metrics:
* **`[app]`**: Versioning, logging levels, session timeouts.
* **`[ai_engine]`**: Fallback chains, temperature thresholds, model overrides.
* **`[database]`**: Host, user, connection pools.
* **`[scanners]`**: Port ranges, rate limits, Nmap argument tuning.

---

## 3. Command Line Interface (CLI) Reference

You can run SecScan AI in direct execution mode or launch specific service daemons directly using CLI switches.

### CLI Commands Syntax
```bash
python3 advance_secscan_ai.py [SWITCHES]
```

### Supported CLI Switches

| Switch | Argument | Description | Example |
|--------|----------|-------------|---------|
| `--target` | String | Target IP, Domain, or CIDR network range | `--target scanme.nmap.org` |
| `--scope` | String | Description of assessment scope | `--scope "Internal Web App Pentest"` |
| `--auth-key` | String | Enterprise authorization token | `--auth-key "AUTH_SECRET_KEY"` |
| `--assessment-type` | `black-box`, `white-box`, `gray-box` | Assessment methodology configuration | `--assessment-type black-box` |
| `--compliance` | `OWASP`, `NIST`, `ISO27001`, `SOC2` | Compliance mapping database filter | `--compliance OWASP` |
| `--api` | None | Starts the Flask API daemon service | `--api` |
| `--web` | None | Launches the local Flask Web Dashboard | `--web` |
| `--realtime` | None | Launches the real-time WebSocket metrics | `--realtime` |
| `--config` | File Path | Specifies a custom path to a config.ini file | `--config custom_config.ini` |

### Command Execution Examples

#### 1. Start a Full Unattended Automatic Assessment
```bash
python3 advance_secscan_ai.py \
  --target 192.168.1.50 \
  --scope "PCI Segment Server A" \
  --auth-key "SECURE_KEY" \
  --assessment-type gray-box \
  --compliance NIST
```

#### 2. Spin Up Web UI Dashboard and API Server
```bash
python3 advance_secscan_ai.py --web
```

#### 3. Run Automated Tests
```bash
pytest tests/ unit/ -v
```

---

## 4. Interactive Console Options (0–16)

When executed without arguments (`python3 advance_secscan_ai.py`), SecScanAI opens an interactive console menu.

### Menu Breakdown

```
  ┌────────────────────────────────────────────────────────┐
  │              SECSCAN_AI ENTERPRISE CONSOLE                │
  └────────────────────────────────────────────────────────┘
```

#### 1. Full Enterprise Pentest (All 6 Phases)
Executes the comprehensive automated penetration testing cycle:
1. **Planning & OSINT**: Subdomain harvesting, DNS/Whois lookup, active port sweeping.
2. **Scanning**: Nmap port enumeration, Nikto vulnerability check, service detection.
3. **Exploitation**: Custom exploit payload generation and safe test execution.
4. **Post-Exploitation**: Automated execution checks (e.g., privilege escalation scripts).
5. **Reporting**: Assembles findings, metrics, remediation lists, and exports.
6. **Retesting**: Validates prior issues to confirm if they have been patched.

#### 2. Run Specific Phase
Allows isolated execution of a single phase (e.g., run Reconnaissance only or generate reports on existing database findings).

#### 3. Custom Assessment Workflow
Creates custom combinations of vulnerability scans (e.g., only execute SQL injection & XSS tests against a scope).

#### 4. View Reports & Analytics
Inspects local database records of current and past penetration test sessions.

#### 5. Generate Executive Summary
Invokes the selected AI Model engine to generate a high-level security summary tailored for corporate executives.

#### 6. Real-time Dashboard
Displays dynamic metrics, system health, queue lengths, and active worker count in the CLI.

#### 7. User & Permission Management (RBAC)
Sets up role-based access control. Assigns roles (Admin, Lead, Senior, Analyst) and registers new user accounts.

#### 8. System Configuration
Views and edits active properties (timeouts, task parallelization settings, and database endpoints).

#### 9. Compliance Management
Queries framework maps to view corresponding control details for OWASP (including API Top 10 and LLM 2025/2026 guidelines), NIST, and ISO27001.

#### 10. Cloud & Container Management
Performs automated scans on cloud setups and local containers (scans Kubernetes configurations and runc environments).

#### 11. AI Engine Configuration
Sets active models (GPT-5, Gemini 3.5, Claude 5, etc.), updates provider keys, and configures fallback thresholds.

#### 12. Tool Management & Updates
Checks if external tools (Nmap, Nikto, Masscan, Gobuster, SQLMap, LinPEAS, WinPEAS) are installed, runs missing installations automatically, and updates tools to their latest versions.

#### 13. Start API Server
Spins up the REST API gateway daemon inside the current console session.

#### 14. Voice Command Mode
Enables voice recognition commands ("Start pentest on target.com", "Generate report").

#### 15. Launch Web Dashboard
Fires up the local Flask web development server and provides a local link (`http://127.0.0.1:8080`).

#### 16. Advanced SOC Analysis
Opens the interactive SOC subsystem to run threat analysis pipelines, parse Syslog feeds, and view correlation alerts.

#### 0. Exit Application
Closes active threads, updates logs, and exits the application cleanly.

---

## 5. Enterprise Web Dashboard GUI

The Web Dashboard offers a graphical interface for real-time monitoring and scan management.

### Accessing the Web Dashboard
1. Run `python3 advance_secscan_ai.py --web`.
2. Open your browser and navigate to `http://localhost:8080`.

### UI Layout
* **Dashboard Tab**: Displays active scans, tool status, database stats, and interactive vulnerability chart widgets.
* **New Assessment Tab**: Provides a form to configure parameters (targets, scope, assessment types, and compliance rules) and start a pentest session.
* **Findings Tab**: Interactive inspector modal to drill down into vulnerability summaries, CVSS 3.1 severity scores, exploit PoCs, and recommendations.
* **Compliance Mapping**: Displays mapping graphs of found vulnerabilities categorized by compliance frameworks.
* **Live Console**: Web terminal displaying real-time log messages from background workers.

---

## 6. Advanced SOC & SIEM Correlation Engine

The SOC subsystem ingests audit logs and correlates events to identify complex threats.

### Log Ingestion & Normalization
* **Log Formats**: Automatically normalizes standard RFC Syslog, structured application JSON, CEF, Firewall logs, and custom CSV feeds.
* **IOC Extraction**: Extracts IPs, hostnames, domains, file hashes (MD5/SHA256), registry keys, and CVE identifiers.

### Alert Correlation Rules
Detects complex attack chains in real-time:
* **Brute Force (T1110)**: Frequent authentication failures followed by a success.
* **Port Scans (T1046)**: Rapid connection attempts to diverse host ports.
* **C2 Beacons (T1071)**: Repetitive beacon requests within tight time gaps.
* **Ransomware Activity (T1486)**: Rapid, massive directory write operations.
* **LLM Prompt Injection**: Direct jailbreak patterns in model inputs.

### SIEM Integration Setup
You can connect external logs to SecScan AI's correlation engine:
1. **Splunk**: Configure REST API (port 8089) and HTTP Event Collector (HEC) for forwarding.
2. **IBM QRadar**: Setup API endpoint and Ariel AQL query endpoints.
3. **Elasticsearch**: Setup cluster endpoint (port 9200) and index mapping.
4. **Webhooks**: Connect Slack or Microsoft Teams for real-time alert broadcasts.

---

## 7. Compliance & Threat Model Frameworks

SecScan AI maintains mapping templates for standard security guidelines:

* **OWASP Top 10 API Security (2023)**: Mapped with controls for **BOLA (Broken Object Level Authorization)** and **SSRF (Server-Side Request Forgery)**.
* **OWASP Top 10 for LLM Applications (2025/2026)**: Mapped with checks for **Prompt Injection (LLM01)**, **Insecure Output Handling (LLM02)**, and **Excessive Agency (LLM08)**.
* **Critical CVE Database**: Scans for signature indicators including **CVE-2024-3094** (XZ supply chain backdoor), **CVE-2024-21626** (runc Container Escape), and **CVE-2024-4577** (PHP CGI RCE).
* **Regulatory Maps**: Comprehensive tags mapping findings to **NIST SP 800-53**, **ISO 27001**, **SOC 2**, and **PCI-DSS** categories.
