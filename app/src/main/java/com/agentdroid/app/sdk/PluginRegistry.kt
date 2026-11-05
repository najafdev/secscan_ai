package com.agentdroid.app.sdk

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.concurrent.ConcurrentHashMap

class PluginRegistry(private val context: Context? = null) {
    private val plugins = ConcurrentHashMap<String, AgentPlugin>()
    private val _installedPlugins = MutableStateFlow<List<PluginMetadata>>(emptyList())
    val installedPlugins: StateFlow<List<PluginMetadata>> = _installedPlugins.asStateFlow()

    fun registerPlugin(plugin: AgentPlugin) {
        plugins[plugin.metadata.pluginId] = plugin
        context?.let { plugin.onInstall(it) }
        updateInstalledList()
    }

    fun unregisterPlugin(pluginId: String) {
        val plugin = plugins.remove(pluginId)
        context?.let { plugin?.onUninstall(it) }
        updateInstalledList()
    }

    fun getPlugin(pluginId: String): AgentPlugin? {
        return plugins[pluginId]
    }

    fun getAllPlugins(): List<AgentPlugin> {
        return plugins.values.toList()
    }

    private fun updateInstalledList() {
        _installedPlugins.value = plugins.values.map { it.metadata }
    }
}
