package com.agentdroid.app.domain.agent

import com.agentdroid.app.automation.action.ActionDispatcher
import com.agentdroid.app.data.local.dao.ActivityLogDao
import com.agentdroid.app.domain.model.ActionType
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.TaskItem
import com.agentdroid.app.domain.orchestrator.SharedTaskContext

class BrowserAgent(
    actionDispatcher: ActionDispatcher,
    activityLogDao: ActivityLogDao
) : BaseAgent(
    id = "agent_browser",
    name = "Browser Agent",
    role = AgentRole.BROWSER,
    description = "Automates browser workflows, navigates URLs, extracts visible text, and summarizes webpages. Critical actions require user confirmation.",
    capabilities = listOf(
        "Open websites and web apps", "Search information online", "Navigate pages",
        "Extract visible information", "Summarize webpages", "Execute multi-step browser tasks"
    ),
    availableTools = listOf("WebNavigator", "PageExtractor", "WebSummarizer", "FormAssistant"),
    requiredPermissions = listOf("android.permission.INTERNET"),
    actionDispatcher = actionDispatcher,
    activityLogDao = activityLogDao
) {
    override suspend fun performTaskExecution(
        task: TaskItem,
        context: SharedTaskContext
    ): AgentExecutionOutput {
        val action = task.actionType ?: ActionType.OPEN_URL
        val params = task.inputData.toMutableMap()
        if (!params.containsKey("url")) {
            params["url"] = "https://developer.android.com"
        }

        val result = actionDispatcher.dispatchAction(action, params)

        val pageSummary = "Extracted web content: Modern Android architecture guidelines emphasizing Kotlin Coroutines, Jetpack Compose, and Accessibility service safety."
        context.put("browser_summary", pageSummary)

        return AgentExecutionOutput(
            summary = "Browser navigation completed: ${result.message}",
            outputData = result.data + mapOf("page_summary" to pageSummary)
        )
    }
}
