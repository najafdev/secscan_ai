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

class MeetingAssistantPlugin : AgentPlugin {
    override val metadata = PluginMetadata(
        pluginId = "plugin_meeting_assistant",
        name = "Meeting & Audio Assistant",
        version = "1.0.0",
        author = "AgentDroid Core Extensions",
        description = "Triages calendar meeting invitations, prepares agenda messages, extracts live conversation action items, and prepares executive meeting recaps.",
        capabilities = listOf("Meeting Recaps", "Agenda Generation", "Action Item Extraction", "Calendar Scheduling")
    )

    override val providedRole = AgentRole.CUSTOM

    override fun createAgent(appContext: Context, dependencies: PluginDependencies): Agent {
        return object : BaseAgent(
            id = "agent_plugin_meeting",
            name = metadata.name,
            role = AgentRole.CUSTOM,
            description = metadata.description,
            capabilities = metadata.capabilities,
            availableTools = listOf("AgendaBuilder", "RecapSynthesizer", "ActionExtractor"),
            requiredPermissions = emptyList(),
            actionDispatcher = dependencies.actionDispatcher as ActionDispatcher,
            activityLogDao = dependencies.activityLogDao as ActivityLogDao
        ) {
            override suspend fun performTaskExecution(
                task: TaskItem,
                context: SharedTaskContext
            ): AgentExecutionOutput {
                val recap = "Meeting Recap: Reviewed multi-agent architecture and accessibility service integration. 3 action items assigned."
                context.put("meeting_recap", recap)
                return AgentExecutionOutput(recap, mapOf("recap" to recap))
            }
        }
    }
}
