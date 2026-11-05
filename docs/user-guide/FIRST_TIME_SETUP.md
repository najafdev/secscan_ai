---
title: First-Time Setup & Permissions
purpose: Initial onboarding walkthrough, permission configuration, and accessibility activation
scope: Initial app launch on Android devices
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/user-guide/INSTALLATION.md
  - docs/user-guide/ACCESSIBILITY_SETUP.md
---

# First-Time Setup & Permissions

When you launch AgentDroid for the first time, complete these 3 quick setup steps:

## Step 1: Grant Notification Permission
On Android 13+ (API 33), AgentDroid requests `POST_NOTIFICATIONS`:
* **Why**: Required to alert you when background multi-agent workflows finish, when high-risk actions require your approval, and to provide the persistent **Emergency Killswitch** in your notification drawer.
* **Action**: Tap **Allow** when the system permission dialog appears.

---

## Step 2: Enable the Accessibility Automation Service
To allow the **Phone Control Agent** to interact with installed Android apps:
1. Tap the **Settings** icon in the bottom navigation bar.
2. Locate the **Accessibility Automation Engine** card.
3. Tap the **Enable** button. AgentDroid will redirect you directly to Android's Accessibility Settings.
4. Tap **AgentDroid Accessibility Service**, toggle the switch to **On**, and tap **Allow** on the Android confirmation dialog.

> [!NOTE]
> AgentDroid uses accessibility strictly for active, user-directed tasks (such as tapping buttons or scrolling). It never records passwords or monitors background activity.

---

## Step 3: Connect Your First AI Provider
AgentDroid operates in **Strict Real AI Mode** and requires a live model connection:
1. In **Settings**, tap **Add Provider**.
2. Select a cloud preset (e.g., **OpenAI**, **Gemini**, **Claude**, **Groq**) or a local preset (**Ollama Local Daemon**).
3. Enter your API key or local LAN IP address and tap **Save & Connect**.
4. Once the status shows **CONNECTED**, you are ready to use the Command Center!
