package com.agentdroid.app.domain.model

enum class TaskStatus {
    PENDING,
    READY,
    RUNNING,
    WAITING_APPROVAL,
    COMPLETED,
    FAILED,
    SKIPPED,
    CANCELLED
}

enum class PlanStatus {
    PLANNING,
    AWAITING_USER_APPROVAL,
    EXECUTING,
    PAUSED,
    COMPLETED,
    FAILED,
    CANCELLED
}

data class TaskItem(
    val id: String,
    val planId: String,
    val agentRole: AgentRole,
    val title: String,
    val description: String,
    val inputData: Map<String, String> = emptyMap(),
    val outputData: Map<String, String> = emptyMap(),
    val dependsOn: List<String> = emptyList(),
    val status: TaskStatus = TaskStatus.PENDING,
    val riskLevel: RiskLevel = RiskLevel.LOW,
    val actionType: ActionType? = null,
    val toolName: String? = null,
    val createdAt: Long = System.currentTimeMillis(),
    val completedAt: Long? = null,
    val error: String? = null,
    val retryCount: Int = 0,
    val maxRetries: Int = 2
)

data class TaskPlan(
    val id: String,
    val userGoal: String,
    val tasks: List<TaskItem>,
    val status: PlanStatus = PlanStatus.PLANNING,
    val createdAt: Long = System.currentTimeMillis(),
    val completedAt: Long? = null,
    val finalSummary: String? = null
)
