package com.agentdroid.app.domain.model

enum class ModelCapability(val displayName: String) {
    TEXT_GENERATION("Text Generation"),
    STREAMING("Streaming"),
    TOOL_CALLING("Tool Calling"),
    STRUCTURED_OUTPUT("Structured Output"),
    VISION("Vision / Image Input"),
    IMAGE_INPUT("Image Input"),
    AUDIO_INPUT("Audio Input"),
    AUDIO_OUTPUT("Audio Output"),
    EMBEDDINGS("Embeddings"),
    REASONING("Reasoning")
}

fun AgentRole.requiredCapabilities(): Set<ModelCapability> {
    return when (this) {
        AgentRole.MASTER -> setOf(ModelCapability.TEXT_GENERATION, ModelCapability.STRUCTURED_OUTPUT, ModelCapability.REASONING)
        AgentRole.PHONE_CONTROL -> setOf(ModelCapability.TEXT_GENERATION, ModelCapability.TOOL_CALLING, ModelCapability.REASONING)
        AgentRole.RESEARCH -> setOf(ModelCapability.TEXT_GENERATION, ModelCapability.TOOL_CALLING)
        AgentRole.CONTENT_CREATION -> setOf(ModelCapability.TEXT_GENERATION)
        AgentRole.SOCIAL_MEDIA -> setOf(ModelCapability.TEXT_GENERATION, ModelCapability.STRUCTURED_OUTPUT)
        AgentRole.COMMUNICATION -> setOf(ModelCapability.TEXT_GENERATION)
        AgentRole.FILE_MANAGEMENT -> setOf(ModelCapability.TEXT_GENERATION)
        AgentRole.PRODUCTIVITY -> setOf(ModelCapability.TEXT_GENERATION, ModelCapability.STRUCTURED_OUTPUT)
        AgentRole.ANALYTICS -> setOf(ModelCapability.TEXT_GENERATION, ModelCapability.STRUCTURED_OUTPUT)
        AgentRole.BROWSER -> setOf(ModelCapability.TEXT_GENERATION, ModelCapability.TOOL_CALLING)
        AgentRole.SECURITY -> setOf(ModelCapability.TEXT_GENERATION, ModelCapability.REASONING)
        AgentRole.CUSTOM -> setOf(ModelCapability.TEXT_GENERATION)
    }
}
