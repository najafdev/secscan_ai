package com.agentdroid.app

import com.agentdroid.app.ai.connection.AiConnectionManager
import com.agentdroid.app.ai.connection.ConnectionState
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
import com.agentdroid.app.data.local.preferences.SecurePreferencesManager
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.ModelCapability
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.runBlocking
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.*
import org.junit.Test
import java.io.IOException
import java.net.UnknownHostException

class ModelDiscoveryTest {

    private class InMemorySettingsDao : SettingsDao {
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
    // 1. Add, Edit, Remove Provider
    // -------------------------------------------------------------------------
    @Test
    fun testAddEditRemoveProvider() = runBlocking {
        val dao = InMemorySettingsDao()
        val prefs = SecurePreferencesManager(null)
        val manager = AiConnectionManager(dao, prefs)

        // Add
        val provider = ApiProviderEntity("prov_groq", "GROQ", "Groq Cloud", "https://api.groq.com/openai/v1", isEnabled = true)
        dao.insertProvider(provider)
        prefs.saveApiKey("prov_groq", "gsk_test_123")

        assertEquals(1, dao.providers.size)
        assertEquals("Groq Cloud", dao.getProviderById("prov_groq")?.displayName)

        // Edit
        val updated = provider.copy(displayName = "Groq High Speed Cloud")
        dao.insertProvider(updated)
        assertEquals("Groq High Speed Cloud", dao.getProviderById("prov_groq")?.displayName)

        // Remove
        manager.removeProvider("prov_groq")
        assertNull(dao.getProviderById("prov_groq"))
        assertEquals("", prefs.getApiKey("prov_groq"))
    }

    // -------------------------------------------------------------------------
    // 2. Invalid API Key Handling (HTTP 401)
    // -------------------------------------------------------------------------
    @Test
    fun testInvalidApiKeyError() = runBlocking {
        val dao = InMemorySettingsDao()
        val mockClient = createMockClient { req ->
            Response.Builder()
                .request(req)
                .protocol(Protocol.HTTP_1_1)
                .code(401)
                .message("Unauthorized")
                .body("{\"error\": {\"message\": \"Incorrect API key provided\"}}".toResponseBody("application/json".toMediaType()))
                .build()
        }
        val discoveryService = ModelDiscoveryService(dao, mockClient)

        val provider = ApiProviderEntity("prov_openai", "OPENAI", "OpenAI", "https://api.openai.com/v1", isEnabled = true)
        val result = discoveryService.discoverAndSync(provider, "sk-invalid-key")

        assertTrue(result is DiscoveryResult.Failure)
        val failure = result as DiscoveryResult.Failure
        assertEquals(ErrorCategory.API_KEY_INVALID, failure.error.category)
    }

    // -------------------------------------------------------------------------
    // 3. Network Unavailable Handling (UnknownHostException)
    // -------------------------------------------------------------------------
    @Test
    fun testNetworkUnavailable() = runBlocking {
        val dao = InMemorySettingsDao()
        val mockClient = createMockClient { _ ->
            throw UnknownHostException("Unable to resolve host api.openai.com")
        }
        val discoveryService = ModelDiscoveryService(dao, mockClient)

        val provider = ApiProviderEntity("prov_openai", "OPENAI", "OpenAI", "https://api.openai.com/v1", isEnabled = true)
        val result = discoveryService.discoverAndSync(provider, "sk-test-key")

        assertTrue(result is DiscoveryResult.Failure)
        val failure = result as DiscoveryResult.Failure
        assertEquals(ErrorCategory.NETWORK_UNAVAILABLE, failure.error.category)
    }

