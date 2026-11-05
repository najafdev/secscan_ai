---
title: Event System & Shared Context API Reference
purpose: Technical contracts for inter-agent communication, events, and task contexts
scope: SharedTaskContext, ContextEvent, OrchestrationUpdate, and reactive state flows
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/api/API_OVERVIEW.md
  - docs/architecture/TASK_ORCHESTRATION.md
  - docs/architecture/MEMORY_ARCHITECTURE.md
---

# Event System & Shared Context API Reference

AgentDroid utilizes an in-memory event bus and reactive state holders to facilitate coordination between the Master Agent and specialized execution agents.

---

## 1. `SharedTaskContext`

`SharedTaskContext` acts as the shared working memory across a single DAG execution plan:

```kotlin
package com.agentdroid.app.domain.orchestrator

import kotlinx.coroutines.flow.StateFlow

interface SharedTaskContext {
    val executionId: String
    val goalPrompt: String
    val stateFlow: StateFlow<ContextState>

    fun putVariable(key: String, value: Any)
    fun <T> getVariable(key: String, clazz: Class<T>): T?
    fun appendArtifact(artifact: TaskArtifact)
    fun getArtifacts(): List<TaskArtifact>
    fun emitEvent(event: ContextEvent)
    fun clear()
}
```

---

## 2. `ContextEvent` Sealed Hierarchy

```kotlin
sealed class ContextEvent {
    data class TaskStarted(val taskId: String, val agentRole: AgentRole) : ContextEvent()
    data class StepCompleted(val taskId: String, val stepName: String, val resultSummary: String) : ContextEvent()
    data class StepFailed(val taskId: String, val error: AiError) : ContextEvent()
    data class ActionRequested(val actionType: ActionType, val parameters: Map<String, Any?>) : ContextEvent()
    data class HumanApprovalRequired(val requestId: String, val message: String) : ContextEvent()
    data class ExecutionFinished(val executionId: String, val success: Boolean) : ContextEvent()
}
```

---

## 3. UI State Consumption

ViewModels observe `SharedTaskContext.stateFlow` to stream real-time execution node updates directly to Jetpack Compose screens:

```kotlin
val executionState: StateFlow<OrchestrationState> = orchestrator.activeContext.stateFlow
```

---

## Related Documentation
* [Task Orchestration](file:///workspaces/agentdroid-/docs/architecture/TASK_ORCHESTRATION.md)
* [Memory Architecture](file:///workspaces/agentdroid-/docs/architecture/MEMORY_ARCHITECTURE.md)
* [Agent Interfaces](file:///workspaces/agentdroid-/docs/api/AGENT_INTERFACES.md)
