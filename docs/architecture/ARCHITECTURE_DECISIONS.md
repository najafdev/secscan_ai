---
title: Architecture Decision Records (ADRs)
purpose: Documents key technical decisions, context, alternatives considered, and tradeoffs
scope: Technical architecture evolution of AgentDroid
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/architecture/SYSTEM_ARCHITECTURE.md
  - docs/architecture/SOFTWARE_ARCHITECTURE.md
---

# Architecture Decision Records (ADRs)

## ADR-001: Strict Real AI Mode (Elimination of Mock Data)
* **Status**: ACCEPTED & IMPLEMENTED
* **Context**: Many AI prototypes utilize hardcoded mock responses when APIs are disconnected.
* **Decision**: Enforce a strict "Real AI" execution policy across the entire production codebase. If an API key is missing or network fails, the system surfaces explicit `AiError` diagnostics rather than fabricated agent responses.
* **Consequences**: Users receive transparent feedback. Zero risk of presenting fabricated automation or fake social analytics as real results.

---

## ADR-002: Destination-Aware Backstack Management in Navigation Compose
* **Status**: ACCEPTED & IMPLEMENTED
* **Context**: Navigating between primary screens and clicking Home resulted in unhandled no-ops when using generic `popUpTo(startDestination.id) { saveState = true }` with `restoreState = true`.
* **Decision**: When navigating to the start destination (`Screen.Dashboard.route`), explicitly call `navController.popBackStack(Screen.Dashboard.route, inclusive = false)` to pop intermediate screens cleanly back to the root without creating duplicate entries or restoring inconsistent state.
* **Consequences**: Eliminates the "Home unresponsive" navigation bug across all screen combinations.

---

## ADR-003: Subnet-Gated Cleartext Network Security Policy
* **Status**: ACCEPTED & IMPLEMENTED
* **Context**: Android 9+ blocks cleartext HTTP by default. Local LLMs (Ollama, LM Studio) typically run over HTTP on local networks (`http://192.168.x.x:11434`, `http://10.0.2.2:11434`).
* **Decision**: Provide a custom `network_security_config.xml` combined with programmatic `NetworkSecurityValidator`. Cleartext HTTP is permitted for local subnets (`localhost`, `10.0.2.2`, `192.168.0.0/16`, `10.0.0.0/8`, `172.16.0.0/12`), while remote endpoints strictly require HTTPS.
* **Consequences**: Enables seamless local LLM pairing on home Wi-Fi while preventing insecure cleartext transmissions across public cloud APIs.

---

## ADR-004: Android Keystore AES-256 GCM for Credential Storage
* **Status**: ACCEPTED & IMPLEMENTED
* **Context**: API keys and bearer tokens must be stored on-device without exposing them to rooted devices or backup extraction.
* **Decision**: Use `EncryptedSharedPreferences` backed by Android Keystore `MasterKey` (`AES256_GCM`).
* **Consequences**: Hardware-backed cryptographic protection on supported devices. Plaintext keys are never stored in SQLite or readable via adb backups.

---

## ADR-005: Multi-Tier Memory Segmentation
* **Status**: ACCEPTED & IMPLEMENTED
* **Context**: Feeding full conversational history into LLMs causes context window exhaustion and inflated token costs.
* **Decision**: Segment memory into 5 functional tiers (`WORKING`, `SHORT_TERM`, `LONG_TERM`, `EPISODIC`, `PROCEDURAL`).
* **Consequences**: Optimized context windows, reduced inference costs, and explicit user controls for purging specific memory tiers.
