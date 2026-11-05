package com.agentdroid.app.ai.connection

import com.agentdroid.app.ai.client.HttpAiProvider
import com.agentdroid.app.ai.discovery.DiscoveryResult
import com.agentdroid.app.ai.discovery.ModelDiscoveryService
import com.agentdroid.app.ai.error.AiError
import com.agentdroid.app.ai.error.ErrorCategory
import com.agentdroid.app.ai.provider.AiProvider
import com.agentdroid.app.data.local.dao.SettingsDao
import com.agentdroid.app.data.local.entity.ApiProviderEntity
import com.agentdroid.app.data.local.entity.ModelConfigEntity
import com.agentdroid.app.data.local.preferences.SecurePreferencesManager
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.requiredCapabilities
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.SocketTimeoutException
import java.net.URI
import java.net.UnknownHostException
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit

enum class ConnectionState {
    NOT_CONFIGURED,
    CONFIGURED,
    CONNECTING,
    CONNECTED,
    AUTHENTICATION_FAILED,
    INVALID_API_KEY,
    MODEL_NOT_FOUND,
    RATE_LIMITED,
    NETWORK_ERROR,
    PROVIDER_UNAVAILABLE,
    REQUEST_TIMEOUT,
    UNKNOWN_ERROR
}

data class ProviderConnectionStatus(
    val providerId: String,
    val providerName: String,
    val state: ConnectionState,
    val lastChecked: Long? = null,
    val lastError: AiError? = null,
    val availableModels: List<String> = emptyList(),
    val isKeyPresent: Boolean = false,
    val isLocal: Boolean = false,
    val activeModel: String? = null
)

data class AiSystemStatus(
    val activeProviderId: String? = null,
    val activeProviderName: String? = null,
    val activeModel: String? = null,
    val connectedProviderCount: Int = 0,
    val totalConfiguredCount: Int = 0,
    val isAnyConnected: Boolean = false,
    val lastCheckTimestamp: Long? = null,
    val currentMasterState: ConnectionState = ConnectionState.NOT_CONFIGURED
)

data class ProviderValidationResult(
    val isConnected: Boolean,
    val state: ConnectionState,
    val error: AiError? = null,
    val responseTimeMs: Long = 0L,
    val availableModels: List<String> = emptyList()
)

