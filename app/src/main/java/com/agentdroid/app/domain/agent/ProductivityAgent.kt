package com.agentdroid.app.domain.agent

import com.agentdroid.app.ai.router.AiModelRouter
import com.agentdroid.app.automation.action.ActionDispatcher
import com.agentdroid.app.data.local.dao.ActivityLogDao
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.TaskItem
import com.agentdroid.app.domain.orchestrator.SharedTaskContext

class ProductivityAgent(
    actionDispatcher: ActionDispatcher,
    activityLogDao: ActivityLogDao,
    private val aiModelRouter: AiModelRouter
) : BaseAgent(
    id = "agent_productivity",
    name = "Productivity Agent",
    role = AgentRole.PRODUCTIVITY,
    description = "Manages personal productivity, creates task plans, builds optimized workday schedules, manages reminders, and tracks project progress.",
    capabilities = listOf(
        "Create tasks and checklists", "Build daily time-blocked schedules",
        "Manage reminders", "Organize complex projects",
        "Track task progress", "Identify overdue obligations"
    ),
    availableTools = listOf("DailyScheduleBuilder", "TaskTracker", "ReminderManager", "ProjectOrganizer"),
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

        val prompt = "Task: ${task.title}\nDetails: ${task.description}\nContext: ${context.getAll()}"
        val systemPrompt = "You are the Productivity Agent of AgentDroid OS. Generate structured, optimized daily schedules, checklists, or action plans based on user requirements."

        val response = provider.generateResponse(prompt, systemPrompt, activeModel)

        context.put("productivity_schedule", response.content)

        return AgentExecutionOutput(
            summary = "Productivity plan generated: ${response.content.take(120)}...",
            outputData = mapOf("schedule" to response.content)
        )
    }
}
