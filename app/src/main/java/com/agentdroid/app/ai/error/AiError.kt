package com.agentdroid.app.ai.error

enum class ErrorCategory {
    AI_NOT_CONFIGURED,
    API_KEY_MISSING,
    API_KEY_INVALID,
    MODEL_NOT_FOUND,
    PROVIDER_UNAVAILABLE,
    RATE_LIMIT_EXCEEDED,
    NETWORK_UNAVAILABLE,
    REQUEST_TIMEOUT,
    INVALID_RESPONSE,
    CONTENT_BLOCKED,
    QUOTA_EXCEEDED,
    AGENT_EXECUTION_FAILED,
    TOOL_EXECUTION_FAILED,
    PERMISSION_DENIED,
    CONFIGURATION_INVALID,
    UNKNOWN_ERROR
}

enum class SuggestedAction {
    CONNECT_PROVIDER,
    OPEN_SETTINGS,
    UPDATE_API_KEY,
    TEST_CONNECTION,
    SELECT_ANOTHER_MODEL,
    RETRY_NOW,
    WAIT_AND_RETRY,
    CHECK_NETWORK,
    CHECK_PROVIDER_USAGE,
    DISMISS
}

data class AiError(
    val errorCode: String,
    val category: ErrorCategory,
    val userFriendlyTitle: String,
    val userFriendlyMessage: String,
    val technicalDetails: String,
    val providerName: String? = null,
    val modelName: String? = null,
    val retryAvailable: Boolean = true,
    val suggestedAction: SuggestedAction = SuggestedAction.OPEN_SETTINGS,
    val timestamp: Long = System.currentTimeMillis()
) : Exception(userFriendlyMessage) {

    companion object {
        fun notConfigured(
            providerName: String? = null,
            modelName: String? = null
        ): AiError {
            return AiError(
                errorCode = "ERR_AI_NOT_CONFIGURED",
                category = ErrorCategory.AI_NOT_CONFIGURED,
                userFriendlyTitle = "AI Model Not Connected",
                userFriendlyMessage = "AgentDroid needs a connected AI model to process your requests. Connect an AI provider in Settings → AI Providers to continue.",
                technicalDetails = "No active AI provider with valid credentials configured for orchestration.",
                providerName = providerName,
                modelName = modelName,
                retryAvailable = false,
                suggestedAction = SuggestedAction.CONNECT_PROVIDER
            )
        }

        fun apiKeyMissing(providerName: String): AiError {
            return AiError(
                errorCode = "ERR_API_KEY_MISSING",
                category = ErrorCategory.API_KEY_MISSING,
                userFriendlyTitle = "API Key Missing",
                userFriendlyMessage = "No API key configured for $providerName. Please provide an API key in Settings.",
                technicalDetails = "Provider '$providerName' has an empty API key in Secure Keystore storage.",
                providerName = providerName,
                retryAvailable = false,
                suggestedAction = SuggestedAction.UPDATE_API_KEY
            )
        }

        fun invalidApiKey(providerName: String, rawError: String): AiError {
            return AiError(
                errorCode = "ERR_AUTH_FAILED",
                category = ErrorCategory.API_KEY_INVALID,
                userFriendlyTitle = "Authentication Failed",
                userFriendlyMessage = "The configured API key was rejected by $providerName. Please verify your credentials.",
                technicalDetails = sanitize(rawError),
                providerName = providerName,
                retryAvailable = false,
                suggestedAction = SuggestedAction.UPDATE_API_KEY
            )
        }

        fun modelNotFound(providerName: String, modelName: String, rawError: String): AiError {
            return AiError(
                errorCode = "ERR_MODEL_NOT_FOUND",
                category = ErrorCategory.MODEL_NOT_FOUND,
                userFriendlyTitle = "Model Unavailable",
                userFriendlyMessage = "The model '$modelName' could not be found or is not accessible with your current $providerName configuration.",
                technicalDetails = sanitize(rawError),
                providerName = providerName,
                modelName = modelName,
                retryAvailable = false,
                suggestedAction = SuggestedAction.SELECT_ANOTHER_MODEL
            )
        }

        fun networkError(providerName: String, rawError: String): AiError {
            return AiError(
                errorCode = "ERR_NETWORK_UNAVAILABLE",
                category = ErrorCategory.NETWORK_UNAVAILABLE,
                userFriendlyTitle = "Connection Failed",
                userFriendlyMessage = "AgentDroid could not reach $providerName. Check your internet connection and try again.",
                technicalDetails = sanitize(rawError),
                providerName = providerName,
                retryAvailable = true,
                suggestedAction = SuggestedAction.CHECK_NETWORK
            )
        }

        fun rateLimited(providerName: String, rawError: String): AiError {
            return AiError(
                errorCode = "ERR_RATE_LIMIT",
                category = ErrorCategory.RATE_LIMIT_EXCEEDED,
                userFriendlyTitle = "Rate Limit Reached",
                userFriendlyMessage = "The AI provider ($providerName) has temporarily limited requests. Please wait before trying again.",
                technicalDetails = sanitize(rawError),
                providerName = providerName,
                retryAvailable = true,
                suggestedAction = SuggestedAction.WAIT_AND_RETRY
            )
        }

        fun quotaExceeded(providerName: String, rawError: String): AiError {
            return AiError(
                errorCode = "ERR_QUOTA_EXCEEDED",
                category = ErrorCategory.QUOTA_EXCEEDED,
                userFriendlyTitle = "Provider Quota Exceeded",
                userFriendlyMessage = "The configured AI provider ($providerName) has insufficient quota or credits to complete this request.",
                technicalDetails = sanitize(rawError),
                providerName = providerName,
                retryAvailable = false,
                suggestedAction = SuggestedAction.CHECK_PROVIDER_USAGE
            )
        }

        fun requestTimeout(providerName: String, rawError: String): AiError {
            return AiError(
                errorCode = "ERR_TIMEOUT",
                category = ErrorCategory.REQUEST_TIMEOUT,
                userFriendlyTitle = "Request Timed Out",
                userFriendlyMessage = "The AI provider ($providerName) did not respond within the allowed time.",
                technicalDetails = sanitize(rawError),
                providerName = providerName,
                retryAvailable = true,
                suggestedAction = SuggestedAction.RETRY_NOW
            )
        }

        fun invalidResponse(providerName: String, rawError: String): AiError {
            return AiError(
                errorCode = "ERR_INVALID_RESPONSE",
                category = ErrorCategory.INVALID_RESPONSE,
                userFriendlyTitle = "Malformed Response",
                userFriendlyMessage = "The AI provider returned an unexpected or malformed response structure.",
                technicalDetails = sanitize(rawError),
                providerName = providerName,
                retryAvailable = true,
                suggestedAction = SuggestedAction.RETRY_NOW
            )
        }

        fun providerUnavailable(providerName: String, rawError: String): AiError {
            return AiError(
                errorCode = "ERR_PROVIDER_UNAVAILABLE",
                category = ErrorCategory.PROVIDER_UNAVAILABLE,
                userFriendlyTitle = "Provider Unavailable",
                userFriendlyMessage = "$providerName is currently experiencing outages or internal errors. Please try again later.",
                technicalDetails = sanitize(rawError),
                providerName = providerName,
                retryAvailable = true,
                suggestedAction = SuggestedAction.WAIT_AND_RETRY
            )
        }

        fun configurationInvalid(
            providerName: String,
            title: String,
            message: String,
            details: String = "",
            action: SuggestedAction = SuggestedAction.OPEN_SETTINGS
        ): AiError {
            return AiError(
                errorCode = "ERR_CONFIGURATION_INVALID",
                category = ErrorCategory.CONFIGURATION_INVALID,
                userFriendlyTitle = title,
                userFriendlyMessage = message,
                technicalDetails = sanitize(details.ifBlank { message }),
                providerName = providerName,
                suggestedAction = action
            )
        }

        fun agentExecutionFailed(agentName: String, rawError: String): AiError {
            return AiError(
                errorCode = "ERR_AGENT_EXECUTION",
                category = ErrorCategory.AGENT_EXECUTION_FAILED,
                userFriendlyTitle = "Agent Execution Failed",
                userFriendlyMessage = "Agent '$agentName' encountered a critical failure during task execution.",
                technicalDetails = sanitize(rawError),
                retryAvailable = true,
                suggestedAction = SuggestedAction.RETRY_NOW
            )
        }

        fun toolExecutionFailed(toolName: String, rawError: String): AiError {
            return AiError(
                errorCode = "ERR_TOOL_EXECUTION",
                category = ErrorCategory.TOOL_EXECUTION_FAILED,
                userFriendlyTitle = "Device Tool Failed",
                userFriendlyMessage = "Device automation tool '$toolName' failed to execute.",
                technicalDetails = sanitize(rawError),
                retryAvailable = true,
                suggestedAction = SuggestedAction.RETRY_NOW
            )
        }

        fun sanitize(input: String): String {
            // Never expose API keys, bearer tokens, or authorization headers in error details or logs
            return input
                .replace(Regex("(?i)Bearer\\s+[a-zA-Z0-9_\\-\\.]+"), "Bearer [REDACTED]")
                .replace(Regex("(?i)(sk-[a-zA-Z0-9_-]{8})[a-zA-Z0-9_-]+"), "$1[REDACTED]")
                .replace(Regex("(?i)(key=)[a-zA-Z0-9_\\-]+"), "$1[REDACTED]")
                .replace(Regex("(?i)x-api-key:\\s*[^\\r\\n]+"), "x-api-key: [REDACTED]")
                .take(300)
        }
    }
}
