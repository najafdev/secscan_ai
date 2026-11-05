---
title: Release Notes Template & Publication Guide
purpose: Standardized template for authoring and distributing release announcements
scope: Release maintainers, marketing, and community distribution
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/release/CHANGELOG.md
  - docs/release/VERSIONING.md
---

# Release Notes Template & Publication Guide

Use this standardized markdown template when drafting release notes for GitHub Releases, community announcements, and Google Play Store update descriptions.

---

## 1. Release Notes Template

```markdown
# AgentDroid v[VERSION] — [CATCHY THEME TITLE]

**Release Date:** [YYYY-MM-DD]
**Target APK SHA-256:** `[CHECKSUM_HASH]`

### Highlights & Major Capabilities
* **[Feature Name]**: Brief explanation of the breakthrough.
* **[Improvement Name]**: Description of UX or performance gains.

### New Features & Enhancements
* Added `[Action / Agent Name]` to the fleet.
* Introduced dynamic discovery for `[Provider Name]`.

### Bug Fixes & Stability
* Resolved issue where `[Bug description]` caused `[Symptom]`.
* Fixed back-stack navigation handling when switching destinations.

### Security & Privacy Updates
* Upgraded credential storage to enforce hardware-backed Keystore checks.

### Verification & Checksums
* Release APK: `app-release.apk`
* SHA-256 Checksum: `[HASH]`
```

---

## Related Documentation
* [System Changelog](file:///workspaces/hacknova/docs/release/CHANGELOG.md)
* [Software Versioning Policy](file:///workspaces/hacknova/docs/release/VERSIONING.md)
