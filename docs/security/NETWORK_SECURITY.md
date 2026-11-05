---
title: Network Security Architecture
purpose: Details transport layer security, network configuration rules, and subnet gating
scope: network_security_config.xml and NetworkSecurityValidator
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/security/SECURITY_REQUIREMENTS.md
  - docs/security/DATA_PROTECTION.md
---

# Network Security Architecture

## Android Network Security Configuration

AgentDroid declares its network transport policy via `network_security_config.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <!-- System trust anchors enforced for all TLS traffic -->
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>

    <!-- Cleartext HTTP explicitly declared for local development & self-hosted engines -->
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">localhost</domain>
        <domain includeSubdomains="true">127.0.0.1</domain>
        <domain includeSubdomains="true">10.0.2.2</domain>
        <domain includeSubdomains="true">local</domain>
        <domain includeSubdomains="true">lan</domain>
    </domain-config>
</network-security-config>
```

---

## Programmatic Subnet Gating (`NetworkSecurityValidator`)

Because Android XML network configurations cannot validate dynamic private IPv4 ranges (such as `192.168.1.100`), AgentDroid pairs OS-level rules with programmatic validation in `NetworkSecurityValidator.kt`:

```kotlin
fun validateEndpointUrl(inputUrl: String): ValidationResult {
    // 1. Verify scheme is http or https
    val scheme = uri.scheme?.lowercase()
    if (scheme != "http" && scheme != "https") {
        return ValidationResult(isValid = false, errorMessage = "Only HTTP and HTTPS are permitted.")
    }

    // 2. Determine if destination host is local / private
    val isLocalHost = isLocalOrPrivateHost(uri.host)

    // 3. Enforce HTTPS for all remote destinations
    if (scheme == "http" && !isLocalHost) {
        return ValidationResult(
            isValid = false,
            errorMessage = "Cleartext HTTP is only permitted for local/LAN endpoints. Remote endpoints must use HTTPS."
        )
    }
    return ValidationResult(isValid = true, sanitizedUrl = cleanUrl, isLocal = isLocalHost)
}
```

### Supported Private Ranges:
* `127.0.0.0/8` (Device Loopback)
* `10.0.2.2` (Android Emulator Host Bridge)
* `10.0.0.0/8` (Class A Private Network)
* `172.16.0.0/12` (Class B Private Network)
* `192.168.0.0/16` (Class C Home Wi-Fi Network)
* `*.local`, `*.lan` (mDNS & Home Gateway Hostnames)
