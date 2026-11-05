package com.agentdroid.app.domain.agent

import com.agentdroid.app.ai.router.AiModelRouter
import com.agentdroid.app.automation.action.ActionDispatcher
import com.agentdroid.app.data.local.dao.ActivityLogDao
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.TaskItem
import com.agentdroid.app.domain.orchestrator.SharedTaskContext

class CommunicationAgent(
    actionDispatcher: ActionDispatcher,
    activityLogDao: ActivityLogDao,
    private val aiModelRouter: AiModelRouter
) : BaseAgent(
    id = "agent_comm",
    name = "Communication Agent",
    role = AgentRole.COMMUNICATION,
    description = "Drafts communications, sends WhatsApp messages, transmits SMS text alerts, summarizes email threads, and triages notifications.",
    capabilities = listOf(
        "Send WhatsApp messages", "Send direct SMS text alerts", "Draft email communications",
        "Summarize incoming threads", "Prepare smart replies", "Extract action items from chats",
        "Triage priority notifications"
    ),
    availableTools = listOf(
        "WhatsAppSender", "SmsSender", "EmailDrafter",
        "ThreadSummarizer", "ActionItemExtractor", "NotificationTriager"
    ),
    requiredPermissions = listOf(
        "android.permission.INTERNET",
        "android.permission.POST_NOTIFICATIONS",
        "android.permission.SEND_SMS",
        "android.permission.READ_CONTACTS"
    ),
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
        val systemPrompt = "You are the Communication Agent of AgentDroid OS. Prepare clear, concise, and courteous communication drafts. Highlight action items clearly."

        val response = provider.generateResponse(prompt, systemPrompt, activeModel)

        context.put("comm_draft", response.content)

        return AgentExecutionOutput(
            summary = "Communication draft prepared: ${response.content.take(120)}...",
            outputData = mapOf(
                "draft" to response.content,
                "summary" to response.content
            )
        )
    }
}
