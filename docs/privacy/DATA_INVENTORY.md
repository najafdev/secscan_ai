---
title: Data Inventory
purpose: Comprehensive classification of all data types processed, stored, or transmitted
scope: Room database entities, preferences, memory tiers, and network payloads
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/privacy/DATA_COLLECTION.md
  - docs/architecture/DATABASE_SCHEMA.md
---

# Data Inventory

## Data Element Classification

| Data Category | Specific Elements | Storage Location | Sensitivity | Egress Destination |
| :--- | :--- | :--- | :--- | :--- |
| **API Credentials** | API keys, Bearer tokens, custom headers | Android Keystore (`EncryptedSharedPreferences`) | Critical | Sent in Authorization headers to configured provider |
| **User Prompts** | Natural language commands, voice input text | Room DB (`conversations`, `messages`) | High | Sent to configured AI provider for inference |
| **Task Outputs** | Agent subtask summaries, intermediate JSON | Room DB (`tasks`, `SharedTaskContext`) | Medium | Kept on device; synthesized in final report |
| **On-Screen Content** | Visible text, package names, view IDs | Ephemeral memory (`StateVerifier`) | High | Evaluated locally; passed to model if context requested |
| **Context Memory** | Preferences, workflow records, access counts | Room DB (`memory_records`) | Medium | Filtered and injected into agent system prompt |
| **Activity Logs** | Action type, timestamp, risk level, status | Room DB (`activity_logs`) | Low / Medium | Kept strictly on device |
| **Connected Accounts**| Platform usernames, account IDs | Room DB (`connected_accounts`) | Medium | Used locally to configure social workflows |
| **Automation Workflows**| Cron triggers, workflow steps, parameters | Room DB (`workflows`, `workflow_steps`) | Medium | Kept strictly on device |
