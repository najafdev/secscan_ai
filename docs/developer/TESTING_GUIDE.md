---
title: Automated Testing & Verification Guide
purpose: Standards and practices for unit, integration, and UI testing in AgentDroid
scope: JUnit 4, Kotlin Coroutines Test, Room testing, and Strict Real AI test suites
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/developer/CODING_STANDARDS.md
  - docs/developer/DEBUGGING.md
---

# Automated Testing & Verification Guide

AgentDroid emphasizes test-driven reliability. Every component—from DAG scheduling to AI connection validation—must be covered by automated test suites.

---

## 1. Test Architecture & Frameworks

* **Unit Testing**: JUnit 4 (`junit:junit:4.13.2`)
* **Coroutines Testing**: `kotlinx-coroutines-test:1.8.1` (`runTest`, `StandardTestDispatcher`)
* **Mocking & HTTP Testing**: OkHttp `MockWebServer` and custom interceptor fakes
* **Android Instrumentation**: AndroidX Test, Espresso, and Compose UI Test Rule

---

## 2. Running Test Suites

Run all local JVM unit tests via Gradle:

```bash
# Run entire unit test suite
./gradlew testDebugUnitTest

# Run a specific test class
./gradlew testDebugUnitTest --tests "com.agentdroid.app.StrictRealAiModeTest"

# Run tests with stacktrace logging
./gradlew testDebugUnitTest --stacktrace --info
```

Test reports are generated in HTML format at:
`app/build/reports/tests/testDebugUnitTest/index.html`

---

## 3. Strict Real AI Mode Testing

Testing in AgentDroid enforces the **Strict Real AI** mandate:
* Verify that unconfigured providers throw `AiError.ProviderNotConfigured`.
* Verify that bad HTTP status codes (401, 403, 500) map to structured, user-actionable errors.
* Unit tests must never assert against hardcoded or dummy response strings.

Example test pattern:
```kotlin
@Test
fun `unconfigured provider emits ProviderNotConfigured error`() = runTest {
    val connectionManager = AiConnectionManager(fakeSettingsDao, fakeSecurePrefs)
    val result = connectionManager.executePrompt("Hello AgentDroid")
    
    assertTrue(result is Result.Failure)
    assertTrue(result.exceptionOrNull() is AiError.ProviderNotConfigured)
}
```

---

## Related Documentation
* [Coding Standards](file:///workspaces/hacknova/docs/developer/CODING_STANDARDS.md)
* [Debugging Guide](file:///workspaces/hacknova/docs/developer/DEBUGGING.md)
