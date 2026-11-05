package com.agentdroid.app.ai.router

import com.agentdroid.app.ai.connection.AiConnectionManager
import com.agentdroid.app.ai.connection.ConnectionState
import com.agentdroid.app.ai.error.AiError
import com.agentdroid.app.ai.provider.AiProvider
import com.agentdroid.app.data.local.dao.SettingsDao
import com.agentdroid.app.data.local.preferences.SecurePreferencesManager
import com.agentdroid.app.domain.model.AgentRole

class AiModelRouter(
    private val settingsDao: SettingsDao,
    private val securePreferences: SecurePreferencesManager,
    private val aiConnectionManager: AiConnectionManager
) {
    suspend fun getProviderForAgent(role: AgentRole): AiProvider {
        val result = aiConnectionManager.validateAndGetProvider(role)
        if (result.isSuccess) {
            return result.getOrThrow()
        }

        val primaryError = result.exceptionOrNull() as? AiError ?: AiError.notConfigured()

        // Check if an explicit fallback provider is configured for this role
        val config = settingsDao.getConfigForRole(role.name)
        val fallbackProviderId = config?.providerId?.takeIf { it.startsWith("fallback_") }
        if (fallbackProviderId != null) {
            val fallbackProvider = settingsDao.getProviderById(fallbackProviderId)
            if (fallbackProvider != null && fallbackProvider.isEnabled) {
                val fallbackKey = securePreferences.getApiKey(fallbackProvider.id)
                if (fallbackKey.isNotBlank()) {
                    val fallbackResult = aiConnectionManager.testProviderConnection(fallbackProvider.id)
                    if (fallbackResult.isConnected) {
                        return aiConnectionManager.validateAndGetProvider(role).getOrNull()
                            ?: throw primaryError
                    }
                }
            }
        }

        // Strict Real AI Mode: No silent mock fallbacks allowed
        throw primaryError
    }

    suspend fun getActiveModelForAgent(role: AgentRole): String {
        val config = settingsDao.getConfigForRole(role.name)
        return config?.modelName ?: "gpt-4o"
    }

    suspend fun isAgentAiReady(role: AgentRole): Boolean {
        return try {
            getProviderForAgent(role)
            true
        } catch (e: Exception) {
            false
        }
    }
}
