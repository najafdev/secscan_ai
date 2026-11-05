---
title: Software Versioning Policy
purpose: Formal versioning schema, release tagging rules, and breaking change definitions
scope: Release numbering, Git tagging conventions, and API backward compatibility
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/release/CHANGELOG.md
  - docs/release/DEPRECATION_POLICY.md
---

# Software Versioning Policy

AgentDroid strictly adheres to **Semantic Versioning 2.0.0** (`MAJOR.MINOR.PATCH`).

---

## 1. Version Format

Versions are specified in the format `X.Y.Z`:
* **MAJOR (`X`)**: Incremented for breaking architectural changes, incompatible database migrations requiring data resets, or major permission shifts.
* **MINOR (`Y`)**: Incremented for new agent roles, newly supported AI providers, additional UI features, and backward-compatible enhancements.
* **PATCH (`Z`)**: Incremented for backward-compatible bug fixes, UI styling corrections, and security hotfixes.

---

## 2. Android Build Numbers

In `app/build.gradle.kts`:
* `versionName`: Matches the Semantic Version (e.g., `"1.0.0"`).
* `versionCode`: Monotonically increasing integer assigned sequentially with each published build.

---

## 3. Git Tagging Protocol

Releases are tagged on the `main` branch:
* Release tags: `v1.0.0`, `v1.0.1`, `v1.1.0`.
* Pre-release tags: `v1.1.0-rc.1`, `v1.1.0-beta.1`.

---

## Related Documentation
* [System Changelog](file:///workspaces/agentdroid-/docs/release/CHANGELOG.md)
* [Deprecation Policy](file:///workspaces/agentdroid-/docs/release/DEPRECATION_POLICY.md)
