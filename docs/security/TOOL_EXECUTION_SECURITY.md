---
title: Tool Execution Security
purpose: Security boundaries, sandboxing, and execution constraints for agent tools
scope: ActionDispatcher, tool parameters, and execution validation
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/security/PROMPT_INJECTION_DEFENSE.md
  - docs/architecture/ANDROID_INTEGRATION.md
---

# Tool Execution Security

## Execution Boundary Specifications

All agent tools in AgentDroid execute via the centralized `ActionDispatcher` (`com.agentdroid.app.automation.action`):

```mermaid
graph TD
    Agent[Agent Requests Tool Execution] --> PreCheck[1. Emergency Killswitch Check]
    PreCheck --> RiskCheck[2. Risk Level Evaluation: Low / Med / High]
    
    RiskCheck -->|High Risk| Gate[Human Approval Queue]
    Gate -->|Approved| ParamCheck[3. Parameter Validation & Sanitization]
    RiskCheck -->|Low / Med| ParamCheck
    
    ParamCheck --> Dispatch[4. Sandboxed System Call]
    Dispatch --> PostVerify[5. StateVerifier Post-Execution Audit]
    PostVerify --> Log[6. ActivityLogDao Audit Log]
```

---

## Tool Security Parameters & Validations

| Action Type | Security Constraints & Parameter Sanitization |
| :--- | :--- |
| `OPEN_APP` | Package name must be non-blank and resolve via `PackageManager.getLaunchIntentForPackage()`. Arbitrary intents are rejected. |
| `OPEN_URL` | URL is validated by `NetworkSecurityValidator`. Supported schemes restricted to `http` and `https`. Schemes like `file:`, `javascript:`, `content:` are rejected. |
| `CLICK_ELEMENT` | Coordinates or node IDs must belong to the active foreground application window. Clicks cannot cross secure overlay windows (e.g., system password fields). |
| `TYPE_TEXT` | Target node must accept text input (`isEditable = true`). Keylogging protections enforced by system IME. |
| `CREATE_FILE` | Writes restricted to scoped app directories (`getExternalFilesDir()`). Path traversal sequences (`../`) are stripped. |
| `DELETE_FILE` | Strictly classified as `RiskLevel.HIGH`. Absolute path verified; system partitions (`/system`, `/data`) cannot be targeted. |
| `SEND_EMAIL` | Strictly classified as `RiskLevel.HIGH`. Dispatches standard Android Intent chooser; cannot send silent background emails without user interaction. |
| `POST_SOCIAL` | Strictly classified as `RiskLevel.HIGH`. Generates pending draft; external API broadcast requires explicit approval. |
