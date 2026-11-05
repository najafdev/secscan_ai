---
title: Project Structure & Code Organization
purpose: Complete directory and package breakdown of the AgentDroid codebase
scope: Source code maps, module structure, and package responsibilities
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/developer/DEVELOPER_GUIDE.md
  - docs/architecture/SOFTWARE_ARCHITECTURE.md
---

# Project Structure & Code Organization

The AgentDroid application is organized as a clean single-module Android project located in `app/`. The source code is organized into logical packages reflecting its domain-driven, multi-agent architecture.

---

## 1. Top-Level Directory Layout

```
agentdroid/
├── app/                              # Android application module
│   ├── build.gradle.kts              # Module build script and dependencies
│   ├── proguard-rules.pro            # R8 / ProGuard shrinkage rules
│   └── src/
│       ├── main/
│       │   ├── AndroidManifest.xml   # Manifest, permissions, services
│       │   ├── java/com/agentdroid/app/
│       │   └── res/                  # Drawables, layouts, xml (security configs)
│       └── test/                     # JVM unit tests (JUnit 4, coroutines)
├── build.gradle.kts                  # Root project build configuration
├── settings.gradle.kts               # Plugin and repository configurations
├── gradle/wrapper/                   # Gradle wrapper binaries & properties
└── docs/                             # Complete project documentation ecosystem
```

---

## 2. Kotlin Package Structure (`com.agentdroid.app`)

```
com.agentdroid.app/
│
├── domain/                           # Core business logic & contracts
│   ├── agent/                        # Agent interface, BaseAgent, 11 Agent implementations
│   ├── orchestrator/                 # AgentOrchestrator, DAGScheduler, SharedTaskContext
│   ├── workflow/                     # WorkflowEngine, triggers, step execution models
│   ├── memory/                       # Multi-tier memory interfaces & context resolvers
│   └── model/                        # Domain models (AgentTask, Plan, ExecutionStatus)
│
├── ai/                               # AI Provider & Communication Engine
│   ├── provider/                     # AiProvider interface, HttpAiProvider, OpenAI / Gemini adapters
│   ├── connection/                   # AiConnectionManager, ConnectivityVerifier
│   ├── discovery/                    # ModelDiscoveryService, ProviderMetadataRegistry
│   ├── router/                       # ModelRouter, FallbackStrategy
│   └── error/                        # AiError, ErrorCategory, failure parsers
│
├── automation/                       # Android System & Accessibility Automation
│   ├── accessibility/                # AgentDroidAccessibilityService, NodeFinder
│   ├── action/                       # ActionDispatcher, ActionType, StateVerifier
│   └── service/                      # Background execution services & notification binds
│
├── data/                             # Persistence & Hardware Storage
│   └── local/
│       ├── AgentDroidDatabase.kt     # Room v2 SQLite database instance
│       ├── dao/                      # 12 Room Data Access Objects (DAOs)
│       ├── entity/                   # 17 Room Database Entities
│       └── security/                 # SecurePreferencesManager (Android Keystore AES-256)
│
├── ui/                               # Jetpack Compose Presentation Layer
│   ├── navigation/                   # Screen destinations, NavGraph, BottomNavBar
│   ├── screens/                      # HomeScreen, AgentFleetScreen, SettingsScreen, etc.
│   ├── components/                   # Reusable UI widgets (AgentCard, MetricTile, ErrorBanner)
│   └── theme/                        # Obsidian dark palette, Typography, Shapes
│
└── sdk/                              # Developer Extension SDK
    └── extensions/                   # Custom agent builder and plugin hooks
```

---

## Related Documentation
* [Developer Guide](file:///workspaces/agentdroid-/docs/developer/DEVELOPER_GUIDE.md)
* [Software Architecture](file:///workspaces/agentdroid-/docs/architecture/SOFTWARE_ARCHITECTURE.md)
* [Database Schema](file:///workspaces/agentdroid-/docs/architecture/DATABASE_SCHEMA.md)
