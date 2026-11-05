---
title: Security Requirements
purpose: Formal security baseline, compliance guidelines, and verification criteria
scope: AgentDroid client security controls
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/security/SECURITY_OVERVIEW.md
  - docs/security/THREAT_MODEL.md
---

# Security Requirements

## Security Baseline Specifications

| Req ID | Control Area | Specification | Implementation Reference |
| :--- | :--- | :--- | :--- |
| **SEC-001** | Cryptographic Storage | API credentials must be encrypted using Android Keystore AES-256 SIV/GCM. Plaintext storage is prohibited. | `SecurePreferencesManager.kt` |
| **SEC-002** | Transport Security | Remote API communication must enforce TLS 1.2+. Cleartext HTTP is restricted to local RFC1918 subnets. | `network_security_config.xml`, `NetworkSecurityValidator.kt` |
| **SEC-003** | Token Sanitization | Log outputs and error messages must redact `Bearer` tokens, passwords, and API key query parameters. | `AiError.sanitize()` |
| **SEC-004** | Life-Safety Killswitch | The application must provide an emergency stop accessible from the notification shade that immediately halts automation. | `EmergencyKillswitch.kt`, `AutomationForegroundService.kt` |
| **SEC-005** | Human Approval Gate | High-risk destructive or external communication tasks must suspend execution until explicit user approval. | `ApprovalDao`, `AgentOrchestrator.kt` |
| **SEC-006** | Android Sandbox Isolation | Scoped storage must be enforced; file operations outside application sandbox require explicit user file picking. | `ActionDispatcher.kt` |
| **SEC-007** | Prompt Injection Defense | External web and screen content must be isolated from system prompt instructions using delimited context framing. | `MasterAgent.kt`, `SecurityAgent.kt` |
| **SEC-008** | Input Validation | All user URLs, hostnames, and ports must be validated prior to initiating OkHttp network requests. | `NetworkSecurityValidator.kt` |

---

## Verification Standards

AgentDroid's security baseline aligns with the following industry benchmarks:
* **OWASP Mobile Application Security Verification Standard (MASVS)**:
  * `MASVS-STORAGE`: Secure credential storage using Android Keystore.
  * `MASVS-CRYPTO`: Industry-standard AES-256 GCM encryption.
  * `MASVS-NETWORK`: TLS enforcement and cleartext gating.
* **OWASP Top 10 for Large Language Model Applications**:
  * `LLM01: Prompt Injection`: Input delimiters and human approval gates.
  * `LLM02: Sensitive Information Disclosure`: Automated token redaction.
  * `LLM06: Excessive Agency`: Risk level classification and execution boundaries.
  * `LLM08: Vector and Embedding Weaknesses`: Sovereign local storage of context memories.
