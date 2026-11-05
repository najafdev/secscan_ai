---
title: Database Development & Room Schema Guide
purpose: Engineering documentation for the local Room SQLite persistence layer
scope: Room schema v2, entity relationships, DAO conventions, and migration rules
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/architecture/DATABASE_SCHEMA.md
  - docs/developer/TESTING_GUIDE.md
---

# Database Development & Room Schema Guide

AgentDroid persists configuration, agent status, conversation threads, workflow definitions, and audit logs using an on-device SQLite database managed by **AndroidX Room 2.6.1**.

---

## 1. Database Configuration

The database class is defined in:
`app/src/main/java/com/agentdroid/app/data/local/AgentDroidDatabase.kt`

* **Current Schema Version**: `2`
* **Entities**: 17 tables (`agents`, `workflows`, `workflow_executions`, `chat_sessions`, `chat_messages`, `context_memory`, `discovered_models`, `activity_logs`, `approval_requests`, `system_metrics`, etc.).
* **KSP Annotation Processor**: Uses Kotlin Symbol Processing (`com.google.devtools.ksp`).

---

## 2. Writing Entities & DAOs

When adding or updating tables:
1. Define primary keys explicitly using `@PrimaryKey(autoGenerate = ...)` or UUID strings.
2. Use `@ColumnInfo(name = "snake_case_name")` for SQL column alignment.
3. Return `Flow<T>` from DAOs for reactive observation in ViewModels:

```kotlin
@Dao
interface WorkflowDao {
    @Query("SELECT * FROM workflows WHERE is_active = 1 ORDER BY updated_at DESC")
    fun getActiveWorkflows(): Flow<List<WorkflowEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertWorkflow(workflow: WorkflowEntity)

    @Delete
    suspend fun deleteWorkflow(workflow: WorkflowEntity)
}
```

---

## 3. Schema Migrations

* **Automated & Manual Migrations**: In production builds, define explicit `Migration` objects (e.g., `MIGRATION_1_2`) when altering columns or indexes.
* **Testing Migrations**: Write Room migration verification tests using `androidx.room:room-testing` to ensure user data survives upgrades without data loss.

---

## Related Documentation
* [Database Schema Specification](file:///workspaces/hacknova/docs/architecture/DATABASE_SCHEMA.md)
* [Testing Guide](file:///workspaces/hacknova/docs/developer/TESTING_GUIDE.md)
