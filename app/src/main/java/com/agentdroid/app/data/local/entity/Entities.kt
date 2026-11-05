package com.agentdroid.app.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

// 1. Agent Entity
@Entity(tableName = "agents")
data class AgentEntity(
    @PrimaryKey val id: String,
    val name: String,
    val role: String,
    val description: String,
    val isEnabled: Boolean = true,
    val isCustom: Boolean = false,
    val createdAt: Long = System.currentTimeMillis()
)

// 2. Agent Configuration Entity
@Entity(
    tableName = "agent_configurations",
    foreignKeys = [
        ForeignKey(
            entity = AgentEntity::class,
            parentColumns = ["id"],
            childColumns = ["agentId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index(value = ["agentId"], unique = true)]
)
data class AgentConfigEntity(
    @PrimaryKey val id: String,
    val agentId: String,
    val assignedModel: String,
    val providerId: String,
    val systemPrompt: String,
    val temperature: Float = 0.7f,
    val executionLimitSeconds: Int = 120,
    val capabilitiesJson: String = "[]",
    val toolsJson: String = "[]"
)

// 3. Task Entity
@Entity(
    tableName = "tasks",
    indices = [Index("planId"), Index("agentRole"), Index("status")]
)
data class TaskEntity(
    @PrimaryKey val id: String,
    val planId: String,
    val agentRole: String,
    val title: String,
    val description: String,
    val status: String,
    val riskLevel: String,
    val actionType: String?,
    val toolName: String?,
    val inputDataJson: String = "{}",
    val outputDataJson: String = "{}",
    val createdAt: Long = System.currentTimeMillis(),
    val completedAt: Long? = null,
    val error: String? = null,
    val retryCount: Int = 0
)

// 4. Task Dependency Entity
@Entity(
    tableName = "task_dependencies",
    primaryKeys = ["taskId", "dependsOnTaskId"],
    foreignKeys = [
        ForeignKey(
            entity = TaskEntity::class,
            parentColumns = ["id"],
            childColumns = ["taskId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index("taskId"), Index("dependsOnTaskId")]
)
data class TaskDependencyEntity(
    val taskId: String,
    val dependsOnTaskId: String
)

// 5. Agent Execution Entity
@Entity(
    tableName = "agent_executions",
    indices = [Index("agentId"), Index("taskId"), Index("startTime")]
)
data class AgentExecutionEntity(
    @PrimaryKey val id: String,
    val agentId: String,
    val taskId: String,
    val state: String,
    val startTime: Long = System.currentTimeMillis(),
    val endTime: Long? = null,
    val tokensUsed: Int = 0,
    val resultSummary: String? = null,
    val errorMessage: String? = null
)

// 6. Conversation Entity
@Entity(tableName = "conversations")
data class ConversationEntity(
    @PrimaryKey val id: String,
    val title: String,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis(),
    val isPinned: Boolean = false
)

// 7. Message Entity
@Entity(
    tableName = "messages",
    foreignKeys = [
        ForeignKey(
            entity = ConversationEntity::class,
            parentColumns = ["id"],
            childColumns = ["conversationId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index("conversationId"), Index("timestamp")]
)
data class MessageEntity(
    @PrimaryKey val id: String,
    val conversationId: String,
    val senderRole: String, // "USER", "MASTER", or agent role
    val content: String,
    val timestamp: Long = System.currentTimeMillis(),
    val associatedPlanId: String? = null,
    val isStreaming: Boolean = false
)

// 8. Memory Record Entity
@Entity(
    tableName = "memory_records",
    indices = [Index("tier"), Index("key"), Index("agentRole")]
)
data class MemoryRecordEntity(
    @PrimaryKey val id: String,
    val tier: String,
    val agentRole: String?,
    val key: String,
    val value: String,
    val tagsJson: String = "[]",
    val confidence: Float = 1.0f,
    val timestamp: Long = System.currentTimeMillis(),
    val accessCount: Int = 0
)

// 9. Workflow Entity
@Entity(tableName = "workflows")
data class WorkflowEntity(
    @PrimaryKey val id: String,
    val title: String,
    val prompt: String,
    val triggerType: String,
    val cronSchedule: String? = null,
    val isEnabled: Boolean = true,
    val lastRun: Long? = null,
    val nextRun: Long? = null,
    val executionCount: Int = 0,
    val createdAt: Long = System.currentTimeMillis()
)

// 10. Workflow Step Entity
@Entity(
    tableName = "workflow_steps",
    foreignKeys = [
        ForeignKey(
            entity = WorkflowEntity::class,
            parentColumns = ["id"],
            childColumns = ["workflowId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index("workflowId")]
)
data class WorkflowStepEntity(
    @PrimaryKey val id: String,
    val workflowId: String,
    val stepOrder: Int,
    val agentRole: String,
    val instruction: String,
    val requiredRiskLevel: String = "LOW"
)

// 11. Connected Account Entity
@Entity(tableName = "connected_accounts")
data class ConnectedAccountEntity(
    @PrimaryKey val id: String,
    val platform: String,
    val username: String,
    val displayName: String,
    val isConnected: Boolean = true,
    val permissionsJson: String = "[]",
    val lastSyncTime: Long = System.currentTimeMillis()
)

// 12. API Provider Entity
@Entity(tableName = "api_providers")
data class ApiProviderEntity(
    @PrimaryKey val id: String,
    val providerType: String,
    val displayName: String,
    val baseUrl: String,
    val isEnabled: Boolean = true,
    val totalTokensUsed: Long = 0L
)

// 13. Model Configuration Entity
@Entity(
    tableName = "model_configurations",
    indices = [Index("agentRole", unique = true)]
)
data class ModelConfigEntity(
    @PrimaryKey val id: String,
    val agentRole: String,
    val providerId: String,
    val modelName: String,
    val temperature: Float = 0.7f,
    val maxTokens: Int = 2048
)

// 13b. Discovered Model Entity
@Entity(
    tableName = "discovered_models",
    indices = [Index("providerId"), Index("modelId")]
)
data class DiscoveredModelEntity(
    @PrimaryKey val id: String, // "$providerId:$modelId"
    val modelId: String,
    val providerId: String,
    val displayName: String,
    val modelType: String, // "CLOUD" or "LOCAL"
    val capabilitiesJson: String = "[\"TEXT_GENERATION\",\"STREAMING\"]",
    val contextWindow: Int? = null,
    val isAvailable: Boolean = true,
    val isLocal: Boolean = false,
    val lastVerified: Long = System.currentTimeMillis(),
    val isManualEntry: Boolean = false,
    val isCached: Boolean = false
)

// 14. Permission Entity
@Entity(
    tableName = "permissions",
    indices = [Index(value = ["agentRole", "permissionName"], unique = true)]
)
data class PermissionEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val agentRole: String,
    val permissionName: String,
    val isGranted: Boolean = false,
    val grantedAt: Long? = null
)

// 15. Approval Request Entity
@Entity(
    tableName = "approval_requests",
    indices = [Index("taskId"), Index("status")]
)
data class ApprovalRequestEntity(
    @PrimaryKey val id: String,
    val taskId: String,
    val planId: String,
    val agentRole: String,
    val title: String,
    val description: String,
    val riskLevel: String,
    val actionDetails: String,
    val targetPayload: String? = null,
    val status: String,
    val timestamp: Long = System.currentTimeMillis()
)

// 16. Activity Log Entity
@Entity(
    tableName = "activity_logs",
    indices = [Index("timestamp"), Index("agentRole"), Index("actionType")]
)
data class ActivityLogEntity(
    @PrimaryKey val id: String,
    val agentRole: String,
    val actionType: String,
    val description: String,
    val riskLevel: String,
    val status: String,
    val timestamp: Long = System.currentTimeMillis(),
    val metadata: String? = null,
    val taskId: String? = null
)
