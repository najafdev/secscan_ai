---
title: User Journeys
purpose: Maps end-to-end user workflows from onboarding to autonomous multi-agent execution
scope: Interaction flows, screen states, decision branches, and recovery paths
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/product/USER_PERSONAS.md
  - docs/user-guide/GETTING_STARTED.md
---

# User Journeys

## Journey 1: First-Time Setup & Local Ollama Connection

```mermaid
journey
    title First-Time User: Setup & Local Ollama Connection
    section Installation & Permissions
      Install APK: 5: User
      Grant Notifications & Foreground Service: 4: User
      Enable Accessibility Service in Android Settings: 3: User
    section AI Connectivity
      Open Settings -> Add Provider: 5: User
      Select "Local / LAN Servers" -> Ollama Preset: 5: User
      Enter LAN IP (http://192.168.1.50:11434): 4: User
      Click "Save & Connect": 5: User
      Verify Dynamic Model Listing: 5: User, AgentDroid
    section Execution
      Navigate to Command Center: 5: User
      Execute first goal: 5: User, AgentDroid
```

### Steps:
1. User installs AgentDroid on Android device.
2. App opens on Home Dashboard; system status displays `No AI Provider Connected`.
3. User taps `Settings` in bottom navigation.
4. Taps `Enable` on Accessibility Automation card; Android Settings opens where user enables `AgentDroid Accessibility Service`.
5. Taps `Add Provider` in AI Providers card, toggles to `LOCAL / LAN SERVERS`, and taps `Ollama Local Daemon`.
6. Replaces default `10.0.2.2` with their PC's LAN IP (`http://192.168.1.50:11434`).
7. Taps `Save & Connect`. AgentDroid calls `GET /api/tags`, discovers `llama3.2:latest`, marks status `CONNECTED`, and populates local model catalog.

---

## Journey 2: Complex Multi-Agent Goal with High-Risk Approval

### Context:
User commands: *"Research top three Android AI security practices, draft an executive brief, and prepare an email to team@company.com with the brief."*

```mermaid
flowchart TD
    A[User speaks command in Command Center] --> B[Master Agent decomposes into 3 tasks]
    B --> C[Task 1: Research Agent searches security practices - LOW Risk]
    C --> D[Task 2: Content Agent drafts executive brief - LOW Risk]
    D --> E[Task 3: Communication Agent prepares email to team - HIGH Risk]
    E --> F{Requires Human Approval?}
    F -->|Yes| G[Approval Dialog surfaced to User]
    G --> H[User reviews email draft and recipient]
    H -->|Click Approve| I[ActionDispatcher sends email intent]
    H -->|Click Reject| J[Task cancelled without email sent]
    I --> K[Master Agent compiles final report]
    J --> K
    K --> L[Dashboard displays complete execution summary]
```

### Steps:
1. User enters command in Command Center.
2. Master Agent queries model, breaks goal into:
   * Task 1 (`RESEARCH`): "Analyze top Android AI security guidelines" (Risk: `LOW`)
   * Task 2 (`CONTENT_CREATION`): "Synthesize research into executive brief" (Risk: `LOW`)
   * Task 3 (`COMMUNICATION`): "Send email to team@company.com with brief" (Risk: `HIGH`, depends on Task 2)
3. Task 1 and Task 2 execute autonomously; progress indicators update live.
4. Task 3 detects `HIGH` risk level. Orchestrator suspends execution and alerts user via dialog and notification.
5. User reviews email recipient and body, then taps `Approve`.
6. ActionDispatcher launches email intent; Master Agent synthesizes final report.
