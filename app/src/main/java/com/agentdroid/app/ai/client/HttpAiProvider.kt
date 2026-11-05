package com.agentdroid.app.ai.client

import com.agentdroid.app.ai.error.AiError
import com.agentdroid.app.ai.error.ErrorCategory
import com.agentdroid.app.ai.provider.AiProvider
import com.agentdroid.app.ai.provider.AiResponse
import com.agentdroid.app.domain.model.ActionType
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.RiskLevel
import com.agentdroid.app.domain.model.TaskItem
import com.agentdroid.app.domain.model.TaskStatus
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject
import java.io.IOException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.util.UUID
import java.util.concurrent.TimeUnit

class HttpAiProvider(
    override val providerId: String,
    override val displayName: String,
    private val baseUrl: String,
    private val apiKeyProvider: () -> String,
    private val providerType: String,
    val activeModel: String = "gpt-4o"
) : AiProvider {

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    override suspend fun generateResponse(
        prompt: String,
        systemPrompt: String,
        model: String,
        temperature: Float,
        maxTokens: Int
    ): AiResponse = withContext(Dispatchers.IO) {
        val apiKey = apiKeyProvider()
        val isLocal = providerType == "OLLAMA" || baseUrl.contains("localhost") || baseUrl.contains("127.0.0.1") || baseUrl.contains("10.0.2.2") || baseUrl.contains("192.168.")
        if (apiKey.isBlank() && !isLocal) {
            throw AiError.apiKeyMissing(displayName)
        }

        val effectiveModel = if (model.isNotBlank()) model else activeModel

        try {
            when (providerType.uppercase()) {
                "GEMINI" -> executeGeminiRequest(prompt, systemPrompt, effectiveModel, apiKey)
                "ANTHROPIC" -> executeAnthropicRequest(prompt, systemPrompt, effectiveModel, apiKey, maxTokens, temperature)
                "OLLAMA" -> executeOllamaChatRequest(prompt, systemPrompt, effectiveModel, maxTokens, temperature)
                else -> executeOpenAiCompatibleRequest(prompt, systemPrompt, effectiveModel, apiKey, maxTokens, temperature)
            }
        } catch (e: Exception) {
            when (e) {
                is AiError -> throw e
                is SocketTimeoutException -> throw AiError.requestTimeout(displayName, e.message ?: "Socket timeout")
                is UnknownHostException -> throw AiError.networkError(displayName, "DNS host resolution failed")
                is IOException -> throw AiError.networkError(displayName, e.message ?: "Network error")
                is JSONException -> throw AiError.invalidResponse(displayName, e.message ?: "Malformed JSON in response")
                else -> throw AiError(
                    errorCode = "ERR_REQUEST_FAILED",
                    category = ErrorCategory.UNKNOWN_ERROR,
                    userFriendlyTitle = "Request Failed",
                    userFriendlyMessage = "AI request to $displayName failed: ${e.message}",
                    technicalDetails = AiError.sanitize(e.stackTraceToString()),
                    providerName = displayName,
                    modelName = effectiveModel
                )
            }
        }
    }

    private fun executeOllamaChatRequest(
        prompt: String,
        systemPrompt: String,
        model: String,
        maxTokens: Int,
        temperature: Float
    ): AiResponse {
        val url = if (baseUrl.endsWith("/")) "${baseUrl}api/chat" else "$baseUrl/api/chat"

        val jsonBody = JSONObject().apply {
            put("model", model)
            put("stream", false)
            val messages = JSONArray().apply {
                if (systemPrompt.isNotBlank()) {
                    put(JSONObject().apply {
                        put("role", "system")
                        put("content", systemPrompt)
                    })
                }
                put(JSONObject().apply {
                    put("role", "user")
                    put("content", prompt)
                })
            }
            put("messages", messages)
            put("options", JSONObject().apply {
                put("temperature", temperature)
                if (maxTokens > 0) put("num_predict", maxTokens)
            })
        }

        val request = Request.Builder()
            .url(url)
            .addHeader("Content-Type", "application/json")
            .post(jsonBody.toString().toRequestBody(jsonMediaType))
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                val errorBody = response.body?.string().orEmpty()
                if (response.code == 404) {
                    throw AiError.modelNotFound(displayName, model, "Model '$model' not found on Ollama server. Pull it using 'ollama pull $model'.")
                }
                handleErrorResponse(response.code, errorBody, model)
            }
            val resJson = JSONObject(response.body!!.string())
            val msgObj = resJson.optJSONObject("message")
            val content = msgObj?.optString("content", "") ?: ""

            val promptTokens = resJson.optInt("prompt_eval_count", 0)
            val compTokens = resJson.optInt("eval_count", 0)

            return AiResponse(
                content = content,
                promptTokens = promptTokens,
                completionTokens = compTokens,
                totalTokens = promptTokens + compTokens,
                modelUsed = model
            )
        }
    }

    private fun executeOpenAiCompatibleRequest(
        prompt: String,
        systemPrompt: String,
        model: String,
        apiKey: String,
        maxTokens: Int,
        temperature: Float
    ): AiResponse {
        val url = if (baseUrl.endsWith("/")) "${baseUrl}chat/completions" else "$baseUrl/chat/completions"

        val jsonBody = JSONObject().apply {
            put("model", model)
            put("temperature", temperature)
            put("max_tokens", maxTokens)
            val messages = JSONArray().apply {
                if (systemPrompt.isNotBlank()) {
                    put(JSONObject().apply {
                        put("role", "system")
                        put("content", systemPrompt)
                    })
                }
                put(JSONObject().apply {
                    put("role", "user")
                    put("content", prompt)
                })
            }
            put("messages", messages)
        }

        val request = Request.Builder()
            .url(url)
            .apply {
                if (apiKey.isNotBlank()) {
                    addHeader("Authorization", "Bearer $apiKey")
                }
            }
            .addHeader("Content-Type", "application/json")
            .post(jsonBody.toString().toRequestBody(jsonMediaType))
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                val errorBody = response.body?.string().orEmpty()
                handleErrorResponse(response.code, errorBody, model)
            }
            val resJson = JSONObject(response.body!!.string())
            val choices = resJson.getJSONArray("choices")
            if (choices.length() == 0) {
                throw AiError.invalidResponse(displayName, "No choices returned by $displayName")
            }
            val content = choices
                .getJSONObject(0)
                .getJSONObject("message")
                .getString("content")

            val usage = resJson.optJSONObject("usage")
            val promptTokens = usage?.optInt("prompt_tokens", 0) ?: 0
            val compTokens = usage?.optInt("completion_tokens", 0) ?: 0
            val totalTokens = usage?.optInt("total_tokens", promptTokens + compTokens) ?: (promptTokens + compTokens)

            return AiResponse(
                content = content,
                promptTokens = promptTokens,
                completionTokens = compTokens,
                totalTokens = totalTokens,
                modelUsed = model
            )
        }
    }

    private fun executeGeminiRequest(
        prompt: String,
        systemPrompt: String,
        model: String,
        apiKey: String
    ): AiResponse {
        val cleanModel = if (model.contains("/")) model.substringAfterLast("/") else model
        val url = "$baseUrl/v1beta/models/$cleanModel:generateContent?key=$apiKey"

        val jsonBody = JSONObject().apply {
            if (systemPrompt.isNotBlank()) {
                put("system_instruction", JSONObject().apply {
                    put("parts", JSONArray().apply {
                        put(JSONObject().apply { put("text", systemPrompt) })
                    })
                })
            }
            val contents = JSONArray().apply {
                put(JSONObject().apply {
                    put("role", "user")
                    put("parts", JSONArray().apply {
                        put(JSONObject().apply { put("text", prompt) })
                    })
                })
            }
            put("contents", contents)
        }

        val request = Request.Builder()
            .url(url)
            .addHeader("Content-Type", "application/json")
            .post(jsonBody.toString().toRequestBody(jsonMediaType))
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                val errorBody = response.body?.string().orEmpty()
                handleErrorResponse(response.code, errorBody, model)
            }
            val resJson = JSONObject(response.body!!.string())
            val candidates = resJson.optJSONArray("candidates")
            if (candidates == null || candidates.length() == 0) {
                val promptFeedback = resJson.optJSONObject("promptFeedback")
                if (promptFeedback?.optString("blockReason")?.isNotBlank() == true) {
                    throw AiError(
                        errorCode = "ERR_CONTENT_BLOCKED",
                        category = ErrorCategory.CONTENT_BLOCKED,
                        userFriendlyTitle = "Content Blocked",
                        userFriendlyMessage = "The request was blocked by the safety filters of $displayName.",
                        technicalDetails = promptFeedback.toString(),
                        providerName = displayName,
                        modelName = model,
                        retryAvailable = false
                    )
                }
                throw AiError.invalidResponse(displayName, "No candidates returned by Gemini: $resJson")
            }
            val candidate = candidates.getJSONObject(0)
            val parts = candidate.getJSONObject("content").getJSONArray("parts")
            val textBuilder = StringBuilder()
            for (i in 0 until parts.length()) {
                textBuilder.append(parts.getJSONObject(i).optString("text", ""))
            }

            val usageMeta = resJson.optJSONObject("usageMetadata")
            val promptTokens = usageMeta?.optInt("promptTokenCount", 0) ?: 0
            val compTokens = usageMeta?.optInt("candidatesTokenCount", 0) ?: 0

            return AiResponse(
                content = textBuilder.toString(),
                promptTokens = promptTokens,
                completionTokens = compTokens,
                totalTokens = promptTokens + compTokens,
                modelUsed = model
            )
        }
    }

    private fun executeAnthropicRequest(
        prompt: String,
        systemPrompt: String,
        model: String,
        apiKey: String,
        maxTokens: Int,
        temperature: Float
    ): AiResponse {
        val url = if (baseUrl.endsWith("/")) "${baseUrl}messages" else "$baseUrl/messages"

        val jsonBody = JSONObject().apply {
            put("model", model)
            put("max_tokens", maxTokens)
            put("temperature", temperature)
            if (systemPrompt.isNotBlank()) {
                put("system", systemPrompt)
            }
            val messages = JSONArray().apply {
                put(JSONObject().apply {
                    put("role", "user")
                    put("content", prompt)
                })
            }
            put("messages", messages)
        }

        val request = Request.Builder()
            .url(url)
            .addHeader("x-api-key", apiKey)
            .addHeader("anthropic-version", "2023-06-01")
            .addHeader("Content-Type", "application/json")
            .post(jsonBody.toString().toRequestBody(jsonMediaType))
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                val errorBody = response.body?.string().orEmpty()
                handleErrorResponse(response.code, errorBody, model)
            }
            val resJson = JSONObject(response.body!!.string())
            val contentArray = resJson.getJSONArray("content")
            val textBuilder = StringBuilder()
            for (i in 0 until contentArray.length()) {
                textBuilder.append(contentArray.getJSONObject(i).optString("text", ""))
            }

            val usage = resJson.optJSONObject("usage")
            val inputTokens = usage?.optInt("input_tokens", 0) ?: 0
            val outputTokens = usage?.optInt("output_tokens", 0) ?: 0

            return AiResponse(
                content = textBuilder.toString(),
                promptTokens = inputTokens,
                completionTokens = outputTokens,
                totalTokens = inputTokens + outputTokens,
                modelUsed = model
            )
        }
    }

    private fun handleErrorResponse(code: Int, errorBody: String, model: String): Nothing {
        when {
            code == 401 || code == 403 -> {
                throw AiError.invalidApiKey(displayName, "HTTP $code: $errorBody")
            }
            code == 404 -> {
                throw AiError.modelNotFound(displayName, model, "HTTP 404: $errorBody")
            }
            code == 429 -> {
                if (errorBody.contains("insufficient_quota", ignoreCase = true)) {
                    throw AiError.quotaExceeded(displayName, errorBody)
                } else {
                    throw AiError.rateLimited(displayName, errorBody)
                }
            }
            code in 500..599 -> {
                throw AiError.providerUnavailable(displayName, "HTTP $code: $errorBody")
            }
            else -> {
                throw AiError.invalidResponse(displayName, "HTTP $code: $errorBody")
            }
        }
    }

    override fun streamResponse(
        prompt: String,
        systemPrompt: String,
        model: String,
        temperature: Float
    ): Flow<String> = flow {
        val full = generateResponse(prompt, systemPrompt, model, temperature)
        val words = full.content.split(" ")
        for (w in words) {
            emit("$w ")
            kotlinx.coroutines.delay(20)
        }
    }

    override suspend fun decomposeUserGoal(
        userGoal: String,
        availableAgents: List<AgentRole>
    ): List<TaskItem> {
        val systemPrompt = """
            You are the Master Orchestration Agent of AgentDroid OS.
            Decompose the user goal into discrete, logical subtasks.
            Each subtask must be assigned to exactly one of the available agents:
            ${availableAgents.joinToString { it.name }}
            
            Return ONLY a valid JSON array of objects with keys:
            - "title": short task title
            - "agentRole": one of ${availableAgents.joinToString { it.name }}
            - "description": specific instructions
            - "riskLevel": "LOW", "MEDIUM", or "HIGH"
            - "actionType": one of "OPEN_APP", "READ_SCREEN", "TYPE_TEXT", "POST_SOCIAL", "SEND_EMAIL", "CREATE_FILE", "EXECUTE_CUSTOM_TOOL", "OPEN_URL"
        """.trimIndent()

        val response = generateResponse(userGoal, systemPrompt, activeModel, 0.2f)
        return parseTasksFromJson(response.content, userGoal)
    }

    override suspend fun synthesizeReport(
        userGoal: String,
        completedTasks: List<TaskItem>
    ): String {
        val taskSummaries = completedTasks.joinToString("\n") { t ->
            "- [${t.agentRole.displayName}] ${t.title}: ${t.outputData["summary"] ?: t.description}"
        }
        val prompt = "User Goal: $userGoal\n\nSubtasks Completed:\n$taskSummaries\n\nGenerate a consolidated, professional executive report synthesizing the results for the user."
        val response = generateResponse(prompt, "You are AgentDroid Master Agent summarizing completed multi-agent operations.", activeModel, 0.5f)
        return response.content
    }

    override suspend fun testConnection(): Boolean = withContext(Dispatchers.IO) {
        try {
            val apiKey = apiKeyProvider()
            val isLocal = providerType == "OLLAMA" || baseUrl.contains("localhost") || baseUrl.contains("127.0.0.1") || baseUrl.contains("10.0.2.2") || baseUrl.contains("192.168.")
            if (apiKey.isBlank() && !isLocal) return@withContext false
            val res = generateResponse("ping", "reply pong", activeModel, 0.1f, 10)
            res.content.isNotBlank()
        } catch (e: Exception) {
            false
        }
    }

    private fun parseTasksFromJson(jsonStr: String, goal: String): List<TaskItem> {
        val tasks = mutableListOf<TaskItem>()
        val planId = UUID.randomUUID().toString()
        val cleaned = jsonStr.substringAfter("[").substringBeforeLast("]")
        if (cleaned.isBlank()) {
            throw AiError.invalidResponse(displayName, "Model did not output a valid JSON array of tasks: $jsonStr")
        }

        val jsonArray = JSONArray("[$cleaned]")
        for (i in 0 until jsonArray.length()) {
            val obj = jsonArray.getJSONObject(i)
            val roleName = obj.optString("agentRole", "MASTER")
            val role = try { AgentRole.valueOf(roleName) } catch (e: Exception) { AgentRole.MASTER }
            val title = obj.optString("title", "Step ${i + 1}")
            val desc = obj.optString("description", "")
            val risk = try { RiskLevel.valueOf(obj.optString("riskLevel", "LOW")) } catch (e: Exception) { RiskLevel.LOW }
            val actionType = try { ActionType.valueOf(obj.optString("actionType", "EXECUTE_CUSTOM_TOOL")) } catch (e: Exception) { ActionType.EXECUTE_CUSTOM_TOOL }

            val taskId = "task_${planId}_${i + 1}"
            val dependsOn = if (i > 0) listOf("task_${planId}_$i") else emptyList()

            tasks.add(
                TaskItem(
                    id = taskId,
                    planId = planId,
                    agentRole = role,
                    title = title,
                    description = desc,
                    status = TaskStatus.PENDING,
                    riskLevel = risk,
                    actionType = actionType,
                    dependsOn = dependsOn
                )
            )
        }
        return tasks
    }
}
