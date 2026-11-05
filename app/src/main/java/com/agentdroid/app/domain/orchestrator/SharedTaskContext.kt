package com.agentdroid.app.domain.orchestrator

import com.agentdroid.app.domain.model.AgentRole
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import java.util.concurrent.ConcurrentHashMap

data class AgentMessage(
    val fromAgent: AgentRole,
    val toAgent: AgentRole,
    val content: String,
    val timestamp: Long = System.currentTimeMillis()
)

data class OrchestratorEvent(
    val type: String,
    val agentRole: AgentRole?,
    val taskId: String?,
    val message: String,
    val timestamp: Long = System.currentTimeMillis()
)

class SharedTaskContext(val planId: String) {
    private val dataStore = ConcurrentHashMap<String, String>()
    private val messages = mutableListOf<AgentMessage>()
    private val _events = MutableSharedFlow<OrchestratorEvent>(replay = 50, extraBufferCapacity = 100)
    val events: SharedFlow<OrchestratorEvent> = _events.asSharedFlow()

    fun put(key: String, value: String) {
        dataStore[key] = value
    }

    fun get(key: String): String? {
        return dataStore[key]
    }

    fun getOrDefault(key: String, default: String): String {
        return dataStore[key] ?: default
    }

    fun getAll(): Map<String, String> {
        return HashMap(dataStore)
    }

    @Synchronized
    fun postMessage(fromAgent: AgentRole, toAgent: AgentRole, content: String) {
        val msg = AgentMessage(fromAgent, toAgent, content)
        messages.add(msg)
    }

    @Synchronized
    fun getMessagesFor(agent: AgentRole): List<AgentMessage> {
        return messages.filter { it.toAgent == agent }
    }

    suspend fun emitEvent(type: String, agentRole: AgentRole?, taskId: String?, message: String) {
        _events.emit(OrchestratorEvent(type, agentRole, taskId, message))
    }
}
