---
title: Privacy Settings User Guide
purpose: User guide for configuring privacy modes, local execution, and credential encryption
scope: User privacy controls, telemetry isolation, and credential security
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/privacy/PRIVACY_OVERVIEW.md
  - docs/security/CREDENTIAL_MANAGEMENT.md
  - docs/user-guide/MEMORY_MANAGEMENT.md
---

# Privacy Settings User Guide

AgentDroid is engineered with privacy as a foundational principle. The application does not include third-party tracking libraries, does not sell user data, and offers an air-gapped local AI mode.

---

## 1. Local-Only (Air-Gapped) Mode

If you require absolute data confidentiality (e.g., enterprise data, personal medical notes, or sensitive financial workflows):

1. Go to **Settings → AI Providers**.
2. Select **Ollama** or **Local LM Studio / vLLM**.
3. Enter your local private network endpoint (e.g., `http://192.168.1.50:11434` or `http://10.0.2.2:11434`).
4. Ensure all cloud providers (OpenAI, Gemini, Anthropic) are disabled or have no API keys stored.

When configured this way:
* **Zero bytes** leave your local Wi-Fi network.
* Prompts and responses travel solely between your phone and your private computer running the LLM.

---

## 2. Managing API Keys & Encrypted Storage

All API credentials entered into AgentDroid are secured using Android's hardware-backed **Keystore System**:
* Credentials are encrypted using **AES-256-GCM** via AndroidX `MasterKey` before touching disk.
* Decryption keys never leave the hardware secure element (TEE or StrongBox).
* **Viewing Keys**: You can tap the Eye icon in provider cards to reveal masked keys for verification.
* **Deleting Keys**: Tapping **Disconnect / Clear Key** wipes the encrypted key instantly from storage.

---

## 3. Telemetry & Analytics Isolation

AgentDroid contains **zero advertising SDKs** and **zero background marketing beacons**:
* No Google Analytics for Firebase.
* No Facebook/Meta Pixel or SDKs.
* All metrics visible in the **Activity** screen are stored strictly inside your phone's local SQLite database (`activity_logs` table).

---

## 4. Resetting Permissions & Revoking Access

To revoke system permissions granted to AgentDroid:
1. Open Android **Settings → Apps → AgentDroid → Permissions**.
2. Revoke permissions for **Notifications**, **Storage / Photos**, or **Microphone** as desired.
3. To disable UI automation, open Android **Settings → Accessibility → AgentDroid Assistant Service** and toggle off.

---

## Related Documentation
* [Privacy Overview](file:///workspaces/hacknova/docs/privacy/PRIVACY_OVERVIEW.md)
* [Credential Management Architecture](file:///workspaces/hacknova/docs/security/CREDENTIAL_MANAGEMENT.md)
* [Memory Management Guide](file:///workspaces/hacknova/docs/user-guide/MEMORY_MANAGEMENT.md)
