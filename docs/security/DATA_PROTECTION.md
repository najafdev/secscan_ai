---
title: Data Protection
purpose: Architectural controls governing data at rest, data in transit, and data in memory
scope: Storage encryption, network cipher suites, and memory lifecycle
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/security/SECURE_STORAGE.md
  - docs/privacy/PRIVACY_OVERVIEW.md
---

# Data Protection

## Data State Protection Matrix

| Data State | Classification | Security Control Enforced |
| :--- | :--- | :--- |
| **Data at Rest (Credentials)** | Critical | Android Keystore `MasterKey` AES-256 SIV (keys) & AES-256 GCM (values). |
| **Data at Rest (Relational DB)**| Sensitive / Personal | Stored in private app sandbox (`/data/data/com.agentdroid.app/databases/agentdroid.db`). Android sandbox permissions (`0600`) restrict access to application UID. |
| **Data in Transit (Cloud AI)** | Sensitive / External | Enforced TLS 1.2+ encryption using system trust anchors. Cleartext HTTP strictly blocked. |
| **Data in Transit (Local LAN)** | Local Network | Cleartext HTTP permitted only for private subnets (`127.0.0.1`, `10.0.2.2`, `192.168.0.0/16`, `10.0.0.0/8`, `172.16.0.0/12`). |
| **Data in Memory (Ephemeral)** | Transient | Context variables held in scoped coroutine memory; garbage-collected when execution job finishes. |

---

## Zero-Knowledge Architecture for Developers

1. **No Developer Telemetry**: The AgentDroid project does not operate an analytics or crash ingestion server.
2. **Direct Point-to-Point Communication**: API calls travel directly from the user's Android device to the user's configured provider (e.g., OpenAI, Google, Anthropic, or local Ollama). There are no intermediate proxy servers operated by AgentDroid maintainers.
3. **Hardware Isolation**: API keys cannot be read by another Android application unless the underlying Android OS is compromised by root escalation.
