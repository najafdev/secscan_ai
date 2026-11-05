---
title: Data Retention & Deletion Policy
purpose: Retention periods, lifecycle management, and user-initiated deletion mechanisms
scope: Room database, Keystore, and file system storage
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/privacy/USER_DATA_CONTROL.md
  - docs/legal/PRIVACY_POLICY.md
---

# Data Retention & Deletion Policy

## Default Retention Schedules

All data created within AgentDroid resides locally on your Android device.

| Data Type | Retention Schedule | Deletion Mechanism |
| :--- | :--- | :--- |
| **Working Memory** | Ephemeral: Discarded upon task completion | Automated by coroutine garbage collection |
| **Short-Term Memory** | Session: Cleared when plan completes or app closes | Automated / User Reset |
| **Long-Term Memory** | Retained until user reset | Settings $\rightarrow$ Multi-Tier Context Memory $\rightarrow$ Reset |
| **Episodic & Procedural**| Retained until user reset | Settings $\rightarrow$ Multi-Tier Context Memory $\rightarrow$ Reset |
| **Activity Logs** | Rolling retention (latest 100 entries in DB) | Auto-capped / Settings $\rightarrow$ Purge Logs |
| **API Keys** | Retained until user edits or deletes provider | Settings $\rightarrow$ Remove Provider / Delete Key |
| **Conversations** | Retained indefinitely in local SQLite DB | App Data Clear / Settings $\rightarrow$ Reset History |

---

## Complete Data Deletion Mechanisms

Users have three instantaneous methods to completely purge all data:
1. **Granular Memory Reset**: In **Settings $\rightarrow$ Multi-Tier Context Memory**, tap **Reset** next to any specific tier, or tap **Purge All** to wipe all memory records immediately.
2. **Provider Key Deletion**: In **Settings $\rightarrow$ AI Providers**, tap **Delete** on any provider to immediately wipe the API key from Android Keystore.
3. **Total Application Reset**: Android **Settings $\rightarrow$ Apps $\rightarrow$ AgentDroid $\rightarrow$ Storage $\rightarrow$ Clear Data** completely destroys the local SQLite database, Keystore ciphertext, and all internal files.
