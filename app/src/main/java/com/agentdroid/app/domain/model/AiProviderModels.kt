package com.agentdroid.app.domain.model

enum class AiProviderType(val displayName: String) {
    OPENAI("OpenAI"),
    GEMINI("Google Gemini"),
    ANTHROPIC("Anthropic Claude"),
    OPENROUTER("OpenRouter"),
    GROQ("Groq"),
    TOGETHER("Together AI"),
    OLLAMA("Ollama (Local)"),
    CUSTOM_ENDPOINT("Custom OpenAI Compatible"),
    AUTONOMOUS_FALLBACK("Autonomous Mock AI Engine")
}

data class AiProviderConfig(
    val id: String,
    val providerType: AiProviderType,
    val displayName: String,
    val baseUrl: String,
    val apiKey: String = "",
    val defaultModel: String,
    val availableModels: List<String>,
    val isEnabled: Boolean = true,
    val timeoutSeconds: Int = 45,
    val totalTokensUsed: Long = 0L
)

data class AiModelAssignment(
    val agentRole: AgentRole,
    val providerId: String,
    val modelName: String,
    val temperature: Float = 0.7f,
    val maxTokens: Int = 2048
)
