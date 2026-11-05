package com.agentdroid.app.domain.agent

import com.agentdroid.app.ai.router.AiModelRouter
import com.agentdroid.app.automation.action.ActionDispatcher
import com.agentdroid.app.data.local.dao.ActivityLogDao
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.TaskItem
import com.agentdroid.app.domain.orchestrator.SharedTaskContext

class MasterAgent(
    actionDispatcher: ActionDispatcher,
    activityLogDao: ActivityLogDao,
    private val aiModelRouter: AiModelRouter
) : BaseAgent(
    id = "agent_master",
    name = "Master Agent",
    role = AgentRole.MASTER,
    description = "Central AI controller for intent classification, subtask decomposition, agent coordination, and final report synthesis.",
    capabilities = listOf("Intent Classification", "Task Decomposition", "Agent Delegation", "Execution Monitoring", "Report Synthesis"),
    availableTools = listOf("GoalDecomposer", "ReportSynthesizer", "AgentCoordinator"),
    requiredPermissions = listOf("android.permission.INTERNET"),
    actionDispatcher = actionDispatcher,
    activityLogDao = activityLogDao
) {
    override suspend fun performTaskExecution(
        task: TaskItem,
        context: SharedTaskContext
    ): AgentExecutionOutput {
        val provider = aiModelRouter.getProviderForAgent(role)
        val activeModel = aiModelRouter.getActiveModelForAgent(role)

        val prompt = "Task: ${task.title}\nDescription: ${task.description}\nContext: ${context.getAll()}"
        val response = provider.generateResponse(prompt, "You are the Master Agent orchestrating execution.", activeModel)

        return AgentExecutionOutput(
            summary = response.content,
            outputData = mapOf("master_result" to response.content)
        )
    }

    suspend fun decomposeGoal(goal: String, availableAgents: List<AgentRole>): List<TaskItem> {
        val provider = aiModelRouter.getProviderForAgent(role)
        return provider.decomposeUserGoal(goal, availableAgents)
    }

    suspend fun synthesizeReport(goal: String, completedTasks: List<TaskItem>): String {
        val provider = aiModelRouter.getProviderForAgent(role)
        return provider.synthesizeReport(goal, completedTasks)
    }
}
