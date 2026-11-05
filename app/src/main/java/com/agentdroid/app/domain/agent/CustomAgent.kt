package com.agentdroid.app.domain.agent

import com.agentdroid.app.ai.router.AiModelRouter
import com.agentdroid.app.automation.action.ActionDispatcher
import com.agentdroid.app.data.local.dao.ActivityLogDao
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.TaskItem
import com.agentdroid.app.domain.orchestrator.SharedTaskContext

class CustomAgent(
    id: String,
    name: String,
    description: String,
    capabilities: List<String>,
    availableTools: List<String>,
    requiredPermissions: List<String>,
    val systemPrompt: String,
    val assignedModel: String,
    actionDispatcher: ActionDispatcher,
    activityLogDao: ActivityLogDao,
    private val aiModelRouter: AiModelRouter
) : BaseAgent(
    id = id,
    name = name,
    role = AgentRole.CUSTOM,
    description = description,
    capabilities = capabilities,
    availableTools = availableTools,
    requiredPermissions = requiredPermissions,
    actionDispatcher = actionDispatcher,
    activityLogDao = activityLogDao
) {
    override suspend fun performTaskExecution(
        task: TaskItem,
        context: SharedTaskContext
    ): AgentExecutionOutput {
        val provider = aiModelRouter.getProviderForAgent(role)
        val prompt = "Task: ${task.title}\nDescription: ${task.description}\nAvailable Shared Context: ${context.getAll()}"
        val response = provider.generateResponse(prompt, systemPrompt, assignedModel)

        return AgentExecutionOutput(
            summary = "Custom Agent '$name' completed task: ${response.content.take(120)}...",
            outputData = mapOf("custom_result" to response.content)
        )
    }
}
