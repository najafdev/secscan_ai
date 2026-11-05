---
title: Product Requirements Document (PRD)
purpose: Defines functional, non-functional, security, and interface specifications for AgentDroid
scope: AgentDroid Android Application (v1.0.0)
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/product/TECHNICAL_REQUIREMENTS_DOCUMENT.md
  - docs/product/FEATURE_SPECIFICATION.md
  - docs/product/REQUIREMENTS_TRACEABILITY.md
---

# Product Requirements Document (PRD)

## 1. Document Control & Metadata

| Attribute | Specification |
| :--- | :--- |
| **Product Name** | AgentDroid (Android AI Operating System) |
| **Package Identifier** | `com.agentdroid.app` |
| **Current Target Version** | `1.0.0` (Build 1) |
| **Platform Target** | Android 8.0+ (API 26) through Android 14 (API 34) |
| **Status** | Production-Ready Implemented Core |

---

## 2. Problem Statement & Proposed Solution

### The Problem
Smartphones host dozens of siloed applications. Executing a modern digital task (e.g., researching three competitors, writing an analysis summary, drafting social announcements across two networks, and emailing stakeholders) forces users into repetitive manual app-switching, copy-pasting, and manual scheduling. Existing AI assistants act merely as single-turn chat windows, isolated from native device interaction, lacking true multi-step agency, and providing zero local LLM privacy options.

### The Solution: AgentDroid
AgentDroid provides a centralized, autonomous multi-agent operating system on Android. A **Master Agent** decomposes high-level requests into Directed Acyclic Graph (DAG) task trees, delegating work to 10 specialized agents. The system reads and controls native Android app UIs via Accessibility APIs, discovers models dynamically from cloud and local LAN Ollama servers, secures credentials using Android Keystore AES-256 GCM, and enforces human-in-the-loop safety before executing high-risk actions.

---

## 3. User Personas & User Stories

### Persona Profiles

#### Persona 1: Devendra (Self-Employed Creator & Founder)
* **Goal**: Needs hands-off social media coordination, competitive research, and automated content scheduling.
* **Pain Point**: App switching takes 3+ hours daily; cloud AI tools do not integrate with installed Android mobile apps.

#### Persona 2: Elena (Cybersecurity & Privacy Engineer)
* **Goal**: Automate device tasks and local document summaries without transmitting sensitive data to third-party clouds.
* **Pain Point**: Rejects typical cloud AI assistants due to prompt logging and corporate surveillance.

### User Stories

* **US-01 (Multi-Agent Decomposition)**: *As a user*, I want to enter a single goal ("Research 3 competitors, draft a report, and schedule an X post"), *so that* Master Agent breaks it into subtasks, delegates to specialized agents, and executes them without manual intervention.
* **US-02 (Local Inference)**: *As a privacy-focused user*, I want to connect my laptop's Ollama instance over local Wi-Fi (`http://192.168.1.50:11434`), *so that* my data never leaves my private network.
* **US-03 (Per-Agent Model Selection)**: *As a power user*, I want my Phone Control Agent to use a fast local model while my Master Agent uses GPT-4o, *so that* I optimize for speed, cost, and reasoning power.
* **US-04 (Safety Approval)**: *As a cautious user*, I want AgentDroid to pause and ask for my cryptographic approval before deleting files or publishing posts, *so that* accidental destructive actions are prevented.

---

## 4. Functional Requirements Traceability Matrix

