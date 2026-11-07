# 6. AI Providers

HackBot supports **10 AI providers** out of the box. All providers use the OpenAI-compatible API format.

---

## Switching Providers

### CLI
```
/provider openai                     # Switch to OpenAI
/provider anthropic                  # Switch to Anthropic
/providers                           # List all providers
/models                              # List models for current provider
/models groq                         # List models for a specific provider
/key YOUR_API_KEY                    # Set API key (validates immediately)
```

### Terminal
```bash
hackbot setup YOUR_API_KEY --provider anthropic --model claude-sonnet-4-20250514
```

### GUI
Use the **Settings** panel — select provider from dropdown, pick a model, enter your API key, and click Validate.

---

## Provider Reference

### 1. OpenAI

| Field | Value |
|-------|-------|
| ID | `openai` |
| Base URL | `https://api.openai.com/v1` |
| Env Variable | `OPENAI_API_KEY` |

**Models:**
| Model | Description |
|-------|-------------|
| `gpt-5.2` | Latest GPT-5 series |
| `gpt-5.1` | GPT-5.1 |
| `gpt-5.2-codex` | Code-focused GPT-5 |
| `gpt-5.2-codex-mini` | Smaller code model |
| `gpt-4o` | Fast multimodal flagship |
| `gpt-4o-mini` | Cost-effective small model |
| `gpt-4-turbo` | Previous generation turbo |
| `o3-mini` | Reasoning model (mini) |
| `o1` | Reasoning model |

---

### 2. Anthropic (Claude)

| Field | Value |
|-------|-------|
| ID | `anthropic` |
| Base URL | `https://api.anthropic.com/v1` |
| Env Variable | `ANTHROPIC_API_KEY` |

**Models:**
| Model | Description |
|-------|-------------|
| `claude-opus-4.6` | Latest Opus |
| `claude-opus-4.5` | Opus 4.5 |
| `claude-sonnet-4` | Sonnet 4 |
| `claude-opus-4` | Opus 4 |
| `claude-3-7-sonnet` | Claude 3.7 Sonnet |
| `claude-3-5-haiku` | Fast & affordable |

---

### 3. Google Gemini

| Field | Value |
|-------|-------|
| ID | `gemini` |
| Base URL | `https://generativelanguage.googleapis.com/...` |
| Env Variable | `GEMINI_API_KEY` or `GOOGLE_API_KEY` |

**Models:**
| Model | Description |
|-------|-------------|
| `gemini-3-pro` | Latest Gemini 3 Pro |
| `gemini-3-flash-preview` | Gemini 3 Flash preview |
| `gemini-2.5-pro` | Gemini 2.5 Pro |
| `gemini-2.5-flash` | Gemini 2.5 Flash |
| `gemini-2.0-flash` | Gemini 2.0 Flash |

---

### 4. Groq (Ultra-fast Inference)

| Field | Value |
|-------|-------|
| ID | `groq` |
| Base URL | `https://api.groq.com/openai/v1` |
| Env Variable | `GROQ_API_KEY` |

**Models:**
| Model | Description |
|-------|-------------|
| `llama-3.3-70b-versatile` | Llama 3.3 70B |
| `llama-3.1-405b-reasoning` | Llama 3.1 405B |
| `llama-3.1-8b-instant` | Fast 8B model |
| `mixtral-8x7b-32768` | Mixtral MoE |
| `gemma2-9b-it` | Google Gemma 2 |

---

### 5. Mistral AI

| Field | Value |
|-------|-------|
| ID | `mistral` |
| Base URL | `https://api.mistral.ai/v1` |
| Env Variable | `MISTRAL_API_KEY` |

**Models:**
| Model | Description |
|-------|-------------|
| `mistral-large-2` | Latest large model |
| `mistral-large-latest` | Large (latest alias) |
| `mistral-small-latest` | Small fast model |
| `codestral-latest` | Code-focused |
| `open-mistral-nemo` | Open Nemo model |

---

### 6. DeepSeek

| Field | Value |
|-------|-------|
| ID | `deepseek` |
| Base URL | `https://api.deepseek.com/v1` |
| Env Variable | `DEEPSEEK_API_KEY` |

**Models:**
| Model | Description |
|-------|-------------|
| `deepseek-chat` | DeepSeek V3 |
| `deepseek-reasoner` | DeepSeek R1 (reasoning) |

---

### 7. Together AI

| Field | Value |
|-------|-------|
| ID | `together` |
| Base URL | `https://api.together.xyz/v1` |
| Env Variable | `TOGETHER_API_KEY` |

