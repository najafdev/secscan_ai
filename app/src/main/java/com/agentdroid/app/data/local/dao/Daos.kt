package com.agentdroid.app.data.local.dao

import androidx.room.*
import com.agentdroid.app.data.local.entity.*
import kotlinx.coroutines.flow.Flow

@Dao
interface AgentDao {
    @Query("SELECT * FROM agents ORDER BY isCustom ASC, name ASC")
    fun getAllAgents(): Flow<List<AgentEntity>>

    @Query("SELECT * FROM agents WHERE id = :id")
    suspend fun getAgentById(id: String): AgentEntity?

    @Query("SELECT * FROM agents WHERE role = :role LIMIT 1")
    suspend fun getAgentByRole(role: String): AgentEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAgent(agent: AgentEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAgents(agents: List<AgentEntity>)

    @Update
    suspend fun updateAgent(agent: AgentEntity)

    @Delete
    suspend fun deleteAgent(agent: AgentEntity)

    @Query("DELETE FROM agents WHERE id = :id")
    suspend fun deleteAgentById(id: String)

    @Query("UPDATE agents SET isEnabled = :isEnabled WHERE id = :id")
    suspend fun setAgentEnabled(id: String, isEnabled: Boolean)

    @Query("SELECT * FROM agent_configurations WHERE agentId = :agentId")
    suspend fun getConfigForAgent(agentId: String): AgentConfigEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertConfig(config: AgentConfigEntity)

    @Query("SELECT COUNT(*) FROM agents")
    suspend fun getAgentCount(): Int
}

@Dao
interface TaskDao {
    @Query("SELECT * FROM tasks WHERE planId = :planId ORDER BY createdAt ASC")
    fun getTasksForPlan(planId: String): Flow<List<TaskEntity>>

    @Query("SELECT * FROM tasks WHERE id = :id")
    suspend fun getTaskById(id: String): TaskEntity?

    @Query("SELECT * FROM tasks WHERE status = 'RUNNING'")
    fun getRunningTasks(): Flow<List<TaskEntity>>

    @Query("SELECT * FROM tasks WHERE status = 'COMPLETED' ORDER BY completedAt DESC LIMIT 20")
    fun getRecentCompletedTasks(): Flow<List<TaskEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertTask(task: TaskEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertTasks(tasks: List<TaskEntity>)

    @Update
    suspend fun updateTask(task: TaskEntity)

    @Query("UPDATE tasks SET status = :status, completedAt = :completedAt, error = :error WHERE id = :id")
    suspend fun updateTaskStatus(id: String, status: String, completedAt: Long? = null, error: String? = null)

    @Query("SELECT * FROM task_dependencies WHERE taskId = :taskId")
    suspend fun getDependenciesForTask(taskId: String): List<TaskDependencyEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertDependencies(deps: List<TaskDependencyEntity>)
}

@Dao
interface ConversationDao {
    @Query("SELECT * FROM conversations ORDER BY updatedAt DESC")
    fun getAllConversations(): Flow<List<ConversationEntity>>

    @Query("SELECT * FROM conversations WHERE id = :id")
    suspend fun getConversationById(id: String): ConversationEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertConversation(conversation: ConversationEntity)

    @Query("SELECT * FROM messages WHERE conversationId = :conversationId ORDER BY timestamp ASC")
    fun getMessagesForConversation(conversationId: String): Flow<List<MessageEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMessage(message: MessageEntity)

    @Query("UPDATE messages SET content = :content, isStreaming = :isStreaming WHERE id = :messageId")
    suspend fun updateMessageContent(messageId: String, content: String, isStreaming: Boolean)

    @Query("DELETE FROM messages WHERE conversationId = :conversationId")
    suspend fun clearMessages(conversationId: String)

    @Query("SELECT COUNT(*) FROM conversations")
    suspend fun getConversationCount(): Int
}

@Dao
interface MemoryDao {
    @Query("SELECT * FROM memory_records ORDER BY timestamp DESC")
    fun getAllMemoryRecords(): Flow<List<MemoryRecordEntity>>

    @Query("SELECT * FROM memory_records WHERE tier = :tier ORDER BY timestamp DESC")
    fun getMemoryByTier(tier: String): Flow<List<MemoryRecordEntity>>

    @Query("SELECT * FROM memory_records WHERE `key` = :key LIMIT 1")
    suspend fun getMemoryByKey(key: String): MemoryRecordEntity?

    @Query("SELECT * FROM memory_records WHERE agentRole = :role OR agentRole IS NULL")
    suspend fun getMemoryForAgent(role: String): List<MemoryRecordEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMemory(record: MemoryRecordEntity)

    @Query("UPDATE memory_records SET accessCount = accessCount + 1 WHERE id = :id")
    suspend fun incrementAccess(id: String)

    @Query("DELETE FROM memory_records WHERE id = :id")
    suspend fun deleteMemory(id: String)

    @Query("DELETE FROM memory_records WHERE tier = :tier")
    suspend fun clearTier(tier: String)

    @Query("DELETE FROM memory_records")
    suspend fun clearAllMemory()
}

@Dao
interface WorkflowDao {
    @Query("SELECT * FROM workflows ORDER BY createdAt DESC")
    fun getAllWorkflows(): Flow<List<WorkflowEntity>>

