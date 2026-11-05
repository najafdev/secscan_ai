---
title: Model Routing & Capability Validation
purpose: Details per-agent model resolution, fallback strategies, and capability matching
scope: AiModelRouter and capability validation rules
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/architecture/AI_PROVIDER_ARCHITECTURE.md
  - docs/product/FEATURE_SPECIFICATION.md
---

# Model Routing & Capability Validation

## Model Resolution Strategy

When an agent requests an AI provider instance, `AiConnectionManager.validateAndGetProvider(role)` resolves the target model through a prioritized three-step fallback hierarchy:

```mermaid
flowchart TD
    Req[Agent Requests Provider: e.g. Phone Control] --> S1{Agent-Specific Config Exists in DB?}
    S1 -->|Yes| P1[Use Specific Model Config: e.g. Ollama llama3.2]
    S1 -->|No| S2{GLOBAL_DEFAULT Config Exists in DB?}
    S2 -->|Yes| P2[Use Global Default Model Config]
    S2 -->|No| S3{Master Agent Config Exists?}
    S3 -->|Yes| P3[Use Master Agent Model Config: e.g. GPT-4o]
    S3 -->|No| Err[Throw AiError: AI_NOT_CONFIGURED]
    
    P1 --> CapCheck[Validate Model Capabilities]
    P2 --> CapCheck
    P3 --> CapCheck
    
    CapCheck -->|All Capabilities Present| Run[Instantiate HttpAiProvider with activeModel]
    CapCheck -->|Missing Required Capabilities| CapErr[Throw AiError: ERR_CAPABILITY_MISMATCH]
```

---

## Agent Capability Matching Rules

Agent roles require distinct capability sets defined in `com.agentdroid.app.domain.model.ModelCapability`:

| Agent Role | Required Model Capabilities | Failure Consequence if Missing |
| :--- | :--- | :--- |
| **`MASTER`** | `TEXT_GENERATION`, `STRUCTURED_OUTPUT`, `REASONING` | Cannot output valid JSON subtask arrays; goal decomposition fails. |
| **`PHONE_CONTROL`**| `TEXT_GENERATION`, `TOOL_CALLING`, `REASONING` | Cannot map UI accessibility node IDs to action gestures. |
| **`RESEARCH`** | `TEXT_GENERATION`, `TOOL_CALLING` | Cannot invoke search tools or structured intelligence extractors. |
| **`CONTENT_CREATION`**| `TEXT_GENERATION` | Basic text models permitted; high creativity and tone adherence required. |
| **`SOCIAL_MEDIA`**| `TEXT_GENERATION`, `STRUCTURED_OUTPUT` | Cannot format multi-platform JSON metadata and post scheduling dates. |
| **`SECURITY`** | `TEXT_GENERATION`, `REASONING` | Cannot perform deep AST and Android permission security audits. |

If a user assigns a model lacking required capabilities, `AiConnectionManager` rejects execution with an actionable error:
> *"Model 'basic-text' lacks required capabilities for Phone Control Agent: Tool Calling. Select a model supporting Tool Calling in Settings $\rightarrow$ Model Picker."*
