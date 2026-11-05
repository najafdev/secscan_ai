---
title: Troubleshooting & Error Resolution Guide
purpose: Step-by-step solutions for common operational and connection issues
scope: AI provider connectivity, local network errors, accessibility faults, and database resets
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/api/ERROR_CODES.md
  - docs/user-guide/OLLAMA_SETUP.md
  - docs/user-guide/ACCESSIBILITY_SETUP.md
---

# Troubleshooting & Error Resolution Guide

This guide provides immediate solutions for errors and unexpected behavior in AgentDroid.

---

## 1. Common AI Connection Errors

### A. "AI Model Not Connected" or `ERR_AI_NOT_CONFIGURED`
* **Cause**: No AI provider has been set up or activated.
* **Fix**: Tap the banner or navigate to **Settings → AI Providers**. Select a provider (e.g., Gemini, OpenAI, or Ollama) and enter your valid API key or endpoint URL.

### B. "Invalid API Key" or `ERR_API_KEY_INVALID` (HTTP 401 / 403)
* **Cause**: The API key entered is expired, revoked, mistyped, or lacks quota permissions.
* **Fix**: Re-generate a fresh API key in your provider dashboard (e.g., Google AI Studio, OpenAI Platform) and paste it into AgentDroid. Check for leading/trailing whitespace.

### C. "Ollama Connection Failed" or `ERR_PROVIDER_UNREACHABLE`
* **Cause**: AgentDroid cannot reach your Ollama server over your Wi-Fi network.
* **Troubleshooting Steps**:
  1. Confirm your PC and phone are on the exact same Wi-Fi network.
  2. Verify your PC firewall allows incoming traffic on port `11434`.
  3. Ensure Ollama is configured to listen on all interfaces:
     * Linux / macOS: `export OLLAMA_HOST=0.0.0.0:11434`
     * Windows: Set system environment variable `OLLAMA_HOST` to `0.0.0.0:11434` and restart Ollama.
  4. Ensure you entered your PC's LAN IP address (e.g., `http://192.168.1.100:11434`), not `localhost` or `127.0.0.1` (which refers to the phone itself).

### D. "No models discovered for provider" or `ERR_OLLAMA_NO_MODELS`
* **Cause**: Ollama is reachable, but `GET /api/tags` returned an empty model list.
* **Fix**: Run `ollama pull llama3:8b` or `ollama pull mistral` on your computer, then tap **Fetch Models** again in AgentDroid.

---

## 2. Phone Automation & Accessibility Issues

### A. "Accessibility Service Not Running"
* **Cause**: The background service was killed by Android battery optimization or system restart.
* **Fix**: Open Android **Settings → Accessibility → AgentDroid Assistant Service**, toggle it Off and back On. Add AgentDroid to your device's "Unrestricted Battery" list under **Settings → Apps → AgentDroid → Battery**.

### B. Agent Cannot Find Screen Element
* **Cause**: Target app changed layout, or element text differs from prompt.
* **Fix**: Open the target app manually to verify element text. Simplify the instruction or specify exact button labels (e.g., *"Click button labeled 'Next'"*).

---

## 3. Database & Cache Reset

If the application displays persistent database sync errors:
1. Go to **Settings → App Settings**.
2. Tap **Clear Application Cache**.
3. If issues persist, tap **Purge Conversation History** or perform an app data reset via Android Settings.

---

## Related Documentation
* [Error Codes Catalog](file:///workspaces/hacknova/docs/api/ERROR_CODES.md)
* [Ollama Setup Guide](file:///workspaces/hacknova/docs/user-guide/OLLAMA_SETUP.md)
* [Accessibility Setup Guide](file:///workspaces/hacknova/docs/user-guide/ACCESSIBILITY_SETUP.md)
