---
title: Device & Platform Compatibility Matrix
purpose: Detailed hardware, Android OS, and architecture compatibility requirements
scope: Supported Android API levels, CPU architectures, and OEM skin considerations
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/release/CHANGELOG.md
  - docs/user-guide/INSTALLATION.md
---

# Device & Platform Compatibility Matrix

This document defines the supported operating systems, hardware platforms, and device requirements for AgentDroid.

---

## 1. Operating System Compatibility

| Android Version | API Level | Status | Notes |
|---|---|---|---|
| **Android 14** | API 34 | Fully Supported | Primary target platform. Restricted Settings override required for sideloaded accessibility. |
| **Android 13** | API 33 | Fully Supported | Notification permission runtime prompt enforced. |
| **Android 12 / 12L** | API 31 / 32 | Fully Supported | Splash screen API and Material 3 dynamic theming. |
| **Android 11** | API 30 | Fully Supported | Scoped storage enforcement. |
| **Android 10** | API 29 | Fully Supported | Dark mode native theme syncing. |
| **Android 9.0 Pie** | API 28 | Supported | Biometric prompt compatibility. |
| **Android 8.0 / 8.1 Oreo** | API 26 / 27 | Minimum Supported | Minimum SDK requirement (`minSdk = 26`). Background execution limits apply. |

---

## 2. Hardware & Architecture Support

* **ABIs**:
  * `arm64-v8a`: Supported (standard 64-bit Android smartphones).
  * `armeabi-v7a`: Supported (32-bit legacy devices).
  * `x86_64`: Supported (Android Virtual Devices / emulators, ChromeOS).
* **RAM Requirements**: Minimum 3 GB RAM; 6 GB+ recommended when orchestrating multi-agent DAGs with concurrent network streams.
* **Storage**: Minimum 100 MB free internal flash storage for app binary and Room database.

---

## Related Documentation
* [Installation Guide](file:///workspaces/agentdroid-/docs/user-guide/INSTALLATION.md)
* [System Changelog](file:///workspaces/agentdroid-/docs/release/CHANGELOG.md)
