---
title: Privacy Impact Assessment (PIA)
purpose: Formal Privacy Impact Assessment evaluating processing risks, mitigations, and compliance
scope: AgentDroid client features, accessibility monitoring, and AI inference
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/privacy/PRIVACY_OVERVIEW.md
  - docs/security/DATA_PROTECTION.md
---

# Privacy Impact Assessment (PIA)

## Risk Assessment Matrix

| Processing Activity | Privacy Risk Identified | Initial Risk | Architectural Mitigation | Residual Risk |
| :--- | :--- | :--- | :--- | :--- |
| **Accessibility Screen Inspection** | Inspection of sensitive on-screen content (passwords, banking interfaces). | **HIGH** | Accessibility service ignores secure password view types; screen inspection occurs only during user-initiated automation; no continuous recording. | **LOW** |
| **Cloud AI Prompt Transmission** | User accidentally pastes confidential text into Command Bar sent to cloud LLM. | **MEDIUM** | Clear visual indicators of active provider; first-class support for local LAN Ollama models keeping all inference on-premise. | **LOW** |
| **Local SQLite Data Storage** | Unauthorized extraction of memory records from device storage. | **MEDIUM** | Android sandbox application UID isolation (`0600` permissions); credentials stored separately in Keystore. | **LOW** |
| **Automated Social Media Drafts** | AI posts unintended content directly to public social networks. | **HIGH** | `RiskLevel.HIGH` classification mandates explicit Human-in-the-Loop user approval before any post is published. | **VERY LOW** |

---

## Conclusion of Privacy Assessment

AgentDroid's local-first architecture, absence of tracking telemetry, hardware-backed Keystore encryption, and native support for offline/local LLMs render it significantly more privacy-protective than standard commercial AI assistants. Residual risks are managed through mandatory human approval gates and granular user data controls.