    // -------------------------------------------------------------------------
    // 4. Provider Unavailable Handling (HTTP 503)
    // -------------------------------------------------------------------------
    @Test
    fun testProviderUnavailable() = runBlocking {
        val dao = InMemorySettingsDao()
        val mockClient = createMockClient { req ->
            Response.Builder()
                .request(req)
                .protocol(Protocol.HTTP_1_1)
                .code(503)
                .message("Service Unavailable")
                .body("Outage".toResponseBody("text/plain".toMediaType()))
                .build()
        }
        val discoveryService = ModelDiscoveryService(dao, mockClient)

        val provider = ApiProviderEntity("prov_openai", "OPENAI", "OpenAI", "https://api.openai.com/v1", isEnabled = true)
        val result = discoveryService.discoverAndSync(provider, "sk-test-key")

        assertTrue(result is DiscoveryResult.Failure)
        val failure = result as DiscoveryResult.Failure
        assertEquals(ErrorCategory.PROVIDER_UNAVAILABLE, failure.error.category)
    }

    // -------------------------------------------------------------------------
    // 5. Dynamic OpenAI Model Discovery
    // -------------------------------------------------------------------------
    @Test
    fun testOpenAiModelDiscovery() = runBlocking {
        val dao = InMemorySettingsDao()
        val jsonPayload = """
            {
              "data": [
                {"id": "gpt-4o", "object": "model"},
                {"id": "gpt-4o-mini", "object": "model"},
                {"id": "whisper-1", "object": "model"},
                {"id": "o1-preview", "object": "model"}
              ]
            }
        """.trimIndent()

        val mockClient = createMockClient { req ->
            Response.Builder()
                .request(req)
                .protocol(Protocol.HTTP_1_1)
                .code(200)
                .message("OK")
                .body(jsonPayload.toResponseBody("application/json".toMediaType()))
                .build()
        }

        val discoveryService = ModelDiscoveryService(dao, mockClient)
        val provider = ApiProviderEntity("prov_openai", "OPENAI", "OpenAI", "https://api.openai.com/v1", isEnabled = true)
        val result = discoveryService.discoverAndSync(provider, "sk-valid-key")

        assertTrue(result is DiscoveryResult.Success)
        val success = result as DiscoveryResult.Success
        // Whisper should be filtered out
        val modelIds = success.models.map { it.modelId }
        assertTrue(modelIds.contains("gpt-4o"))
        assertTrue(modelIds.contains("gpt-4o-mini"))
        assertTrue(modelIds.contains("o1-preview"))
        assertFalse(modelIds.contains("whisper-1"))

        // Check capabilities
        val gpt4o = success.models.first { it.modelId == "gpt-4o" }
        assertTrue(gpt4o.capabilitiesJson.contains("TOOL_CALLING"))
        assertTrue(gpt4o.capabilitiesJson.contains("VISION"))
        assertEquals(128000, gpt4o.contextWindow)

        val o1 = success.models.first { it.modelId == "o1-preview" }
        assertTrue(o1.capabilitiesJson.contains("REASONING"))

        // Check persisted to DAO
        val inDb = dao.getDiscoveredModelsForProviderSync("prov_openai")
        assertEquals(3, inDb.size)
    }

    // -------------------------------------------------------------------------
    // 6. Manual Model ID Entry Persistence
    // -------------------------------------------------------------------------
    @Test
    fun testManualModelIdEntry() = runBlocking {
        val dao = InMemorySettingsDao()
        val manualModel = DiscoveredModelEntity(
            id = "prov_openai:ft:gpt-4o:my-org:custom-v1",
            modelId = "ft:gpt-4o:my-org:custom-v1",
            providerId = "prov_openai",
            displayName = "Custom Fine-Tuned GPT-4o",
            modelType = "CLOUD",
            isManualEntry = true,
            isAvailable = true
        )
        dao.insertDiscoveredModel(manualModel)

        val found = dao.getDiscoveredModelsForProviderSync("prov_openai")
        assertEquals(1, found.size)
        assertTrue(found.first().isManualEntry)
        assertEquals("ft:gpt-4o:my-org:custom-v1", found.first().modelId)
    }

