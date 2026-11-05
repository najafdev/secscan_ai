---
title: Technical Requirements Document (TRD)
purpose: In-depth engineering specifications, architecture diagrams, sequence flows, and system interactions
scope: Android Application Technical Architecture (`com.agentdroid.app`)
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/product/PRODUCT_REQUIREMENTS_DOCUMENT.md
  - docs/architecture/SYSTEM_ARCHITECTURE.md
  - docs/architecture/TASK_ORCHESTRATION.md
---

# Technical Requirements Document (TRD)

## 1. System Technology Stack

| Layer | Component / Library | Version / Details | Purpose |
| :--- | :--- | :--- | :--- |
| **Language & Runtime** | Kotlin / JVM 17 | `1.9.24` / Java 17 | Core development language with Coroutines and Flows |
| **UI Framework** | Jetpack Compose / Material 3 | BOM `2024.05.00` | Declarative UI, Obsidian Dark theme, animations |
| **Navigation** | Navigation Compose | `2.7.7` | Deep-link capable, single-activity navigation graph |
| **Local Persistence** | Android Room / SQLite | `2.6.1` (KSP) | Relational database (17 entities, DAOs, Flow emissions) |
| **Security & Crypto** | AndroidX Security Crypto | `1.1.0-alpha06` | Android Keystore backed MasterKey AES-256 GCM encryption |
| **Network Client** | Square OkHttp | `4.12.0` | HTTP/2, connection pooling, SSE streaming, NDJSON |
| **Background Work** | AndroidX WorkManager | `2.9.0` | Periodic scheduled workflow execution |
| **Android Automation** | Accessibility API | Level 26+ | Native screen inspection, gesture dispatch, app launching |
| **Foreground Service** | Android Foreground Service | `dataSync` | Safe continuous multi-agent execution & killswitch notification |

---

## 2. Component Architecture & System Topography

```mermaid
graph TD
    subgraph UI_Layer [Jetpack Compose UI Layer]
        MainActivity --> NavHost[Jetpack NavHost]
        NavHost --> Dash[DashboardScreen]
        NavHost --> Cmd[CommandCenterScreen]
        NavHost --> AgentsDash[AgentsDashboardScreen]
        NavHost --> AutoDash[AutomationCenterScreen]
        NavHost --> ActDash[ActivityCenterScreen]
        NavHost --> SetDash[SettingsScreen]
        NavHost --> BldDash[CustomAgentBuilderScreen]
    end

    subgraph Orchestration_Layer [Multi-Agent Orchestration Layer]
        Orch[AgentOrchestrator]
        Master[MasterAgent]
        DAG[DAGScheduler]
        ContextBus[SharedTaskContext]
        Fleet[Agent Fleet: Phone, Social, Content, Research, etc.]
        
        Orch --> Master
        Orch --> DAG
        Orch --> ContextBus
        Orch --> Fleet
    end

    subgraph Automation_Layer [Android Automation Layer]
        AccService[AgentDroidAccessibilityService]
        Dispatcher[ActionDispatcher]
        Verifier[StateVerifier]
        Killswitch[EmergencyKillswitch]
        FgService[AutomationForegroundService]
        
        Dispatcher --> AccService
        Dispatcher --> Verifier
        Dispatcher --> Killswitch
        FgService --> Killswitch
    end

    subgraph AI_Infrastructure [AI Connectivity & Registry Layer]
        Router[AiModelRouter]
        ConnMgr[AiConnectionManager]
        Discovery[ModelDiscoveryService]
        HttpProvider[HttpAiProvider]
        NetSec[NetworkSecurityValidator]
        
        Router --> ConnMgr
        ConnMgr --> Discovery
        ConnMgr --> HttpProvider
        Discovery --> NetSec
    end

    subgraph Data_Layer [Data & Security Layer]
        RoomDB[(AgentDroid Room Database v2)]
        Keystore[SecurePreferencesManager: Keystore AES-256]
        MemMgr[AgentMemoryManager: 5 Tiers]
        
        Orch --> RoomDB
        ConnMgr --> RoomDB
        ConnMgr --> Keystore
        Fleet --> MemMgr
        MemMgr --> RoomDB
    end

    UI_Layer --> Orchestration_Layer
    Orchestration_Layer --> Automation_Layer
    Orchestration_Layer --> AI_Infrastructure
    AI_Infrastructure --> Data_Layer
```

---

## 3. Sequence Diagrams

