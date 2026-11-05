---
title: Installation Guide
purpose: Step-by-step instructions for installing AgentDroid via APK or building from source
scope: Android 8.0+ devices, emulators, and build environments
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/user-guide/FIRST_TIME_SETUP.md
  - docs/developer/DEVELOPMENT_SETUP.md
---

# Installation Guide

## System Requirements

* **Operating System**: Android 8.0 Oreo (API level 26) or higher (Android 14 API 34 supported).
* **Architecture**: `arm64-v8a`, `armeabi-v7a`, `x86_64` (emulator).
* **RAM**: Minimum 3 GB RAM (4 GB+ recommended for heavy multi-agent workflows).
* **Storage**: Approximately 35 MB for installation + local database.

---

## Method 1: Sideloading the Release APK

1. Download the latest `app-debug.apk` or `app-release.apk` from the GitHub Releases tab.
2. Transfer the APK file to your Android device via USB, Google Drive, or direct download.
3. Open your Android device's file manager and tap the downloaded APK.
4. If prompted with *"For your security, your phone is not allowed to install unknown apps from this source"*, tap **Settings** and toggle **Allow from this source**.
5. Tap **Install**, then tap **Open** when finished.

---

## Method 2: Building from Source via Gradle

If you are a developer with Android Studio or the command line:

```bash
# Clone the repository
git clone https://github.com/[PROJECT_OWNER]/agentdroid.git
cd agentdroid

# Build the debug APK
./gradlew assembleDebug

# Install directly to a connected device or emulator via adb
adb install -r app/build/outputs/apk/debug/app-debug.apk
```
