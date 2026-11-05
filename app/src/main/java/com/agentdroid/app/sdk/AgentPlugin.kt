package com.agentdroid.app.sdk

import android.content.Context
import com.agentdroid.app.domain.agent.Agent
import com.agentdroid.app.domain.model.AgentRole

data class PluginMetadata(
    val pluginId: String,
    val name: String,
    val version: String,
    val author: String,
    val description: String,
    val capabilities: List<String>,
    val requiredPermissions: List<String> = emptyList(),
    val iconUrl: String? = null
)

interface AgentPlugin {
    val metadata: PluginMetadata
    val providedRole: AgentRole

    fun createAgent(appContext: Context, dependencies: PluginDependencies): Agent
    fun onInstall(appContext: Context) {}
    fun onUninstall(appContext: Context) {}
}

data class PluginDependencies(
    val actionDispatcher: Any,
    val activityLogDao: Any,
    val aiModelRouter: Any
)
