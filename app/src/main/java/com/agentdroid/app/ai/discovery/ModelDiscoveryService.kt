package com.agentdroid.app.ai.discovery

import com.agentdroid.app.ai.connection.NetworkSecurityValidator
import com.agentdroid.app.ai.error.AiError
import com.agentdroid.app.ai.error.ErrorCategory
import com.agentdroid.app.data.local.dao.SettingsDao
import com.agentdroid.app.data.local.entity.ApiProviderEntity
import com.agentdroid.app.data.local.entity.DiscoveredModelEntity
import com.agentdroid.app.domain.model.ModelCapability
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.util.concurrent.TimeUnit

sealed class DiscoveryResult {
    data class Success(val models: List<DiscoveredModelEntity>, val isFresh: Boolean) : DiscoveryResult()
    data class Failure(val error: AiError, val cachedModels: List<DiscoveredModelEntity>) : DiscoveryResult()
}

class ModelDiscoveryService(
    private val settingsDao: SettingsDao,
    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .build()
) {
    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    suspend fun discoverAndSync(
        provider: ApiProviderEntity,
        apiKey: String
    ): DiscoveryResult = withContext(Dispatchers.IO) {
        val existingCached = settingsDao.getDiscoveredModelsForProviderSync(provider.id)

        // Validate URL security before attempting network
        val urlValidation = NetworkSecurityValidator.validateEndpointUrl(provider.baseUrl)
        if (!urlValidation.isValid) {
            val err = AiError.configurationInvalid(
                providerName = provider.displayName,
                title = "Invalid Server URL",
                message = urlValidation.errorMessage ?: "Malformed URL."
            )
            return@withContext DiscoveryResult.Failure(err, existingCached)
        }

        val sanitizedBaseUrl = urlValidation.sanitizedUrl ?: provider.baseUrl
        val isLocalProvider = urlValidation.isLocal || provider.providerType == "OLLAMA"

        try {
            val discoveredList = when (provider.providerType.uppercase()) {
                "OPENAI" -> fetchOpenAiModels(provider.id, provider.displayName, sanitizedBaseUrl, apiKey)
                "GEMINI" -> fetchGeminiModels(provider.id, provider.displayName, sanitizedBaseUrl, apiKey)
                "ANTHROPIC" -> fetchAnthropicModels(provider.id, provider.displayName, sanitizedBaseUrl, apiKey)
                "OPENROUTER" -> fetchOpenRouterModels(provider.id, provider.displayName, sanitizedBaseUrl, apiKey)
                "GROQ" -> fetchGroqModels(provider.id, provider.displayName, sanitizedBaseUrl, apiKey)
                "TOGETHER" -> fetchTogetherModels(provider.id, provider.displayName, sanitizedBaseUrl, apiKey)
                "OLLAMA" -> fetchOllamaModels(provider.id, provider.displayName, sanitizedBaseUrl)
                else -> fetchGenericOpenAiModels(provider.id, provider.displayName, sanitizedBaseUrl, apiKey, isLocalProvider)
            }

            if (discoveredList.isEmpty()) {
                if (provider.providerType == "OLLAMA") {
                    val err = AiError(
                        errorCode = "ERR_OLLAMA_NO_MODELS",
                        category = ErrorCategory.MODEL_NOT_FOUND,
                        userFriendlyTitle = "No Local Models Found",
                        userFriendlyMessage = "No local models found on the Ollama server ($sanitizedBaseUrl). Pull or install a model using 'ollama run <model>' first.",
                        technicalDetails = "Ollama /api/tags returned an empty models array.",
                        suggestedAction = com.agentdroid.app.ai.error.SuggestedAction.DISMISS,
                        providerName = provider.displayName
                    )
                    return@withContext DiscoveryResult.Failure(err, existingCached)
                }
            }

            // Sync with Room database: overwrite with fresh models
            settingsDao.deleteDiscoveredModelsForProvider(provider.id)
            settingsDao.insertDiscoveredModels(discoveredList)

            DiscoveryResult.Success(discoveredList, isFresh = true)
        } catch (e: Exception) {
            val aiErr = when (e) {
                is AiError -> e
                is SocketTimeoutException -> AiError.requestTimeout(provider.displayName, "Model discovery timed out.")
                is UnknownHostException -> AiError.networkError(provider.displayName, "DNS resolution failed for server host.")
                is IOException -> AiError.networkError(provider.displayName, e.message ?: "I/O error connecting to server.")
                else -> AiError(
                    errorCode = "ERR_DISCOVERY_FAILED",
                    category = ErrorCategory.UNKNOWN_ERROR,
                    userFriendlyTitle = "Model Discovery Failed",
                    userFriendlyMessage = "Failed to fetch model catalog from ${provider.displayName}: ${e.message}",
                    technicalDetails = AiError.sanitize(e.stackTraceToString()),
                    providerName = provider.displayName
                )
            }

            // Preserve cached models marked as cached
            val markedCached = existingCached.map { it.copy(isCached = true) }
            if (markedCached.isNotEmpty()) {
                settingsDao.insertDiscoveredModels(markedCached)
            }
            DiscoveryResult.Failure(aiErr, markedCached)
        }
    }

    private fun fetchOpenAiModels(
        providerId: String,
        providerName: String,
        baseUrl: String,
        apiKey: String
    ): List<DiscoveredModelEntity> {
        if (apiKey.isBlank()) throw AiError.apiKeyMissing(providerName)
        val url = if (baseUrl.endsWith("/")) "${baseUrl}models" else "$baseUrl/models"
        val request = Request.Builder()
            .url(url)
            .addHeader("Authorization", "Bearer $apiKey")
            .get()
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                handleHttpError(response.code, response.body?.string().orEmpty(), providerName)
            }
            val json = JSONObject(response.body!!.string())
            val data = json.optJSONArray("data") ?: JSONArray()
            val result = mutableListOf<DiscoveredModelEntity>()

            for (i in 0 until data.length()) {
                val item = data.getJSONObject(i)
                val modelId = item.optString("id")
                if (modelId.isBlank()) continue

                // Filter out non-chat utility models (whisper, dall-e, tts, embeddings)
                if (modelId.contains("whisper") || modelId.contains("tts") || modelId.contains("dall-e") || modelId.contains("embedding") || modelId.contains("moderation")) {
                    continue
                }

                val caps = mutableListOf(ModelCapability.TEXT_GENERATION.name, ModelCapability.STREAMING.name)
                if (modelId.contains("gpt-4") || modelId.contains("o1") || modelId.contains("o3") || modelId.contains("turbo")) {
                    caps.add(ModelCapability.TOOL_CALLING.name)
                    caps.add(ModelCapability.STRUCTURED_OUTPUT.name)
                }
                if (modelId.contains("vision") || modelId.contains("4o") || modelId.contains("gpt-4-turbo")) {
                    caps.add(ModelCapability.VISION.name)
                    caps.add(ModelCapability.IMAGE_INPUT.name)
                }
                if (modelId.startsWith("o1") || modelId.startsWith("o3")) {
                    caps.add(ModelCapability.REASONING.name)
                }

                val context = when {
                    modelId.contains("4o") || modelId.contains("o1") -> 128000
                    modelId.contains("turbo") -> 128000
                    else -> 16384
                }

                result.add(
                    DiscoveredModelEntity(
                        id = "$providerId:$modelId",
                        modelId = modelId,
                        providerId = providerId,
                        displayName = modelId,
                        modelType = "CLOUD",
                        capabilitiesJson = JSONArray(caps).toString(),
                        contextWindow = context,
                        isAvailable = true,
                        isLocal = false,
                        lastVerified = System.currentTimeMillis(),
                        isCached = false
                    )
                )
            }
            return result
        }
    }

    private fun fetchGeminiModels(
        providerId: String,
        providerName: String,
        baseUrl: String,
        apiKey: String
    ): List<DiscoveredModelEntity> {
        if (apiKey.isBlank()) throw AiError.apiKeyMissing(providerName)
        val url = "$baseUrl/v1beta/models?key=$apiKey"
        val request = Request.Builder().url(url).get().build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                handleHttpError(response.code, response.body?.string().orEmpty(), providerName)
            }
            val json = JSONObject(response.body!!.string())
            val models = json.optJSONArray("models") ?: JSONArray()
            val result = mutableListOf<DiscoveredModelEntity>()

            for (i in 0 until models.length()) {
                val item = models.getJSONObject(i)
                val rawName = item.optString("name")
                val cleanId = rawName.substringAfterLast("/")
                if (cleanId.isBlank()) continue

                // Check supportedGenerationMethods
                val methods = item.optJSONArray("supportedGenerationMethods")
                val supportsGenerate = methods?.let { arr ->
                    (0 until arr.length()).any { arr.getString(it) == "generateContent" }
                } ?: true

                if (!supportsGenerate) continue

                val caps = mutableListOf(
                    ModelCapability.TEXT_GENERATION.name,
                    ModelCapability.STREAMING.name,
                    ModelCapability.TOOL_CALLING.name,
                    ModelCapability.STRUCTURED_OUTPUT.name,
                    ModelCapability.VISION.name
                )
                if (cleanId.contains("pro") || cleanId.contains("thinking")) {
                    caps.add(ModelCapability.REASONING.name)
                }

                val contextWindow = item.optInt("inputTokenLimit", 1000000)
                val displayName = item.optString("displayName", cleanId)

                result.add(
                    DiscoveredModelEntity(
                        id = "$providerId:$cleanId",
                        modelId = cleanId,
                        providerId = providerId,
                        displayName = displayName,
                        modelType = "CLOUD",
                        capabilitiesJson = JSONArray(caps).toString(),
                        contextWindow = contextWindow,
                        isAvailable = true,
                        isLocal = false,
                        lastVerified = System.currentTimeMillis(),
                        isCached = false
                    )
                )
            }
            return result
        }
    }

    private fun fetchAnthropicModels(
        providerId: String,
        providerName: String,
        baseUrl: String,
        apiKey: String
    ): List<DiscoveredModelEntity> {
        if (apiKey.isBlank()) throw AiError.apiKeyMissing(providerName)
        val url = if (baseUrl.endsWith("/")) "${baseUrl}models" else "$baseUrl/models"
        val request = Request.Builder()
            .url(url)
            .addHeader("x-api-key", apiKey)
            .addHeader("anthropic-version", "2023-06-01")
            .get()
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                // If models endpoint is not accessible or returns 404, fallback to known official Claude models
                if (response.code == 404) {
                    return getAnthropicFallbackModels(providerId)
                }
                handleHttpError(response.code, response.body?.string().orEmpty(), providerName)
            }
            val json = JSONObject(response.body!!.string())
            val data = json.optJSONArray("data") ?: JSONArray()
            val result = mutableListOf<DiscoveredModelEntity>()

            for (i in 0 until data.length()) {
                val item = data.getJSONObject(i)
                val modelId = item.optString("id")
                if (modelId.isBlank()) continue

                val caps = mutableListOf(
                    ModelCapability.TEXT_GENERATION.name,
                    ModelCapability.STREAMING.name,
                    ModelCapability.TOOL_CALLING.name,
                    ModelCapability.STRUCTURED_OUTPUT.name,
                    ModelCapability.VISION.name
                )
                if (modelId.contains("sonnet") || modelId.contains("opus")) {
                    caps.add(ModelCapability.REASONING.name)
                }

                val displayName = item.optString("display_name", modelId)
                result.add(
                    DiscoveredModelEntity(
                        id = "$providerId:$modelId",
                        modelId = modelId,
                        providerId = providerId,
                        displayName = displayName,
                        modelType = "CLOUD",
                        capabilitiesJson = JSONArray(caps).toString(),
                        contextWindow = 200000,
                        isAvailable = true,
                        isLocal = false,
                        lastVerified = System.currentTimeMillis(),
                        isCached = false
                    )
                )
            }
            return if (result.isEmpty()) getAnthropicFallbackModels(providerId) else result
        }
    }

    private fun getAnthropicFallbackModels(providerId: String): List<DiscoveredModelEntity> {
        return listOf(
            DiscoveredModelEntity("$providerId:claude-3-5-sonnet-20241022", "claude-3-5-sonnet-20241022", providerId, "Claude 3.5 Sonnet v2", "CLOUD", "[\"TEXT_GENERATION\",\"STREAMING\",\"TOOL_CALLING\",\"STRUCTURED_OUTPUT\",\"VISION\",\"REASONING\"]", 200000, isAvailable = true, isLocal = false),
            DiscoveredModelEntity("$providerId:claude-3-5-haiku-20241022", "claude-3-5-haiku-20241022", providerId, "Claude 3.5 Haiku", "CLOUD", "[\"TEXT_GENERATION\",\"STREAMING\",\"TOOL_CALLING\",\"STRUCTURED_OUTPUT\"]", 200000, isAvailable = true, isLocal = false),
            DiscoveredModelEntity("$providerId:claude-3-opus-20240229", "claude-3-opus-20240229", providerId, "Claude 3 Opus", "CLOUD", "[\"TEXT_GENERATION\",\"STREAMING\",\"TOOL_CALLING\",\"STRUCTURED_OUTPUT\",\"VISION\",\"REASONING\"]", 200000, isAvailable = true, isLocal = false)
        )
    }

    private fun fetchOpenRouterModels(
        providerId: String,
        providerName: String,
        baseUrl: String,
        apiKey: String
    ): List<DiscoveredModelEntity> {
        val url = if (baseUrl.endsWith("/")) "${baseUrl}models" else "$baseUrl/models"
        val request = Request.Builder()
            .url(url)
            .apply { if (apiKey.isNotBlank()) addHeader("Authorization", "Bearer $apiKey") }
            .get()
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                handleHttpError(response.code, response.body?.string().orEmpty(), providerName)
            }
            val json = JSONObject(response.body!!.string())
            val data = json.optJSONArray("data") ?: JSONArray()
            val result = mutableListOf<DiscoveredModelEntity>()

            for (i in 0 until data.length()) {
                val item = data.getJSONObject(i)
                val modelId = item.optString("id")
                if (modelId.isBlank()) continue

                val name = item.optString("name", modelId)
                val context = item.optInt("context_length", 32768)
                val caps = mutableListOf(ModelCapability.TEXT_GENERATION.name, ModelCapability.STREAMING.name)
                val arch = item.optJSONObject("architecture")
                val modality = arch?.optString("modality", "") ?: ""
                if (modality.contains("image")) {
                    caps.add(ModelCapability.VISION.name)
                }
                caps.add(ModelCapability.TOOL_CALLING.name)

                result.add(
                    DiscoveredModelEntity(
                        id = "$providerId:$modelId",
                        modelId = modelId,
                        providerId = providerId,
                        displayName = name,
                        modelType = "CLOUD",
                        capabilitiesJson = JSONArray(caps).toString(),
                        contextWindow = context,
                        isAvailable = true,
                        isLocal = false,
                        lastVerified = System.currentTimeMillis(),
                        isCached = false
                    )
                )
            }
            return result
        }
    }

    private fun fetchGroqModels(
        providerId: String,
        providerName: String,
        baseUrl: String,
        apiKey: String
    ): List<DiscoveredModelEntity> {
        if (apiKey.isBlank()) throw AiError.apiKeyMissing(providerName)
        val url = if (baseUrl.endsWith("/")) "${baseUrl}models" else "$baseUrl/models"
        val request = Request.Builder()
            .url(url)
            .addHeader("Authorization", "Bearer $apiKey")
            .get()
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                handleHttpError(response.code, response.body?.string().orEmpty(), providerName)
            }
            val json = JSONObject(response.body!!.string())
            val data = json.optJSONArray("data") ?: JSONArray()
            val result = mutableListOf<DiscoveredModelEntity>()

            for (i in 0 until data.length()) {
                val item = data.getJSONObject(i)
                val modelId = item.optString("id")
                if (modelId.isBlank() || modelId.contains("whisper")) continue

                val context = item.optInt("context_window", 128000)
                val caps = mutableListOf(
                    ModelCapability.TEXT_GENERATION.name,
                    ModelCapability.STREAMING.name,
                    ModelCapability.TOOL_CALLING.name
                )
                if (modelId.contains("vision")) {
                    caps.add(ModelCapability.VISION.name)
                }

                result.add(
                    DiscoveredModelEntity(
                        id = "$providerId:$modelId",
                        modelId = modelId,
                        providerId = providerId,
                        displayName = modelId,
                        modelType = "CLOUD",
                        capabilitiesJson = JSONArray(caps).toString(),
                        contextWindow = context,
                        isAvailable = true,
                        isLocal = false,
                        lastVerified = System.currentTimeMillis(),
                        isCached = false
                    )
                )
            }
            return result
        }
    }

    private fun fetchTogetherModels(
        providerId: String,
        providerName: String,
        baseUrl: String,
        apiKey: String
    ): List<DiscoveredModelEntity> {
        if (apiKey.isBlank()) throw AiError.apiKeyMissing(providerName)
        val url = if (baseUrl.endsWith("/")) "${baseUrl}models" else "$baseUrl/models"
        val request = Request.Builder()
            .url(url)
            .addHeader("Authorization", "Bearer $apiKey")
            .get()
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                handleHttpError(response.code, response.body?.string().orEmpty(), providerName)
            }
            val bodyStr = response.body!!.string()
            val result = mutableListOf<DiscoveredModelEntity>()

            val dataArray = try {
                if (bodyStr.trim().startsWith("[")) {
                    JSONArray(bodyStr)
                } else {
                    JSONObject(bodyStr).optJSONArray("data") ?: JSONArray()
                }
            } catch (e: Exception) {
                JSONArray()
            }

            for (i in 0 until dataArray.length()) {
                val item = dataArray.getJSONObject(i)
                val modelId = item.optString("id").ifBlank { item.optString("name") }
                if (modelId.isBlank()) continue

                val type = item.optString("type", "chat")
                if (type != "chat" && type != "language") continue

                val context = item.optInt("context_length", 32768)
                val caps = listOf(ModelCapability.TEXT_GENERATION.name, ModelCapability.STREAMING.name)

                result.add(
                    DiscoveredModelEntity(
                        id = "$providerId:$modelId",
                        modelId = modelId,
                        providerId = providerId,
                        displayName = modelId,
                        modelType = "CLOUD",
                        capabilitiesJson = JSONArray(caps).toString(),
                        contextWindow = context,
                        isAvailable = true,
                        isLocal = false,
                        lastVerified = System.currentTimeMillis(),
                        isCached = false
                    )
                )
            }
            return result
        }
    }

    private fun fetchOllamaModels(
        providerId: String,
        providerName: String,
        baseUrl: String
    ): List<DiscoveredModelEntity> {
        val url = if (baseUrl.endsWith("/")) "${baseUrl}api/tags" else "$baseUrl/api/tags"
        val request = Request.Builder().url(url).get().build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                handleHttpError(response.code, response.body?.string().orEmpty(), providerName)
            }
            val json = JSONObject(response.body!!.string())
            val models = json.optJSONArray("models") ?: JSONArray()
            val result = mutableListOf<DiscoveredModelEntity>()

            for (i in 0 until models.length()) {
                val item = models.getJSONObject(i)
                val modelName = item.optString("name").ifBlank { item.optString("model") }
                if (modelName.isBlank()) continue

                val details = item.optJSONObject("details")
                val paramSize = details?.optString("parameter_size", "") ?: ""
                val family = details?.optString("family", "") ?: ""
                val cleanTitle = if (paramSize.isNotBlank()) "$modelName ($paramSize)" else modelName

                val caps = mutableListOf(ModelCapability.TEXT_GENERATION.name, ModelCapability.STREAMING.name)
                if (modelName.contains("llama3") || modelName.contains("qwen2") || modelName.contains("mistral")) {
                    caps.add(ModelCapability.TOOL_CALLING.name)
                    caps.add(ModelCapability.STRUCTURED_OUTPUT.name)
                }
                if (modelName.contains("llava") || modelName.contains("vision")) {
                    caps.add(ModelCapability.VISION.name)
                }

                result.add(
                    DiscoveredModelEntity(
                        id = "$providerId:$modelName",
                        modelId = modelName,
                        providerId = providerId,
                        displayName = cleanTitle,
                        modelType = "LOCAL",
                        capabilitiesJson = JSONArray(caps).toString(),
                        contextWindow = 8192,
                        isAvailable = true,
                        isLocal = true,
                        lastVerified = System.currentTimeMillis(),
                        isCached = false
                    )
                )
            }
            return result
        }
    }

    private fun fetchGenericOpenAiModels(
        providerId: String,
        providerName: String,
        baseUrl: String,
        apiKey: String,
        isLocal: Boolean
    ): List<DiscoveredModelEntity> {
        val url = if (baseUrl.endsWith("/")) "${baseUrl}models" else "$baseUrl/models"
        val request = Request.Builder()
            .url(url)
            .apply {
                if (apiKey.isNotBlank()) {
                    addHeader("Authorization", "Bearer $apiKey")
                }
            }
            .get()
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                handleHttpError(response.code, response.body?.string().orEmpty(), providerName)
            }
            val json = JSONObject(response.body!!.string())
            val data = json.optJSONArray("data") ?: JSONArray()
            val result = mutableListOf<DiscoveredModelEntity>()

            for (i in 0 until data.length()) {
                val item = data.getJSONObject(i)
                val modelId = item.optString("id")
                if (modelId.isBlank()) continue

                val caps = listOf(
                    ModelCapability.TEXT_GENERATION.name,
                    ModelCapability.STREAMING.name,
                    ModelCapability.TOOL_CALLING.name
                )

                result.add(
                    DiscoveredModelEntity(
                        id = "$providerId:$modelId",
                        modelId = modelId,
                        providerId = providerId,
                        displayName = modelId,
                        modelType = if (isLocal) "LOCAL" else "CLOUD",
                        capabilitiesJson = JSONArray(caps).toString(),
                        contextWindow = 32768,
                        isAvailable = true,
                        isLocal = isLocal,
                        lastVerified = System.currentTimeMillis(),
                        isCached = false
                    )
                )
            }
            return result
        }
    }

    private fun handleHttpError(code: Int, errorBody: String, providerName: String): Nothing {
        when {
            code == 401 || code == 403 -> throw AiError.invalidApiKey(providerName, "HTTP $code: $errorBody")
            code == 404 -> throw AiError(
                errorCode = "ERR_ENDPOINT_NOT_FOUND",
                category = ErrorCategory.MODEL_NOT_FOUND,
                userFriendlyTitle = "Endpoint Not Found",
                userFriendlyMessage = "$providerName model discovery endpoint returned 404.",
                technicalDetails = errorBody,
                providerName = providerName
            )
            code == 429 -> throw AiError.rateLimited(providerName, errorBody)
            code in 500..599 -> throw AiError.providerUnavailable(providerName, "HTTP $code: $errorBody")
            else -> throw AiError.invalidResponse(providerName, "HTTP $code: $errorBody")
        }
    }
}
