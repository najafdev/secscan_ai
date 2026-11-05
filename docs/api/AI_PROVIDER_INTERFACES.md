---
title: AI Provider Interfaces & API Reference
purpose: Technical specifications for AiProvider, HttpAiProvider, and AiConnectionManager
scope: Interface definitions, data transfer objects, request/response structures, and streaming
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/api/API_OVERVIEW.md
  - docs/architecture/AI_PROVIDER_ARCHITECTURE.md
  - docs/developer/PROVIDER_INTEGRATION.md
---

# AI Provider Interfaces & API Reference

This document provides the API reference for AI provider integration, client communication, and model discovery.

---

## 1. `AiProvider` Interface

```kotlin
package com.agentdroid.app.ai.provider

import kotlinx.coroutines.flow.Flow

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

## 2. Supporting Data Structures

### `CompletionOptions`
```kotlin
data class CompletionOptions(
    val model: String? = null,
    val temperature: Float = 0.7f,
    val maxTokens: Int = 2048,
    val topP: Float = 1.0f,
    val stopSequences: List<String> = emptyList(),
    val systemPrompt: String? = null
)
```

### `AiResponse`
```kotlin
data class AiResponse(
    val text: String,
    val modelUsed: String,
    val promptTokens: Int = 0,
    val completionTokens: Int = 0,
    val totalTokens: Int = 0,
    val finishReason: String? = null,
    val rawResponse: String? = null
)
```

### `ConnectionStatus`
```kotlin
sealed class ConnectionStatus {
    object Connected : ConnectionStatus()
    data class Degraded(val latencyMs: Long, val warning: String) : ConnectionStatus()
    data class Disconnected(val error: AiError) : ConnectionStatus()
}
```

---

## 3. `ModelDiscoveryService`

Used to query local servers (Ollama, LM Studio) or cloud endpoints dynamically:

```kotlin
interface ModelDiscoveryService {
    suspend fun discoverModels(
        providerId: String,
        endpointUrl: String
    ): Result<List<DiscoveredModel>>
}
```

---

## Related Documentation
* [AI Provider Architecture](file:///workspaces/agentdroid-/docs/architecture/AI_PROVIDER_ARCHITECTURE.md)
* [Provider Integration Guide](file:///workspaces/agentdroid-/docs/developer/PROVIDER_INTEGRATION.md)
* [Error Codes Catalog](file:///workspaces/agentdroid-/docs/api/ERROR_CODES.md)
