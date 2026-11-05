---
title: User Personas
purpose: Details the demographic, behavioral, and technical archetypes targeted by AgentDroid
scope: User experience and functional design references
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/product/PRODUCT_OVERVIEW.md
  - docs/product/USER_JOURNEYS.md
---

# User Personas

## Persona 1: Devendra Sharma (Solo Founder & Creator)
* **Age**: 29
* **Location**: Bengaluru, India
* **Role**: Tech Founder & Independent Creator
* **Hardware**: Pixel 8 Pro (Android 14), Linux Workstation running Ollama
* **Technical Savvy**: High (comfortable with APIs, terminal, and automation tools)
* **Key Goals**:
  * Run competitive intelligence without manual web searching.
  * Schedule daily social media announcements across X and LinkedIn.
  * Automate repetitive device tasks like archiving invoice receipts from Gmail.
* **Pain Points with Existing Tools**:
  * Chatbots cannot interact with native Android apps.
  * Cloud subscriptions become costly when querying large context windows.
* **Why AgentDroid Fits**:
  * Assigns GPT-4o for complex research synthesis, and local Ollama Llama 3.2 on his home Wi-Fi for bulk drafting without API fees.

---

## Persona 2: Sarah Jenkins (Operations & Productivity Specialist)
* **Age**: 38
* **Location**: London, United Kingdom
* **Role**: Executive Assistant & Workflow Consultant
* **Hardware**: Samsung Galaxy S23 (Android 13)
* **Technical Savvy**: Medium (uses SaaS tools, shortcuts, and spreadsheets)
* **Key Goals**:
  * Single natural language command to organize daily schedules, calendar reminders, and draft briefing emails.
  * Ensure no client email or calendar invitation is sent without her prior review.
* **Pain Points with Existing Tools**:
  * Autonomous agents can execute hallucinated or embarrassing external actions.
* **Why AgentDroid Fits**:
  * High-risk Human-in-the-Loop approvals give her complete veto power before any communication is dispatched.

---

## Persona 3: Marcus Vance (Security Engineer & Privacy Advocate)
* **Age**: 34
* **Location**: Berlin, Germany
* **Role**: Information Security Analyst
* **Hardware**: Nothing Phone 2 (Android 14)
* **Technical Savvy**: Expert (audits network traffic, decompiles APKs, runs self-hosted infrastructure)
* **Key Goals**:
  * Use mobile AI automation with zero data leakage to cloud providers.
  * Audit permissions, accessibility node inspection, and network security configs.
* **Pain Points with Existing Tools**:
  * Commercial AI apps harvest device telemetry, contacts, and unencrypted credentials.
* **Why AgentDroid Fits**:
  * Hardware Keystore AES-256 GCM encryption, zero tracker SDKs, open-source codebase, and strict local network cleartext policies with enforced remote HTTPS.
