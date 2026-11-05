package com.agentdroid.app.domain.agent

import com.agentdroid.app.automation.action.ActionDispatcher
import com.agentdroid.app.data.local.dao.ActivityLogDao
import com.agentdroid.app.domain.model.ActionType
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.TaskItem
import com.agentdroid.app.domain.orchestrator.SharedTaskContext

class PhoneControlAgent(
    actionDispatcher: ActionDispatcher,
    activityLogDao: ActivityLogDao
) : BaseAgent(
    id = "agent_phone",
    name = "Phone Control Agent",
    role = AgentRole.PHONE_CONTROL,
    description = "Controls and interacts with the Android device via Accessibility Services, Intents, and System APIs. Dispatches WhatsApp messages, SMS, phone calls, system volume/torch/DND, and screen automation.",
    capabilities = listOf(
        "Open installed applications", "Send WhatsApp messages", "Send direct SMS",
        "Place phone calls", "Control system settings (Volume, Flashlight, DND, Vibrate)",
        "Search & resolve device contacts", "Click buttons & UI elements", "Type text",
        "Scroll screens", "Navigate back/home", "Read visible screen content",
        "Search device files", "Create files", "Verify resulting device state"
    ),
    availableTools = listOf(
        "AccessibilityDriver", "WhatsAppAutomator", "SmsDispatcher", "CallDialer",
        "SystemController", "ContactResolver", "IntentLauncher", "ScreenInspector",
        "GestureAutomator", "DeviceSearchEngine", "FileCreator"
    ),
    requiredPermissions = listOf(
        "android.permission.BIND_ACCESSIBILITY_SERVICE",
        "android.permission.SEND_SMS",
        "android.permission.CALL_PHONE",
        "android.permission.READ_CONTACTS",
        "android.permission.WRITE_SETTINGS",
        "android.permission.MODIFY_AUDIO_SETTINGS",
        "android.permission.QUERY_ALL_PACKAGES"
    ),
    actionDispatcher = actionDispatcher,
    activityLogDao = activityLogDao
) {
    override suspend fun performTaskExecution(
        task: TaskItem,
        context: SharedTaskContext
    ): AgentExecutionOutput {
        val action = task.actionType ?: ActionType.READ_SCREEN
        val params = task.inputData.toMutableMap()
        if (!params.containsKey("target")) {
            params["target"] = task.description
        }

        val result = actionDispatcher.dispatchAction(action, params)
        if (!result.isSuccess) {
            throw RuntimeException("Phone action failed: ${result.message}")
        }

        context.put("phone_last_action", action.name)
        context.put("phone_result", result.message)

        return AgentExecutionOutput(
            summary = result.message,
            outputData = result.data + mapOf("summary" to result.message)
        )
    }
}
