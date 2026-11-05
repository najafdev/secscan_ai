---
title: Secure Storage Architecture
purpose: In-depth technical specification of local storage mechanisms and Keystore integrations
scope: SecurePreferencesManager and Room SQLite configuration
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/security/DATA_PROTECTION.md
  - docs/security/CREDENTIAL_MANAGEMENT.md
---

# Secure Storage Architecture

## Keystore AES-256 GCM Implementation Details

AgentDroid implements secure storage via `SecurePreferencesManager.kt`, which wraps `EncryptedSharedPreferences`:

```kotlin
val masterKey = MasterKey.Builder(context)
    .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
    .build()

val sharedPreferences = EncryptedSharedPreferences.create(
    context,
    "agentdroid_secure_prefs",
    masterKey,
    EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
    EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
)
```

### Cryptographic Guarantees:
* **Key Encryption**: Preference keys are deterministically encrypted using `AES256_SIV`, preventing leakage of configured provider identities while enabling fast key lookups.
* **Value Encryption**: Preference values are encrypted using `AES256_GCM`, providing both confidentiality and cryptographic authentication against on-disk tampering.
* **Hardware Storage**: The master wrapping key is stored within the Android Keystore system. On devices equipped with hardware security chips (Titan M, Samsung Knox, ARM TrustZone), the master key never resides in application RAM.

---

## Scoped App Data Separation

* **`agentdroid_secure_prefs.xml`**: Encrypted API keys, bearer tokens, custom server headers.
* **`agentdroid.db`**: Relational tables (tasks, logs, memory records, discovered models).
* **`agentdroid_note.txt`**: Scoped user file exports located in `context.getExternalFilesDir(null)`.
* **Backup Rules (`backup_rules.xml`)**:
  * Critical secure preferences are excluded from automated cloud backups to prevent credential leaks across Google Drive backups.