class AiConnectionManager(
    private val settingsDao: SettingsDao,
    private val securePreferences: SecurePreferencesManager,
    val modelDiscoveryService: ModelDiscoveryService = ModelDiscoveryService(settingsDao)
) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .build()

    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    private val _providerStatuses = ConcurrentHashMap<String, ProviderConnectionStatus>()
    private val _systemStatus = MutableStateFlow(AiSystemStatus())
    val systemStatus: StateFlow<AiSystemStatus> = _systemStatus.asStateFlow()

    private val _statusMapFlow = MutableStateFlow<Map<String, ProviderConnectionStatus>>(emptyMap())
    val providerStatuses: StateFlow<Map<String, ProviderConnectionStatus>> = _statusMapFlow.asStateFlow()

    suspend fun refreshAllStatuses() = withContext(Dispatchers.IO) {
        val providers = settingsDao.getAllProvidersSync()
        val allDiscovered = settingsDao.getAllDiscoveredModelsSync()
        val allConfigs = settingsDao.getConfigForRole(AgentRole.MASTER.name)
        var connectedCount = 0
        var configuredCount = 0

        for (provider in providers) {
            val key = securePreferences.getApiKey(provider.id)
            val isHostLocal = try {
                val host = URI.create(provider.baseUrl).host ?: ""
                NetworkSecurityValidator.isLocalOrPrivateHost(host)
            } catch (e: Exception) { false }
            val isLocal = isHostLocal || provider.providerType == "OLLAMA"
            val isKeyConfigured = key.isNotBlank() || isLocal

            if (isKeyConfigured) {
                configuredCount++
            }

            val currentStatus = _providerStatuses[provider.id]
            val state = when {
                !provider.isEnabled -> ConnectionState.NOT_CONFIGURED
                !isKeyConfigured -> ConnectionState.NOT_CONFIGURED
                currentStatus?.state == ConnectionState.CONNECTED -> {
                    connectedCount++
                    ConnectionState.CONNECTED
                }
                isKeyConfigured -> currentStatus?.state ?: ConnectionState.CONFIGURED
                else -> ConnectionState.NOT_CONFIGURED
            }

            val modelsForProv = allDiscovered.filter { it.providerId == provider.id }.map { it.modelId }
            val assignedConfig = settingsDao.getConfigForRole(AgentRole.MASTER.name)?.takeIf { it.providerId == provider.id }

            _providerStatuses[provider.id] = ProviderConnectionStatus(
                providerId = provider.id,
                providerName = provider.displayName,
                state = state,
                lastChecked = currentStatus?.lastChecked,
                lastError = currentStatus?.lastError,
                availableModels = modelsForProv.ifEmpty { currentStatus?.availableModels ?: emptyList() },
                isKeyPresent = key.isNotBlank(),
                isLocal = isLocal,
                activeModel = assignedConfig?.modelName
            )
        }

        val masterConfig = settingsDao.getConfigForRole(AgentRole.MASTER.name)
        val activeProvider = masterConfig?.let { settingsDao.getProviderById(it.providerId) }
        val masterStatus = activeProvider?.let { _providerStatuses[it.id]?.state } ?: ConnectionState.NOT_CONFIGURED

        _systemStatus.value = AiSystemStatus(
            activeProviderId = activeProvider?.id,
            activeProviderName = activeProvider?.displayName,
            activeModel = masterConfig?.modelName,
            connectedProviderCount = connectedCount,
            totalConfiguredCount = configuredCount,
            isAnyConnected = connectedCount > 0,
            lastCheckTimestamp = System.currentTimeMillis(),
            currentMasterState = masterStatus
        )
        _statusMapFlow.value = _providerStatuses.toMap()
    }

    suspend fun testProviderConnection(providerId: String): ProviderValidationResult = withContext(Dispatchers.IO) {
        val provider = settingsDao.getProviderById(providerId)
            ?: return@withContext ProviderValidationResult(
                isConnected = false,
                state = ConnectionState.NOT_CONFIGURED,
                error = AiError.notConfigured(providerId)
            )

        // 1. Validate Base URL
        val urlValidation = NetworkSecurityValidator.validateEndpointUrl(provider.baseUrl)
        if (!urlValidation.isValid) {
            val err = AiError.configurationInvalid(
                providerName = provider.displayName,
                title = "Invalid Base URL",
                message = urlValidation.errorMessage ?: "Invalid URL format."
            )
            updateStatus(provider.id, provider.displayName, ConnectionState.UNKNOWN_ERROR, err, false)
            return@withContext ProviderValidationResult(false, ConnectionState.UNKNOWN_ERROR, err)
        }

        val isLocal = urlValidation.isLocal || provider.providerType == "OLLAMA"
        val apiKey = securePreferences.getApiKey(provider.id)

        // 2. Validate API key if required
        if (apiKey.isBlank() && !isLocal) {
            val err = AiError.apiKeyMissing(provider.displayName)
            updateStatus(provider.id, provider.displayName, ConnectionState.NOT_CONFIGURED, err, false)
            return@withContext ProviderValidationResult(false, ConnectionState.NOT_CONFIGURED, err)
        }

        // 3. Mark Connecting
        updateStatus(provider.id, provider.displayName, ConnectionState.CONNECTING, null, apiKey.isNotBlank(), isLocal = isLocal)

        val startTime = System.currentTimeMillis()

        // 4. Perform dynamic model discovery and connectivity test
        val discoveryResult = modelDiscoveryService.discoverAndSync(provider, apiKey)
        val duration = System.currentTimeMillis() - startTime

        return@withContext when (discoveryResult) {
            is DiscoveryResult.Success -> {
                val modelNames = discoveryResult.models.map { it.modelId }
                val assignedConfig = settingsDao.getConfigForRole(AgentRole.MASTER.name)?.takeIf { it.providerId == provider.id }
                updateStatus(
                    providerId = provider.id,
                    providerName = provider.displayName,
                    state = ConnectionState.CONNECTED,
                    error = null,
                    keyPresent = apiKey.isNotBlank(),
                    models = modelNames,
                    isLocal = isLocal,
                    activeModel = assignedConfig?.modelName ?: modelNames.firstOrNull()
                )
                ProviderValidationResult(
                    isConnected = true,
                    state = ConnectionState.CONNECTED,
                    error = null,
                    responseTimeMs = duration,
                    availableModels = modelNames
                )
            }
            is DiscoveryResult.Failure -> {
                val connState = aiErrToConnectionState(discoveryResult.error)
                val cachedNames = discoveryResult.cachedModels.map { it.modelId }
                updateStatus(
                    providerId = provider.id,
                    providerName = provider.displayName,
                    state = connState,
                    error = discoveryResult.error,
                    keyPresent = apiKey.isNotBlank(),
                    models = cachedNames,
                    isLocal = isLocal
                )
                ProviderValidationResult(
                    isConnected = false,
                    state = connState,
                    error = discoveryResult.error,
                    responseTimeMs = duration,
                    availableModels = cachedNames
                )
            }
        }
    }

    suspend fun refreshModelsForProvider(providerId: String): DiscoveryResult = withContext(Dispatchers.IO) {
        val provider = settingsDao.getProviderById(providerId)
            ?: return@withContext DiscoveryResult.Failure(
                AiError.notConfigured(providerId),
                emptyList()
            )
        val key = securePreferences.getApiKey(provider.id)
        val result = modelDiscoveryService.discoverAndSync(provider, key)
        refreshAllStatuses()
        return@withContext result
    }

    suspend fun assignModelToAgent(
        roleName: String,
        providerId: String,
        modelName: String,
        temperature: Float = 0.7f,
        maxTokens: Int = 2048
    ) = withContext(Dispatchers.IO) {
        val configId = "cfg_${roleName.lowercase()}"
        val entity = ModelConfigEntity(
            id = configId,
            agentRole = roleName,
            providerId = providerId,
            modelName = modelName,
            temperature = temperature,
            maxTokens = maxTokens
        )
        settingsDao.insertModelConfig(entity)
        refreshAllStatuses()
    }

    suspend fun removeProvider(providerId: String) = withContext(Dispatchers.IO) {
        val provider = settingsDao.getProviderById(providerId)
        if (provider != null) {
            settingsDao.deleteProvider(provider)
        }
        settingsDao.deleteDiscoveredModelsForProvider(providerId)
        securePreferences.saveApiKey(providerId, "")
        _providerStatuses.remove(providerId)
        refreshAllStatuses()
    }

    suspend fun validateAndGetProvider(role: AgentRole): Result<AiProvider> = withContext(Dispatchers.IO) {
        val roleConfig = settingsDao.getConfigForRole(role.name)
            ?: settingsDao.getConfigForRole("GLOBAL_DEFAULT")
            ?: settingsDao.getConfigForRole(AgentRole.MASTER.name)
            ?: return@withContext Result.failure(AiError.notConfigured())

        val provider = settingsDao.getProviderById(roleConfig.providerId)
            ?: return@withContext Result.failure(AiError.notConfigured(roleConfig.providerId))

        if (!provider.isEnabled) {
            return@withContext Result.failure(
                AiError.providerUnavailable(provider.displayName, "Provider is disabled in settings.")
            )
        }

        val isLocalHost = try {
            val host = URI.create(provider.baseUrl).host ?: ""
            NetworkSecurityValidator.isLocalOrPrivateHost(host)
        } catch (e: Exception) { false }
        val isLocal = isLocalHost || provider.providerType == "OLLAMA"

        val apiKey = securePreferences.getApiKey(provider.id)
        if (apiKey.isBlank() && !isLocal) {
            val err = AiError.apiKeyMissing(provider.displayName)
            updateStatus(provider.id, provider.displayName, ConnectionState.NOT_CONFIGURED, err, false, isLocal = isLocal)
            return@withContext Result.failure(err)
        }

        // Validate Model Capabilities for this specific agent
        val discoveredModels = settingsDao.getDiscoveredModelsForProviderSync(provider.id)
        val modelEntity = discoveredModels.firstOrNull { it.modelId == roleConfig.modelName }
        if (modelEntity != null && modelEntity.capabilitiesJson.isNotBlank()) {
            try {
                val jsonArr = JSONArray(modelEntity.capabilitiesJson)
                val modelCaps = (0 until jsonArr.length()).map { jsonArr.getString(it) }.toSet()
                val required = role.requiredCapabilities()
                val missing = required.filter { !modelCaps.contains(it.name) }
                if (missing.isNotEmpty()) {
                    val err = AiError.configurationInvalid(
                        providerName = provider.displayName,
                        title = "Model Capability Incompatible",
                        message = "Model '${roleConfig.modelName}' lacks required capabilities for ${role.displayName}: ${missing.joinToString { it.displayName }}.",
                        details = "Missing required capabilities: ${missing.map { it.name }}",
                        action = com.agentdroid.app.ai.error.SuggestedAction.SELECT_ANOTHER_MODEL
                    )
                    return@withContext Result.failure(err)
                }
            } catch (_: Exception) {}
        }

        val cachedStatus = _providerStatuses[provider.id]
        if (cachedStatus?.state != ConnectionState.CONNECTED) {
            val validation = testProviderConnection(provider.id)
            if (!validation.isConnected) {
                return@withContext Result.failure(validation.error ?: AiError.notConfigured(provider.displayName))
            }
        }

        val httpProvider = HttpAiProvider(
            providerId = provider.id,
            displayName = provider.displayName,
            baseUrl = provider.baseUrl,
            apiKeyProvider = { securePreferences.getApiKey(provider.id) },
            providerType = provider.providerType,
            activeModel = roleConfig.modelName
        )
        return@withContext Result.success(httpProvider)
    }

    private fun aiErrToConnectionState(err: AiError): ConnectionState {
        return when (err.category) {
            ErrorCategory.AI_NOT_CONFIGURED -> ConnectionState.NOT_CONFIGURED
            ErrorCategory.API_KEY_MISSING -> ConnectionState.NOT_CONFIGURED
            ErrorCategory.API_KEY_INVALID -> ConnectionState.INVALID_API_KEY
            ErrorCategory.MODEL_NOT_FOUND -> ConnectionState.MODEL_NOT_FOUND
            ErrorCategory.RATE_LIMIT_EXCEEDED, ErrorCategory.QUOTA_EXCEEDED -> ConnectionState.RATE_LIMITED
            ErrorCategory.NETWORK_UNAVAILABLE -> ConnectionState.NETWORK_ERROR
            ErrorCategory.REQUEST_TIMEOUT -> ConnectionState.REQUEST_TIMEOUT
            ErrorCategory.PROVIDER_UNAVAILABLE -> ConnectionState.PROVIDER_UNAVAILABLE
            else -> ConnectionState.UNKNOWN_ERROR
        }
    }

    private fun updateStatus(
        providerId: String,
        providerName: String,
        state: ConnectionState,
        error: AiError?,
        keyPresent: Boolean,
        models: List<String> = emptyList(),
        isLocal: Boolean = false,
        activeModel: String? = null
    ) {
        val updated = ProviderConnectionStatus(
            providerId = providerId,
            providerName = providerName,
            state = state,
            lastChecked = System.currentTimeMillis(),
            lastError = error,
            availableModels = models.ifEmpty { _providerStatuses[providerId]?.availableModels ?: emptyList() },
            isKeyPresent = keyPresent,
            isLocal = isLocal,
            activeModel = activeModel ?: _providerStatuses[providerId]?.activeModel
        )
        _providerStatuses[providerId] = updated
        _statusMapFlow.value = _providerStatuses.toMap()

        val connectedCount = _providerStatuses.values.count { it.state == ConnectionState.CONNECTED }
        val configuredCount = _providerStatuses.values.count { it.isKeyPresent || it.isLocal }

        _systemStatus.value = _systemStatus.value.copy(
            connectedProviderCount = connectedCount,
            totalConfiguredCount = configuredCount,
            isAnyConnected = connectedCount > 0,
            lastCheckTimestamp = System.currentTimeMillis()
        )
    }
}
