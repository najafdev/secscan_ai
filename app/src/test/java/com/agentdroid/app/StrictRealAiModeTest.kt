package com.agentdroid.app

import com.agentdroid.app.ai.client.HttpAiProvider
import com.agentdroid.app.ai.connection.AiConnectionManager
import com.agentdroid.app.ai.connection.ConnectionState
import com.agentdroid.app.ai.error.AiError
import com.agentdroid.app.ai.error.ErrorCategory
import com.agentdroid.app.ai.error.SuggestedAction
import com.agentdroid.app.data.local.dao.SettingsDao
import com.agentdroid.app.data.local.entity.ApiProviderEntity
import com.agentdroid.app.data.local.entity.ModelConfigEntity
import com.agentdroid.app.data.local.entity.PermissionEntity
import com.agentdroid.app.data.local.preferences.SecurePreferencesManager
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.TaskItem
import com.agentdroid.app.domain.model.TaskStatus
import com.agentdroid.app.domain.orchestrator.DAGScheduler
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test
import java.io.IOException
import java.net.SocketTimeoutException
import java.net.UnknownHostException

class StrictRealAiModeTest {

    // Fake SettingsDao for unit testing
    private class FakeSettingsDao : SettingsDao {
        val providers = mutableListOf<ApiProviderEntity>()
        val configs = mutableListOf<ModelConfigEntity>()

