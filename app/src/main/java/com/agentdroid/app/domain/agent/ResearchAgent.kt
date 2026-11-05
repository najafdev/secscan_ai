package com.agentdroid.app.domain.agent

import com.agentdroid.app.ai.router.AiModelRouter
import com.agentdroid.app.automation.action.ActionDispatcher
import com.agentdroid.app.data.local.dao.ActivityLogDao
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.TaskItem
import com.agentdroid.app.domain.orchestrator.SharedTaskContext

class ResearchAgent(
    actionDispatcher: ActionDispatcher,
    activityLogDao: ActivityLogDao,
    private val aiModelRouter: AiModelRouter
) : BaseAgent(
    id = "agent_research",
    name = "Research Agent",
    role = AgentRole.RESEARCH,
    description = "Conducts deep intelligence, web research, competitive landscape analysis, and structured citation reports.",
    capabilities = listOf(
        "Search web sources", "Research multi-domain topics", "Compare competitor products",
        "Extract structured data from documents", "Synthesize findings with verifiable citations"
    ),
    availableTools = listOf("WebSearchEngine", "CompetitorComparator", "CitationCompiler", "DocumentExtractor"),
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

        val prompt = "Research Topic: ${task.title}\nDetails: ${task.description}\nPrior Context: ${context.getAll()}"
        val systemPrompt = "You are the Research Agent of AgentDroid OS. Gather factual, objective, analytical insights with key competitor differentiation metrics. Do not fabricate citations or facts."

        val response = provider.generateResponse(prompt, systemPrompt, activeModel)

        context.put("research_summary", response.content)
        context.put("research_full_text", response.content)

        return AgentExecutionOutput(
            summary = "Research completed: ${response.content.take(120)}...",
            outputData = mapOf(
                "research_summary" to response.content,
                "full_analysis" to response.content
            )
        )
    }
}