**Models:**
| Model | Description |
|-------|-------------|
| `meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo` | Llama 405B Turbo |
| `meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo` | Llama 70B Turbo |
| `TinyLlama/TinyLlama-1.1B-Chat-v1.0` | TinyLlama 1.1B Chat (low-end PC) |
| `Qwen/Qwen2.5-72B-Instruct-Turbo` | Qwen 2.5 72B |
| `mistralai/Mistral-Large-2-Instruct-2411` | Mistral Large 2 |
| `deepseek-ai/DeepSeek-R1` | DeepSeek R1 |

---

### 8. OpenRouter (Multi-provider Gateway)

| Field | Value |
|-------|-------|
| ID | `openrouter` |
| Base URL | `https://openrouter.ai/api/v1` |
| Env Variable | `OPENROUTER_API_KEY` |

**Models:**
| Model | Description |
|-------|-------------|
| `openai/gpt-5.2` | GPT-5.2 via OpenRouter |
| `openai/gpt-5.1` | GPT-5.1 via OpenRouter |
| `anthropic/claude-opus-4.6` | Claude Opus 4.6 |
| `anthropic/claude-opus-4.5` | Claude Opus 4.5 |
| `google/gemini-3-pro` | Gemini 3 Pro |
| `openai/gpt-4o` | GPT-4o |
| `meta-llama/llama-3.1-405b-instruct` | Llama 405B |
| `tinyllama/tinyllama-1.1b-chat` | TinyLlama 1.1B Chat (low-end PC) |
| `whiterabbitneo/whiterabbitneo-13b` | WhiteRabbitNeo 13B (cybersecurity) |
| `deepseek/deepseek-r1` | DeepSeek R1 |
| `mistralai/mistral-large-2` | Mistral Large 2 |

---

### 9. Ollama (Local Models)

| Field | Value |
|-------|-------|
| ID | `ollama` |
| Base URL | `http://localhost:11434/v1` |
| API Key | Not required |

**Models:**
| Model | Description |
|-------|-------------|
| `llama3.1:405b` | Llama 3.1 405B (local) |
| `llama3.1:70b` | Llama 3.1 70B |
| `llama3.2` | Llama 3.2 |
| `tinyllama` | TinyLlama 1.1B (low-end PC, ~600 MB) |
| `xploiter/pentester` | Pentester (ethical hacking / offensive security) |
| `whiterabbitneo` | WhiteRabbitNeo (cybersecurity / pentesting) |
| `mistral` | Mistral 7B |
| `mixtral` | Mixtral MoE |
| `vicuna:13b` | Vicuna 13B |
| `deepseek-r1:14b` | DeepSeek R1 14B |
| `qwen2.5:14b` | Qwen 2.5 14B |
| `glm4:9b` | GLM-4 9B |

