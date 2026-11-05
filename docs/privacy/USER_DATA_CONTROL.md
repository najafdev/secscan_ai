---
title: User Data Control & Sovereign Rights
purpose: Details user sovereign controls, data export, tier purging, and GDPR/DPDP rights
scope: Client data management controls
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/privacy/DATA_RETENTION.md
  - docs/legal/PRIVACY_POLICY.md
---

# User Data Control & Sovereign Rights

## Sovereign Privacy Controls in AgentDroid

AgentDroid provides native, granular controls empowering users to govern their data:

```mermaid
graph TD
    User([User]) --> ControlPanel[Settings Dashboard]
    
    ControlPanel --> C1[1. Purge Context Memory Tiers: Working / Short / Long / Episodic / Procedural]
    ControlPanel --> C2[2. Delete Stored Keystore API Keys & Custom Headers]
    ControlPanel --> C3[3. Enable / Disable Accessibility Automation Service]
    ControlPanel --> C4[4. Clear Relational SQLite Database & Activity Logs]
    ControlPanel --> C5[5. Switch Active Model to Local LAN Ollama Server]
```

---

## Alignment with Global Privacy Frameworks

### 1. Indian Digital Personal Data Protection Act (DPDPA 2023)
* **Right to Access & Rectify**: Users can view all memory records, discovered models, and execution logs directly in the app UI.
* **Right to Erasure**: Instantaneous single-tap memory purging permanently deletes records from local SQLite storage.
* **Consent Architecture**: Clear affirmative action required when enabling Accessibility Services or adding API keys.

### 2. General Data Protection Regulation (GDPR)
* **Data Minimization (Art. 5(1)(c))**: AgentDroid stores only data strictly required for task execution.
* **Integrity & Confidentiality (Art. 5(1)(f))**: Hardware Keystore AES-256 GCM encryption.
* **Right to Erasure / "To be Forgotten" (Art. 17)**: Users hold physical possession of all data on their device and can wipe records at will.
