package com.agentdroid.app.ai.provider

import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.TaskItem
import com.agentdroid.app.domain.model.TaskPlan
import kotlinx.coroutines.flow.Flow

interface AiProvider {
    val providerId: String
    val displayName: String

    suspend fun generateResponse(
        prompt: String,
        systemPrompt: String,
        model: String,
        temperature: Float = 0.7f,
        maxTokens: Int = 2048
    ): AiResponse

    fun streamResponse(
        prompt: String,
        systemPrompt: String,
        model: String,
        temperature: Float = 0.7f
    ): Flow<String>

    suspend fun decomposeUserGoal(
        userGoal: String,
        availableAgents: List<AgentRole>
    ): List<TaskItem>

    suspend fun synthesizeReport(
        userGoal: String,
        completedTasks: List<TaskItem>
    ): String

    suspend fun testConnection(): Boolean
}

data class AiResponse(
    val content: String,
    val promptTokens: Int = 0,
    val completionTokens: Int = 0,
    val totalTokens: Int = 0,
    val modelUsed: String = ""
)