> Install Ollama from [ollama.com](https://ollama.com), then `ollama pull llama3.1:70b`.
> For low-end PCs: `ollama pull tinyllama` (only ~600 MB VRAM).
> For ethical hacking: `ollama pull xploiter/pentester` (recommended for pentesters).
> For cybersecurity: `ollama pull whiterabbitneo`.

#### Installing & Using Ollama Models

**Step 1 — Install Ollama**

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Windows — download installer from https://ollama.com/download
```

**Step 2 — Start the Ollama server**

```bash
ollama serve
# Runs on http://localhost:11434 by default
```

**Step 3 — Pull a model**

```bash
# General-purpose (pick one based on your hardware)
ollama pull llama3.2           # ~2 GB — good default
ollama pull llama3.1:70b       # ~40 GB — powerful, needs 48 GB+ RAM/VRAM
ollama pull llama3.1:405b      # ~230 GB — top-tier, needs high-end server

# Low-end / lightweight (runs on almost any machine)
ollama pull tinyllama           # ~600 MB — 1.1B params, 2 GB RAM is enough
ollama pull mistral             # ~4 GB — solid 7B model

# Cybersecurity / pentesting focused
ollama pull xploiter/pentester  # Best for ethical hacking & offensive security
ollama pull whiterabbitneo      # Trained for offensive security tasks

# Reasoning & code
ollama pull deepseek-r1:14b    # DeepSeek R1 reasoning model
ollama pull qwen2.5:14b        # Strong multilingual + code
ollama pull glm4:9b            # GLM-4 9B
```

**Step 4 — Use with HackBot**

```bash
# From the terminal
hackbot --provider ollama --model llama3.2
hackbot --provider ollama --model tinyllama
hackbot --provider ollama --model xploiter/pentester
hackbot --provider ollama --model whiterabbitneo

# Or inside the HackBot REPL
/provider ollama
/model llama3.2
/models ollama          # list all available Ollama models
```

**Step 5 — Custom Ollama host (remote server)**

If Ollama runs on another machine or a non-default port:

```bash
# CLI flag
hackbot --provider ollama --base-url http://192.168.1.100:11434/v1

# Or set in config.yaml
# ai:
#   provider: ollama
#   model: llama3.2
#   base_url: http://192.168.1.100:11434/v1
```

**Hardware Guidelines for Ollama Models:**

| Model | Parameters | RAM / VRAM | Best For |
|-------|-----------|------------|----------|
| `tinyllama` | 1.1B | ~2 GB | Low-end PCs, Raspberry Pi, quick tests |
| `mistral` | 7B | ~6 GB | Budget desktops, good all-rounder |
| `xploiter/pentester` | — | ~8 GB | Ethical hacking, offensive security (recommended) |
| `whiterabbitneo` | 13B | ~10 GB | Cybersecurity / pentesting tasks |
| `vicuna:13b` | 13B | ~10 GB | General conversation |
| `deepseek-r1:14b` | 14B | ~12 GB | Reasoning & code |
| `qwen2.5:14b` | 14B | ~12 GB | Multilingual + code |
| `mixtral` | 8x7B (MoE) | ~26 GB | High-quality, needs more RAM |
| `llama3.1:70b` | 70B | ~48 GB | Near-cloud quality locally |
| `llama3.1:405b` | 405B | ~230 GB | Server-grade, top performance |

> **Tip:** On low-end hardware, start with `tinyllama` or `mistral`. They provide usable cybersecurity assistance even on machines with 4–8 GB of RAM.

---

### 10. Local / Custom Endpoint

| Field | Value |
|-------|-------|
| ID | `local` |
| Base URL | `http://localhost:8080/v1` |
| API Key | Not required |

**Models:**
| Model | Description |
|-------|-------------|
| `default` | Uses whatever model is served at the endpoint |

> Use this for any OpenAI-compatible local server (vLLM, text-generation-webui, LocalAI, etc.).
> Override the base URL: `/provider local` then set `base_url` in config.

#### Using Local / Custom Model Servers

The `local` provider connects HackBot to any server that exposes an **OpenAI-compatible** `/v1/chat/completions` endpoint. This includes:

- [vLLM](https://github.com/vllm-project/vllm)
- [text-generation-webui](https://github.com/oobabooga/text-generation-webui) (with `--api` flag)
- [LocalAI](https://localai.io/)
- [LM Studio](https://lmstudio.ai/)
- [llama.cpp server](https://github.com/ggerganov/llama.cpp/tree/master/examples/server)
- Any custom FastAPI / Flask wrapper

**Example: vLLM**

```bash
# Start vLLM serving a model
python -m vllm.entrypoints.openai.api_server \
    --model TheBloke/Llama-2-13B-chat-GPTQ \
    --port 8080

# Connect HackBot
hackbot --provider local --base-url http://localhost:8080/v1 --model TheBloke/Llama-2-13B-chat-GPTQ
```

**Example: text-generation-webui**

```bash
# Start with API enabled
python server.py --api --listen-port 5000

# Connect HackBot
hackbot --provider local --base-url http://localhost:5000/v1
```

**Example: LM Studio**

```
1. Open LM Studio → download a model (e.g. TinyLlama, Mistral, etc.)
2. Go to "Local Server" tab → Start Server (default port 1234)
3. Connect HackBot:
```

```bash
hackbot --provider local --base-url http://localhost:1234/v1
```

**Example: llama.cpp server**

```bash
# Build and run llama.cpp server
./server -m models/tinyllama-1.1b-chat.Q4_K_M.gguf \
    --host 0.0.0.0 --port 8080

# Connect HackBot
hackbot --provider local --base-url http://localhost:8080/v1
```

**Inside the HackBot REPL:**

```
/provider local
/model default
```

To change the base URL at runtime, edit `~/.config/hackbot/config.yaml`:

```yaml
ai:
  provider: local
  model: default
  base_url: http://localhost:8080/v1
```

> **Tip:** The `local` provider sends `api_key: "local"` by default, which most local servers accept. If your server requires an actual key, set it with `/key YOUR_KEY`.

---

## Environment Variables

You can set API keys via environment variables instead of `/key`:

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export GEMINI_API_KEY=AIza...
export GROQ_API_KEY=gsk_...
export MISTRAL_API_KEY=...
export DEEPSEEK_API_KEY=sk-...
export TOGETHER_API_KEY=...
export OPENROUTER_API_KEY=sk-or-...

# Or the universal override:
export HACKBOT_API_KEY=your-key
export HACKBOT_PROVIDER=openai
export HACKBOT_MODEL=gpt-4o
```

---

Next: [Reporting →](07-reporting.md)