| Requirement ID | Description | Priority | Implementation Status | Dependencies | Acceptance Criteria |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PRD-001** | **Multi-Provider AI Registry**: Configure multiple cloud and local AI providers. | P0 | IMPLEMENTED | Room DB, SecurePrefs | User can configure OpenAI, Gemini, Claude, OpenRouter, Groq, Together, Ollama, and Custom endpoints. |
| **PRD-002** | **Dynamic Model Discovery**: Fetch available model catalogs dynamically from provider APIs. | P0 | IMPLEMENTED | OkHttp, ModelDiscoveryService | Calling `discoverAndSync()` queries official listing endpoints and populates Room DB with available models. |
| **PRD-003** | **Per-Agent Model Assignment**: Assign distinct models to specific agents. | P0 | IMPLEMENTED | SettingsDao, ModelConfigEntity | Master, Phone, Research, and other agents can each resolve different model configurations. |
| **PRD-004** | **Model Capability Validation**: Enforce required capabilities before dispatch. | P1 | IMPLEMENTED | ModelCapability.kt | Models lacking `TOOL_CALLING` or `REASONING` cannot be assigned to Phone Control or Master agents without warning. |
| **PRD-005** | **Ollama Local LLM Support**: Connect local Ollama instances over LAN/localhost. | P0 | IMPLEMENTED | NetworkSecurityValidator | App connects via `/api/tags`, checks installed models, and executes inference via `/api/chat`. |
| **PRD-006** | **DAG Task Scheduler**: Decompose goals into dependency graphs and execute concurrently. | P0 | IMPLEMENTED | DAGScheduler, Coroutines | Independent tasks run concurrently; dependent tasks wait for upstream outputs. |
| **PRD-007** | **Android Phone Automation**: Native UI clicking, scrolling, typing, and app launching. | P0 | IMPLEMENTED | AccessibilityService, ActionDispatcher | Accessibility service inspects view hierarchies and performs gesture dispatches. |
| **PRD-008** | **Human-in-the-Loop Approvals**: Require user approval for High-Risk actions. | P0 | IMPLEMENTED | ApprovalDao, Mutex | Tasks flagged `HIGH` risk pause execution until user clicks "Approve" or "Reject". |
| **PRD-009** | **Emergency Killswitch**: Instantly halt all running agents and UI automations. | P0 | IMPLEMENTED | EmergencyKillswitch.kt | Triggering killswitch immediately throws `SecurityException` and terminates background jobs. |
| **PRD-010** | **5-Tier Context Memory**: Persist knowledge across Working, Short, Long, Episodic, Procedural tiers. | P1 | IMPLEMENTED | MemoryDao, AgentMemoryManager | Agents retrieve relevant memory keys and update access counts; users can purge tiers individually. |
| **PRD-011** | **Obsidian Black Jetpack Compose UI**: 5-tab navigation system adhering to `#08090B` theme. | P0 | IMPLEMENTED | MainActivity, Navigation.kt | 5 primary tabs (Home, Agents, Automations, Activity, Settings) work seamlessly with zero backstack lockup. |
| **PRD-012** | **Hardware Keystore AES-256 GCM**: Secure storage for all API keys and bearer tokens. | P0 | IMPLEMENTED | EncryptedSharedPreferences | Keys are encrypted via MasterKey Android Keystore scheme; never logged or exposed in plaintext. |
| **PRD-013** | **Network Security Policy**: Cleartext HTTP permitted only for local subnets. | P0 | IMPLEMENTED | network_security_config.xml | Cleartext HTTP is allowed for `127.0.0.1`, `10.0.2.2`, `192.168.x.x`; remote calls enforce HTTPS. |
| **PRD-014** | **Strict Real AI Mode**: Elimination of fake responses or simulated thinking. | P0 | IMPLEMENTED | HttpAiProvider, AiError | Missing keys or network outages produce structured errors rather than mock text. |
| **PRD-015** | **Custom Agent Builder**: Allow users to configure bespoke agents with tailored system prompts. | P1 | IMPLEMENTED | CustomAgentBuilderScreen | Users define agent name, role, system prompt, capabilities, and icon, stored in Room DB. |
| **PRD-016** | **Modular Extension Plugin SDK**: Safe runtime extension points for external agent tools. | P2 | IMPLEMENTED | PluginRegistry, AgentPlugin | Plugins declare metadata, permissions, and custom tool handlers (e.g., Vision OCR, Meeting Assistant). |
| **PRD-017** | **Manual Model ID Entry**: Fallback entry for unlisted fine-tuned or private models. | P1 | IMPLEMENTED | ModelPickerDialog.kt | Users can manually input model ID strings (e.g. `ft:gpt-4o:org:custom-v1`) if discovery is restricted. |

---

## 5. Non-Functional Requirements (NFR)

* **NFR-01 (Reliability & Robustness)**: The system must gracefully handle network disconnections, API rate limits (`HTTP 429`), and server outages (`HTTP 503`) without crashing, preserving uncompleted task states in Room.
* **NFR-02 (Performance & Latency)**: Cold start to interactive Home Dashboard under 1.5 seconds on mid-range Android hardware. DAG task evaluation overhead under 50ms per node.
* **NFR-03 (Security & Encryption)**: Zero plaintext credential storage. Credentials encrypted with Android Keystore AES-256 SIV (keys) and AES-256 GCM (values).
* **NFR-04 (Privacy & Data Minimization)**: No unsolicited telemetry or third-party tracking SDKs. Data is communicated only to user-configured inference endpoints.
* **NFR-05 (Battery & Background Optimization)**: Long-running automation workflows execute under an explicit Android Foreground Service (`dataSync` type) with persistent notification, preventing OS process kills while minimizing CPU wake locks.

---

## 6. Success Metrics & Acceptance Criteria

1. **Navigation Integrity**: 100% of primary navigation transitions (Home $\leftrightarrow$ Settings, Home $\leftrightarrow$ Agents, Home $\leftrightarrow$ Activity, Home $\leftrightarrow$ Automations) succeed without backstack deadlocks.
2. **Real AI Execution Rate**: 100% of production agent tasks query live models; 0% generate mock or hardcoded execution fixtures.
3. **Local LLM Compatibility**: Full interoperability with Ollama servers across localhost, emulator bridges, and Wi-Fi LAN subnets.
4. **Automated Test Coverage**: Clean execution of automated test suites across unit, DAG, navigation, provider discovery, and security injection boundaries.
