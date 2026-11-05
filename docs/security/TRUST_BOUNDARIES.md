---
title: Trust Boundaries
purpose: Defines system trust domains, security perimeters, and boundary transitions
scope: Architecture boundaries across user, application, device, and network
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/security/SECURITY_OVERVIEW.md
  - docs/security/ATTACK_SURFACE_ANALYSIS.md
---

# Trust Boundaries

## Trust Domain Model

```mermaid
graph TD
    subgraph Domain_User [Trust Domain 1: User Direct Input - HIGH TRUST]
        User[Human User]
        Approvals[Biometric / UI Approval Confirmations]
        KillswitchUI[Emergency Stop Notification]
    end

    subgraph Domain_App [Trust Domain 2: AgentDroid Sandbox - SECURE TRUST]
        Keystore[Android Keystore Hardware Key]
        SecurePrefs[EncryptedSharedPreferences]
        RoomDB[Internal SQLite Database]
        Orchestrator[Agent Orchestration Core]
    end

    subgraph Domain_LocalLAN [Trust Domain 3: User Local Network - MEDIUM TRUST]
        OllamaServer[Local Ollama / LM Studio Server]
        LANRouter[Home Wi-Fi Router / 192.168.x.x]
    end

    subgraph Domain_Cloud [Trust Domain 4: Cloud AI Vendors - CONDITIONAL TRUST]
        OpenAI[OpenAI API]
        Anthropic[Anthropic API]
        Gemini[Google Gemini API]
    end

    subgraph Domain_Untrusted [Trust Domain 5: Untrusted External Environment - ZERO TRUST]
        Websites[Public Websites via Browser Agent]
        ScreenContent[Third-Party App UI Elements via Accessibility]
        Attacker[Adversarial Web Pages / Prompt Injections]
    end

    Domain_User ==>|Commands & Approvals| Domain_App
    Domain_App <==|Local HTTP GET/POST| Domain_LocalLAN
    Domain_App <==|Encrypted TLS HTTPS| Domain_Cloud
    Domain_Untrusted -.->|Parsed as Data Only| Domain_App
```

---

## Boundary Transition Controls

| Transition | From Domain $\rightarrow$ To Domain | Data / Control Flow | Security Controls Enforced |
| :--- | :--- | :--- | :--- |
| **B-01** | User $\rightarrow$ App | Voice/Text commands, Approval clicks | Sanitized input buffer, explicit Confirmation Dialogs |
| **B-02** | App $\rightarrow$ Keystore | Storing & retrieving API keys | Hardware-backed MasterKey AES-256 GCM encryption |
| **B-03** | App $\rightarrow$ Cloud AI | Prompts, task instructions, completions | Strict TLS 1.2+ encryption, Bearer token header injection |
| **B-04** | App $\rightarrow$ Local LAN | Ollama inference & tag discovery | Subnet validation (`192.168.0.0/16`, `10.0.0.0/8`, `127.0.0.1`) |
| **B-05** | Untrusted $\rightarrow$ App | Third-party app UI strings, web HTML | Node filtering, delimited context fencing, Human Approval for High-Risk actions |
