---
title: Android System Integration
purpose: Specifications for Accessibility Service, Foreground Services, Intents, and OS bridges
scope: Native Android system integrations and permissions
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/security/PERMISSION_MODEL.md
  - docs/user-guide/PHONE_AUTOMATION.md
---

# Android System Integration

## Accessibility Automation Service

AgentDroid interacts with native third-party Android applications via `AgentDroidAccessibilityService` (`com.agentdroid.app.automation.accessibility`), declared in `accessibility_service_config.xml`:

```xml
<accessibility-service xmlns:android="http://schemas.android.com/apk/res/android"
    android:accessibilityEventTypes="typeAllMask"
    android:accessibilityFeedbackType="feedbackGeneric"
    android:accessibilityFlags="flagDefault|flagRetrieveInteractiveWindows|flagReportViewIds"
    android:canRetrieveWindowContent="true"
    android:canPerformGestures="true"
    android:description="@string/accessibility_service_description"
    android:notificationTimeout="100" />
```

### Automation Capabilities:
1. **Interactive Node Traversal**: Recursively scans `AccessibilityNodeInfo` hierarchies to locate actionable UI elements by text label, content description, or View ID (`findAccessibilityNodeInfosByViewId`).
2. **Gesture Dispatch**: Executes programmatic clicks (`ACTION_CLICK`), focus actions (`ACTION_FOCUS`), and text entry (`ACTION_SET_TEXT`).
3. **Screen Scrolling**: Dispatches `ACTION_SCROLL_FORWARD` and `ACTION_SCROLL_BACKWARD` across scrollable lists and web views.
4. **Window Inspection**: Reads visible on-screen text to provide screen context to the `StateVerifier`.

---

## Foreground Service & Life-Safety Killswitch

To ensure Android does not kill continuous multi-agent execution while the user switches to other apps, AgentDroid runs `AutomationForegroundService` (`dataSync` type):

* **Persistent Notification**: Informs user that AgentDroid multi-agent execution is actively running.
* **Notification Killswitch Action**: Embeds an immediate `ACTION_EMERGENCY_STOP` Intent directly in the Android status bar notification. Tapping "Emergency Stop" dispatches `EmergencyKillswitch.triggerEmergencyStop()`, terminating automation within milliseconds without requiring the user to open the app.

---

## Android Intents & Package Querying

* **Application Launching**: Resolves installed packages via `PackageManager.getLaunchIntentForPackage()` guarded by `<uses-permission android:name="android.permission.QUERY_ALL_PACKAGES" />`.
* **External Action Dispatching**: Dispatches standard Android Intents:
  * `Intent.ACTION_VIEW` for web URLs.
  * `Intent.ACTION_SEND` / `Intent.ACTION_SENDTO` (`mailto:`) for email drafts.
  * `Settings.ACTION_ACCESSIBILITY_SETTINGS` for seamless onboarding.
