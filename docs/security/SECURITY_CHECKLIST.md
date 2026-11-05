---
title: Security Release Checklist
purpose: Pre-release verification checklist covering OWASP MASVS, encryption, permissions, and network policies
scope: Pre-deployment verification for production APK/AAB releases
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/security/SECURITY_REQUIREMENTS.md
  - docs/release/RELEASE_NOTES_TEMPLATE.md
---

# Security Release Checklist

All items must be verified prior to tagging any production build:

## 1. Storage & Cryptography
- [x] API keys and bearer tokens stored strictly in `EncryptedSharedPreferences` backed by Android Keystore `MasterKey` (`AES256_GCM`).
- [x] Room SQLite database stores zero unencrypted credentials or secrets.
- [x] Automated cloud backup rules (`backup_rules.xml`) exclude encrypted preferences.
- [x] Token redaction verified in `AiError.sanitize()` across all UI error banners and logs.

## 2. Network & Transport Security
- [x] Cleartext HTTP blocked for all non-private remote domains via `network_security_config.xml`.
- [x] Programmatic `NetworkSecurityValidator` validates user-entered Base URLs and rejects remote cleartext endpoints.
- [x] TLS trust anchors enforce system certificate authority validation; no arbitrary SSL pinning bypass.
- [x] Connection timeouts configured (15s connect, 60s read) to prevent resource hangs.

## 3. Autonomous Execution & Governance
- [x] `RiskLevel.HIGH` actions enforce `ApprovalRequestEntity` human-in-the-loop queue.
- [x] `EmergencyKillswitch` halts running automation within milliseconds.
- [x] Foreground Service persistent notification displays active execution status and emergency stop action.
- [x] Maximum retry count (`maxRetries = 3`) enforced on all DAG task nodes to prevent runaway loops.

## 4. Code & Build Hygiene
- [x] All 52 automated tests pass with 0 failures (`./gradlew testDebugUnitTest`).
- [x] No hardcoded production API keys, tokens, or mock fallback secrets in source code.
- [x] ProGuard/R8 release optimization enabled with optimized rules.
- [x] Release APK signed with verified production signing key.