    // -------------------------------------------------------------------------
    // 7. Model Refresh Preserves Cached State On Failure
    // -------------------------------------------------------------------------
    @Test
    fun testModelRefreshPreservesCacheOnFailure() = runBlocking {
        val dao = InMemorySettingsDao()
        val initialModel = DiscoveredModelEntity(
            id = "prov_openai:gpt-4o",
            modelId = "gpt-4o",
            providerId = "prov_openai",
            displayName = "GPT-4o Omnimodal",
            modelType = "CLOUD",
            isCached = false
        )
        dao.insertDiscoveredModel(initialModel)

        // Mock failure on refresh
        val mockClient = createMockClient { _ ->
            throw IOException("Network reset")
        }
        val discoveryService = ModelDiscoveryService(dao, mockClient)
        val provider = ApiProviderEntity("prov_openai", "OPENAI", "OpenAI", "https://api.openai.com/v1", isEnabled = true)

        val result = discoveryService.discoverAndSync(provider, "sk-test")
        assertTrue(result is DiscoveryResult.Failure)

        val failure = result as DiscoveryResult.Failure
        assertEquals(1, failure.cachedModels.size)
        assertTrue("Must be marked as cached", failure.cachedModels.first().isCached)
    }

    // -------------------------------------------------------------------------
    // 8. Per-Agent Model Assignment & Capability Validation
    // -------------------------------------------------------------------------
    @Test
    fun testPerAgentModelAssignmentAndCapabilityValidation() = runBlocking {
        val dao = InMemorySettingsDao()
        val prefs = SecurePreferencesManager(null)
        prefs.saveApiKey("prov_openai", "sk-valid-key")
        val manager = AiConnectionManager(dao, prefs)

        val provider = ApiProviderEntity("prov_openai", "OPENAI", "OpenAI", "https://api.openai.com/v1", isEnabled = true)
        dao.insertProvider(provider)

        // Model 1: Basic text only (lacks TOOL_CALLING)
        val basicModel = DiscoveredModelEntity(
            id = "prov_openai:basic-text",
            modelId = "basic-text",
            providerId = "prov_openai",
            displayName = "Basic Text",
            modelType = "CLOUD",
            capabilitiesJson = "[\"TEXT_GENERATION\"]",
            isAvailable = true
        )
        dao.insertDiscoveredModel(basicModel)

        // Assign basic-text to Phone Control Agent (which requires TOOL_CALLING)
        manager.assignModelToAgent(AgentRole.PHONE_CONTROL.name, "prov_openai", "basic-text")

        // Validation must fail because TOOL_CALLING is missing
        val result = manager.validateAndGetProvider(AgentRole.PHONE_CONTROL)
        assertTrue("Must fail capability check", result.isFailure)
        val err = result.exceptionOrNull() as? AiError
        assertNotNull(err)
        assertEquals(ErrorCategory.CONFIGURATION_INVALID, err?.category)
        assertTrue(err?.userFriendlyMessage?.contains("lacks required capabilities") == true)

        // Now assign a model that supports TOOL_CALLING and REASONING
        val advancedModel = DiscoveredModelEntity(
            id = "prov_openai:gpt-4o",
            modelId = "gpt-4o",
            providerId = "prov_openai",
            displayName = "GPT-4o",
            modelType = "CLOUD",
            capabilitiesJson = "[\"TEXT_GENERATION\",\"STREAMING\",\"TOOL_CALLING\",\"REASONING\"]",
            isAvailable = true
        )
        dao.insertDiscoveredModel(advancedModel)
        manager.assignModelToAgent(AgentRole.PHONE_CONTROL.name, "prov_openai", "gpt-4o")

        // Pre-set status to CONNECTED for test
        dao.insertModelConfig(ModelConfigEntity("cfg_phone", AgentRole.PHONE_CONTROL.name, "prov_openai", "gpt-4o"))
    }
}
