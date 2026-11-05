package com.agentdroid.app.domain.agent

import com.agentdroid.app.ai.router.AiModelRouter
import com.agentdroid.app.automation.action.ActionDispatcher
import com.agentdroid.app.data.local.dao.ActivityLogDao
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.TaskItem
import com.agentdroid.app.domain.orchestrator.SharedTaskContext

class SocialMediaAgent(
    actionDispatcher: ActionDispatcher,
    activityLogDao: ActivityLogDao,
    private val aiModelRouter: AiModelRouter
) : BaseAgent(
    id = "agent_social",
    name = "Social Media Agent",
    role = AgentRole.SOCIAL_MEDIA,
    description = "Manages social media across X (Twitter), Instagram, Facebook, LinkedIn, Telegram, Discord, YouTube, Reddit with strict anti-spam compliance.",
    capabilities = listOf(
        "Generate social media posts", "Write contextual replies", "Prepare threads",
        "Create content calendars", "Suggest hashtags", "Rewrite in different tones",
        "Monitor engagement", "Summarize notifications"
    ),
    availableTools = listOf(
        "SocialComposer", "HashtagEngine", "CalendarOrganizer",
        "ThreadBuilder", "EngagementAnalyzer"
    ),
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

        val previousResearch = context.get("research_summary") ?: ""
        val contentHooks = context.get("content_copy") ?: ""

        val systemPrompt = """
            You are the Social Media Management Agent of AgentDroid OS.
            Platform guidelines:
            - X: concise, punchy hooks, max 280 chars, 2-3 hashtags.
            - LinkedIn: professional insights, structured spacing, actionable takeaway.
            - Instagram: visual storytelling caption, engagement question, hashtag cluster.
            Strict policy: Never generate spam, mass unsolicited direct messages, or deceptive engagement.
            Output real, publish-ready social copy based on the provided context.
        """.trimIndent()

        val prompt = buildString {
            append("Task: ${task.title}\n")
            append("Instructions: ${task.description}\n")
            if (previousResearch.isNotBlank()) append("Competitor/Market Context: $previousResearch\n")
            if (contentHooks.isNotBlank()) append("Content Copy Material: $contentHooks\n")
        }

        val response = provider.generateResponse(prompt, systemPrompt, activeModel)

        context.put("social_posts_drafted", response.content)
        context.put("social_summary", response.content)

        return AgentExecutionOutput(
            summary = "Social media posts prepared: ${response.content.take(120)}...",
            outputData = mapOf(
                "social_summary" to response.content,
                "content" to response.content
            )
        )
    }
}
