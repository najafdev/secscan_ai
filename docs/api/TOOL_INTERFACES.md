---
title: Tool & Action Interfaces Reference
purpose: Technical contracts for ActionDispatcher, ActionType, and ActionResult
scope: Action execution, parameter specifications, state verifiers, and permissions
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/api/API_OVERVIEW.md
  - docs/developer/TOOL_DEVELOPMENT.md
  - docs/security/TOOL_EXECUTION_SECURITY.md
---

# Tool & Action Interfaces Reference

This document specifies the contracts used by agents to execute actions on the Android operating system.

---

## 1. `ActionDispatcher` Contract

```kotlin
package com.agentdroid.app.automation.action

interface ActionDispatcher {
    suspend fun dispatch(
        actionType: ActionType,
        parameters: Map<String, Any?>
    ): ActionResult

    fun isActionSupported(actionType: ActionType): Boolean
}
```

---

## 2. `ActionResult` Hierarchy

```kotlin
sealed class ActionResult {
    data class Success(
        val data: Map<String, Any?> = emptyMap(),
        val verificationPassed: Boolean = true,
        val message: String = "Action executed successfully."
    ) : ActionResult()

    data class Failure(
        val error: String,
        val errorCode: String = "ERR_TOOL_EXECUTION",
        val retryable: Boolean = false
    ) : ActionResult()

    object Cancelled : ActionResult()
}
```

---

## 3. Supported `ActionType` Enums & Parameters

```kotlin
enum class ActionType {
    OPEN_APP,              // params: { "package_name": "com.example.app" }
    CLICK_ELEMENT,         // params: { "text": "Login", "view_id": "btn_submit" }
    TYPE_TEXT,             // params: { "text": "hello world", "field_name": "search_input" }
    SCROLL_SCREEN,         // params: { "direction": "FORWARD" }
    NAVIGATE_BACK,         // params: {}
    NAVIGATE_HOME,         // params: {}
    EXTRACT_SCREEN_TEXT,   // params: {}
    TAKE_SCREENSHOT,       // params: {}
    READ_CLIPBOARD,        // params: {}
    WRITE_CLIPBOARD        // params: { "text": "payload" }
}
```

---

## 4. `StateVerifier` Contract

```kotlin
interface StateVerifier {
    suspend fun verify(
        actionType: ActionType,
        expectedState: Map<String, Any?>,
        timeoutMs: Long = 3000L
    ): Boolean
}
```

---

## Related Documentation
* [Tool Development Guide](file:///workspaces/agentdroid-/docs/developer/TOOL_DEVELOPMENT.md)
* [Tool Execution Security](file:///workspaces/agentdroid-/docs/security/TOOL_EXECUTION_SECURITY.md)
* [Android Integration](file:///workspaces/agentdroid-/docs/architecture/ANDROID_INTEGRATION.md)
