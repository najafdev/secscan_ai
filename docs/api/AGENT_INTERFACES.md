---
title: Agent Interfaces & Lifecycle Contracts
purpose: Technical specification of the Agent interface, MasterAgent, and step result structures
scope: Core agent contracts, task definitions, step execution results, and capabilities
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/api/API_OVERVIEW.md
  - docs/architecture/MULTI_AGENT_ARCHITECTURE.md
  - docs/developer/AGENT_DEVELOPMENT.md
---

# Agent Interfaces & Lifecycle Contracts

This document specifies the internal contracts governing agent operations and task delegation.

---

## 1. The `Agent` Interface

```kotlin
package com.agentdroid.app.domain.agent

import com.agentdroid.app.domain.model.*
import com.agentdroid.app.domain.orchestrator.SharedTaskContext

interface Agent {
    val id: String
    val role: AgentRole
    val name: String
    val description: String
    val capabilities: List<String>
    val status: AgentStatus

    suspend fun executeTask(
        task: AgentTask,
        context: SharedTaskContext
    ): AgentStepResult

    suspend fun terminate()
}
```

---

## 2. Supporting Domain Types

### `AgentRole`
```kotlin
enum class AgentRole {
    MASTER,
    PHONE_CONTROL,
    SOCIAL_MEDIA,
    CONTENT_CREATION,
    RESEARCH,
    COMMUNICATION,
    FILE_MANAGEMENT,
    PRODUCTIVITY,
    ANALYTICS,
    BROWSER,
    SECURITY,
    CUSTOM
}
```

### `AgentStepResult`
```kotlin
sealed class AgentStepResult {
    data class Success(
        val output: String,
        val artifacts: List<TaskArtifact> = emptyList(),
        val metrics: ExecutionMetrics = ExecutionMetrics()
    ) : AgentStepResult()

    data class RequiresApproval(
        val requestId: String,
        val prompt: String,
        val pendingAction: PendingAction
    ) : AgentStepResult()

    data class Failure(
        val error: AiError,
        val recoverable: Boolean = false
    ) : AgentStepResult()
}
```

### `AgentTask`
```kotlin
data class AgentTask(
    val id: String,
    val parentGoalId: String,
    val assignedRole: AgentRole,
    val title: String,
    val instructions: String,
    val dependencies: List<String> = emptyList(),
    val priority: Int = 0,
    val timeoutMs: Long = 60_000L
)
```

---

## Related Documentation
* [Multi-Agent Architecture](file:///workspaces/hacknova/docs/architecture/MULTI_AGENT_ARCHITECTURE.md)
* [Agent Lifecycle](file:///workspaces/hacknova/docs/architecture/AGENT_LIFECYCLE.md)
* [Agent Development Guide](file:///workspaces/hacknova/docs/developer/AGENT_DEVELOPMENT.md)
