---
title: Operational Backup & Restore Procedures
purpose: Standard operating procedures for backing up, exporting, and restoring AgentDroid data
scope: Room database exports, workflow migrations, Keystore key handling, and user data archives
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/operations/DISASTER_RECOVERY.md
  - docs/architecture/DATABASE_SCHEMA.md
  - docs/security/SECURE_STORAGE.md
---

# Operational Backup & Restore Procedures

This document outlines procedures for safely backing up and restoring user configurations, workflow definitions, and conversation histories in AgentDroid.

---

## 1. What Can and Cannot Be Backed Up

| Data Asset | Location | Backup Strategy | Hardware Tied? |
|---|---|---|---|
| **Workflow Definitions** | Room SQLite (`workflows`) | Exportable as JSON bundle | No |
| **Agent Configurations** | Room SQLite (`agents`) | Exportable as JSON bundle | No |
| **Conversation Threads** | Room SQLite (`chat_sessions`) | SQLite file or JSON export | No |
| **Encrypted API Keys** | `EncryptedSharedPreferences` | Android Keystore AES-256 | **Yes (Cannot be ported across devices)** |

> [!WARNING]
> Because encryption keys are tied to the device's hardware Secure Element (StrongBox or TEE), raw backups of `EncryptedSharedPreferences` cannot be restored onto a different physical device. API keys must be re-entered upon restoring onto a new device.

---

## 2. Manual Backup Procedure

### Exporting Database via ADB (Development / Power User)
```bash
# Force Room SQLite WAL checkpointing
adb shell am broadcast -a com.agentdroid.app.CHECKPOINT_DB

# Pull database file
adb backup -f agentdroid_backup.ab -noapk com.agentdroid.app
```

---

## 3. Restoration Procedure

1. Install the target version of AgentDroid on the destination device.
2. Complete first-time launch to initialize the Room schema and generate device-specific Keystore keys.
3. Import workflow definitions via the Workflow Center JSON import.
4. Open **Settings → AI Providers** and re-enter credentials for chosen AI backends.

---

## Related Documentation
* [Disaster Recovery](file:///workspaces/agentdroid-/docs/operations/DISASTER_RECOVERY.md)
* [Database Schema](file:///workspaces/agentdroid-/docs/architecture/DATABASE_SCHEMA.md)
* [Secure Storage](file:///workspaces/agentdroid-/docs/security/SECURE_STORAGE.md)
