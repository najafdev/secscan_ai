---
title: Data Collection Practices
purpose: Specifies what data is collected, what is NOT collected, and collection triggers
scope: Runtime data processing across device sensors and APIs
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/privacy/DATA_INVENTORY.md
  - docs/legal/PRIVACY_POLICY.md
---

# Data Collection Practices

## Verified Data Practices

### What AgentDroid Collects
1. **User-Provided Configuration**:
   * API keys and endpoint URLs entered in Settings.
   * Prompts, goals, and feedback submitted in the Command Center.
2. **Device State for Automation (When Accessibility is Enabled)**:
   * View hierarchy, package names, and visible text strings required by the Phone Control Agent to locate buttons and execute actions.
3. **Execution Records**:
   * Task execution timestamps, status logs, error categories, and approval decisions.

### What AgentDroid DOES NOT Collect
1. **Zero Location Tracking**: AgentDroid does not request GPS, network location, or Wi-Fi SSID location data.
2. **Zero Telemetry / Crash Reporting**: No automated crash logs, device analytics, or usage statistics are transmitted to the maintainers or third parties.
3. **Zero Contact / Call / SMS Ingestion**: AgentDroid does not read user contact books, SMS message databases, or call history.
4. **Zero Advertising Identifiers**: AgentDroid does not read or transmit the Google Advertising ID (GAID).
5. **Zero Background Audio Eavesdropping**: Microphone access is engaged only when the user explicitly taps the microphone button in the Command Center.
