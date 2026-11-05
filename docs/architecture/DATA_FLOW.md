---
title: Data Flow Architecture
purpose: Maps data flow across user prompts, AI requests, Android gestures, and storage
scope: End-to-end data pipelines and boundary crossings
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/architecture/SYSTEM_ARCHITECTURE.md
  - docs/privacy/DATA_COLLECTION.md
---

# Data Flow Architecture

## Inbound Prompt to Execution Data Pipeline

```mermaid
flowchart TD
    User([User Voice/Text Prompt]) --> InputBuffer[Command Input Buffer]
    InputBuffer --> Orchestrator[AgentOrchestrator]
    
    Orchestrator --> MasterAgent[Master Agent Prompt Synthesis]
    MasterAgent --> KeystoreRead[Read API Key from Keystore AES-256]
    KeystoreRead --> HttpAi[HttpAiProvider: OkHttp Network Call]
    
    HttpAi --> RemoteAI[(Cloud Provider or Local Ollama)]
    RemoteAI --> HttpAi
    
    HttpAi --> Sanitizer[AiError & Output JSON Parser]
    Sanitizer --> DAGQueue[DAG Task Scheduler Queue]
    
    DAGQueue --> AgentExecution[Concurrent Agent Worker Coroutines]
    AgentExecution --> ContextBus[SharedTaskContext In-Memory Bus]
    AgentExecution --> MemoryStore[Room DB: memory_records]
    
    AgentExecution --> RiskGate{Risk Level Evaluation}
    RiskGate -->|Low / Medium| Dispatcher[ActionDispatcher]
    RiskGate -->|High| ApprovalQueue[Human Approval Queue in Room DB]
    
    ApprovalQueue -->|User Approves| Dispatcher
    
    Dispatcher --> Accessibility[Accessibility Node Gesture / Intent]
    Accessibility --> AndroidOS[Android System UI & Third-Party Apps]
```

---

## Data Boundary Analysis

1. **Memory Boundaries**:
   * Prompts and streaming chunks are held in temporary memory during active sessions.
   * `SharedTaskContext` retains inter-task state only during the active `planId` lifecycle.
2. **Persistence Boundaries**:
   * API credentials are encrypted with hardware-backed AES-256 GCM in `EncryptedSharedPreferences`. They are never stored in Room SQLite.
   * Chat messages, activity logs, and memory records reside exclusively on local device storage (`/data/data/com.agentdroid.app/databases/agentdroid.db`).
3. **Egress Boundaries**:
   * Egress traffic is restricted solely to the Base URL of the configured AI provider.
   * Remote endpoints enforce TLS (`HTTPS`). Cleartext HTTP is permitted only for verified local subnets (`localhost`, `10.0.2.2`, `192.168.0.0/16`, `10.0.0.0/8`, `172.16.0.0/12`).
   * No telemetry, crash analytics, or user prompts are ever sent to AgentDroid developers or third-party tracking networks.
