package com.agentdroid.app.domain.agent

import com.agentdroid.app.ai.router.AiModelRouter
import com.agentdroid.app.automation.action.ActionDispatcher
import com.agentdroid.app.data.local.dao.ActivityLogDao
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.TaskItem
import com.agentdroid.app.domain.orchestrator.SharedTaskContext

class ContentCreationAgent(
    actionDispatcher: ActionDispatcher,
    activityLogDao: ActivityLogDao,
    private val aiModelRouter: AiModelRouter
) : BaseAgent(
    id = "agent_content",
    name = "Content Creation Agent",
    role = AgentRole.CONTENT_CREATION,
    description = "Generates and organizes high-impact digital content including articles, marketing copy, ad scripts, and document summaries.",
    capabilities = listOf(
        "Write long-form articles", "Generate captions & hooks", "Create marketing strategies",
        "Write video/audio scripts", "Summarize documents", "Rewrite content in various tones",
        "Maintain user style preferences"
    ),
    availableTools = listOf("ArticleWriter", "MarketingStrategist", "CopyDrafter", "ToneTransformer"),
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

        val researchContext = context.get("research_summary") ?: ""
        val prompt = buildString {
            append("Task: ${task.title}\n")
            append("Objective: ${task.description}\n")
            if (researchContext.isNotBlank()) append("Context Data: $researchContext\n")
        }

        val systemPrompt = "You are the Content Creation Agent. Produce compelling, well-structured, professional copy tailored to audience expectations."
        val response = provider.generateResponse(prompt, systemPrompt, activeModel)

        context.put("content_copy", response.content)

        return AgentExecutionOutput(
            summary = "Generated strategic copy and content variations based on context.",
            outputData = mapOf("content_result" to response.content)
        )
    }
}
