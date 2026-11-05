---
title: Development Environment Setup
purpose: Step-by-step instructions for configuring an Android development environment for AgentDroid
scope: Tooling, JDK, Android SDK, emulators, and local Ollama mock environments
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/developer/DEVELOPER_GUIDE.md
  - docs/developer/BUILD_AND_RELEASE.md
  - docs/user-guide/OLLAMA_SETUP.md
---

# Development Environment Setup

Follow these instructions to configure your workstation to build, test, and debug AgentDroid.

---

## 1. Prerequisites & Tooling

* **Operating System**: Linux (Ubuntu 20.04+ / Debian 11+), macOS (12+), or Windows 11 with WSL2.
* **JDK**: **Java 17 OpenJDK** (e.g., Eclipse Temurin or OpenLogic).
* **Android Studio**: Android Studio Hedgehog (2023.1.1) or newer (Iguana / Jellyfish recommended).
* **Android SDK**:
  * Compile SDK: `34` (Android 14)
  * Target SDK: `34`
  * Minimum SDK: `26` (Android 8.0 Oreo)
  * Build Tools: `34.0.0`
  * Android SDK Command-line Tools & CMake (optional).

---

## 2. Cloning & Initial Build

Clone the repository and verify Gradle wrapper execution:

```bash
git clone https://github.com/agentdroid/agentdroid.git
cd agentdroid
chmod +x gradlew

# Run test suite
./gradlew testDebugUnitTest

# Assemble debug binary
./gradlew assembleDebug
```

The compiled APK will be generated at:
`app/build/outputs/apk/debug/app-debug.apk`

---

## 3. Emulator Configuration

When testing with Android Virtual Devices (AVD):
1. Create a Pixel 7 / Pixel 8 emulator running **API 34 (Android 14, Google APIs)**.
2. Allocate at least 4GB of RAM to the emulator.
3. **Connecting to Local Host Services**:
   * Android emulators map the host workstation's loopback interface (`localhost`) to `10.0.2.2`.
   * To connect to Ollama running on your workstation from the emulator, configure provider endpoint as:
     `http://10.0.2.2:11434`

---

## 4. Environment Variables

Create a local `.env` or set shell variables for integration tests (optional):
```bash
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="AIzaSy..."
export OLLAMA_HOST="http://localhost:11434"
```

---

## Related Documentation
* [Developer Guide](file:///workspaces/hacknova/docs/developer/DEVELOPER_GUIDE.md)
* [Build and Release](file:///workspaces/hacknova/docs/developer/BUILD_AND_RELEASE.md)
* [Ollama Setup](file:///workspaces/hacknova/docs/user-guide/OLLAMA_SETUP.md)
