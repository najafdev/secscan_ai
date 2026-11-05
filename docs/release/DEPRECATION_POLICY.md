---
title: API & Feature Deprecation Policy
purpose: Formal timeline and procedures for retiring legacy APIs, database tables, and features
scope: Public interfaces, Room migrations, and deprecated agent roles
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/release/VERSIONING.md
  - docs/developer/CODING_STANDARDS.md
---

# API & Feature Deprecation Policy

To maintain agility while ensuring stability for extensions and workflows, AgentDroid enforces a structured deprecation lifecycle.

---

## 1. Deprecation Lifecycle

```mermaid
flowchart LR
    Active[Active Feature / API] --> Deprecated[Deprecated: @Deprecated Annotation]
    Deprecated --> GracePeriod[Grace Period: Minimum 1 Minor Release]
    GracePeriod --> Removal[Removal in Next Major Release]
```

1. **Announcement**: The element is annotated with `@Deprecated` in Kotlin, specifying the `message` and replacement element.
2. **Grace Period**: The deprecated element remains functional for at least **one full minor release cycle** (e.g., deprecated in v1.1.0, retained in v1.2.0).
3. **Removal**: The element is removed in the next major version (e.g., v2.0.0).

---

## 2. Room Database Schema Deprecations

* Table columns marked for deprecation are retained as nullable until the subsequent major schema migration.
* Room migrations must never drop user data silently without providing an automated export or transformation path.

---

## Related Documentation
* [Software Versioning Policy](file:///workspaces/agentdroid-/docs/release/VERSIONING.md)
* [Coding Standards](file:///workspaces/agentdroid-/docs/developer/CODING_STANDARDS.md)
