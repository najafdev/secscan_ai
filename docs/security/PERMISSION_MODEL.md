---
title: Permission Model
purpose: Complete catalog of Android OS permissions, justification, and risk mitigations
scope: AndroidManifest.xml permissions and runtime permission handling
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/security/SECURITY_REQUIREMENTS.md
  - docs/architecture/ANDROID_INTEGRATION.md
---

# Permission Model

## Android Permission Inventory

AgentDroid declares only essential Android permissions in `AndroidManifest.xml`:

| Permission Identifier | Protection Level | Purpose & Justification | Mitigation & User Control |
| :--- | :--- | :--- | :--- |
| `android.permission.INTERNET` | Normal | Connect to user-configured cloud AI providers (OpenAI, Gemini, Claude) and local LAN Ollama servers. | Network traffic is restricted to configured Base URLs; TLS enforced for cloud. |
| `android.permission.ACCESS_NETWORK_STATE` | Normal | Detect network availability and Wi-Fi state before attempting inference requests. | Read-only state check; no network mutations. |
| `android.permission.FOREGROUND_SERVICE` | Normal | Keep multi-agent workflow execution alive when user switches to other apps. | Enforces persistent notification with status and emergency stop button. |
| `android.permission.FOREGROUND_SERVICE_DATA_SYNC`| Normal | Declare specific Android 14 foreground service type for data and workflow synchronization. | Required by Android 14 (API 34) platform policy. |
| `android.permission.POST_NOTIFICATIONS` | Dangerous | Alert user to completed plans, emergency stop events, and pending Human Approval requests. | Explicit runtime prompt on Android 13+ (API 33). |
| `android.permission.QUERY_ALL_PACKAGES` | Special | Phone Control Agent resolves installed app package names to execute `OPEN_APP` commands. | Filtered to application launching; package names never exfiltrated. |
| `BIND_ACCESSIBILITY_SERVICE` | Signature / Special | Allows `AgentDroidAccessibilityService` to inspect screen hierarchies and dispatch gestures. | Explicit manual activation in Android Accessibility Settings with system warning. |

---

## Principle of Least Privilege

1. **No SMS / Telephony Permissions**: AgentDroid does not request `READ_SMS`, `SEND_SMS`, or `READ_CALL_LOG`. Text messages and phone calls can only be initiated via standard Android `Intent` choosers, requiring user tap confirmation.
2. **No Location Permissions**: AgentDroid does not request `ACCESS_FINE_LOCATION` or `ACCESS_COARSE_LOCATION`.
3. **No External Storage Root Access**: AgentDroid operates within Android Scoped Storage (`getExternalFilesDir()`); arbitrary root file modifications are prohibited.