### 3.1 User Command Execution & Master Agent Delegation

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Dashboard / Command Center
    participant Orch as AgentOrchestrator
    participant Master as MasterAgent
    participant Router as AiModelRouter
    participant AI as Configured AI Provider
    participant DAG as DAGScheduler
    participant Context as SharedTaskContext
    participant Fleet as Specialized Agents

    User->>UI: Submit Natural Language Goal
    UI->>Orch: startGoalExecution(userGoal)
    Orch->>Master: decomposeGoal(userGoal, availableAgents)
    Master->>Router: getProviderForAgent(MASTER)
    Router-->>Master: Active AiProvider (e.g. GPT-4o / Ollama)
    Master->>AI: generateResponse(decompositionPrompt)
    AI-->>Master: JSON array of TaskItems with dependencies
    Master-->>Orch: List<TaskItem>
    Orch->>DAG: getReadyTasks(tasks)
    DAG-->>Orch: Initial executable tasks (no unsatisfied dependencies)

    loop While Plan Incomplete
        Orch->>Fleet: execute(task, Context)
        Fleet->>AI: generateResponse(subtaskPrompt)
        AI-->>Fleet: subtask results
        Fleet->>Context: put(key, result)
        Fleet-->>Orch: TaskStatus.COMPLETED
        Orch->>DAG: getReadyTasks(tasks)
    end

    Orch->>Master: synthesizeReport(goal, completedTasks)
    Master->>AI: generateResponse(synthesisPrompt)
    AI-->>Master: Consolidated Executive Report
    Master-->>Orch: finalReport String
    Orch-->>UI: PlanCompleted(finalReport)
    UI-->>User: Display synthesized report & task metrics
```

---

### 3.2 Human-in-the-Loop Approval-Required Actions

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Agent as Specialized Agent (e.g. Phone Control)
    participant Orch as AgentOrchestrator
    participant ApprovalDao as Room ApprovalDao
    participant UI as UI Approval Dialog / Activity Center
    participant Dispatcher as ActionDispatcher
    participant OS as Android System / Target App

    Agent->>Orch: Dispatch TaskItem (riskLevel = HIGH)
    Orch->>Orch: Detect HIGH Risk Level
    Orch->>ApprovalDao: insertApproval(ApprovalRequestEntity)
    Orch->>UI: Emit OrchestrationUpdate.ApprovalRequired
    UI-->>User: Present Confirmation Dialog (action, target, risk)
    
    alt User Approves
        User->>UI: Click "Approve Action"
        UI->>Orch: handleApproval(taskId, isApproved = true)
        Orch->>Dispatcher: dispatchAction(actionType, params)
        Dispatcher->>OS: Perform Gesture / Send Intent / Mutate File
        OS-->>Dispatcher: ActionResult(isSuccess = true)
        Dispatcher-->>Orch: Success
        Orch-->>Agent: Resume Task Execution
    else User Rejects
        User->>UI: Click "Reject Action"
        UI->>Orch: handleApproval(taskId, isApproved = false)
        Orch->>Orch: Mark task CANCELLED / FAILED
        Orch->>UI: Emit TaskStateChanged(CANCELLED)
    end
```

---

### 3.3 Dynamic Model Discovery & Ollama Local Inference

```mermaid
sequenceDiagram
    autonumber
    participant UI as SettingsScreen / AddProviderDialog
    participant ConnMgr as AiConnectionManager
    participant Discovery as ModelDiscoveryService
    participant NetSec as NetworkSecurityValidator
    participant Ollama as Local Ollama Server (LAN / 10.0.2.2:11434)
    participant Dao as Room SettingsDao

    UI->>ConnMgr: testProviderConnection("prov_ollama")
    ConnMgr->>NetSec: validateEndpointUrl("http://10.0.2.2:11434")
    NetSec-->>ConnMgr: ValidationResult(isValid = true, isLocal = true)
    ConnMgr->>Discovery: discoverAndSync(provider, apiKey = "")
    Discovery->>Ollama: GET /api/tags
    
    alt Ollama Server Reachable
        Ollama-->>Discovery: HTTP 200 {"models": [{"name": "llama3.2:latest", ...}]}
        Discovery->>Dao: deleteDiscoveredModelsForProvider("prov_ollama")
        Discovery->>Dao: insertDiscoveredModels([DiscoveredModelEntity])
        Discovery-->>ConnMgr: DiscoveryResult.Success(models, isFresh = true)
        ConnMgr->>ConnMgr: updateStatus(state = CONNECTED)
        ConnMgr-->>UI: ProviderValidationResult(isConnected = true, state = CONNECTED)
    else Server Unreachable / Timeout
        Discovery--xOllama: SocketTimeoutException / Connection Refused
        Discovery-->>ConnMgr: DiscoveryResult.Failure(NETWORK_UNAVAILABLE, cachedModels)
        ConnMgr->>ConnMgr: updateStatus(state = NETWORK_ERROR)
        ConnMgr-->>UI: ProviderValidationResult(isConnected = false, state = NETWORK_ERROR)
    end
```

