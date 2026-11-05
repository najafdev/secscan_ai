---
title: Legal Review Checklist
purpose: Highlights unresolved legal decisions, missing placeholders, and clauses requiring professional counsel
scope: Legal and regulatory review prior to commercial distribution
applicable_version: v1.0.0
last_updated: 2026-11-01
status: UNDER REVIEW
cross_references:
  - docs/legal/PRIVACY_POLICY.md
  - docs/legal/TERMS_AND_CONDITIONS.md
---

# Legal Review Checklist

> [!IMPORTANT]
> The documentation in `docs/legal/` provides publication-ready drafts reflecting the actual technical behavior of AgentDroid. Prior to official public distribution (particularly on Google Play Store or commercial channels), the project owner must review and complete the items flagged below.

---

## 1. Unresolved Placeholders Requiring Project Owner Input

- [ ] **Legal Entity Identification**:
  * Replace `[LEGAL ENTITY NAME]` with the registered corporate entity, foundation name, or primary maintainer collective in all legal documents.
- [ ] **Official Contact Channels**:
  * Replace `[OFFICIAL CONTACT EMAIL]` with designated, monitored mailboxes (e.g., `privacy@agentdroid.org`, `security@agentdroid.org`).
- [ ] **Governing Law & Forum**:
  * Replace `[APPLICABLE JURISDICTION]` in `TERMS_AND_CONDITIONS.md` with the chosen jurisdiction (e.g. Republic of India, State of Delaware, or relevant national court).
- [ ] **Effective Date**:
  * Confirm the official go-live date in `PRIVACY_POLICY.md` and `TERMS_AND_CONDITIONS.md`.

---

## 2. Regulatory & App Store Compliance Checklist

- [ ] **Google Play Accessibility Service Policy**:
  * Ensure the in-app prominent disclosure modal is displayed prior to redirecting the user to `Settings.ACTION_ACCESSIBILITY_SETTINGS`.
  * Ensure the Play Store listing accurately declares Accessibility Service usage for UI automation.
- [ ] **Indian Digital Personal Data Protection Act (DPDPA 2023)**:
  * Review notice and consent mechanisms for Indian users.
  * Confirm that local-only SQLite storage aligns with data fiduciary obligations.
- [ ] **GDPR / EU Compliance**:
  * If offering services to European residents, confirm that point-to-point data transmission to US-based AI APIs (OpenAI, Anthropic) is backed by standard contractual clauses (SCCs) via the user's direct API relationship.
- [ ] **Export Control & Cryptography Disclosures**:
  * Confirm that standard Android Keystore AES-256 usage qualifies for standard mass-market encryption exemptions (EAR 740.17).