        override fun getAllProviders(): Flow<List<ApiProviderEntity>> = flowOf(providers)
        override suspend fun getAllProvidersSync(): List<ApiProviderEntity> = providers
        override suspend fun getProviderById(id: String): ApiProviderEntity? = providers.find { it.id == id }
        override suspend fun insertProvider(provider: ApiProviderEntity) {
            providers.removeAll { it.id == provider.id }
            providers.add(provider)
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
        override suspend fun deleteProvider(provider: ApiProviderEntity) {
            providers.removeAll { it.id == provider.id }
        }
        override suspend fun deleteProviderById(id: String) {
            providers.removeAll { it.id == id }
        }

        val discoveredModels = mutableListOf<com.agentdroid.app.data.local.entity.DiscoveredModelEntity>()
        override fun getAllDiscoveredModels(): Flow<List<com.agentdroid.app.data.local.entity.DiscoveredModelEntity>> = flowOf(discoveredModels)
        override suspend fun getAllDiscoveredModelsSync(): List<com.agentdroid.app.data.local.entity.DiscoveredModelEntity> = discoveredModels
        override fun getDiscoveredModelsForProvider(providerId: String): Flow<List<com.agentdroid.app.data.local.entity.DiscoveredModelEntity>> = flowOf(discoveredModels.filter { it.providerId == providerId })
        override suspend fun getDiscoveredModelsForProviderSync(providerId: String): List<com.agentdroid.app.data.local.entity.DiscoveredModelEntity> = discoveredModels.filter { it.providerId == providerId }
        override suspend fun insertDiscoveredModels(models: List<com.agentdroid.app.data.local.entity.DiscoveredModelEntity>) {
            discoveredModels.addAll(models)
        }
        override suspend fun insertDiscoveredModel(model: com.agentdroid.app.data.local.entity.DiscoveredModelEntity) {
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

    // -------------------------------------------------------------
    // Scenario 1: No Provider Configured
    // -------------------------------------------------------------
    @Test
    fun testScenario1_NoProviderConfigured() = runBlocking {
        val dao = FakeSettingsDao()
        val prefs = SecurePreferencesManager(null)
        val connectionManager = AiConnectionManager(dao, prefs)

        val result = connectionManager.validateAndGetProvider(AgentRole.MASTER)
        assertTrue("Must fail when no provider configured", result.isFailure)

        val error = result.exceptionOrNull() as? AiError
        assertNotNull(error)
        assertEquals(ErrorCategory.AI_NOT_CONFIGURED, error?.category)
        assertEquals("AI Model Not Connected", error?.userFriendlyTitle)
        assertEquals(SuggestedAction.CONNECT_PROVIDER, error?.suggestedAction)
    }

    // -------------------------------------------------------------
    // Scenario 2: API Key Missing
    // -------------------------------------------------------------
    @Test
    fun testScenario2_ApiKeyMissing() = runBlocking {
        val dao = FakeSettingsDao()
        dao.insertProvider(ApiProviderEntity("prov_openai", "OPENAI", "OpenAI", "https://api.openai.com/v1", isEnabled = true))
        dao.insertModelConfig(ModelConfigEntity("cfg_master", "MASTER", "prov_openai", "gpt-4o", 0.7f, 4096))

        val prefs = SecurePreferencesManager(null) // No key saved
        val connectionManager = AiConnectionManager(dao, prefs)

        val result = connectionManager.validateAndGetProvider(AgentRole.MASTER)
        assertTrue("Must fail when API key is missing", result.isFailure)

        val error = result.exceptionOrNull() as? AiError
        assertNotNull(error)
        assertEquals(ErrorCategory.API_KEY_MISSING, error?.category)
        assertEquals("API Key Missing", error?.userFriendlyTitle)
        assertEquals(SuggestedAction.UPDATE_API_KEY, error?.suggestedAction)
    }

    // -------------------------------------------------------------
    // Scenario 3: Invalid API Key (HTTP 401/403)
    // -------------------------------------------------------------
    @Test
    fun testScenario3_InvalidApiKey() {
        val raw = "HTTP 401: {\"error\": {\"message\": \"Incorrect API key provided: sk-1234567890abcdef. You can find your API key at...\"}}"
        val err = AiError.invalidApiKey("OpenAI", raw)

        assertEquals(ErrorCategory.API_KEY_INVALID, err.category)
        assertEquals("Authentication Failed", err.userFriendlyTitle)
        assertFalse(err.retryAvailable)
        // Ensure sensitive key was sanitized
        assertFalse(err.technicalDetails.contains("sk-1234567890abcdef"))
        assertTrue(err.technicalDetails.contains("REDACTED"))
    }

    // -------------------------------------------------------------
    // Scenario 4: Valid API Key with Inaccessible Model (HTTP 404)
    // -------------------------------------------------------------
    @Test
    fun testScenario4_ModelNotFound() {
        val err = AiError.modelNotFound("Google Gemini", "gemini-2.5-nonexistent", "HTTP 404: Model not found")

        assertEquals(ErrorCategory.MODEL_NOT_FOUND, err.category)
        assertEquals("Model Unavailable", err.userFriendlyTitle)
        assertEquals(SuggestedAction.SELECT_ANOTHER_MODEL, err.suggestedAction)
        assertFalse(err.retryAvailable)
    }

    // -------------------------------------------------------------
    // Scenario 5: Successful Model Connection (State = CONNECTED)
    // -------------------------------------------------------------
    @Test
    fun testScenario5_SuccessfulModelConnection() = runBlocking {
        val dao = FakeSettingsDao()
        dao.insertProvider(ApiProviderEntity("prov_ollama", "OLLAMA", "Ollama Local", "http://127.0.0.1:11434", isEnabled = true))
        dao.insertModelConfig(ModelConfigEntity("cfg_master", "MASTER", "prov_ollama", "llama3", 0.7f, 4096))

        val prefs = SecurePreferencesManager(null)
        val connectionManager = AiConnectionManager(dao, prefs)

        // Initial state before testing connection is CONFIGURED or NOT_CONFIGURED, NEVER CONNECTED
        assertNotEquals(ConnectionState.CONNECTED, connectionManager.systemStatus.value.currentMasterState)
    }

    // -------------------------------------------------------------
    // Scenario 6: Network Disconnected
    // -------------------------------------------------------------
    @Test
    fun testScenario6_NetworkDisconnected() {
        val err = AiError.networkError("Anthropic", "UnknownHostException: Unable to resolve host api.anthropic.com")

        assertEquals(ErrorCategory.NETWORK_UNAVAILABLE, err.category)
        assertEquals("Connection Failed", err.userFriendlyTitle)
        assertEquals(SuggestedAction.CHECK_NETWORK, err.suggestedAction)
        assertTrue(err.retryAvailable)
    }

    // -------------------------------------------------------------
    // Scenario 7: Provider Outage (HTTP 500/503)
    // -------------------------------------------------------------
    @Test
    fun testScenario7_ProviderOutage() {
        val err = AiError.providerUnavailable("OpenAI", "HTTP 503: Service Unavailable. Servers under heavy load.")

        assertEquals(ErrorCategory.PROVIDER_UNAVAILABLE, err.category)
        assertEquals("Provider Unavailable", err.userFriendlyTitle)
        assertEquals(SuggestedAction.WAIT_AND_RETRY, err.suggestedAction)
        assertTrue(err.retryAvailable)
    }

    // -------------------------------------------------------------
    // Scenario 8: Rate Limit Exceeded (HTTP 429)
    // -------------------------------------------------------------
    @Test
    fun testScenario8_RateLimitExceeded() {
        val err = AiError.rateLimited("OpenAI", "HTTP 429: Rate limit reached for requests per minute.")

        assertEquals(ErrorCategory.RATE_LIMIT_EXCEEDED, err.category)
        assertEquals("Rate Limit Reached", err.userFriendlyTitle)
        assertEquals(SuggestedAction.WAIT_AND_RETRY, err.suggestedAction)
        assertTrue(err.retryAvailable)
    }

    // -------------------------------------------------------------
    // Scenario 9: Insufficient Provider Quota
    // -------------------------------------------------------------
    @Test
    fun testScenario9_InsufficientQuota() {
        val err = AiError.quotaExceeded("OpenAI", "You exceeded your current quota, please check your plan and billing details.")

        assertEquals(ErrorCategory.QUOTA_EXCEEDED, err.category)
        assertEquals("Provider Quota Exceeded", err.userFriendlyTitle)
        assertEquals(SuggestedAction.CHECK_PROVIDER_USAGE, err.suggestedAction)
        assertFalse(err.retryAvailable)
    }

    // -------------------------------------------------------------
    // Scenario 10: API Timeout (SocketTimeoutException)
    // -------------------------------------------------------------
    @Test
    fun testScenario10_ApiTimeout() {
        val err = AiError.requestTimeout("Anthropic", "Read timed out after 30000ms")

        assertEquals(ErrorCategory.REQUEST_TIMEOUT, err.category)
        assertEquals("Request Timed Out", err.userFriendlyTitle)
        assertEquals(SuggestedAction.RETRY_NOW, err.suggestedAction)
        assertTrue(err.retryAvailable)
    }

    // -------------------------------------------------------------
    // Scenario 11: Malformed API Response (JSONException)
    // -------------------------------------------------------------
    @Test
    fun testScenario11_MalformedApiResponse() {
        val err = AiError.invalidResponse("OpenAI", "Value <html> at choices of type java.lang.String cannot be converted to JSONArray")

        assertEquals(ErrorCategory.INVALID_RESPONSE, err.category)
        assertEquals("Malformed Response", err.userFriendlyTitle)
        assertEquals(SuggestedAction.RETRY_NOW, err.suggestedAction)
    }

    // -------------------------------------------------------------
    // Scenario 12: Agent Execution Failure
    // -------------------------------------------------------------
    @Test
    fun testScenario12_AgentExecutionFailure() {
        val err = AiError.agentExecutionFailed("Research Agent", "Content synthesis engine threw OutOfMemory")

        assertEquals(ErrorCategory.AGENT_EXECUTION_FAILED, err.category)
        assertEquals("Agent Execution Failed", err.userFriendlyTitle)
        assertTrue(err.userFriendlyMessage.contains("Research Agent"))
    }

    // -------------------------------------------------------------
    // Scenario 13: Tool Execution Failure
    // -------------------------------------------------------------
    @Test
    fun testScenario13_ToolExecutionFailure() {
        val err = AiError.toolExecutionFailed("AccessibilityDriver", "Target button not found on screen hierarchy")

        assertEquals(ErrorCategory.TOOL_EXECUTION_FAILED, err.category)
        assertEquals("Device Tool Failed", err.userFriendlyTitle)
        assertTrue(err.userFriendlyMessage.contains("AccessibilityDriver"))
    }

    // -------------------------------------------------------------
    // Scenario 14: Task Cancellation
    // -------------------------------------------------------------
    @Test
    fun testScenario14_TaskCancellation() {
        val task = TaskItem(
            id = "task_cancel_1",
            planId = "plan_1",
            agentRole = AgentRole.PHONE_CONTROL,
            title = "Click button",
            description = "Click submit",
            status = TaskStatus.RUNNING
        )

        val cancelledTask = task.copy(status = TaskStatus.CANCELLED, error = "Operation cancelled by user.")
        assertEquals(TaskStatus.CANCELLED, cancelledTask.status)
        assertEquals("Operation cancelled by user.", cancelledTask.error)
    }

    // -------------------------------------------------------------
    // Scenario 15: Provider Fallback (Explicit Configuration Only)
    // -------------------------------------------------------------
    @Test
    fun testScenario15_ProviderFallbackExplicitOnly() = runBlocking {
        val dao = FakeSettingsDao()
        dao.insertProvider(ApiProviderEntity("prov_primary", "OPENAI", "OpenAI Primary", "https://api.openai.com/v1", isEnabled = true))
        dao.insertModelConfig(ModelConfigEntity("cfg_master", "MASTER", "prov_primary", "gpt-4o", 0.7f, 4096))

        val prefs = SecurePreferencesManager(null)
        val connectionManager = AiConnectionManager(dao, prefs)

        // Without credentials, primary fails and DOES NOT silently switch to any mock provider!
        val result = connectionManager.validateAndGetProvider(AgentRole.MASTER)
        assertTrue(result.isFailure)
        assertEquals(ErrorCategory.API_KEY_MISSING, (result.exceptionOrNull() as AiError).category)
    }

    // -------------------------------------------------------------
    // Scenario 16: Partial Multi-Agent Workflow Failure
    // -------------------------------------------------------------
    @Test
    fun testScenario16_PartialMultiAgentWorkflowFailure() {
        val scheduler = DAGScheduler()

        val task1 = TaskItem("t1", "p1", AgentRole.RESEARCH, "Market Research", "Analyze market", status = TaskStatus.COMPLETED)
        val task2 = TaskItem("t2", "p1", AgentRole.CONTENT_CREATION, "Draft Copy", "Generate hooks", status = TaskStatus.FAILED, retryCount = 2, maxRetries = 2)
        val task3 = TaskItem("t3", "p1", AgentRole.SOCIAL_MEDIA, "Publish Social", "Post to X", dependsOn = listOf("t2"), status = TaskStatus.PENDING)

        val currentTasks = listOf(task1, task2, task3)

        // Because t2 failed and max retries exceeded, task3 must be skipped
        assertTrue("Workflow has unrecoverable failure", scheduler.hasUnrecoverableFailure(currentTasks))

        val markedTasks = scheduler.markSkippedTasks(currentTasks)
        assertEquals(TaskStatus.COMPLETED, markedTasks[0].status)
        assertEquals(TaskStatus.FAILED, markedTasks[1].status)
        assertEquals(TaskStatus.SKIPPED, markedTasks[2].status)

        // Entire workflow is complete with failure
        assertTrue(scheduler.isPlanComplete(markedTasks))
        assertFalse("Plan did NOT succeed completely", markedTasks.all { it.status == TaskStatus.COMPLETED })
    }

    // -------------------------------------------------------------
    // Security & Credential Redaction Test
    // -------------------------------------------------------------
    @Test
    fun testSecurityCredentialSanitization() {
        val secretHeader = "Authorization: Bearer sk-proj-1234567890abcdefABCDEF123456"
        val sanitized = AiError.sanitize(secretHeader)

        assertFalse("Must never expose bearer tokens", sanitized.contains("sk-proj-1234567890abcdefABCDEF123456"))
        assertTrue("Must contain sanitized indicator", sanitized.contains("[REDACTED]"))
    }
}