    @Query("SELECT * FROM workflows WHERE isEnabled = 1")
    suspend fun getActiveWorkflows(): List<WorkflowEntity>

    @Query("SELECT * FROM workflows WHERE id = :id")
    suspend fun getWorkflowById(id: String): WorkflowEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertWorkflow(workflow: WorkflowEntity)

    @Update
    suspend fun updateWorkflow(workflow: WorkflowEntity)

    @Delete
    suspend fun deleteWorkflow(workflow: WorkflowEntity)

    @Query("UPDATE workflows SET isEnabled = :isEnabled WHERE id = :id")
    suspend fun setWorkflowEnabled(id: String, isEnabled: Boolean)

    @Query("UPDATE workflows SET lastRun = :lastRun, executionCount = executionCount + 1 WHERE id = :id")
    suspend fun recordExecution(id: String, lastRun: Long)
}

@Dao
interface ApprovalDao {
    @Query("SELECT * FROM approval_requests WHERE status = 'PENDING' ORDER BY timestamp DESC")
    fun getPendingApprovals(): Flow<List<ApprovalRequestEntity>>

    @Query("SELECT * FROM approval_requests ORDER BY timestamp DESC LIMIT 50")
    fun getAllApprovals(): Flow<List<ApprovalRequestEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertApproval(request: ApprovalRequestEntity)

    @Query("UPDATE approval_requests SET status = :status WHERE id = :id")
    suspend fun updateApprovalStatus(id: String, status: String)
}

@Dao
interface ActivityLogDao {
    @Query("SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 100")
    fun getRecentLogs(): Flow<List<ActivityLogEntity>>

    @Query("SELECT * FROM activity_logs WHERE agentRole = :role ORDER BY timestamp DESC LIMIT 50")
    fun getLogsForAgent(role: String): Flow<List<ActivityLogEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertLog(log: ActivityLogEntity)

    @Query("DELETE FROM activity_logs")
    suspend fun clearLogs()
}

@Dao
interface AccountDao {
    @Query("SELECT * FROM connected_accounts")
    fun getAllAccounts(): Flow<List<ConnectedAccountEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAccount(account: ConnectedAccountEntity)

    @Delete
    suspend fun deleteAccount(account: ConnectedAccountEntity)

    @Query("SELECT * FROM connected_accounts WHERE platform = :platform LIMIT 1")
    suspend fun getAccountByPlatform(platform: String): ConnectedAccountEntity?

    @Query("DELETE FROM connected_accounts WHERE id = :id")
    suspend fun deleteAccountById(id: String)

    @Query("DELETE FROM connected_accounts WHERE platform = :platform")
    suspend fun deleteByPlatform(platform: String)

    @Query("SELECT COUNT(*) FROM connected_accounts")
    suspend fun getAccountCount(): Int

    @Query("SELECT * FROM connected_accounts")
    suspend fun getAllAccountsSync(): List<ConnectedAccountEntity>
}

@Dao
interface SettingsDao {
    @Query("SELECT * FROM api_providers")
    fun getAllProviders(): Flow<List<ApiProviderEntity>>

    @Query("SELECT * FROM api_providers")
    suspend fun getAllProvidersSync(): List<ApiProviderEntity>

    @Query("SELECT * FROM api_providers WHERE id = :id")
    suspend fun getProviderById(id: String): ApiProviderEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertProvider(provider: ApiProviderEntity)

    @Delete
    suspend fun deleteProvider(provider: ApiProviderEntity)

    @Query("DELETE FROM api_providers WHERE id = :id")
    suspend fun deleteProviderById(id: String)

    @Query("SELECT * FROM model_configurations")
    fun getAllModelConfigs(): Flow<List<ModelConfigEntity>>

    @Query("SELECT * FROM model_configurations WHERE agentRole = :role LIMIT 1")
    suspend fun getConfigForRole(role: String): ModelConfigEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertModelConfig(config: ModelConfigEntity)

    @Query("DELETE FROM model_configurations WHERE agentRole = :role")
    suspend fun deleteModelConfigForRole(role: String)

    // Discovered Model Catalog Methods
    @Query("SELECT * FROM discovered_models ORDER BY displayName ASC")
    fun getAllDiscoveredModels(): Flow<List<DiscoveredModelEntity>>

    @Query("SELECT * FROM discovered_models")
    suspend fun getAllDiscoveredModelsSync(): List<DiscoveredModelEntity>

    @Query("SELECT * FROM discovered_models WHERE providerId = :providerId ORDER BY displayName ASC")
    fun getDiscoveredModelsForProvider(providerId: String): Flow<List<DiscoveredModelEntity>>

    @Query("SELECT * FROM discovered_models WHERE providerId = :providerId")
    suspend fun getDiscoveredModelsForProviderSync(providerId: String): List<DiscoveredModelEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertDiscoveredModels(models: List<DiscoveredModelEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertDiscoveredModel(model: DiscoveredModelEntity)

    @Query("DELETE FROM discovered_models WHERE providerId = :providerId")
    suspend fun deleteDiscoveredModelsForProvider(providerId: String)

    @Query("DELETE FROM discovered_models WHERE id = :id")
    suspend fun deleteDiscoveredModelById(id: String)

    @Query("SELECT * FROM permissions WHERE agentRole = :role")
    suspend fun getPermissionsForRole(role: String): List<PermissionEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertPermission(permission: PermissionEntity)
}
