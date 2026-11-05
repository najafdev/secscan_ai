package com.agentdroid.app.domain.orchestrator

import android.content.Context
import com.agentdroid.app.ai.connection.AiConnectionManager
import com.agentdroid.app.ai.connection.ConnectionState
import com.agentdroid.app.ai.error.AiError
import com.agentdroid.app.ai.error.ErrorCategory
import com.agentdroid.app.automation.action.EmergencyKillswitch
import com.agentdroid.app.automation.service.AutomationForegroundService
import com.agentdroid.app.data.local.dao.ActivityLogDao
import com.agentdroid.app.data.local.dao.ApprovalDao
import com.agentdroid.app.data.local.dao.TaskDao
import com.agentdroid.app.data.local.entity.ActivityLogEntity
import com.agentdroid.app.data.local.entity.ApprovalRequestEntity
import com.agentdroid.app.data.local.entity.TaskEntity
import com.agentdroid.app.domain.agent.Agent
import com.agentdroid.app.domain.agent.AgentExecutionOutput
import com.agentdroid.app.domain.agent.MasterAgent
import com.agentdroid.app.domain.model.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.util.UUID

sealed class OrchestrationUpdate {
    data class Validating(val message: String) : OrchestrationUpdate()
    data class PlanCreated(val plan: TaskPlan) : OrchestrationUpdate()
    data class TaskStateChanged(val task: TaskItem) : OrchestrationUpdate()
    data class ApprovalRequired(val request: ApprovalRequest) : OrchestrationUpdate()
    data class ProgressLog(val message: String) : OrchestrationUpdate()
    data class PlanCompleted(val plan: TaskPlan, val finalReport: String) : OrchestrationUpdate()
    data class PlanFailed(val plan: TaskPlan, val error: String, val aiError: AiError? = null) : OrchestrationUpdate()
    data class ExecutionCancelled(val plan: TaskPlan) : OrchestrationUpdate()
}

