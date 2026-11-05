---
title: Build, Packaging & Release Pipeline
purpose: Procedures for compiling, optimizing, signing, and packaging release binaries
scope: Gradle tasks, R8 / ProGuard shrinkage, keystore signing, and APK / AAB artifacts
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/developer/DEVELOPMENT_SETUP.md
  - docs/release/VERSIONING.md
---

# Build, Packaging & Release Pipeline

This document details the build targets, optimization settings, and packaging procedures for AgentDroid.

---

## 1. Gradle Build Targets

AgentDroid uses standard Android Gradle Plugin (AGP) tasks:

| Command | Output Artifact | Purpose |
|---|---|---|
| `./gradlew assembleDebug` | `app-debug.apk` | Unminified binary for local development and debugging. |
| `./gradlew assembleRelease` | `app-release-unsigned.apk` | Minified production APK. |
| `./gradlew bundleRelease` | `app-release.aab` | Android App Bundle optimized for Google Play distribution. |
| `./gradlew testDebugUnitTest` | Test Reports HTML | Unit and component verification suite. |

---

## 2. R8 ProGuard Configuration

Release builds utilize R8 code shrinking and optimization. The configuration is maintained in `app/proguard-rules.pro`:
* Preserves Kotlin Coroutines and Serialization reflection descriptors.
* Preserves Room Database entity classes and DAOs.
* Retains OkHttp and Conscrypt network provider classes.

Verify minification integrity prior to tag publishing:
```bash
./gradlew check
./gradlew assembleRelease
```

---

## 3. Release Signing Protocol

Release binaries must be signed with a production keystore:

```bash
# Example apksigner invocation
apksigner sign --ks release-keystore.jks \
  --ks-key-alias agentdroid-release \
  --out app-release-signed.apk \
  app/build/outputs/apk/release/app-release-unsigned.apk
```

Environment variables for automated CI/CD signing:
* `KEYSTORE_BASE64`
* `KEYSTORE_PASSWORD`
* `KEY_ALIAS`
* `KEY_PASSWORD`

---

## Related Documentation
* [Development Setup](file:///workspaces/agentdroid-/docs/developer/DEVELOPMENT_SETUP.md)
* [Versioning Policy](file:///workspaces/agentdroid-/docs/release/VERSIONING.md)
