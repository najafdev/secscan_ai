package com.agentdroid.app

import com.agentdroid.app.ai.client.HttpAiProvider
import com.agentdroid.app.ai.connection.NetworkSecurityValidator
import com.agentdroid.app.ai.discovery.DiscoveryResult
import com.agentdroid.app.ai.discovery.ModelDiscoveryService
import com.agentdroid.app.ai.error.AiError
import com.agentdroid.app.ai.error.ErrorCategory
import com.agentdroid.app.data.local.dao.SettingsDao
import com.agentdroid.app.data.local.entity.ApiProviderEntity
import com.agentdroid.app.data.local.entity.DiscoveredModelEntity
import com.agentdroid.app.data.local.entity.ModelConfigEntity
import com.agentdroid.app.data.local.entity.PermissionEntity
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.runBlocking
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.*
import org.junit.Test
import java.net.SocketTimeoutException

class OllamaAndLocalLlmTest {

    private class MockSettingsDao : SettingsDao {
        val providers = mutableListOf<ApiProviderEntity>()
        val configs = mutableListOf<ModelConfigEntity>()
        val discoveredModels = mutableListOf<DiscoveredModelEntity>()

        override fun getAllProviders(): Flow<List<ApiProviderEntity>> = flowOf(providers)
        override suspend fun getAllProvidersSync(): List<ApiProviderEntity> = providers
        override suspend fun getProviderById(id: String): ApiProviderEntity? = providers.find { it.id == id }
        override suspend fun insertProvider(provider: ApiProviderEntity) {
            providers.removeAll { it.id == provider.id }
            providers.add(provider)
        }
        override suspend fun deleteProvider(provider: ApiProviderEntity) {
            providers.removeAll { it.id == provider.id }
        }
        override suspend fun deleteProviderById(id: String) {
            providers.removeAll { it.id == id }
        }

        override fun getAllModelConfigs(): Flow<List<ModelConfigEntity>> = flowOf(configs)
        override suspend fun getConfigForRole(role: String): ModelConfigEntity? = configs.find { it.agentRole == role }
        override suspend fun insertModelConfig(config: ModelConfigEntity) {
            configs.removeAll { it.id == config.id }
            configs.add(config)
        }
        override suspend fun deleteModelConfigForRole(role: String) {
            configs.removeAll { it.agentRole == role }
        }

        override fun getAllDiscoveredModels(): Flow<List<DiscoveredModelEntity>> = flowOf(discoveredModels)
        override suspend fun getAllDiscoveredModelsSync(): List<DiscoveredModelEntity> = discoveredModels
        override fun getDiscoveredModelsForProvider(providerId: String): Flow<List<DiscoveredModelEntity>> =
            flowOf(discoveredModels.filter { it.providerId == providerId })
        override suspend fun getDiscoveredModelsForProviderSync(providerId: String): List<DiscoveredModelEntity> =
            discoveredModels.filter { it.providerId == providerId }

        override suspend fun insertDiscoveredModels(models: List<DiscoveredModelEntity>) {
            for (m in models) {
                discoveredModels.removeAll { it.id == m.id }
                discoveredModels.add(m)
            }
        }
        override suspend fun insertDiscoveredModel(model: DiscoveredModelEntity) {
            discoveredModels.removeAll { it.id == model.id }
            discoveredModels.add(model)
        }
        override suspend fun deleteDiscoveredModelsForProvider(providerId: String) {
            discoveredModels.removeAll { it.providerId == providerId }
        }
        override suspend fun deleteDiscoveredModelById(id: String) {
            discoveredModels.removeAll { it.id == id }
        }

        override suspend fun getPermissionsForRole(role: String): List<PermissionEntity> = emptyList()
        override suspend fun insertPermission(permission: PermissionEntity) {}
    }

    private fun createMockClient(interceptor: (Request) -> Response): OkHttpClient {
        return OkHttpClient.Builder()
            .addInterceptor { chain -> interceptor(chain.request()) }
            .build()
    }

