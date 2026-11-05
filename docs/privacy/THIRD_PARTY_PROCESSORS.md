---
title: Third-Party Data Processors
purpose: Disclosures regarding external AI vendors, cloud endpoints, and data processing terms
scope: Configurable cloud AI providers
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/privacy/AI_DATA_PROCESSING.md
  - docs/legal/PRIVACY_POLICY.md
---

# Third-Party Data Processors

AgentDroid acts as a **direct client** to third-party AI services configured by the user. AgentDroid operates no intermediary relay servers. Data transmitted to a cloud provider is subject to that provider's commercial terms and privacy commitments:

| Provider | Applicable Endpoint | Typical Data Retention | Training Policy on Commercial APIs |
| :--- | :--- | :--- | :--- |
| **OpenAI** | `api.openai.com/v1` | 30 days for abuse monitoring (Zero Retention available on Enterprise) | Commercial API inputs are **not** used to train models by default |
| **Google Gemini** | `generativelanguage.googleapis.com` | Governed by Google Cloud Data Governance terms | Paid commercial API data is **not** used to train models |
| **Anthropic** | `api.anthropic.com/v1` | Retained for up to 30 days unless legal holds apply | Commercial API data is **not** used to train models |
| **OpenRouter** | `openrouter.ai/api/v1` | Subject to selected underlying upstream model vendor | Depends on selected upstream model |
| **Groq Cloud** | `api.groq.com/openai/v1` | Transient caching for inference speed | Data is **not** retained for model training |
| **Together AI** | `api.together.xyz/v1` | Subject to Together commercial data policy | Data is **not** used for training |
| **Self-Hosted Ollama** | User's Private Host (`192.168.x.x`) | **100% User-Controlled**: Zero third-party transmission | **Zero third-party exposure** |

---

## User Responsibility Notice

When choosing a cloud AI provider, users should review that vendor's privacy policy and data residency guarantees. For highly sensitive, air-gapped, or regulated data, users should configure **Ollama Local Daemon** or a self-hosted **LM Studio / vLLM** instance on their private local network.
