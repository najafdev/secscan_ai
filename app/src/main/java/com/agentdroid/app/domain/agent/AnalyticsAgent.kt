package com.agentdroid.app.domain.agent

import com.agentdroid.app.ai.router.AiModelRouter
import com.agentdroid.app.automation.action.ActionDispatcher
import com.agentdroid.app.data.local.dao.ActivityLogDao
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.TaskItem
import com.agentdroid.app.domain.orchestrator.SharedTaskContext

class AnalyticsAgent(
    actionDispatcher: ActionDispatcher,
    activityLogDao: ActivityLogDao,
    private val aiModelRouter: AiModelRouter
) : BaseAgent(
    id = "agent_analytics",
    name = "Analytics Agent",
    role = AgentRole.ANALYTICS,
    description = "Analyzes cross-platform engagement, tracks AI token expenditure, monitors task completion metrics, and generates growth and performance reports.",
    capabilities = listOf(
        "Analyze social media engagement", "Track AI model token expenditure",
        "Generate daily and weekly performance reports", "Measure workflow conversion rates",
        "Identify high-performing content trends"
    ),
    availableTools = listOf("EngagementAnalyzer", "TokenExpenditureTracker", "ReportSynthesizer", "TrendDetector"),
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

        val socialSummary = context.get("social_summary") ?: "Active multi-platform campaign operations"
        val prompt = "Task: ${task.title}\nDetails: ${task.description}\nSocial Context: $socialSummary\nAvailable System Context: ${context.getAll()}"
        val systemPrompt = "You are the Analytics Agent of AgentDroid OS. Produce data-driven, actionable analytics reports with impressions, engagement rates, and ROI metrics based on real task context."

        val response = provider.generateResponse(prompt, systemPrompt, activeModel)

        context.put("analytics_summary", response.content)

        return AgentExecutionOutput(
            summary = "Analyzed metrics: ${response.content.take(120)}...",
            outputData = mapOf(
                "analytics_metrics" to response.content,
                "full_report" to response.content
            )
        )
    }
}
