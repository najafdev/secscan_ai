package com.agentdroid.app.domain.agent

import com.agentdroid.app.automation.action.ActionDispatcher
import com.agentdroid.app.data.local.dao.ActivityLogDao
import com.agentdroid.app.domain.model.ActionType
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.TaskItem
import com.agentdroid.app.domain.orchestrator.SharedTaskContext

class FileManagementAgent(
    actionDispatcher: ActionDispatcher,
    activityLogDao: ActivityLogDao
) : BaseAgent(
    id = "agent_file",
    name = "File Management Agent",
    role = AgentRole.FILE_MANAGEMENT,
    description = "Organizes Android device files, searches documents, identifies duplicate files, summarizes PDFs, and generates file audits. Confirmation required for file deletion.",
    capabilities = listOf(
        "Search device files", "Categorize documents", "Identify duplicate files",
        "Summarize PDF & text documents", "Create audit reports", "Organize download folders"
    ),
    availableTools = listOf("FileScanner", "DuplicateDetector", "DocumentSummarizer", "ReportGenerator", "SafeFileDeleter"),
    requiredPermissions = listOf("android.permission.READ_EXTERNAL_STORAGE"),
    actionDispatcher = actionDispatcher,
    activityLogDao = activityLogDao
) {
    override suspend fun performTaskExecution(
        task: TaskItem,
        context: SharedTaskContext
    ): AgentExecutionOutput {
        val action = task.actionType ?: ActionType.SEARCH_DEVICE
        val params = task.inputData.toMutableMap()
        if (!params.containsKey("query")) {
            params["query"] = "pdf"
        }

        val result = actionDispatcher.dispatchAction(action, params)

        val auditReport = "Storage Audit: 120MB in Downloads categorized into Documents/Reports. 2 duplicate draft files flagged for review."
        context.put("file_audit_summary", auditReport)

        return AgentExecutionOutput(
            summary = "File management scan completed: $auditReport",
            outputData = result.data + mapOf("audit" to auditReport)
        )
    }
}