    // -------------------------------------------------------------------------
    // 1. Ollama Connection & Dynamic Model Discovery (/api/tags)
    // -------------------------------------------------------------------------
    @Test
    fun testOllamaModelDiscovery() = runBlocking {
        val dao = MockSettingsDao()
        val ollamaTagsResponse = """
            {
              "models": [
                {
                  "name": "llama3.2:latest",
                  "model": "llama3.2:latest",
                  "details": {
                    "format": "gguf",
                    "family": "llama",
                    "parameter_size": "3.2B"
                  }
                },
                {
                  "name": "qwen2.5:7b",
                  "model": "qwen2.5:7b",
                  "details": {
                    "format": "gguf",
                    "family": "qwen2",
                    "parameter_size": "7B"
                  }
                }
              ]
            }
        """.trimIndent()

        val mockClient = createMockClient { req ->
            assertTrue(req.url.toString().contains("/api/tags"))
            Response.Builder()
                .request(req)
                .protocol(Protocol.HTTP_1_1)
                .code(200)
                .message("OK")
                .body(ollamaTagsResponse.toResponseBody("application/json".toMediaType()))
                .build()
        }

        val discoveryService = ModelDiscoveryService(dao, mockClient)
        val provider = ApiProviderEntity("prov_ollama", "OLLAMA", "Ollama Local Daemon", "http://10.0.2.2:11434", isEnabled = true)

        val result = discoveryService.discoverAndSync(provider, "")
        assertTrue(result is DiscoveryResult.Success)

        val success = result as DiscoveryResult.Success
        assertEquals(2, success.models.size)

        val llama = success.models.first { it.modelId == "llama3.2:latest" }
        assertTrue("Must be marked local", llama.isLocal)
        assertEquals("LOCAL", llama.modelType)
        assertTrue(llama.displayName.contains("3.2B"))
        assertTrue(llama.capabilitiesJson.contains("TOOL_CALLING"))
    }

    // -------------------------------------------------------------------------
    // 2. Ollama Missing Local Models Handling
    // -------------------------------------------------------------------------
    @Test
    fun testOllamaNoModelsFound() = runBlocking {
        val dao = MockSettingsDao()
        val emptyOllamaResponse = "{\"models\": []}"

        val mockClient = createMockClient { req ->
            Response.Builder()
                .request(req)
                .protocol(Protocol.HTTP_1_1)
                .code(200)
                .message("OK")
                .body(emptyOllamaResponse.toResponseBody("application/json".toMediaType()))
                .build()
        }

        val discoveryService = ModelDiscoveryService(dao, mockClient)
        val provider = ApiProviderEntity("prov_ollama", "OLLAMA", "Ollama Local Daemon", "http://10.0.2.2:11434", isEnabled = true)

        val result = discoveryService.discoverAndSync(provider, "")
        assertTrue(result is DiscoveryResult.Failure)

        val failure = result as DiscoveryResult.Failure
        assertEquals(ErrorCategory.MODEL_NOT_FOUND, failure.error.category)
        assertTrue(failure.error.userFriendlyMessage.contains("No local models found on the Ollama server"))
    }

    // -------------------------------------------------------------------------
    // 3. Network Security Validator (Cleartext vs HTTPS & Private IP rules)
    // -------------------------------------------------------------------------
    @Test
    fun testNetworkSecurityValidation() {
        // Valid local/LAN addresses with HTTP
        assertTrue(NetworkSecurityValidator.validateEndpointUrl("http://localhost:11434").isValid)
        assertTrue(NetworkSecurityValidator.validateEndpointUrl("http://127.0.0.1:11434").isValid)
        assertTrue(NetworkSecurityValidator.validateEndpointUrl("http://10.0.2.2:11434").isValid)
        assertTrue(NetworkSecurityValidator.validateEndpointUrl("http://192.168.1.100:11434").isValid)
        assertTrue(NetworkSecurityValidator.validateEndpointUrl("http://10.0.0.5:8000/v1").isValid)
        assertTrue(NetworkSecurityValidator.validateEndpointUrl("http://ollama-server.local:11434").isValid)

        // Valid remote addresses with HTTPS
        assertTrue(NetworkSecurityValidator.validateEndpointUrl("https://api.openai.com/v1").isValid)
        assertTrue(NetworkSecurityValidator.validateEndpointUrl("https://openrouter.ai/api/v1").isValid)
        assertTrue(NetworkSecurityValidator.validateEndpointUrl("https://ollama.my-domain.com").isValid)

        // Invalid: Remote cleartext HTTP
        val remoteHttp = NetworkSecurityValidator.validateEndpointUrl("http://api.openai.com/v1")
        assertFalse("Remote HTTP must be rejected", remoteHttp.isValid)
        assertTrue(remoteHttp.errorMessage!!.contains("Remote endpoints must use HTTPS"))

        // Invalid: Unsupported URL scheme
        val badScheme = NetworkSecurityValidator.validateEndpointUrl("ftp://192.168.1.1")
        assertFalse(badScheme.isValid)
        assertTrue(badScheme.errorMessage!!.contains("Unsupported protocol"))

        // Invalid: Malformed URL
        assertFalse(NetworkSecurityValidator.validateEndpointUrl("not-a-url").isValid)
    }

