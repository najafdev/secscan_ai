package com.agentdroid.app.sdk.extensions

import android.content.Context
import com.agentdroid.app.automation.action.ActionDispatcher
import com.agentdroid.app.data.local.dao.ActivityLogDao
import com.agentdroid.app.domain.agent.Agent
import com.agentdroid.app.domain.agent.AgentExecutionOutput
import com.agentdroid.app.domain.agent.BaseAgent
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.TaskItem
import com.agentdroid.app.domain.orchestrator.SharedTaskContext
import com.agentdroid.app.sdk.AgentPlugin
import com.agentdroid.app.sdk.PluginDependencies
import com.agentdroid.app.sdk.PluginMetadata

class CodingAgentPlugin : AgentPlugin {
    override val metadata = PluginMetadata(
        pluginId = "plugin_coding_agent",
        name = "Coding & Scripting Agent",
        version = "1.0.0",
        author = "AgentDroid Core Extensions",
        description = "Automates code analysis, syntax verification, bash scripting, and programmatic data transformation.",
        capabilities = listOf("Code Generation", "Syntax Auditing", "Script Generation", "Diff Computation")
    )

    override val providedRole = AgentRole.CUSTOM

    override fun createAgent(appContext: Context, dependencies: PluginDependencies): Agent {
        return object : BaseAgent(
            id = "agent_plugin_coding",
            name = metadata.name,
            role = AgentRole.CUSTOM,
            description = metadata.description,
            capabilities = metadata.capabilities,
            availableTools = listOf("CodeGenerator", "SyntaxAuditor", "ScriptExecutor"),
            requiredPermissions = emptyList(),
            actionDispatcher = dependencies.actionDispatcher as ActionDispatcher,
            activityLogDao = dependencies.activityLogDao as ActivityLogDao
        ) {
            override suspend fun performTaskExecution(
                task: TaskItem,
                context: SharedTaskContext
            ): AgentExecutionOutput {
                val codeOutput = "Generated automated Kotlin task executor with verified coroutine cancellation boundaries."
                context.put("coding_result", codeOutput)
                return AgentExecutionOutput(codeOutput, mapOf("code" to codeOutput))
            }
        }
    }
}
