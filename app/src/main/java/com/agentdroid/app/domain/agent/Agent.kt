package com.agentdroid.app.domain.agent

import com.agentdroid.app.domain.model.AgentExecutionState
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.TaskItem
import com.agentdroid.app.domain.orchestrator.SharedTaskContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.StateFlow

data class AgentStepResult(
    val taskId: String,
    val agentRole: AgentRole,
    val state: AgentExecutionState,
    val progressMessage: String,
    val intermediateData: Map<String, String> = emptyMap(),
    val isComplete: Boolean = false,
    val isFailed: Boolean = false,
    val errorMessage: String? = null
)

interface Agent {
    val id: String
    val name: String
    val role: AgentRole
    val description: String
    val capabilities: List<String>
    val availableTools: List<String>
    val requiredPermissions: List<String>
    val executionState: StateFlow<AgentExecutionState>

    fun execute(task: TaskItem, context: SharedTaskContext): Flow<AgentStepResult>
    fun cancel()
}
