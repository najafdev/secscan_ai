---
title: Debugging, Diagnostics & Profiling Guide
purpose: Engineering procedures for diagnosing issues, inspecting state, and debugging services
scope: Logcat tagging, Room SQLite inspection, accessibility node inspection, and network traces
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/developer/TESTING_GUIDE.md
  - docs/architecture/ANDROID_INTEGRATION.md
---

# Debugging, Diagnostics & Profiling Guide

This guide describes techniques and diagnostic tooling for debugging AgentDroid during local development.

---

## 1. Logcat Tagging Conventions

AgentDroid components log using consistent tags for focused filtering:

| Tag | Component | Description |
|---|---|---|
| `AgentDroid:Orchestrator` | `AgentOrchestrator` | Task graph construction, agent assignment, and execution flow. |
| `AgentDroid:AiConnection` | `AiConnectionManager` | Provider selection, ping latencies, and connection errors. |
| `AgentDroid:Accessibility` | `AgentDroidAccessibilityService` | Screen node discovery, window events, and gesture dispatch. |
| `AgentDroid:Action` | `ActionDispatcher` | Tool parameters, pre-execution checks, and state verifications. |
| `AgentDroid:DB` | `AgentDroidDatabase` | Room queries, migrations, and transaction logs. |

Filter Logcat via ADB:
```bash
adb logcat -s "AgentDroid:Orchestrator" "AgentDroid:AiConnection"
```

---

## 2. Inspecting Room SQLite Database

To inspect on-device database tables without root:
1. Open **App Inspection** in Android Studio.
2. Select the running `com.agentdroid.app.debug` process.
3. Open the **Database Inspector** tab to view live tables (`agents`, `workflows`, `activity_logs`).
4. Execute ad-hoc SQL queries directly against the connected device.

---

## 3. Inspecting Accessibility View Trees

When troubleshooting UI automation failures:
* Use **Layout Inspector** in Android Studio to inspect the view hierarchy of target apps.
* Alternatively, run:
  ```bash
  adb shell uiautomator dump /data/local/tmp/uidump.xml
  adb pull /data/local/tmp/uidump.xml
  ```
  Inspect the XML output to identify missing `resource-id` or `content-desc` attributes on buttons.

---

## 4. HTTP Network Tracing

When running debug builds (`app-debug.apk`), OkHttp's `HttpLoggingInterceptor` is configured with `Level.BODY` for non-sensitive local network requests (e.g., local Ollama endpoints). Sensitive API keys in `Authorization` headers are sanitized.

---

## Related Documentation
* [Testing Guide](file:///workspaces/hacknova/docs/developer/TESTING_GUIDE.md)
* [Android Integration](file:///workspaces/hacknova/docs/architecture/ANDROID_INTEGRATION.md)