class AgentOrchestrator(
    private val context: Context,
    val masterAgent: MasterAgent,
    private val agentsMap: Map<AgentRole, Agent>,
    private val taskDao: TaskDao,
    private val approvalDao: ApprovalDao,
    private val activityLogDao: ActivityLogDao,
    private val aiConnectionManager: AiConnectionManager,
    private val dagScheduler: DAGScheduler = DAGScheduler()
) {
    private val mutex = Mutex()

    private val _currentPlan = MutableStateFlow<TaskPlan?>(null)
    val currentPlan: StateFlow<TaskPlan?> = _currentPlan.asStateFlow()

    private val _orchestratorStatus = MutableStateFlow("Idle")
    val orchestratorStatus: StateFlow<String> = _orchestratorStatus.asStateFlow()

    private var executionJob: Job? = null
    private var activeContext: SharedTaskContext? = null
    private val pendingApprovalTaskIds = mutableSetOf<String>()

    fun startGoalExecution(userGoal: String): Flow<OrchestrationUpdate> = flow {
        EmergencyKillswitch.resetKillswitch()

        // 1. Strict Master Agent Protection: Pre-flight AI connectivity check
        _orchestratorStatus.value = "VALIDATING MODEL"
        emit(OrchestrationUpdate.Validating("Master Agent: Checking AI provider connectivity..."))

        val masterValidation = aiConnectionManager.validateAndGetProvider(AgentRole.MASTER)
        if (masterValidation.isFailure) {
            val err = masterValidation.exceptionOrNull() as? AiError
                ?: AiError.notConfigured(modelName = "Master Agent")

            _orchestratorStatus.value = "FAILED — AI MODEL NOT CONNECTED"
            activityLogDao.insertLog(
                ActivityLogEntity(
                    id = UUID.randomUUID().toString(),
                    agentRole = AgentRole.MASTER.name,
                    actionType = "AI_PREFLIGHT_CHECK",
                    description = "Execution blocked: ${err.userFriendlyTitle}. ${err.userFriendlyMessage}",
                    riskLevel = RiskLevel.HIGH.name,
                    status = "FAILED",
                    timestamp = System.currentTimeMillis()
                )
            )

            val emptyPlan = TaskPlan(
                id = UUID.randomUUID().toString(),
                userGoal = userGoal,
                tasks = emptyList(),
                status = PlanStatus.FAILED
            )
            _currentPlan.value = emptyPlan
            emit(OrchestrationUpdate.PlanFailed(emptyPlan, err.userFriendlyMessage, err))
            return@flow
        }

        emit(OrchestrationUpdate.ProgressLog("AI Provider online. Master Agent decomposing goal: \"$userGoal\"..."))
        _orchestratorStatus.value = "Planning"

        // Start Foreground Service with emergency stop notification
        try {
            AutomationForegroundService.startService(context, "Executing: $userGoal")
        } catch (e: Exception) {
            // Ignore background restriction if present
        }

        // 2. Decompose Goal using Master Agent with real LLM
        val availableRoles = agentsMap.keys.toList()
        val subtasks: List<TaskItem>
        try {
            subtasks = masterAgent.decomposeGoal(userGoal, availableRoles)
        } catch (e: Exception) {
            val err = if (e is AiError) e else AiError(
                errorCode = "ERR_DECOMPOSITION_FAILED",
                category = ErrorCategory.AGENT_EXECUTION_FAILED,
                userFriendlyTitle = "Goal Decomposition Failed",
                userFriendlyMessage = "The Master Agent could not break down your request: ${e.message}",
                technicalDetails = e.stackTraceToString(),
                providerName = "Master Agent"
            )
            _orchestratorStatus.value = "Failed"
            AutomationForegroundService.stopService(context)
            val failedPlan = TaskPlan(UUID.randomUUID().toString(), userGoal, emptyList(), PlanStatus.FAILED)
            _currentPlan.value = failedPlan
            emit(OrchestrationUpdate.PlanFailed(failedPlan, err.userFriendlyMessage, err))
            return@flow
        }

        val plan = TaskPlan(
            id = UUID.randomUUID().toString(),
            userGoal = userGoal,
            tasks = subtasks,
            status = PlanStatus.EXECUTING
        )
        _currentPlan.value = plan

        // Persist tasks in database
        val entities = subtasks.map { task ->
            TaskEntity(
                id = task.id,
                planId = plan.id,
                agentRole = task.agentRole.name,
                title = task.title,
                description = task.description,
                status = task.status.name,
                riskLevel = task.riskLevel.name,
                actionType = task.actionType?.name,
                toolName = task.toolName
            )
        }
        taskDao.insertTasks(entities)

        emit(OrchestrationUpdate.PlanCreated(plan))
        emit(OrchestrationUpdate.ProgressLog("Plan constructed with ${subtasks.size} subtasks. Executing DAG fleet..."))

        val sharedContext = SharedTaskContext(plan.id)
        activeContext = sharedContext

        var currentTasks = subtasks

        // 3. Multi-Agent DAG Execution Loop
        while (!dagScheduler.isPlanComplete(currentTasks)) {
            EmergencyKillswitch.checkStatus()

            val readyTasks = dagScheduler.getReadyTasks(currentTasks)
            if (readyTasks.isEmpty()) {
                if (currentTasks.any { it.status == TaskStatus.WAITING_APPROVAL }) {
                    _orchestratorStatus.value = "Waiting for Human Approval"
                    delay(500)
                    continue
                }
                currentTasks = dagScheduler.markSkippedTasks(currentTasks)
                if (dagScheduler.isPlanComplete(currentTasks)) break
                delay(300)
                continue
            }

            // Execute ready tasks in parallel up to 4 concurrent agents
            coroutineScope {
                val jobs = readyTasks.take(4).map { task ->
                    async {
                        executeSingleTask(task, sharedContext)
                    }
                }
                val results = jobs.awaitAll()
                mutex.withLock {
                    for (updated in results) {
                        currentTasks = currentTasks.map { if (it.id == updated.id) updated else it }
                        taskDao.updateTaskStatus(updated.id, updated.status.name, updated.completedAt, updated.error)
                    }
                    _currentPlan.value = plan.copy(tasks = currentTasks)
                }
            }

            for (task in currentTasks.filter { readyTasks.any { r -> r.id == it.id } }) {
                emit(OrchestrationUpdate.TaskStateChanged(task))
            }

            // Check unrecoverable failures
            if (dagScheduler.hasUnrecoverableFailure(currentTasks)) {
                currentTasks = dagScheduler.markSkippedTasks(currentTasks)
                _currentPlan.value = plan.copy(tasks = currentTasks)
                break
            }
        }

        // 4. Synthesis & Final Report
        val finalStatus = if (currentTasks.all { it.status == TaskStatus.COMPLETED }) {
            PlanStatus.COMPLETED
        } else {
            PlanStatus.FAILED
        }

        val completedTasks = currentTasks.filter { it.status == TaskStatus.COMPLETED }
        val finalReport = try {
            if (completedTasks.isNotEmpty()) {
                masterAgent.synthesizeReport(userGoal, completedTasks)
            } else {
                "No tasks completed successfully. Review failed subtasks for details."
            }
        } catch (e: Exception) {
            "Partial summary: ${completedTasks.size}/${currentTasks.size} tasks succeeded. Report synthesis failed: ${e.message}"
        }

        val finishedPlan = plan.copy(
            tasks = currentTasks,
            status = finalStatus,
            completedAt = System.currentTimeMillis(),
            finalSummary = finalReport
        )
        _currentPlan.value = finishedPlan
        _orchestratorStatus.value = if (finalStatus == PlanStatus.COMPLETED) "Completed" else "Finished with errors"

        // Stop Foreground Service
        AutomationForegroundService.stopService(context)

        if (finalStatus == PlanStatus.COMPLETED) {
            emit(OrchestrationUpdate.PlanCompleted(finishedPlan, finalReport))
        } else {
            emit(OrchestrationUpdate.PlanFailed(finishedPlan, "One or more subtasks failed during execution."))
        }
    }.catch { e ->
        _orchestratorStatus.value = "Failed"
        AutomationForegroundService.stopService(context)
        val p = _currentPlan.value ?: TaskPlan(UUID.randomUUID().toString(), userGoal, emptyList(), PlanStatus.FAILED)
        val aiErr = if (e is AiError) e else null
        emit(OrchestrationUpdate.PlanFailed(p, e.message ?: "Unknown error in orchestration.", aiErr))
    }

    private suspend fun executeSingleTask(
        task: TaskItem,
        sharedContext: SharedTaskContext
    ): TaskItem {
        // High Risk Gate: requires human approval
        if (task.riskLevel == RiskLevel.HIGH && !pendingApprovalTaskIds.contains(task.id)) {
            val approvalRequest = ApprovalRequestEntity(
                id = UUID.randomUUID().toString(),
                taskId = task.id,
                planId = task.planId,
                agentRole = task.agentRole.name,
                title = "Approval Required: ${task.title}",
                description = task.description,
                riskLevel = task.riskLevel.name,
                actionDetails = "Action: ${task.actionType?.name ?: "Custom"} | Agent: ${task.agentRole.displayName}",
                status = "PENDING"
            )
            approvalDao.insertApproval(approvalRequest)
            pendingApprovalTaskIds.add(task.id)

            return task.copy(status = TaskStatus.WAITING_APPROVAL)
        }

        // Validate agent's AI connectivity if AI-dependent
        val agent = agentsMap[task.agentRole] ?: masterAgent
        val isAiRole = task.agentRole != AgentRole.PHONE_CONTROL &&
                task.agentRole != AgentRole.FILE_MANAGEMENT &&
                task.agentRole != AgentRole.SECURITY

        if (isAiRole) {
            val validation = aiConnectionManager.validateAndGetProvider(task.agentRole)
            if (validation.isFailure) {
                val err = validation.exceptionOrNull() as? AiError
                    ?: AiError.notConfigured(providerName = task.agentRole.displayName)
                return task.copy(
                    status = TaskStatus.FAILED,
                    completedAt = System.currentTimeMillis(),
                    error = "${err.userFriendlyTitle}: ${err.userFriendlyMessage}"
                )
            }
        }

        var runningTask = task.copy(status = TaskStatus.RUNNING)

        return try {
            var lastResult: AgentExecutionOutput? = null
            agent.execute(runningTask, sharedContext).collect { step ->
                if (step.isComplete) {
                    lastResult = AgentExecutionOutput(step.progressMessage, step.intermediateData)
                }
            }

            runningTask.copy(
                status = TaskStatus.COMPLETED,
                completedAt = System.currentTimeMillis(),
                outputData = lastResult?.outputData ?: mapOf("summary" to (lastResult?.summary ?: "Done"))
            )
        } catch (e: Exception) {
            if (runningTask.retryCount < runningTask.maxRetries && isRetryable(e)) {
                runningTask.copy(
                    retryCount = runningTask.retryCount + 1,
                    status = TaskStatus.PENDING,
                    error = "Retry ${runningTask.retryCount + 1}/${runningTask.maxRetries}: ${e.message}"
                )
            } else {
                runningTask.copy(
                    status = TaskStatus.FAILED,
                    completedAt = System.currentTimeMillis(),
                    error = e.message ?: "Task execution failed"
                )
            }
        }
    }

    private fun isRetryable(e: Exception): Boolean {
        if (e is AiError) {
            return e.retryAvailable
        }
        val msg = e.message.orEmpty().lowercase()
        return !msg.contains("401") && !msg.contains("403") && !msg.contains("invalid api key")
    }

    suspend fun approveTask(taskId: String) {
        pendingApprovalTaskIds.remove(taskId)
        taskDao.updateTaskStatus(taskId, TaskStatus.PENDING.name)
        val plan = _currentPlan.value ?: return
        val updated = plan.tasks.map { if (it.id == taskId) it.copy(status = TaskStatus.PENDING, riskLevel = RiskLevel.LOW) else it }
        _currentPlan.value = plan.copy(tasks = updated)
    }

    suspend fun rejectTask(taskId: String) {
        pendingApprovalTaskIds.remove(taskId)
        taskDao.updateTaskStatus(taskId, TaskStatus.SKIPPED.name, error = "Rejected by user.")
        val plan = _currentPlan.value ?: return
        val updated = plan.tasks.map { if (it.id == taskId) it.copy(status = TaskStatus.SKIPPED, error = "Rejected by user.") else it }
        _currentPlan.value = plan.copy(tasks = updated)
    }

    fun cancelExecution() {
        executionJob?.cancel()
        agentsMap.values.forEach { it.cancel() }
        masterAgent.cancel()
        _orchestratorStatus.value = "Cancelled"
        AutomationForegroundService.stopService(context)
    }

    fun triggerEmergencyStop() {
        EmergencyKillswitch.triggerEmergencyStop()
        cancelExecution()
    }
}
