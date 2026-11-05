package com.agentdroid.app.ai.connection

import java.net.URI

object NetworkSecurityValidator {

    data class ValidationResult(
        val isValid: Boolean,
        val sanitizedUrl: String? = null,
        val isLocal: Boolean = false,
        val errorMessage: String? = null
    )

    fun validateEndpointUrl(inputUrl: String): ValidationResult {
        val trimmed = inputUrl.trim()
        if (trimmed.isBlank()) {
            return ValidationResult(isValid = false, errorMessage = "Base URL cannot be blank.")
        }

        val uri = try {
            URI.create(trimmed)
        } catch (e: Exception) {
            return ValidationResult(isValid = false, errorMessage = "Invalid URL format: ${e.message}")
        }

        val scheme = uri.scheme?.lowercase()
        if (scheme != "http" && scheme != "https") {
            return ValidationResult(
                isValid = false,
                errorMessage = "Unsupported protocol '$scheme'. Only HTTP and HTTPS are permitted."
            )
        }

        val host = uri.host
        if (host.isNullOrBlank()) {
            return ValidationResult(isValid = false, errorMessage = "URL must specify a valid host.")
        }

        val isLocalHost = isLocalOrPrivateHost(host)

        if (scheme == "http" && !isLocalHost) {
            return ValidationResult(
                isValid = false,
                errorMessage = "Cleartext HTTP is only permitted for local/LAN endpoints (localhost, 127.0.0.1, 10.0.2.2, 192.168.x.x, 10.x.x.x). Remote endpoints must use HTTPS."
            )
        }

        val port = uri.port
        if (port != -1 && (port < 1 || port > 65535)) {
            return ValidationResult(isValid = false, errorMessage = "Port number must be between 1 and 65535.")
        }

        val cleanUrl = trimmed.trimEnd('/')
        return ValidationResult(
            isValid = true,
            sanitizedUrl = cleanUrl,
            isLocal = isLocalHost
        )
    }

    fun isLocalOrPrivateHost(host: String): Boolean {
        val lower = host.lowercase()
        if (lower == "localhost" || lower == "127.0.0.1" || lower == "10.0.2.2") return true
        if (lower.endsWith(".local") || lower.endsWith(".lan")) return true

        // Check IPv4 private subnets
        val parts = lower.split(".")
        if (parts.size == 4 && parts.all { it.toIntOrNull() != null }) {
            val octets = parts.map { it.toInt() }
            if (octets.any { it !in 0..255 }) return false

            // 127.0.0.0/8
            if (octets[0] == 127) return true
            // 10.0.0.0/8
            if (octets[0] == 10) return true
            // 172.16.0.0/12
            if (octets[0] == 172 && octets[1] in 16..31) return true
            // 192.168.0.0/16
            if (octets[0] == 192 && octets[1] == 168) return true
        }

        return false
    }
}
