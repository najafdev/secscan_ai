---
title: Custom Local LLM & OpenAI-Compatible Server Setup
purpose: Instructions for connecting LM Studio, vLLM, LocalAI, and llama.cpp servers to AgentDroid
scope: Self-hosted OpenAI-compatible inference servers
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/user-guide/OLLAMA_SETUP.md
  - docs/security/NETWORK_SECURITY.md
---

# Custom Local LLM & OpenAI-Compatible Server Setup

## 1. Connecting LM Studio

LM Studio (`https://lmstudio.ai`) allows running local models with a local OpenAI-compatible inference server:

1. In LM Studio, load your desired model (e.g., `Meta-Llama-3.1-8B-Instruct`).
2. Go to the **Local Server** tab (double-arrow icon on the left).
3. Toggle the server to **ON**.
4. In **Server Settings**, verify:
   * **CORS**: Enabled.
   * **Network Binding**: Change from `127.0.0.1` to `0.0.0.0` or select your Wi-Fi interface.
   * Default Port: `1234`.
5. In AgentDroid:
   * Tap **Settings $\rightarrow$ Add Provider $\rightarrow$ LOCAL / LAN SERVERS $\rightarrow$ LM Studio**.
   * Base URL: `http://192.168.x.x:1234/v1` (or `http://10.0.2.2:1234/v1` on emulator).
   * Tap **Save & Connect**.
   * AgentDroid queries `/v1/models` and confirms connectivity!

---

## 2. Connecting vLLM / LocalAI / llama.cpp Server

AgentDroid connects to any standard OpenAI-compatible API endpoint:

| Server | Typical Launch Command | Default Base URL |
| :--- | :--- | :--- |
| **vLLM** | `python -m vllm.entrypoints.openai.api_server --model mistralai/Mistral-7B-Instruct-v0.3 --host 0.0.0.0 --port 8000` | `http://192.168.x.x:8000/v1` |
| **LocalAI** | `docker run -p 8080:8080 localai/localai:latest-cpu` | `http://192.168.x.x:8080/v1` |
| **llama.cpp** | `./llama-server -m models/llama-3.2-3b.gguf --host 0.0.0.0 --port 8080` | `http://192.168.x.x:8080/v1` |

### Configuration in AgentDroid:
1. Tap **Settings $\rightarrow$ Add Provider $\rightarrow$ LOCAL / LAN SERVERS $\rightarrow$ Custom Local LLM**.
2. Enter your server's Base URL (e.g. `http://192.168.1.50:8000/v1`).
3. If your server requires an optional Bearer token, paste it into the API Key field; otherwise leave it empty.
4. Tap **Save & Connect**.
