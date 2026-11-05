---
title: Kotlin & Android Coding Standards
purpose: Architectural and stylistic standards for maintaining codebase quality and consistency
scope: Kotlin idioms, Jetpack Compose conventions, coroutines, and error handling
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/developer/DEVELOPER_GUIDE.md
  - docs/developer/TESTING_GUIDE.md
---

# Kotlin & Android Coding Standards

All contributions to AgentDroid must adhere to the following architectural, stylistic, and performance guidelines.

---

## 1. Kotlin Language Conventions

* **Immutability First**: Default to `val` for variables and properties. Use immutable collections (`List`, `Map`, `Set`) instead of mutable ones in public APIs.
* **Data Classes**: Use `data class` for models, events, and state representations.
* **Sealed Hierarchies**: Model bounded states (such as `UiState`, `AiResponse`, `AgentStepResult`) with `sealed class` or `sealed interface`.
* **Coroutines Best Practices**:
  * Never block threads; always use `suspend` functions for I/O and network operations.
  * Inject `CoroutineDispatcher` (e.g., `Dispatchers.IO`, `Dispatchers.Default`) to facilitate deterministic unit testing.
  * Avoid `GlobalScope`. Use structured concurrency via `viewModelScope` or explicit `CoroutineScope` instances tied to component lifecycles.

---

## 2. Jetpack Compose Guidelines

* **Unidirectional Data Flow (UDF)**:
  * Composables must receive state as parameters and emit events via lambda callbacks.
  * Avoid instantiating ViewModels or accessing database instances directly within leaf UI composables.
* **State Hoisting**:
  * Keep composable widgets stateless wherever possible to maximize reusability and previewability.
* **Stable Keys in Lazy Layouts**:
  * Always provide unique `key` parameters for items in `LazyColumn` and `LazyRow` to prevent unnecessary recompositions:
    ```kotlin
    items(agents, key = { it.id }) { agent ->
        AgentCard(agent = agent)
    }
    ```

---

## 3. Error Handling & Real AI Mandate

* **No Silent Failures**: Never catch `Exception` and silently swallow it. Either handle the error, recover, or bubble up a structured domain error (`AiError`).
* **Strict Real AI**: Never return placeholder text (e.g., `"Mock AI response"`, `"Simulated task completed"`) when an AI call fails. Always throw or return `AiError.ProviderNotConfigured`, `AiError.AuthenticationFailed`, or `AiError.NetworkTimeout`.

---

## Related Documentation
* [Developer Guide](file:///workspaces/agentdroid-/docs/developer/DEVELOPER_GUIDE.md)
* [Testing Guide](file:///workspaces/agentdroid-/docs/developer/TESTING_GUIDE.md)
