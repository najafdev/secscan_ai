---
title: Frequently Asked Questions (FAQ)
purpose: Quick answers to the most common questions regarding AgentDroid
scope: General product questions, pricing, security, compatibility, and offline usage
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/user-guide/GETTING_STARTED.md
  - docs/security/SECURITY_OVERVIEW.md
  - docs/release/COMPATIBILITY.md
---

# Frequently Asked Questions (FAQ)

### General Questions

#### What is AgentDroid?
AgentDroid is an autonomous multi-agent operating system for Android. Instead of a single chatbot, it coordinates multiple specialized AI agents (Phone Control, Social Media, Research, Content Creation, Analytics, etc.) to execute multi-step tasks across Android applications.

#### Is AgentDroid free?
Yes. AgentDroid is open-source software licensed under the Apache 2.0 license. You only pay for your own AI provider API usage (e.g., OpenAI or Anthropic credits), or you can run completely free with local models via Ollama.

#### Does AgentDroid support offline AI execution?
Yes. You can connect AgentDroid to a local LLM running on your PC or home server via Ollama or LM Studio over your local Wi-Fi. In this setup, zero data leaves your local network.

---

### Security & Privacy

#### Does AgentDroid upload my personal data or screen content?
No. AgentDroid has no centralized servers, advertising trackers, or telemetry beacons. All chat histories, task plans, and settings reside in your device's encrypted local database. When using cloud models, only the prompt context necessary for your request is transmitted to your chosen AI provider.

#### Can AgentDroid make unauthorized purchases or transfer money?
No. The Phone Control Agent operates under a strict **Human-in-the-Loop** policy. High-risk actions, sensitive financial applications, and system modifications trigger an explicit confirmation prompt requiring your biometric authentication or tap approval.

---

### Performance & Compatibility

#### Which Android versions are supported?
AgentDroid supports Android 8.0 (API level 26) through Android 14+ (API level 34). Certain advanced accessibility and dynamic shortcut features function best on Android 10 and above.

#### Why does phone automation fail when the screen is locked?
Android's hardware security prevents background services from inspecting UI elements or simulating screen taps while the device is locked. Ensure the screen is active and unlocked during automated workflows.

---

## Related Documentation
* [Getting Started](file:///workspaces/hacknova/docs/user-guide/GETTING_STARTED.md)
* [Security Overview](file:///workspaces/hacknova/docs/security/SECURITY_OVERVIEW.md)
* [Device Compatibility](file:///workspaces/hacknova/docs/release/COMPATIBILITY.md)
