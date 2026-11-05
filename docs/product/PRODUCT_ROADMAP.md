---
title: Product Roadmap
purpose: Outlines current implemented milestones and planned future capabilities
scope: Product development horizons and feature backlog
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/product/PRODUCT_REQUIREMENTS_DOCUMENT.md
  - docs/release/CHANGELOG.md
---

# Product Roadmap

## Current Release: v1.0.0 (Production Core)

* **Status**: `IMPLEMENTED` & Fully Verified
* **Deliverables**:
  * Multi-agent execution engine with Master Agent and 10 specialized agent roles.
  * Directed Acyclic Graph (DAG) task scheduler with dependency resolution.
  * Strict Real AI policy with full elimination of mock or simulated responses.
  * Dynamic model discovery across OpenAI, Gemini, Anthropic, OpenRouter, Groq, Together, Ollama, and custom servers.
  * Native Ollama `/api/tags` and `/api/chat` integration with local LAN support.
  * Obsidian Black dark interface (`#08090B`) with 5-tab responsive navigation.
  * Android Accessibility Service UI automation and state verifier.
  * Android Keystore hardware-backed encryption (AES-256 GCM) for credentials.
  * Network security policy allowing cleartext HTTP only on local subnets.
  * 5-Tier Memory Engine (Working, Short-Term, Long-Term, Episodic, Procedural).
  * Human-in-the-Loop Approval Queue and persistent Emergency Killswitch.

---

## Horizon 1: v1.1.0 (Enhanced Intelligence & Tooling)

* **Status**: `PLANNED`
* **Target Features**:
  * **On-Device Vision Inspection**: Direct screenshot OCR via bundled Tesseract/ML Kit without external cloud upload.
  * **Interactive Multi-Step Web Automations**: Advanced Chrome/Browser agent form filling and CAPTCHA detection alerts.
  * **Voice Wake-Word Engine**: Offline on-device wake-word detection (e.g. "Hey Droid") for hands-free activation.
  * **Enhanced Cron Workflows**: Periodic background execution triggered via system broadcasts and calendar triggers.

---

## Horizon 2: v1.2.0 (Ecosystem & Extension Expansion)

* **Status**: `PLANNED`
* **Target Features**:
  * **Community Plugin Store**: Sandboxed distribution of third-party agent plugins using Android package intents.
  * **Local Vector Embeddings**: On-device vector store (e.g., sqlite-vss / llama.cpp embeddings) for semantic episodic memory search.
  * **Encrypted Cloud Backup**: End-to-end encrypted backup of workflows and memory records to user-owned Google Drive or WebDAV storage.
  * **Wear OS Companion**: Quick action trigger and notification approval directly from Wear OS smartwatches.
