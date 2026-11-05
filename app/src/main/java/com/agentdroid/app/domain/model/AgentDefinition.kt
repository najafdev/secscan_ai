package com.agentdroid.app.domain.model

data class AgentDefinition(
    val id: String,
    val name: String,
    val role: AgentRole,
    val description: String,
    val capabilities: List<String>,
    val availableTools: List<String>,
    val requiredPermissions: List<String>,
    val assignedModel: String,
    val systemPrompt: String,
    val isEnabled: Boolean = true,
    val isCustom: Boolean = false,
    val temperature: Float = 0.7f,
    val executionLimitSeconds: Int = 120
)
