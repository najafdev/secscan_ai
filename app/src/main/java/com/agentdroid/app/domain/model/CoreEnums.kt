package com.agentdroid.app.domain.model

enum class AgentRole(val displayName: String, val roleId: String) {
    MASTER("Master Agent", "agent_master"),
    PHONE_CONTROL("Phone Control Agent", "agent_phone"),
    SOCIAL_MEDIA("Social Media Agent", "agent_social"),
    CONTENT_CREATION("Content Creation Agent", "agent_content"),
    RESEARCH("Research Agent", "agent_research"),
    COMMUNICATION("Communication Agent", "agent_comm"),
    FILE_MANAGEMENT("File Management Agent", "agent_file"),
    PRODUCTIVITY("Productivity Agent", "agent_productivity"),
    ANALYTICS("Analytics Agent", "agent_analytics"),
    BROWSER("Browser Agent", "agent_browser"),
    SECURITY("Security Agent", "agent_security"),
    CUSTOM("Custom Agent", "agent_custom");

    companion object {
        fun fromId(id: String): AgentRole {
            return entries.firstOrNull { it.roleId == id } ?: CUSTOM
        }
    }
}

enum class AgentExecutionState {
    IDLE,
    THINKING,
    PLANNING,
    ASSIGNED,
    RUNNING,
    WAITING_FOR_APPROVAL,
    COMPLETED,
    FAILED,
    CANCELLED
}

enum class RiskLevel {
    LOW,
    MEDIUM,
    HIGH
}

enum class ActionType {
    OPEN_APP,
    CLICK_ELEMENT,
    TYPE_TEXT,
    SCROLL_SCREEN,
    GO_BACK,
    TAKE_SCREENSHOT,
    READ_SCREEN,
    OPEN_URL,
    COPY_TEXT,
    PASTE_TEXT,
    SEARCH_DEVICE,
    CREATE_FILE,
    DELETE_FILE,
    SEND_EMAIL,
    POST_SOCIAL,
    QUERY_DATABASE,
    EXECUTE_CUSTOM_TOOL,
    SEND_WHATSAPP,
    SEND_SMS,
    MAKE_CALL,
    CONTROL_SYSTEM,
    READ_CONTACTS
}
