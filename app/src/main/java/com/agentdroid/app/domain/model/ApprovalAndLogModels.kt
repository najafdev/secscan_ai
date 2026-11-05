package com.agentdroid.app.domain.model

enum class ApprovalStatus {
    PENDING,
    APPROVED,
    REJECTED
}

data class ApprovalRequest(
    val id: String,
    val taskId: String,
    val planId: String,
    val agentRole: AgentRole,
    val title: String,
    val description: String,
    val riskLevel: RiskLevel,
    val actionDetails: String,
    val targetPayload: String? = null,
    val status: ApprovalStatus = ApprovalStatus.PENDING,
    val timestamp: Long = System.currentTimeMillis()
)

data class ActivityLogItem(
    val id: String,
    val agentRole: AgentRole,
    val actionType: ActionType,
    val description: String,
    val riskLevel: RiskLevel,
    val status: String,
    val timestamp: Long = System.currentTimeMillis(),
    val metadata: String? = null,
    val taskId: String? = null
)