---

### 3.4 Phone Automation via Android Accessibility Service

```mermaid
sequenceDiagram
    autonumber
    participant Agent as PhoneControlAgent
    participant Dispatcher as ActionDispatcher
    participant Killswitch as EmergencyKillswitch
    participant AccService as AgentDroidAccessibilityService
    participant Verifier as StateVerifier
    participant TargetApp as Target Android Application

    Agent->>Dispatcher: dispatchAction(CLICK_ELEMENT, {"target": "Submit"})
    Dispatcher->>Killswitch: checkStatus()
    Killswitch-->>Dispatcher: Status OK (Killswitch not engaged)
    Dispatcher->>AccService: clickByTextOrViewId("Submit")
    AccService->>AccService: Traverse AccessibilityNodeInfo tree
    AccService->>TargetApp: performAction(ACTION_CLICK)
    TargetApp-->>AccService: Action accepted
    Dispatcher->>Verifier: verifyTargetState(condition)
    Verifier->>AccService: inspectScreenContent()
    AccService-->>Verifier: Updated Node Tree
    Verifier-->>Dispatcher: State transition verified
    Dispatcher-->>Agent: ActionResult(isSuccess = true)
```

---

## 4. Technical Specifications of Subsystems

### 4.1 AI Provider Engine (`com.agentdroid.app.ai`)
* **`AiProvider` Interface**:
  * `generateResponse(prompt, systemPrompt, model, temperature, maxTokens): AiResponse`
  * `streamResponse(prompt, systemPrompt, model, temperature): Flow<String>`
  * `decomposeUserGoal(userGoal, availableAgents): List<TaskItem>`
  * `synthesizeReport(userGoal, completedTasks): String`
  * `testConnection(): Boolean`
* **`HttpAiProvider`**: Implements real HTTP communication via OkHttp with native endpoints:
  * OpenAI-Compatible: `POST /chat/completions` (OpenAI, OpenRouter, Groq, Together, LM Studio, vLLM)
  * Google Gemini: `POST /v1beta/models/{model}:generateContent?key={key}`
  * Anthropic: `POST /v1/messages` with `x-api-key` and `anthropic-version: 2023-06-01`
  * Ollama: `POST /api/chat` with options `{temperature, num_predict}`
* **Error Sanitization**: `AiError.sanitize(rawError)` intercepts raw headers, query params, and stack traces, replacing Bearer tokens, passwords, and sensitive keys with `[REDACTED]` before UI rendering or persistence.

### 4.2 Local Network Security Config (`network_security_config.xml`)
Android network security enforces TLS encryption by default while selectively permitting cleartext HTTP for local inference nodes:
* `localhost`, `127.0.0.1` (device-local daemons)
* `10.0.2.2` (Android emulator to host loopback bridge)
* `*.local`, `*.lan` (mDNS and local local-area-network domains)
* Private RFC1918 subnets (`192.168.0.0/16`, `10.0.0.0/8`, `172.16.0.0/12`) validated through `NetworkSecurityValidator`. Any remote address attempting cleartext HTTP is rejected immediately at runtime.

### 4.3 Database Architecture (Room Database v2)
17 SQLite entities managed by Room:
* `agents`, `agent_configs`: Agent identities, enabled states, and assigned parameters.
* `tasks`, `task_dependencies`: Task items, execution plans, dependency relations, retry limits.
* `agent_executions`, `activity_logs`: Audit trail of every dispatched agent action, duration, and metadata.
* `conversations`, `messages`: Natural language chat sessions, prompts, and streaming chunks.
* `memory_records`: 5-tier context storage with access counters and confidence weighting.
* `workflows`, `workflow_steps`: Reusable multi-agent automation templates and cron schedules.
* `connected_accounts`: Configured external identities (X, LinkedIn, Google, etc.).
* `api_providers`, `model_configurations`, `discovered_models`: Inference engines, model catalogs, per-agent routing tables.
* `permissions`, `approval_requests`: Human-in-the-loop governance queue.
