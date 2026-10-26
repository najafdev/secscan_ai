<!-- SecScan AI document -->
# 🚀 SecScan AI Enterprise Release History

This document logs the release updates, bug fixes, and feature integrations for SecScan AI Enterprise.

---

> [!IMPORTANT]
> ### 💖 Critical Notice: Project Sponsorship, Donations & Funding Required
> SecScan AI Enterprise is an independent, community-driven AI security assessment framework. Maintaining cutting-edge penetration testing tools, supporting multi-provider AI model integrations, and sustaining security research infrastructure requires continuous resources. **We urgently require funds, donations, and sponsorships to maintain and advance this project.**
>
> **Please consider donating and sponsoring SecScan AI development!**
> - **GitHub Sponsors (Active)**: [Sponsor @yashab-cyber on GitHub Sponsors](https://github.com/sponsors/yashab-cyber)
> - **Cryptocurrency Transfers**: For crypto donations (Solana, Bitcoin, Ethereum, USDT, etc.), please email: **yashabalam707@gmail.com**
> - **Sponsorships & Inquiries**: Contact creator directly at: **yashabalam707@gmail.com**
> - View full donation channels and guidelines in [DONATE.md](../DONATE.md).

---

## 🚀 Version 2026.10.23

*Release Date: October 23, 2026*

> [!IMPORTANT]
> **Official Solana Contract Address (CA):** Soon Available

We are excited to announce the release of **SecScan AI Enterprise Version 2026.10.23**! This milestone release introduces the **OrcaRouter Cyber Inference** model provider contributed by community developer **[@beilsteinernest215-cmd](https://github.com/beilsteinernest215-cmd)** (PR #26), a comprehensive **Cloud Security Posture Management (CSPM)** and **Kubernetes Security Posture Management (KSPM)** engine with automated **Infrastructure-as-Code (IaC) Security Auditing**, AI-powered cloud blast radius threat modeling, automated multi-cloud remediation scripting, and robust installation enhancements for container and PRoot environments.

### 🌟 What's New in Version 2026.10.23

#### 1. 🐋 OrcaRouter Cyber Inference Provider (PR #26 by [@beilsteinernest215-cmd](https://github.com/beilsteinernest215-cmd))
> [!NOTE]
> Special credit and heartfelt thanks to community developer **[@beilsteinernest215-cmd](https://github.com/beilsteinernest215-cmd)** for creating and contributing **Pull Request #26 (`feat(ai): add OrcaRouter Cyber Inference as a named model provider`)**!

* **Named Model Provider Integration (`ai_engine/orcarouter.py`, `ai_engine/providers.py`)**:
  * Added **OrcaRouter Cyber Inference** (`ModelProvider.ORCAROUTER`) with official base endpoint `https://api.orcarouter.ai/v1`.
  * Specialized security reasoning routing to flagship OrcaCyber models: `orca/orcacyber-ultra-1.0` and `orca/orcacyber-zero-1.5`, with general fallback to `orcarouter/fusion`.
  * Generation-safe credential management (`credential_store`) that stores runtime API keys server-side with masked previews (`sk-orca-...0000`) without leaking secrets into client responses or debug logs.
  * Live model discovery via `GET https://api.orcarouter.ai/v1/models?capability=chat` with capability filtering (chat, multimodal, embeddings) and automatic fallback to verified seed models when unauthenticated or degraded.
* **Interactive Dashboard Integration (`templates/dashboard.html`, `static/css/style.css`)**:
  * New **AI Providers** management view in the web dashboard allowing operators to configure, update, and clear OrcaRouter API credentials on the fly.
  * Capability-filtered dynamic model selection dropdown driven by the `/api/ai/models` endpoint.

#### 2. ☁️ Cloud & Kubernetes Security Posture Management (`security/cspm_scanner.py`)
* **Multi-Cloud Posture Auditing**: Comprehensive rule-based and static analysis coverage across major cloud providers and container orchestrators:
  * **Amazon Web Services (AWS)**: S3 bucket public access (read/write), missing server-side encryption (SSE-S3 / SSE-KMS), IAM administrative wildcard privileges (`*:*`), and Security Groups with unconstrained ingress (0.0.0.0/0) to administrative and database ports (22, 3389, 3306, 5432).
  * **Microsoft Azure**: Storage Account unencrypted blob services, public network access policies, and missing HTTPS enforcement.
  * **Google Cloud Platform (GCP)**: Cloud Storage buckets exposing public permissions to `allUsers` or `allAuthenticatedUsers`, uniform bucket-level access misconfigurations.
  * **Kubernetes (K8s / KSPM)**: Privileged containers (`privileged: true`), sensitive host filesystem volume mounts (`/var/run/docker.sock`, `/etc`), hostile namespace sharing (`hostNetwork`, `hostPID`, `hostIPC`), unconfined root execution (`runAsNonRoot: false`), missing read-only root filesystems, and unconstrained RBAC ClusterRoleBindings to `system:anonymous` or `system:unauthenticated`.
* **Compliance Framework Benchmarking**: Built-in compliance checks mapped against:
  * **CIS AWS Foundations Benchmark v3.0**
  * **CIS Kubernetes Benchmark v1.8**
  * **NIST SP 800-53 Rev 5** (AC-3, AC-6, SC-8, SC-13, CM-7)
  * **MITRE ATT&CK Cloud Matrix** (T1078.004, T1530, T1552, T1610, T1611)
* **Automated Remediation Code Generation**:
  * Outputs copy-paste executable CLI commands (`aws s3api`, `az storage account update`, `gcloud storage buckets`, `kubectl delete clusterrolebinding`).
  * Generates Terraform HCL remediation blocks with secure parameters.
  * Supports direct script export via `--export-cloud-fix <script_path>`.

#### 3. 🧠 AI Cloud Blast Radius & Threat Modeling (`ai_engine/advanced_engine.py`)
* Integrated `analyze_cloud_posture()` in `AdvancedAIEngine`:
  * Evaluates multi-cloud misconfigurations using frontier LLMs.
  * Synthesizes blast-radius severity tags: `TENANT_TAKEOVER_RISK`, `CLUSTER_TAKEOVER_RISK`, `DATA_EXFILTRATION_RISK`, and `LATERAL_MOVEMENT_RISK`.
  * Generates prioritized executive summaries and automated defensive recommendations.

#### 4. 🖥️ Interactive Console & CLI Enhancements (`advance_secscan_ai.py`)
* Interactive Menu Option 20: `Cloud Security Posture & K8s Audit (CSPM/KSPM)`.
* New CLI options:
  * `--cspm-scan [PATH]`: Execute multi-cloud CSPM/IaC scan across Terraform directory, cloud config JSON, or built-in benchmark.
  * `--k8s-audit [PATH]`: Execute targeted Kubernetes Security Posture Management assessment.
  * `--export-cloud-fix [FILE]`: Export an automated remediation shell script containing fix commands.

#### 5. 🛠️ Robust PRoot and Linux Installer Enhancements (`install.sh`)
* Fixed PRoot symlink depth recursion limit on `/usr/bin/cc`.
* Ensured GNU coreutils priority to resolve dpkg hardlink errors under Termux PRoot-Distro environments.
* Added noninteractive frontend mode to eliminate blocking setup dialogs.
* Added fallback resolution for metadata and media inspection packages (`libimage-exiftool-perl`).

#### 6. 🧪 Testing & Verification
* **163 Unit Tests Passing**: Expanded test suite to 163 passing tests (`pytest tests/unit/ -v`), covering OrcaRouter Cyber Inference, Cloud Security Posture Management (CSPM), Kubernetes Security Posture Management (KSPM), API Security Scanner, and AI Red Teaming.
* Verified end-to-end installation and offline compatibility via `test_installation.py`.

---

*Release Date: October 22, 2026*

> [!IMPORTANT]
> **Official Solana Contract Address (CA):** Soon Available

We are proud to announce the major release of **SecScan AI Enterprise Version 2026.10.22.1**! This milestone update delivers enterprise-grade **AI Red Teaming (OWASP LLM Top 10)**, an automated **API Security Scanner (OWASP API Top 10)**, **MITRE D3FEND Countermeasure Defense Matrices**, **Detection-as-Code Rule Generation (Sigma & Splunk SPL)**, **Automated Ansible Remediation Playbooks**, and massive **50x cold start latency optimizations**.

### 🌟 What's New in Version 2026.10.22.1

#### 1. AI Red Teaming Engine (`ai_engine/llm_red_team.py`)
* **OWASP LLM Top 10 Probing Framework**: Automated security testing across all ten critical LLM vulnerability vectors:
  * **LLM01: Prompt Injection** — System prompt override, jailbreaks, multi-turn indirect injection.
  * **LLM02: Insecure Output Handling** — Tool execution sanitization, cross-context script injection.
  * **LLM03: Training Data Poisoning** — Backdoor trigger validation and weight perturbation heuristic checks.
  * **LLM04: Model Denial of Service** — Context window exhaustion, recursion flooding, high-compute prompts.
  * **LLM05: Supply Chain Vulnerabilities** — Malicious adapter/LoRA checks and third-party model registry integrity.
  * **LLM06: Sensitive Information Disclosure** — System prompt extraction, credential/PII leakage probes.
  * **LLM07: Insecure Plugin Design** — Tool authorization boundary validation and privilege escalation.
  * **LLM08: Excessive Agency** — Unconstrained autonomous agent action checks and missing human-in-the-loop safeguards.
  * **LLM09: Overreliance** — Code hallucination verification and safety refusal consistency analysis.
  * **LLM10: Model Theft** — System reconstruction, model inversion, and extraction fingerprinting.
* **Automated Guardrail Generation**: Dynamically crafts defense-in-depth system prompts and safety constraints.
* **Enterprise Menu & CLI**: Interactive Option 18 and `--llm-redteam <model_or_endpoint>`.

#### 2. API Security Scanner (`security/api_scanner.py`)
* **OWASP API Security Top 10 Detection**: Comprehensive automated auditing for modern REST/JSON APIs:
  * **API1: Broken Object Level Authorization (BOLA/IDOR)** — Cross-tenant resource manipulation via dual-token differential testing.
  * **API2: Broken Authentication** — JWT `none` algorithm injection, null/weak signature bypass, unauthenticated endpoints.
  * **API3: Broken Object Property Level Authorization** — Mass assignment and sensitive property disclosure.
  * **API4: Unrestricted Resource Consumption** — Missing rate limits and unbounded query parameter pagination (`limit=100000`).
  * **API5: Broken Function Level Authorization (BFLA)** — User-to-admin vertical privilege escalation.
  * **API6: Unrestricted Access to Sensitive Business Flows** — Automated workflow abuse and brute-force velocity.
  * **API7: Server Side Request Forgery (SSRF)** — Cloud metadata (`169.254.169.254`) and internal network probing.
  * **API8: Security Misconfiguration** — Overly permissive CORS (`*`), stack trace leakage, missing security headers.
  * **API9: Improper Inventory Management** — Shadow/deprecated API versions (`/v1` vs `/v2`) and debug endpoints (`/actuator`, `/debug`).
  * **API10: Unsafe Consumption of APIs** — Downstream third-party integration validation and blind injection.
* **OpenAPI & Swagger Parser**: Ingests OpenAPI 3.0 and Swagger 2.0 definitions (JSON or YAML) with full endpoint route mapping.
* **Enterprise Menu & CLI**: Interactive Option 19 and `--api-scan <spec_file_or_url>`.

#### 3. MITRE D3FEND Countermeasure Defense Matrix (`ai_engine/attack_chainer.py`)
* **Offensive-to-Defensive Mapping**: Maps offensive MITRE ATT&CK attack paths directly to MITRE D3FEND defensive countermeasures:
  * Initial Access (`T1190`) ➔ Inbound Traffic Filtering (`D3-INWA`), Execution Prevention (`D3-EBR`)
  * Execution (`T1059`) ➔ Process Spawn Analysis (`D3-SPAP`), Script Execution Control (`D3-SCA`)
  * Privilege Escalation (`T1548`/`T1068`) ➔ User Account Control (`D3-UAC`), Privilege Restriction (`D3-POA`)
  * Credential Access (`T1003`) ➔ LSASS Memory Protection (`D3-LSA`), Credential Binding (`D3-CBA`)
  * Lateral Movement (`T1021`) ➔ Network Segmentation (`D3-NWS`), Multi-Factor Authentication (`D3-MFA`)
  * Impact (`T1485`) ➔ Immutable Data Backup (`D3-BKP`), File System Integrity Verification (`D3-FSR`)
* **Dedicated CLI Flag**: `--d3fend-matrix`.

#### 4. Detection-as-Code: Sigma Rules & Splunk SPL (`ai_engine/attack_chainer.py`)
* **Sigma Rule Generation**: Automatically exports production-ready YAML Sigma rules for SIEM/SOC ingestion with MITRE ATT&CK tagging and multi-logsource mapping (`process_creation`, `network_connection`, `webserver`).
* **Splunk SPL Search Queries**: Synthesizes real-time Splunk search queries correlated with discovered attack steps.
* **Dedicated CLI Flag**: `--export-sigma`.

#### 5. Automated Remediation Playbooks (`ai_engine/attack_chainer.py`)
* **Ansible Automation Playbooks**: Auto-generates idempotent YAML Ansible playbooks to remediate chokepoints across Linux hosts (firewall rules, service isolation, account lockdowns).
* **Hardening Shell Scripts**: Auto-generates standalone Bash scripts for rapid incident containment.
* **Dedicated CLI Flag**: `--export-ansible`.

#### 6. Performance Optimization & Startup Latency Reduction
* **PyTorch / Hugging Face Lazy Loading**: Lazy-loads heavy deep-learning packages, slashing startup time from **105 seconds down to 2.2 seconds** (~50x reduction).
* **POSIX Subprocess Optimization**: Refactored `install.sh` to use pure POSIX parameter expansion, eliminating external process forks.
* **Robust Logging Initialization**: Hardened logging directory auto-creation across legacy and enterprise entrypoints.

#### 7. Testing & Verification
* **120 Passing Tests**: Test suite expanded from 105 to **120 passing tests** (`pytest tests/ -v`), verifying 100% test pass rate across all new modules.
* **CI/Offline Installation Verification**: 100% verified via `python3 test_installation.py --ci`.

---

## 🚀 Version 2026.10.22

*Release Date: October 22, 2026*

> [!IMPORTANT]
> **Official Solana Contract Address (CA):** Soon Available

We are proud to present **SecScan AI Enterprise Version 2026.10.22**! This release introduces the next-generation **Automated Attack Graph & Multi-Stage Chaining Engine**, **CVE Threat Intelligence with EPSS & CISA KEV Scoring**, and official Solana token contract address integration.

### 🌟 What's New in Version 2026.10.22

#### 1. Automated Attack Graph & Multi-Stage Chaining Engine (`ai_engine/attack_chainer.py`)
* **MITRE ATT&CK Aligned Graph Modeling**: Automatically synthesizes complex, multi-stage attack scenarios across Initial Access (`T1190`), Execution (`T1059`), Privilege Escalation (`T1548`/`T1068`), Credential Access (`T1003`), Lateral Movement (`T1021`), and Impact (`T1485`).
* **Critical Defensive Chokepoint Analysis**: Discovers single points of defensive failure across attack graphs and calculates mitigation ROI to break the maximum number of attack paths.
* **Remediation Priority Roadmaps**: Produces prioritized, strategic remediation sequences sorted by defensive impact.
* **Mermaid Flowchart Generation**: Generates color-coded, visual Mermaid syntax (`flowchart TD`) directly exportable for reports, dashboards, and documentation.

#### 2. CVE Threat Intelligence & EPSS Scoring Engine (`ai_engine/cve_intelligence.py`)
* **Automated CVE Extraction**: High-performance regex parser (`CVE-\d{4}-\d{4,7}`) extracts and deduplicates CVEs from raw scan output, banners, and tool logs.
* **Curated Offline Knowledge Base**: Curated database for high-impact CVEs (Log4Shell, EternalBlue, Spring4Shell, ProxyLogon, Dirty Pipe, PwnKit, MOVEit, Heartbleed, etc.) with heuristic estimation for novel CVEs.
* **EPSS Exploit Prediction Scoring**: Calculates probability of active exploitation in the wild (EPSS probability and percentile).
* **CISA KEV Emergency Triage**: Flags vulnerabilities listed in CISA's Known Exploited Vulnerabilities catalog requiring urgent patching.
* **Compound Prioritized Risk Score**: Weighted risk metric synthesizing CVSS v3.1, EPSS likelihood, KEV status, and weaponized exploit availability.

#### 3. Interactive Console & CLI Enhancements (`advance_secscan_ai.py`)
* **Main Menu Option 17**: Dedicated interactive console for `Threat Intel & Attack Graph Chaining`.
* **New Dedicated CLI Flags**:
  * `--cve-lookup <CVE-ID|Text>`: Query CVE intelligence, CVSS v3.1, EPSS probability, and KEV metrics directly from the terminal.
  * `--attack-chain`: Synthesize multi-stage attack graphs and display critical defensive chokepoints.
  * `--mermaid`: Export clean Mermaid diagram syntax for visualization.

#### 4. Official Solana Contract Address (CA) Integration
* **Verified Token CA**: Token CA Soon Available across repository documentation, README banner, and release metadata.

---

## 🚀 Version 2026.09.26

*Release Date: September 26, 2026*

We are proud to present **SecScan AI Enterprise Version 2026.09.26**! This release marks a significant milestone with the integration of the **Evidence Workbench**, cross-platform reliability hardening, reviewable AI and adapter execution lifecycles, and hardened CI test matrices contributed by **Abdulazeez A. Noaman** ([@HostX0](https://github.com/HostX0)) via Pull Request [#21](https://github.com/najafdev/secscan_ai/pull/21).

### 🌟 What's New in Version 2026.09.26

#### 1. Evidence Workbench & Local Assessment Studio (`workbench/`)
* **Local Evidence-First Assessment Studio**: Full-featured local studio and workbench server for reviewable, privacy-preserving security assessments.
* **Privacy-Minimizing Scanner Parsers & Adapters**: Deterministic output parsers for Semgrep, Nuclei, Trivy, and repository metadata scanners that sanitize raw targets, redact credentials, and drop sensitive row data.
* **Bounded Access-Control Matrix**: Strict access-control evaluator ensuring safe testing boundaries and scope enforcement.
* **Coverage-Aware Retest Engine**: Automated verification linking remediation advice directly to previous test evidence and diffs without falsifying test results.
* **Evidence Safety Bundles**: Secure evidence export and review bundles with cryptographic integrity checks.

#### 2. Reviewable Adapter Lifecycle & Execution Receipts
* **Durable Adapter Approval & Planning Lifecycle**: Pre-execution planning, explicit operator approval gates, and durable execution receipts.
* **Cooperative Cancellation & Wall-Clock Deadlines**: Cancellable network transports, shared deadlines, and interrupted run recovery with running checkpoints.
* **Bounded Native Execution Registry**: Closed execution registry with isolated environment runners and resource cleanup.

#### 3. Cross-Platform Reliability & Launcher Hardening
* **Multi-Platform Launchers**: Native launch scripts for Linux, macOS (`workbench/start.command`), and Windows (`workbench/start.cmd`, `workbench/start.py`).
* **Container vs Host Installer Context**: Hardened `install.sh` supporting `SECSCAN_AI_INSTALL_CONTEXT` (`host` vs `container`) to prevent side effects during Docker builds.
* **Backward-Compatible Legacy Entrypoints**: Retained `secscan_ai.py` and `secscan_ai_v2.py` alongside `advance_secscan_ai.py` to preserve legacy tooling and automation workflows.

#### 4. Hardened CI/CD & Automated Testing Matrix
* **Multi-Tier CI Matrix**: Added bounded Python 3.8 CI profile (`requirements-ci-py38.txt`) for legacy core contracts alongside full Python 3.9-3.11 test matrices.
* **Fail-Closed Black Code Quality Pipeline**: Uploads exact format diffs and automated candidate repair archives upon style divergence.
* **Expanded Verification**: 90+ core unit tests, comprehensive contract suites (`test_docker_contract.py`, `test_enterprise_ci_contract.py`, `test_requirements_compat.py`), and workbench E2E tests.

#### 5. Community & Contributor Recognition
* **Special Thanks**: Full credit and gratitude to **Abdulazeez A. Noaman** ([@HostX0](https://github.com/HostX0)) for designing, implementing, and contributing Pull Request [#21](https://github.com/najafdev/secscan_ai/pull/21).

---

## 🚀 Version 2026.09.19

*Release Date: September 19, 2026*

We are thrilled to announce **SecScan AI Enterprise Version 2026.09.19**! This major release delivers dynamic multi-provider AI auto-fetching, frontier model registry expansion (`gpt-astra`, `gpt-6-astra`, `claude-3.7-sonnet`, `gemini-2.0`, `o1`, `deepseek-r1-zero`), custom routing gateways (including OpenRouter overrides and dedicated 9B task dispatchers), and comprehensive stability and bug fixes across the platform.

### 🌟 What's New in Version 2026.09.19

#### 1. Dynamic Multi-Provider Remote Model Auto-Fetching
* **Live Remote Discovery Across 9+ Providers**: Introduced the `fetch_remote_models()` provider abstraction engine and dynamic registry synchronization:
  * **OpenAI**: Live discovery via `client.models.list()` or `/v1/models` endpoint for instant access to latest OpenAI releases.
  * **Anthropic (Claude)**: Direct querying of `https://api.anthropic.com/v1/models` with API key & versioning, with fallback to latest Claude frontier catalog (`claude-3-7-sonnet`, `claude-3-5-sonnet`, `claude-3-opus`).
  * **Google Gemini**: Dynamic discovery via Google Generative Language API (`/models?key=...`), pulling model limits, context windows, and multimodal capabilities.
  * **DeepSeek**: Real-time querying of DeepSeek models (`deepseek-chat`, `deepseek-reasoner` R1, and `deepseek-r1-zero`).
  * **GLM (Zhipu AI)**: Real-time query support for BigModel GLM endpoints and frontier models (`glm-4-plus`, `glm-4-air`, `glm-4-flash`, `glm-4-long`, `codegeex-4`, `glm-zero-preview`).
  * **Local Ollama**: Automatic inspection of locally pulled models via `/api/tags`.
  * **OpenRouter Aggregator**: Live model discovery across hundreds of upstream endpoints via `/models`.
  * **9B Router & Custom Gateways**: Automated inspection of custom router `/models` endpoints.
* **Dynamic Model Catalog & Normalizer (`ai_engine/model_registry.py`)**:
  * `DYNAMIC_MODEL_CATALOG`: Real-time runtime store for discovered models.
  * `fetch_all_provider_models()`: Automated discovery across all or specified providers with caching and fallback.
  * `normalize_provider()`: Robust provider alias resolution supporting flexible strings (`'openai'`, `'claude'`, `'anthropic'`, `'gemini'`, `'google'`, `'deepseek'`, `'glm'`, `'zhipu'`, `'openrouter'`, `'9brouter'`, `'custom'`).

#### 2. Frontier AI Model Catalog Expansion
* Added official support, token windows, and tool-calling parameters for:
  * **GPT Astra** (`gpt-astra`) & **GPT-6 Astra** (`gpt-6-astra`)
  * **Claude 3.7 Sonnet** (`claude-3.7-sonnet`)
  * **Google Gemini 2.0 Flash & Pro** (`gemini-2.0-flash`, `gemini-2.0-pro`)
  * **OpenAI o1 & o1-mini** (`o1`, `o1-mini`)
  * **DeepSeek R1 Zero** (`deepseek-r1-zero`)

#### 3. Custom Routers & Intelligent Task Dispatching
* **9B Router (`9brouter/*`)**: Specialized client (`NineBRouterProvider`) for 9B parameter task and exploitation routers (e.g. Qwen 2.5 9B, Gemma 2 9B, Llama 3.1 9B) with OpenAI SDK integration and raw HTTP failover.
* **OpenRouter Custom Endpoints (`OPENROUTER_BASE_URL`)**: Configurable base URL overrides for private OpenRouter proxies and enterprise gateways.
* **Custom Router Gateway (`custom_router/*`, `custom/*`)**: Generic client (`CustomRouterProvider`) allowing routing to any internal OpenAI-compatible reverse proxy, vLLM, LiteLLM, or Portkey gateway.
* **Dynamic Routing Prefixes**: Seamless on-the-fly resolution for models prefixed with `openrouter/`, `9brouter/`, `custom_router/`, or `custom/`.

#### 4. Enterprise CLI & Interactive Management
* Added `--model`, `--provider`, and `--custom-route` CLI options.
* Added `--fetch-models` to query and register live models from configured providers on startup.
* Added `--list-models` to print full formatted tables of cataloged and discovered models.
* Integrated automated model discovery into interactive configuration menu option **`11`** (`configure_ai_engine`).

#### 5. Platform Hardening & Bug Fixes
* Fixed database session lifecycle management in PostgreSQL/SQLite adapters.
* Resolved task concurrency handling in Celery/ParallelProcessor pipelines.
* Corrected IOC pattern extraction for edge-case RFC IPv6 and domain representations in the SOC analysis engine.
* Added safe error handling and resilient fallbacks during network timeouts and offline execution.

---

## 🚀 Version 2026.07.beta.4

We are excited to announce the release of **SecScan AI Enterprise Version 2026.07.beta.4**! This release introduces the Advanced SOC (Security Operations Center) Analysis Engine, native SIEM Integrations, and expanded Threat Model compliance mapping to include the latest OWASP Top 10 guidelines and major 2024–2026 CVE detection rules.

### 🌟 What's New in Version 2026.07.beta.4

#### 1. Advanced Security Operations Center (SOC) Analysis Module
* **Multi-Format Log Parser & Normalizer**: Ingests, normalizes, and auto-detects formats for standard RFC Syslog, structured application JSON, Common Event Format (CEF), firewall packet filtering logs, and generic CSV/key-value outputs.
* **Indicator of Compromise (IOC) Extractor**: Leverages regex patterns to extract threat indicators, assess confidence levels, assign threat scores, and categorize:
  * IPv4 & IPv6 addresses (with benign/RFC 1918 private range filters)
  * FQDN Domains (with TLD reputation tracking)
  * File hashes (MD5, SHA-1, SHA-256)
  * CVE references
  * Suspicious URLs, emails, registry keys, and file paths
* **MITRE ATT&CK Technique Mapper**: Scans event payloads against a signature database to automatically map activities to corresponding MITRE ATT&CK Enterprise techniques, including tactics such as Initial Access, Execution, Privilege Escalation, Defense Evasion, Lateral Movement, C2, Exfiltration, and Impact.
* **Sliding-Window Alert Correlation Engine**: Detects specific attack patterns by grouping and deduplicating related events within configurable time windows:
  * SSH/Auth brute force attacks (T1110)
  * Port scanning & network service discovery (T1046)
  * Suspicious scripting & interpreter commands (powershell, cmd, bash) (T1059)
  * Command & Control beaconing (T1071)
  * Data exfiltration over web/alternative protocols (T1048)
  * Privilege escalation attempts (UAC bypass, sudo, setuid) (T1548)
  * Evasion and log tampering activity (T1070)
  * OS credential dumping (mimikatz, SAM/NTDS) (T1003)
  * Active ransomware / destructive payloads (T1486)
* **Statistical Anomaly Detector**: Applies z-score analysis to identify anomalous deviations from established baseline patterns:
  * Hourly event volume spikes
  * Host IP diversity (unusual counts of unique sources)
  * Elevated authentication and processing error rates
  * Off-hours network activity patterns
* **Incident Timeline Reconstructor**: Builds a unified chronological timeline mapping events sequentially across the Cyber Kill Chain.
* **Incident Response Playbooks**: Generates prioritized playbook response runs (including steps, estimated duration, and ownership groups) tailored to the specific threat categories identified.
* **Executive Reporting & Exporting**: Produces a summary report containing risk score assessments, executive summaries, statistics, and tables, with options to export to JSON.

#### 2. Native SIEM Integration Connectors
* **Splunk Connector**:
  * Pulls logs via Splunk REST API search job creation (`/services/search/jobs` and results retrieval `/services/search/jobs/{sid}/results`).
  * Forwards correlated alerts to Splunk HTTP Event Collector (HEC) via the `sourcetype` `secscan_ai:soc:alert` to `services/collector/event`.
* **QRadar Connector**:
  * Ingests event logs by executing Ariel Query Language (AQL) search jobs via QRadar REST API (`/api/ariel/searches`).
  * Forwards alerts to QRadar API endpoint (`/api/custom_events`) to register them as custom security offenses.
* **Elasticsearch Connector**:
  * Pulls logs using Elasticsearch search Query DSL (`/_search`).
  * Posts alert JSON payloads to index `/secscan_ai-soc-alerts/_doc`.
* **Generic Webhook Connector**:
  * Pushes notifications to incoming webhooks like Slack, MS Teams, or custom SOAR solutions.
  * Auto-formats rich markdown messaging blocks for Slack/Teams, or sends full alert JSON structure depending on destination host name.
* **SIEM Connector Manager**:
  * Registers, queries, and tests multiple active connections concurrently.
  * Dispatches correlated alerts to all active integrations in a single routing pipeline.
* **Simulation Mode**:
  * If a connector has `is_mock=True` or the API token contains `"mock"`, the connector runs in simulation mode, yielding realistic search events and mock successful HTTP responses for offline validation.

#### 3. Expanded Vulnerability & Compliance Engine (OWASP & CVEs up to July 2026)
* **OWASP API Security Top 10 (2023)**: Added **BOLA (Broken Object Level Authorization)** and **SSRF (Server-Side Request Forgery)**.
* **OWASP Top 10 for LLM Applications (2025/2026)**: Added **Prompt Injection (LLM01)**, **Insecure Output Handling (LLM02)**, and **Excessive Agency (LLM08)**.
* **OWASP Top 10 Additions**: Added **Software and Data Integrity Failures (A08:2021)** and **Security Logging and Monitoring Failures (A09:2021)**.
* Added MITRE ATT&CK technique **T1195 (Supply Chain Compromise)** and **T1611 (Escape to Host)**.
* Integrated signature alerts and custom exploitation payloads for:
  * **CVE-2024-3094 (XZ Utils Supply Chain Backdoor)**
  * **CVE-2024-21626 (runc Container Escape/breakout)**
  * **CVE-2024-4577 (PHP CGI Remote Code Execution)**
  * **LLM Prompt Injection / Jailbreaks (ignore previous instructions, Dan mode, etc.)**

#### 4. Consolidated Documentation & Unit Tests
* Created `/doc` folder and moved platform documentation files (`release.md`, `PROJECT_SUMMARY.md`, `ENTERPRISE_INTEGRATION_SUMMARY.md`, and `IMPROVEMENT_ROADMAP.md`) inside it for a cleaner repository structure.
* Built comprehensive test suites verifying log parsers, IOC extractors, anomaly trackers, correlation engines, and SIEM connectors.

### 🛠️ Quick Start with version 2026.07.beta.4

1. **Launch Interactive SOC Console**:
   ```bash
   python advance_secscan_ai.py
   ```
   Select option **`16`** from the main menu.

2. **Configure SIEM Connections**:
   Inside the SOC console, select option **`5`** to register Splunk, QRadar, Elasticsearch, or Webhooks.

3. **Query & Analyze Logs**:
   Select option **`6`** to query registered SIEM systems directly and execute correlation runs.

4. **Verify Installation**:
   ```bash
   pytest tests/unit/ -v
   ```

---

## 🚀 Version 2026.07.beta.3

We are excited to announce the release of **SecScan AI Enterprise Version 2026.07.beta.3**! This release introduces multi-provider AI model support, runtime model switching, automatic provider fallback, and a comprehensive model catalog of 26+ advanced AI models.

### 🌟 What's New in Version 2026.07.beta.3

#### 1. Multi-Provider AI Model Engine
* **Expanded Provider Ecosystem**: Integrated 7 key AI providers under a unified abstract client interface (`BaseProvider`):
  * **OpenAI**: Support for next-generation reasoning and multimodal models including `gpt-5`, `gpt-5.6`, `o3`, `o4-mini`, `gpt-4o`, and `gpt-4o-mini`.
  * **Anthropic**: Support for `claude-sonnet-5` (`claude-sonnet-4-20250514`), `claude-opus-4.8` (`claude-opus-4-20250918`), and `claude-haiku-3.5`. Calls the Messages API directly via raw REST request layer.
  * **Google Gemini**: Support for `gemini-3.5-flash`, `gemini-3.1-pro`, `gemini-2.5-pro`, and `gemini-2.5-flash` with massive 1M-2M token context windows.
  * **DeepSeek**: Support for `deepseek-r1` (reasoning with CoT) and `deepseek-v3` (`deepseek-chat`) via custom OpenAI-compatible client.
  * **GLM (Zhipu)**: Support for bilingual language models `glm-5.2` and `glm-4-plus`.
  * **Local LLMs (Ollama)**: Offline capabilities for local models including `llama3.3:70b`, `llama3.2:3b`, `mistral:7b`, `codellama:13b`, `qwen2.5:32b`, `deepseek-r1:14b`, and `phi-4:14b`.
  * **OpenRouter**: Access to 100+ public models through the OpenRouter aggregator using the `openrouter/auto` ID.

#### 2. Runtime Model Switching & Fallback Chain
* **On-the-fly Switch**: Added `engine.set_model(model_id)` to let developers change models programmatically or dynamically during assessments.
* **Provider Fallback**: A three-tier fallback chain ensures high-availability during assessments:
  1. Selected model provider API
  2. Direct OpenAI API key fallback (if `OPENAI_API_KEY` is present)
  3. Local offline models (Hugging Face / Ollama) as the ultimate fail-safe

#### 3. Centralized Model Registry & Client Factory
* Introduced `ai_engine/model_registry.py` managing the complete `MODEL_CATALOG` with token limits, tool-calling capabilities, and provider metadata.
* Introduced `ai_engine/providers.py` hosting concrete client classes and `ProviderFactory` for lazy instantiation and caching.

#### 4. Robust AI Provider Unit Tests & Pathing
* Added `tests/unit/test_ai_providers.py` checking catalog completeness, metadata queries, and API key environment checks.
* Modified the root `conftest.py` testing configuration to allow importing real submodules from the `ai_engine` package during unit runs while keeping external database connections fully isolated.

### 🛠️ Quick Start with version 2026.07.beta.3

1. **Configure Environment**:
   Copy `.env.example` to `.env` and provide your API keys:
   ```bash
   SECSCAN_AI_MODEL=gpt-5
   ANTHROPIC_API_KEY=your_key
   GOOGLE_API_KEY=your_key
   DEEPSEEK_API_KEY=your_key
   ```

2. **Select Model in Code**:
   ```python
   from ai_engine import get_advanced_ai_engine
   
   # Initialize with Claude Sonnet 5
   engine = get_advanced_ai_engine(model_id='claude-sonnet-5')
   ```

3. **Verify Installation**:
   ```bash
   pytest tests/unit/ -v
   python3 test_installation.py
   ```
