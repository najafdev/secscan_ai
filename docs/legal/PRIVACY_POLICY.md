---
title: Privacy Policy
purpose: Official legal Privacy Policy governing the use of the AgentDroid Android application
scope: Global distribution (Google Play Store, F-Droid, GitHub)
applicable_version: v1.0.0
last_updated: 2026-11-01
status: UNDER REVIEW
cross_references:
  - docs/privacy/PRIVACY_OVERVIEW.md
  - docs/legal/LEGAL_REVIEW_CHECKLIST.md
---

# AgentDroid Privacy Policy

**Effective Date**: `[DATE OF ENACTMENT - e.g. November 1, 2026]`  
**Last Updated**: `[DATE - e.g. November 1, 2026]`  
**Legal Entity**: `[LEGAL ENTITY NAME / PROJECT MAINTAINERS]`  
**Contact Email**: `[OFFICIAL CONTACT EMAIL - e.g. privacy@agentdroid.org]`  
**Jurisdiction**: `[APPLICABLE JURISDICTION - e.g. Republic of India / European Union]`

---

## 1. Introduction

`[LEGAL ENTITY NAME]` ("we", "us", or "our") develops and maintains **AgentDroid**, an open-source multi-agent personal AI operating system for Android. This Privacy Policy explains how AgentDroid processes, stores, and protects your information when you install and operate the AgentDroid application.

We are committed to the principle of **User Data Sovereignty**. We do not operate tracking servers, advertising networks, or centralized telemetry pipelines.

---

## 2. Information We Do NOT Collect

To provide transparency regarding our architecture, we explicitly confirm that AgentDroid:
* **Does not collect or sell your personal information.**
* **Does not contain third-party advertising or analytics SDKs.**
* **Does not track your physical GPS or network location.**
* **Does not read your contacts, SMS messages, or call history.**
* **Does not log your prompts to any centralized server operated by us.**

---

## 3. Information Processed On Your Device

All core data created within AgentDroid resides locally on your Android device:
1. **API Credentials**: Your API keys and bearer tokens for third-party AI services are stored locally in Android Keystore hardware-backed encrypted storage (`EncryptedSharedPreferences` using AES-256 GCM). They are never accessible to us.
2. **Conversational History & Prompts**: Natural language commands, conversational turns, and task outputs are stored in your local SQLite database (`agentdroid.db`).
3. **5-Tier Context Memory**: Preferences, learned workflows, and memory tags reside exclusively within your local database and can be purged by you at any time.
4. **Activity Logs**: Audits of executed agent tasks, durations, and risk classifications remain strictly on-device.

---

## 4. Device Permissions & Accessibility Service Disclosure

### Prominent Accessibility Service Disclosure
AgentDroid includes an optional **Accessibility Service** (`AgentDroidAccessibilityService`). If explicitly enabled by you:
* **Purpose**: Allows the Phone Control Agent to autonomously interact with installed Android applications on your behalf (such as clicking UI buttons, typing text, scrolling feeds, and launching apps).
* **Data Accessed**: The service inspects visible on-screen text and view identifiers strictly during active, user-initiated automation workflows to locate relevant UI controls.
* **Data Handling**: On-screen content is evaluated in temporary device memory. It is **never recorded continuously, never sold, and never transmitted to developer servers**.
* **Control**: You can enable, disable, or revoke this service at any time via Android **Settings $\rightarrow$ Accessibility $\rightarrow$ AgentDroid**.

### Additional Permissions
* `INTERNET` & `ACCESS_NETWORK_STATE`: Required to transmit inference requests directly to your configured AI providers.
* `FOREGROUND_SERVICE` & `FOREGROUND_SERVICE_DATA_SYNC`: Required to keep active multi-agent workflows executing with a persistent status notification and Emergency Killswitch.
* `POST_NOTIFICATIONS`: Required on Android 13+ to notify you of completed tasks and pending Human Approval requests.
* `QUERY_ALL_PACKAGES`: Used exclusively by the Phone Control Agent to identify installed apps for voice/text launching commands.

---

## 5. Third-Party AI Providers

AgentDroid functions as a direct client to user-configured AI providers:
* **Cloud AI Providers**: If you configure a cloud service (such as OpenAI, Google Gemini, Anthropic, OpenRouter, Groq, or Together AI), your prompts and context are transmitted directly from your device to that vendor via encrypted HTTPS (TLS 1.2+). That data is governed by the respective vendor's commercial privacy policy.
* **Local Private LLMs**: If you configure a local inference engine (such as **Ollama**, LM Studio, or vLLM running on your device or local Wi-Fi LAN), **no prompt data is transmitted over the public internet**. Inference occurs 100% within your private network.

---

## 6. Data Retention & Deletion Rights

Because all data resides on your physical hardware, you have absolute ownership and control:
* **Instantaneous Memory Purge**: In **Settings $\rightarrow$ Multi-Tier Context Memory**, you can reset individual tiers or tap **Purge All**.
* **Credential Deletion**: Deleting a provider in **Settings $\rightarrow$ AI Providers** immediately erases the associated cryptographic key from Android Keystore.
* **Total Erasure**: Uninstalling AgentDroid or selecting **Clear Storage** in Android Settings permanently destroys the database, Keystore ciphertext, and all internal records.

---

## 7. Children's Privacy

AgentDroid is not directed at children under the age of 13 (or under 16 in applicable European jurisdictions). We do not knowingly solicit or collect data from children.

---

## 8. Changes to this Privacy Policy

We may update this Privacy Policy from time to time to reflect architectural updates or regulatory changes. The updated version will be committed to the open-source repository and included in release notes with an updated effective date.

---

## 9. Contact Information

If you have questions, feedback, or concerns regarding this Privacy Policy or your data sovereignty, please contact:
* **Project Maintainers**: `[LEGAL ENTITY NAME / PROJECT OWNER]`
* **Official Email**: `[OFFICIAL CONTACT EMAIL - e.g. privacy@agentdroid.org]`
* **Repository**: `https://github.com/[PROJECT_OWNER]/agentdroid`
