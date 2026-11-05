---
title: Complete Error Codes & Remediation Catalog
purpose: Comprehensive reference of all system and AI error codes, categories, and actions
scope: AiError, ErrorCategory, SuggestedAction, and user remediation workflows
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/api/API_OVERVIEW.md
  - docs/user-guide/TROUBLESHOOTING.md
  - docs/architecture/AI_PROVIDER_ARCHITECTURE.md
---

# Complete Error Codes & Remediation Catalog

AgentDroid enforces **Strict Real AI Mode**. Fake responses are never emitted. When an operation cannot proceed, a structured `AiError` is returned.

---

## 1. Error Categories (`ErrorCategory`)

| Enum Name | Description | Default Suggested Action |
|---|---|---|
| `AI_NOT_CONFIGURED` | No active AI provider or valid credentials set up. | `CONNECT_PROVIDER` |
| `API_KEY_MISSING` | Provider selected but key is blank in Keystore. | `UPDATE_API_KEY` |
| `API_KEY_INVALID` | Cloud provider returned HTTP 401 or 403 Forbidden. | `UPDATE_API_KEY` |
| `MODEL_NOT_FOUND` | Configured model identifier does not exist on endpoint. | `SELECT_ANOTHER_MODEL` |
| `PROVIDER_UNAVAILABLE` | Endpoint refused connection or server returned 5xx. | `TEST_CONNECTION` |
| `RATE_LIMIT_EXCEEDED` | HTTP 429 Too Many Requests. | `WAIT_AND_RETRY` |
| `NETWORK_UNAVAILABLE` | Device has no internet connectivity or LAN socket timed out. | `CHECK_NETWORK` |
| `REQUEST_TIMEOUT` | Provider did not return response within configured timeout. | `RETRY_NOW` |
| `INVALID_RESPONSE` | Malformed JSON or unrecognizable payload structure. | `RETRY_NOW` |
| `CONTENT_BLOCKED` | Provider safety filter or moderation flagged prompt/response. | `DISMISS` |
| `QUOTA_EXCEEDED` | Provider billing quota or credit balance exhausted. | `CHECK_PROVIDER_USAGE` |
| `AGENT_EXECUTION_FAILED` | Internal error during agent step execution. | `RETRY_NOW` |
| `TOOL_EXECUTION_FAILED` | Accessibility or Android platform action returned failure. | `DISMISS` |
| `PERMISSION_DENIED` | Missing Android OS permission (e.g., Accessibility off). | `OPEN_SETTINGS` |
| `CONFIGURATION_INVALID` | Bad endpoint URL format or conflicting provider settings. | `OPEN_SETTINGS` |
| `UNKNOWN_ERROR` | Unhandled fallback runtime exception. | `DISMISS` |

---

## 2. Standardized Error Codes (`errorCode`)

| Error Code | Category | User-Friendly Message |
|---|---|---|
| `ERR_AI_NOT_CONFIGURED` | `AI_NOT_CONFIGURED` | "AgentDroid needs a connected AI model to process your requests." |
| `ERR_API_KEY_MISSING` | `API_KEY_MISSING` | "No API key configured for {provider}. Please provide an API key in Settings." |
| `ERR_AUTH_FAILED` | `API_KEY_INVALID` | "The configured API key was rejected by {provider}. Please verify your credentials." |
| `ERR_MODEL_NOT_FOUND` | `MODEL_NOT_FOUND` | "The model '{model}' could not be found or is not accessible." |
| `ERR_NETWORK_UNAVAILABLE` | `NETWORK_UNAVAILABLE` | "AgentDroid could not reach {provider}. Check your internet connection." |
| `ERR_RATE_LIMIT` | `RATE_LIMIT_EXCEEDED` | "The AI provider has temporarily limited requests. Please wait." |
| `ERR_QUOTA_EXCEEDED` | `QUOTA_EXCEEDED` | "The configured AI provider has insufficient quota or credits." |
| `ERR_TIMEOUT` | `REQUEST_TIMEOUT` | "The AI provider did not respond within the allowed time." |
| `ERR_INVALID_RESPONSE` | `INVALID_RESPONSE` | "Received an invalid or unparseable response from {provider}." |
| `ERR_OLLAMA_NO_MODELS` | `MODEL_NOT_FOUND` | "No local models found on Ollama server. Run 'ollama pull' first." |
| `ERR_TOOL_EXECUTION` | `TOOL_EXECUTION_FAILED` | "The requested device action could not be completed." |
| `ERR_PERMISSION_REQUIRED` | `PERMISSION_DENIED` | "AgentDroid requires permission to perform this device action." |

---

## Related Documentation
* [Troubleshooting Guide](file:///workspaces/hacknova/docs/user-guide/TROUBLESHOOTING.md)
* [API Overview](file:///workspaces/hacknova/docs/api/API_OVERVIEW.md)
* [AI Provider Architecture](file:///workspaces/hacknova/docs/architecture/AI_PROVIDER_ARCHITECTURE.md)
