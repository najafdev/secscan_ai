package com.agentdroid.app.domain.agent

import com.agentdroid.app.automation.action.ActionDispatcher
import com.agentdroid.app.automation.action.ActionResult
import com.agentdroid.app.automation.action.EmergencyKillswitch
import com.agentdroid.app.data.local.dao.ActivityLogDao
import com.agentdroid.app.data.local.entity.ActivityLogEntity
import com.agentdroid.app.domain.model.ActionType
import com.agentdroid.app.domain.model.AgentExecutionState
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.RiskLevel
import com.agentdroid.app.domain.model.TaskItem
import com.agentdroid.app.domain.orchestrator.SharedTaskContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.flow
import java.util.UUID

abstract class BaseAgent(
    override val id: String,
    override val name: String,
    override val role: AgentRole,
    override val description: String,
    override val capabilities: List<String>,
    override val availableTools: List<String>,
    override val requiredPermissions: List<String>,
    protected val actionDispatcher: ActionDispatcher,
    protected val activityLogDao: ActivityLogDao
) : Agent {

    protected val _executionState = MutableStateFlow(AgentExecutionState.IDLE)
    override val executionState: StateFlow<AgentExecutionState> = _executionState.asStateFlow()

    override fun cancel() {
        _executionState.value = AgentExecutionState.CANCELLED
    }

    override fun execute(task: TaskItem, context: SharedTaskContext): Flow<AgentStepResult> = flow {
        EmergencyKillswitch.checkStatus()
        _executionState.value = AgentExecutionState.THINKING
        emit(
            AgentStepResult(
                taskId = task.id,
                agentRole = role,
                state = AgentExecutionState.THINKING,
                progressMessage = "[$name] Analyzing task: ${task.title}"
            )
        )

        logActivity(
            actionType = task.actionType ?: ActionType.EXECUTE_CUSTOM_TOOL,
            description = "Agent '$name' started task: ${task.title}",
            riskLevel = task.riskLevel,
            status = "STARTED",
            taskId = task.id
        )

        try {
            _executionState.value = AgentExecutionState.RUNNING
            emit(
                AgentStepResult(
                    taskId = task.id,
                    agentRole = role,
                    state = AgentExecutionState.RUNNING,
                    progressMessage = "[$name] Executing operation..."
                )
            )

            val result = performTaskExecution(task, context)

            _executionState.value = AgentExecutionState.COMPLETED
            logActivity(
                actionType = task.actionType ?: ActionType.EXECUTE_CUSTOM_TOOL,
                description = "Agent '$name' completed task: ${task.title}",
                riskLevel = task.riskLevel,
                status = "COMPLETED",
                taskId = task.id
            )

            emit(
                AgentStepResult(
                    taskId = task.id,
                    agentRole = role,
                    state = AgentExecutionState.COMPLETED,
                    progressMessage = "[$name] Finished: ${result.summary}",
                    intermediateData = result.outputData,
                    isComplete = true
                )
            )
        } catch (e: Exception) {
            _executionState.value = AgentExecutionState.FAILED
            logActivity(
                actionType = task.actionType ?: ActionType.EXECUTE_CUSTOM_TOOL,
                description = "Agent '$name' failed: ${e.message}",
                riskLevel = task.riskLevel,
                status = "FAILED",
                taskId = task.id
            )
            emit(
                AgentStepResult(
                    taskId = task.id,
                    agentRole = role,
                    state = AgentExecutionState.FAILED,
                    progressMessage = "[$name] Execution failed: ${e.message}",
                    isFailed = true,
                    errorMessage = e.message
                )
            )
        } finally {
            if (_executionState.value != AgentExecutionState.CANCELLED) {
                _executionState.value = AgentExecutionState.IDLE
            }
        }
    }

    protected abstract suspend fun performTaskExecution(
        task: TaskItem,
        context: SharedTaskContext
    ): AgentExecutionOutput

    protected suspend fun logActivity(
        actionType: ActionType,
        description: String,
        riskLevel: RiskLevel,
        status: String,
        taskId: String? = null
    ) {
        activityLogDao.insertLog(
            ActivityLogEntity(
                id = UUID.randomUUID().toString(),
                agentRole = role.name,
                actionType = actionType.name,
                description = description,
                riskLevel = riskLevel.name,
                status = status,
                taskId = taskId
            )
        )
    }
}

data class AgentExecutionOutput(
    val summary: String,
    val outputData: Map<String, String> = emptyMap()
)
