package com.agentdroid.app.domain.model

enum class TriggerType {
    MANUAL,
    SCHEDULED,
    NOTIFICATION_RECEIVED,
    BATTERY_LOW,
    HEADPHONES_CONNECTED,
    SHARE_INTENT
}

data class Workflow(
    val id: String,
    val title: String,
    val prompt: String,
    val triggerType: TriggerType = TriggerType.MANUAL,
    val cronSchedule: String? = null,
    val isEnabled: Boolean = true,
    val lastRun: Long? = null,
    val nextRun: Long? = null,
    val executionCount: Int = 0
)

enum class PlatformType(val displayName: String) {
    TWITTER("X (Twitter)"),
    INSTAGRAM("Instagram"),
    FACEBOOK("Facebook"),
    LINKEDIN("LinkedIn"),
    TELEGRAM("Telegram"),
    DISCORD("Discord"),
    YOUTUBE("YouTube"),
    REDDIT("Reddit")
}

data class SocialPostDraft(
    val id: String,
    val platform: PlatformType,
    val content: String,
    val hashtags: List<String> = emptyList(),
    val scheduledTime: Long? = null,
    val isPublished: Boolean = false,
    val requiresApproval: Boolean = true,
    val engagementLikes: Int = 0,
    val engagementComments: Int = 0,
    val createdAt: Long = System.currentTimeMillis()
)

data class ConnectedAccount(
    val id: String,
    val platform: PlatformType,
    val username: String,
    val displayName: String,
    val isConnected: Boolean = true,
    val permissionsGranted: List<String> = emptyList(),
    val lastSyncTime: Long = System.currentTimeMillis()
)
