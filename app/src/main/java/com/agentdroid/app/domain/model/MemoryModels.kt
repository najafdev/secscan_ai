package com.agentdroid.app.domain.model

enum class MemoryTier {
    SESSION,
    TASK,
    AGENT,
    USER_PREFERENCES,
    LONG_TERM
}

data class MemoryRecord(
    val id: String,
    val tier: MemoryTier,
    val agentRole: AgentRole?,
    val key: String,
    val value: String,
    val tags: List<String> = emptyList(),
    val confidence: Float = 1.0f,
    val timestamp: Long = System.currentTimeMillis(),
    val accessCount: Int = 0
)