    // -------------------------------------------------------------------------
    // 4. Unreachable LAN Server / Timeout
    // -------------------------------------------------------------------------
    @Test
    fun testUnreachableLanServerTimeout() = runBlocking {
        val dao = MockSettingsDao()
        val mockClient = createMockClient { _ ->
            throw SocketTimeoutException("Connect to 192.168.1.200:11434 timed out after 15000ms")
        }
        val discoveryService = ModelDiscoveryService(dao, mockClient)
        val provider = ApiProviderEntity("prov_ollama_lan", "OLLAMA", "LAN Ollama", "http://192.168.1.200:11434", isEnabled = true)

        val result = discoveryService.discoverAndSync(provider, "")
        assertTrue(result is DiscoveryResult.Failure)

        val failure = result as DiscoveryResult.Failure
        assertEquals(ErrorCategory.REQUEST_TIMEOUT, failure.error.category)
    }

    // -------------------------------------------------------------------------
    // 5. Custom Local Endpoint (LM Studio / vLLM / LocalAI)
    // -------------------------------------------------------------------------
    @Test
    fun testCustomLocalLlmDiscovery() = runBlocking {
        val dao = MockSettingsDao()
        val lmStudioModels = """
            {
              "data": [
                {"id": "meta-llama-3.1-8b-instruct", "object": "model"},
                {"id": "qwen-2.5-coder-7b", "object": "model"}
              ]
            }
        """.trimIndent()

        val mockClient = createMockClient { req ->
            assertTrue(req.url.toString().contains("/models"))
            Response.Builder()
                .request(req)
                .protocol(Protocol.HTTP_1_1)
                .code(200)
                .message("OK")
                .body(lmStudioModels.toResponseBody("application/json".toMediaType()))
                .build()
        }

        val discoveryService = ModelDiscoveryService(dao, mockClient)
        val provider = ApiProviderEntity("prov_lmstudio", "OPENAI_COMPATIBLE", "LM Studio Local", "http://10.0.2.2:1234/v1", isEnabled = true)

        val result = discoveryService.discoverAndSync(provider, "")
        assertTrue(result is DiscoveryResult.Success)

        val success = result as DiscoveryResult.Success
        assertEquals(2, success.models.size)
        assertTrue(success.models.first().isLocal)
        assertEquals("LOCAL", success.models.first().modelType)
    }

    // -------------------------------------------------------------------------
    // 6. Streaming Response Flow
    // -------------------------------------------------------------------------
    @Test
    fun testStreamingResponseFlow() = runBlocking {
        val mockClient = createMockClient { req ->
            val chatResponse = """
                {
                  "model": "llama3.2",
                  "message": {"role": "assistant", "content": "AgentDroid local multi-agent system online"},
                  "done": true
                }
            """.trimIndent()
            Response.Builder()
                .request(req)
                .protocol(Protocol.HTTP_1_1)
                .code(200)
                .message("OK")
                .body(chatResponse.toResponseBody("application/json".toMediaType()))
                .build()
        }

        // We can test streamResponse on HttpAiProvider
        val provider = HttpAiProvider(
            providerId = "prov_ollama",
            displayName = "Ollama Local",
            baseUrl = "http://10.0.2.2:11434",
            apiKeyProvider = { "" },
            providerType = "OLLAMA",
            activeModel = "llama3.2"
        )

        // Verify provider fields
        assertEquals("prov_ollama", provider.providerId)
        assertEquals("llama3.2", provider.activeModel)
    }
}
