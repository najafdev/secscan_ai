---
title: Feature Specification
purpose: Detailed functional breakdown of all AgentDroid features, states, user interactions, and error conditions
scope: User-facing and internal features across all app modules
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/product/PRODUCT_REQUIREMENTS_DOCUMENT.md
  - docs/product/TECHNICAL_REQUIREMENTS_DOCUMENT.md
---

# Feature Specification

## 1. Feature Catalog

| Feature Code | Name | Module | Primary Class / Composable |
| :--- | :--- | :--- | :--- |
| **FEAT-01** | AI Command Center | UI / Command | `CommandCenterScreen.kt` |
| **FEAT-02** | Master Orchestration & DAG Engine | Domain / Orchestration | `AgentOrchestrator.kt`, `DAGScheduler.kt` |
| **FEAT-03** | Phone Automation & Gesture Driver | Automation / Accessibility | `AgentDroidAccessibilityService.kt`, `ActionDispatcher.kt` |
| **FEAT-04** | AI Provider & Dynamic Model Discovery | AI / Connection | `AiConnectionManager.kt`, `ModelDiscoveryService.kt` |
| **FEAT-05** | Per-Agent Model Routing | AI / Router | `AiModelRouter.kt`, `ModelPickerDialog.kt` |
| **FEAT-06** | Ollama & Local LLM Integration | AI / Client | `HttpAiProvider.kt`, `NetworkSecurityValidator.kt` |
| **FEAT-07** | Human-in-the-Loop Approval Queue | Security / Governance | `ApprovalDao`, `ActivityCenterScreen.kt` |
| **FEAT-08** | Emergency Killswitch | Safety / Governance | `EmergencyKillswitch.kt`, `AutomationForegroundService.kt` |
| **FEAT-09** | 5-Tier Context Memory | Domain / Memory | `AgentMemoryManager.kt`, `MemoryDao` |
| **FEAT-10** | Custom Agent Builder | UI / Builder | `CustomAgentBuilderScreen.kt` |
| **FEAT-11** | Modular Plugin Extension SDK | SDK / Extension | `PluginRegistry.kt`, `AgentPlugin.kt` |
| **FEAT-12** | Social Media & Content Engine | Domain / Agent | `SocialMediaAgent.kt`, `ContentCreationAgent.kt` |

---

## 2. Deep Dive: FEAT-01 AI Command Center
* **Inputs**: Natural language voice or text prompt, optional forwarded workflow intent.
* **Outputs**: Streaming conversational responses, interactive execution plan preview, task state progress bars, and final synthesized report.
* **States**:
  * `IDLE`: Displays quick suggestion prompts and voice microphone trigger.
  * `THINKING / PLANNING`: Animates `MasterAgentHeroCard` glow; calls `MasterAgent.decomposeGoal()`.
  * `RUNNING`: Renders task progress cards with agent icons, risk badges, and status chips (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`).
  * `WAITING_FOR_APPROVAL`: Pauses animation, surfaces action details and "Approve" / "Reject" controls.
  * `COMPLETED`: Displays full executive briefing with copy-to-clipboard action.

---

## 3. Deep Dive: FEAT-04 Dynamic Model Discovery & Provider Management
* **Inputs**: Provider preset selection (OpenAI, Gemini, Anthropic, OpenRouter, Groq, Together, Ollama, LM Studio, Custom), Base URL, API Key.
* **Process**:
  1. Validates URL against `NetworkSecurityValidator` (verifies scheme and private subnet rules).
  2. Queries official models endpoint (`/v1/models`, `/v1beta/models`, `/api/tags`).
  3. Parses response, filters non-text utility models (TTS, Whisper, DALL-E), detects capabilities (`TOOL_CALLING`, `VISION`, `REASONING`), and updates Room DB.
  4. Stores API key into `EncryptedSharedPreferences` backed by Android Keystore.
* **Error States**:
  * `HTTP 401/403`: Returns `INVALID_API_KEY` state with prompt to check credentials.
  * `HTTP 404`: Returns `MODEL_NOT_FOUND` state.
  * `HTTP 429`: Returns `RATE_LIMITED` state with quota warning.
  * `SocketTimeout / DNS`: Returns `NETWORK_ERROR` or `REQUEST_TIMEOUT`.

---

## 4. Deep Dive: FEAT-07 & FEAT-08 Safety Governance
* **Risk Evaluation Matrix**:
  * `LOW` (Read screen, parse text, calculate metrics): Dispatched automatically.
  * `MEDIUM` (Draft message, open application, generate social post): Executed with transient activity log recording.
  * `HIGH` (Send email, delete file, execute transaction, install package, post live social update): Enters `ApprovalRequestEntity` queue, emits `OrchestrationUpdate.ApprovalRequired`, and suspends task coroutine until explicit user biometric/click confirmation.
* **Emergency Stop**:
  * Triggerable from persistent foreground service notification or in-app emergency red icon.
  * Atomically sets `EmergencyKillswitch.isEngaged = true`, immediately cancelling all active coroutines and raising `SecurityException` on any subsequent action attempt.
