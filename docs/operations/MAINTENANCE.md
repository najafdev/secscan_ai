---
title: System Maintenance & Lifecycle Operations
purpose: Routine maintenance guidelines for cache management, model catalog refresh, and updates
scope: Scheduled WorkManager tasks, VACUUM optimizations, and model registry syncing
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/operations/PERFORMANCE.md
  - docs/operations/LOGGING_AND_MONITORING.md
  - docs/architecture/DATABASE_SCHEMA.md
---

# System Maintenance & Lifecycle Operations

To maintain high performance and low storage overhead, AgentDroid performs automated background maintenance and provides manual cleanup controls.

---

## 1. Automated Background Tasks (WorkManager)

AgentDroid registers periodic background maintenance jobs via `androidx.work:work-runtime-ktx`:

* **Log Pruning (`NightlyCleanupWorker`)**:
  * Runs once every 24 hours when the device is idle and charging.
  * Deletes audit log entries older than 30 days.
  * Prunes temporary task artifacts and cached screenshots.
* **Database Compaction**:
  * Runs SQLite `PRAGMA wal_checkpoint(TRUNCATE)` and periodic `VACUUM` to reclaim disk space after large deletions.

---

## 2. Model Catalog Refresh Procedure

Cloud and local LLMs evolve frequently. To refresh the model catalog:
1. Open **Settings → AI Providers**.
2. Tap the **Refresh** icon in the top right or the **Fetch Models** button on any provider card.
3. `ModelDiscoveryService` sends discovery probes to cloud endpoints and local Ollama/LM Studio servers, updating the `discovered_models` table with active models.

---

## 3. Manual Maintenance Controls

Users can trigger maintenance actions directly from the **Settings** screen:
* **Clear Image & Web Cache**: Frees temporary browser artifacts and screenshot bitmaps.
* **Prune Task Logs**: Immediately removes completed workflow run records.
* **Verify Provider Health**: Pings all active providers and measures endpoint roundtrip latency.

---

## Related Documentation
* [Performance Tuning](file:///workspaces/hacknova/docs/operations/PERFORMANCE.md)
* [Logging and Monitoring](file:///workspaces/hacknova/docs/operations/LOGGING_AND_MONITORING.md)
* [Database Schema](file:///workspaces/hacknova/docs/architecture/DATABASE_SCHEMA.md)
