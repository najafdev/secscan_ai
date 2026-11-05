---
title: AgentDroid Developer Guide & Onboarding
purpose: Comprehensive technical onboarding guide for contributing to AgentDroid
scope: Architecture overview, engineering principles, development workflow, and repository tour
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/developer/DEVELOPMENT_SETUP.md
  - docs/developer/PROJECT_STRUCTURE.md
  - docs/architecture/SYSTEM_ARCHITECTURE.md
---

# AgentDroid Developer Guide & Onboarding

Welcome to the AgentDroid engineering ecosystem. AgentDroid is an open-source, multi-agent AI operating platform built natively for Android using Kotlin and Jetpack Compose.

---

## 1. Engineering Principles

1. **Strict Real AI**: Zero hardcoded AI responses. If a provider fails or credentials are missing, emit an explicit, typed `AiError` rather than fabricating simulated responses.
2. **Local-First & Privacy Preserving**: User data, encryption keys, and agent memories must stay on-device unless explicitly delegated to a user-configured AI endpoint.
3. **Reactive Unidirectional Data Flow (UDF)**: UI state flows downward via Compose states; user intents flow upward via ViewModel events.
4. **Deterministic Orchestration**: Multi-agent task plans are structured as Directed Acyclic Graphs (DAGs) with explicit dependency resolution and isolated execution contexts.

---

## 2. High-Level Architecture Overview

```mermaid
flowchart TD
    UI[Jetpack Compose UI & Navigation] --> VM[ViewModels]
    VM --> Orch[AgentOrchestrator & DAGScheduler]
    Orch --> Context[SharedTaskContext & Memory Tier]
    Orch --> Agents[Agent Fleet: Master & 10 Specialized Agents]
    Agents --> Dispatcher[ActionDispatcher]
    Agents --> AI[AiConnectionManager & HttpAiProvider]
    Dispatcher --> Service[AgentDroidAccessibilityService]
    AI --> Remote[Cloud LLMs: OpenAI / Gemini / Claude]
    AI --> Local[Local LLMs: Ollama / LM Studio]
    VM --> DB[(Room Database v2: 17 Entities)]
```

---

## 3. Contribution Workflow

1. **Fork & Branch**: Create feature branches off `main` following the naming convention:
   * `feat/agent-<name>`
   * `fix/navigation-<target>`
   * `docs/<topic>`
2. **Build & Verify Locally**:
   * Compile and run unit tests: `./gradlew testDebugUnitTest`
   * Build debug APK: `./gradlew assembleDebug`
3. **Pull Request Protocol**:
   * Reference open issues or task IDs.
   * Provide sample prompt inputs and agent step outputs.
   * Ensure 100% test pass rate with zero lint regressions.

---

## Related Documentation
* [Development Setup](file:///workspaces/hacknova/docs/developer/DEVELOPMENT_SETUP.md)
* [Project Structure](file:///workspaces/hacknova/docs/developer/PROJECT_STRUCTURE.md)
* [System Architecture](file:///workspaces/hacknova/docs/architecture/SYSTEM_ARCHITECTURE.md)
