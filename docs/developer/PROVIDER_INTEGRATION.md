---
title: AI Provider Integration Guide
purpose: Technical instructions for integrating new LLM providers and custom inference endpoints
scope: AiProvider interface, HTTP adapters, streaming contracts, and error mapping
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/architecture/AI_PROVIDER_ARCHITECTURE.md
  - docs/api/AI_PROVIDER_INTERFACES.md
  - docs/developer/DEBUGGING.md
---

# AI Provider Integration Guide

AgentDroid is provider-agnostic. All external AI backends (OpenAI, Gemini, Anthropic, Ollama, Groq, LM Studio) implement the unified `AiProvider` interface.

---

## 1. The `AiProvider` Contract

```kotlin
interface AiProvider {
    val id: String
    val name: String
    val isConfigured: Boolean

    suspend fun complete(
        prompt: String,
        options: CompletionOptions = CompletionOptions()
    ): Result<AiResponse>

    suspend fun stream(
        prompt: String,
        options: CompletionOptions = CompletionOptions()
    ): Flow<String>

    suspend fun validateConnection(): ConnectionStatus
}
```

---

## 2. Implementing a Custom Provider

To add a new provider (e.g., Mistral API or a proprietary internal server):

```kotlin
class MistralAiProvider(
    private val client: OkHttpClient,
    private val securePreferences: SecurePreferencesManager
) : HttpAiProvider() {

    override val id: String = "mistral"
    override val name: String = "Mistral AI"

    override suspend fun complete(prompt: String, options: CompletionOptions): Result<AiResponse> {
        val apiKey = securePreferences.getApiKey(id)
            ?: return Result.failure(AiError.ApiKeyMissing("Mistral API key not configured."))

        val payload = buildJsonPayload(prompt, options)
        val request = Request.Builder()
            .url("https://api.mistral.ai/v1/chat/completions")
            .addHeader("Authorization", "Bearer $apiKey")
            .post(payload.toRequestBody(JSON_MEDIA_TYPE))
            .build()

        return executeRequest(client, request) { responseBody ->
            parseMistralResponse(responseBody)
        }
    }
}
```

---

## 3. Registering with `ModelDiscoveryService`

After creating your provider class:
1. Add provider metadata to `ProviderMetadataRegistry`:
   * Set `endpointPattern`, `discoveryPath`, and supported auth schemes.
2. Register the provider instance in `AiConnectionManager`.
3. Add a unit test verifying serialization, HTTP header construction, and error mapping.

---

## Related Documentation
* [AI Provider Architecture](file:///workspaces/hacknova/docs/architecture/AI_PROVIDER_ARCHITECTURE.md)
* [AI Provider Interfaces](file:///workspaces/hacknova/docs/api/AI_PROVIDER_INTERFACES.md)
* [Debugging Guide](file:///workspaces/hacknova/docs/developer/DEBUGGING.md)
