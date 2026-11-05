---
title: Security Overview
purpose: Comprehensive overview of the AgentDroid defense-in-depth security architecture
scope: Application security, credential handling, automation boundaries, and threat mitigation
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/security/SECURITY_REQUIREMENTS.md
  - docs/security/THREAT_MODEL.md
  - docs/security/CREDENTIAL_MANAGEMENT.md
---

# Security Overview

## Defense-in-Depth Security Model

AgentDroid operates on a multi-layered defense-in-depth security model designed specifically for autonomous agentic systems running on mobile operating systems:

```mermaid
graph TD
    subgraph Layer_1 [Layer 1: Cryptographic Perimeter]
        Keystore[Android Keystore AES-256 GCM Hardware MasterKey]
        EncryptedPrefs[EncryptedSharedPreferences]
        NetSecConfig[Network Security Config: TLS Enforcement]
    end

    subgraph Layer_2 [Layer 2: AI Input / Output Sanitization]
        Sanitizer[AiError Token Sanitizer: Bearer Redaction]
        PromptShield[Structured Output JSON Validation]
        CapValidator[Model Capability & Role Validator]
    end

    subgraph Layer_3 [Layer 3: Autonomous Governance & Life-Safety]
        RiskEngine[Risk Level Engine: LOW / MEDIUM / HIGH]
        HumanApproval[Human-in-the-Loop Approval Queue]
        Killswitch[Emergency Killswitch Persistent Service]
    end

    subgraph Layer_4 [Layer 4: Android Platform Sandboxing]
        AccService[Guarded Accessibility Service Traversal]
        SafStorage[Scoped Storage & Storage Access Framework]
        PkgQuery[QUERY_ALL_PACKAGES Explicit Resolution]
    end

    Layer_1 --> Layer_2
    Layer_2 --> Layer_3
    Layer_3 --> Layer_4
```

---

## Core Security Commitments

1. **Hardware-Backed Cryptography**: API keys, bearer tokens, and custom inference headers are encrypted using Android Keystore `MasterKey` with AES-256 GCM encryption.
2. **Zero Plaintext Token Logging**: The unified error engine (`AiError.sanitize`) automatically strips Bearer tokens, query parameters, and private URLs before any technical detail is rendered in UI or recorded in activity logs.
3. **No Unrestricted Cleartext HTTP**: Cleartext HTTP traffic is rejected at runtime by `NetworkSecurityValidator` unless the destination resolves to a verified local/private IP address (e.g., `127.0.0.1`, `10.0.2.2`, `192.168.0.0/16`).
4. **Human-in-the-Loop Governance**: Any autonomous action that mutates external state (sending emails, publishing social posts, deleting files, executing financial transactions) is halted until explicit user confirmation is received.
5. **Instantaneous Killswitch**: An independent killswitch halts all agent coroutines and UI gesture dispatching within milliseconds upon user activation from the persistent status bar notification.
