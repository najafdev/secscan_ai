"""
HackBot AI Engine
=================
Manages LLM interactions with support for multiple providers (OpenAI, Ollama, etc.).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from openai import OpenAI

from hackbot.config import AIConfig

# ── Provider Registry ────────────────────────────────────────────────────────

PROVIDERS: Dict[str, Dict[str, Any]] = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "models": [
            {"id": "gpt-5.2", "name": "GPT-5.2 (latest flagship)", "ctx": 128000},
            {"id": "gpt-5.1", "name": "GPT-5.1 (reasoning + code)", "ctx": 128000},
            {"id": "gpt-5.2-codex", "name": "GPT-5.2 Codex (coding)", "ctx": 128000},
            {"id": "gpt-5.2-codex-mini", "name": "GPT-5.2 Codex Mini (fast coding)", "ctx": 128000},
            {"id": "gpt-4o", "name": "GPT-4o (recommended)", "ctx": 128000},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini (fast/cheap)", "ctx": 128000},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "ctx": 128000},
            {"id": "o3-mini", "name": "o3-mini (reasoning)", "ctx": 200000},
            {"id": "o1", "name": "o1 (reasoning)", "ctx": 200000},
        ],
    },
    "anthropic": {
        "name": "Anthropic (Claude)",
        "base_url": "https://api.anthropic.com/v1",
        "env_key": "ANTHROPIC_API_KEY",
        "models": [
            {"id": "claude-opus-4.6", "name": "Claude Opus 4.6 (latest)", "ctx": 200000},
            {"id": "claude-opus-4.5", "name": "Claude Opus 4.5 (research + code)", "ctx": 200000},
            {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4 (recommended)", "ctx": 200000},
            {"id": "claude-opus-4-20250514", "name": "Claude Opus 4", "ctx": 200000},
            {"id": "claude-3-7-sonnet-20250219", "name": "Claude 3.7 Sonnet", "ctx": 200000},
            {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku (fast)", "ctx": 200000},
        ],
    },
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "env_key": "GEMINI_API_KEY",
        "models": [
            {"id": "gemini-3-pro", "name": "Gemini 3 Pro (latest)", "ctx": 1000000},
            {"id": "gemini-3-flash-preview", "name": "Gemini 3 Flash Preview (fast)", "ctx": 1000000},
            {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro (recommended)", "ctx": 1000000},
            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "ctx": 1000000},
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "ctx": 1000000},
        ],
    },
    "groq": {
        "name": "Groq (Ultra-fast)",
        "base_url": "https://api.groq.com/openai/v1",
        "env_key": "GROQ_API_KEY",
        "models": [
            {"id": "llama-3.3-70b-versatile", "name": "LLaMA 3.3 70B (recommended)", "ctx": 128000},
            {"id": "llama-3.1-405b-reasoning", "name": "LLaMA 3.1 405B (reasoning)", "ctx": 131072},
            {"id": "llama-3.1-8b-instant", "name": "LLaMA 3.1 8B (fast)", "ctx": 128000},
            {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B", "ctx": 32768},
            {"id": "gemma2-9b-it", "name": "Gemma 2 9B", "ctx": 8192},
        ],
    },
    "mistral": {
        "name": "Mistral AI",
        "base_url": "https://api.mistral.ai/v1",
        "env_key": "MISTRAL_API_KEY",
        "models": [
            {"id": "mistral-large-2", "name": "Mistral Large 2 (latest)", "ctx": 128000},
            {"id": "mistral-large-latest", "name": "Mistral Large (recommended)", "ctx": 128000},
            {"id": "mistral-small-latest", "name": "Mistral Small (fast)", "ctx": 32000},
            {"id": "codestral-latest", "name": "Codestral (code)", "ctx": 32000},
            {"id": "open-mistral-nemo", "name": "Mistral Nemo (open)", "ctx": 128000},
        ],
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "env_key": "DEEPSEEK_API_KEY",
        "models": [
            {"id": "deepseek-chat", "name": "DeepSeek V3 (recommended)", "ctx": 64000},
            {"id": "deepseek-reasoner", "name": "DeepSeek R1 (reasoning)", "ctx": 64000},
        ],
    },
    "together": {
        "name": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "env_key": "TOGETHER_API_KEY",
        "models": [
            {"id": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo", "name": "LLaMA 3.1 405B Turbo", "ctx": 131072},
            {"id": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", "name": "LLaMA 3.1 70B Turbo", "ctx": 131072},
            {"id": "TinyLlama/TinyLlama-1.1B-Chat-v1.0", "name": "TinyLlama 1.1B Chat (low-end PC)", "ctx": 2048},
            {"id": "Qwen/Qwen2.5-72B-Instruct-Turbo", "name": "Qwen 2.5 72B", "ctx": 32768},
            {"id": "mistralai/Mistral-Large-2-Instruct", "name": "Mistral Large 2", "ctx": 128000},
            {"id": "deepseek-ai/DeepSeek-R1", "name": "DeepSeek R1", "ctx": 64000},
        ],
    },
    "openrouter": {
        "name": "OpenRouter (Multi-provider)",
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "models": [
            {"id": "openai/gpt-5.2", "name": "GPT-5.2", "ctx": 128000},
            {"id": "openai/gpt-5.1", "name": "GPT-5.1", "ctx": 128000},
            {"id": "anthropic/claude-opus-4.6", "name": "Claude Opus 4.6", "ctx": 200000},
            {"id": "anthropic/claude-opus-4.5", "name": "Claude Opus 4.5", "ctx": 200000},
            {"id": "google/gemini-3-pro", "name": "Gemini 3 Pro", "ctx": 1000000},
            {"id": "openai/gpt-4o", "name": "GPT-4o", "ctx": 128000},
            {"id": "meta-llama/llama-3.1-405b-instruct", "name": "LLaMA 3.1 405B", "ctx": 131072},
            {"id": "tinyllama/tinyllama-1.1b-chat", "name": "TinyLlama 1.1B Chat (low-end PC)", "ctx": 2048},
            {"id": "xploiter/pentester", "name": "Pentester (ethical hacking)", "ctx": 8192},
            {"id": "whiterabbitneo/whiterabbitneo-13b", "name": "WhiteRabbitNeo 13B (cybersecurity)", "ctx": 8192},
            {"id": "deepseek/deepseek-r1", "name": "DeepSeek R1", "ctx": 64000},
            {"id": "mistralai/mistral-large-2", "name": "Mistral Large 2", "ctx": 128000},
        ],
    },
    "ollama": {
        "name": "Ollama (Local)",
        "base_url": "http://localhost:11434/v1",
        "env_key": "",
        "models": [
            {"id": "llama3.1:405b", "name": "LLaMA 3.1 405B", "ctx": 131072},
            {"id": "llama3.1:70b", "name": "LLaMA 3.1 70B", "ctx": 128000},
            {"id": "llama3.2", "name": "LLaMA 3.2 (default)", "ctx": 128000},
            {"id": "tinyllama", "name": "TinyLlama 1.1B (low-end PC)", "ctx": 2048},
            {"id": "xploiter/pentester", "name": "Pentester (ethical hacking / offensive security)", "ctx": 8192},
            {"id": "whiterabbitneo", "name": "WhiteRabbitNeo (cybersecurity)", "ctx": 8192},
            {"id": "mistral", "name": "Mistral 7B", "ctx": 32000},
            {"id": "mixtral", "name": "Mixtral 8x7B", "ctx": 32000},
            {"id": "vicuna:13b", "name": "Vicuna 13B", "ctx": 16384},
            {"id": "deepseek-r1:14b", "name": "DeepSeek R1 14B", "ctx": 64000},
            {"id": "qwen2.5:14b", "name": "Qwen 2.5 14B", "ctx": 32768},
            {"id": "glm4:9b", "name": "GLM-4 9B", "ctx": 128000},
        ],
    },
    "local": {
        "name": "Local / Custom Endpoint",
        "base_url": "http://localhost:8080/v1",
        "env_key": "",
        "models": [
            {"id": "default", "name": "Default model on server", "ctx": 4096},
        ],
    },
}

# ── System Prompts ───────────────────────────────────────────────────────────

SYSTEM_PROMPT_CHAT = """You are HackBot, an expert cybersecurity AI assistant.

IDENTITY & CREDITS:
You were created and developed by **Yashab Alam**.
- GitHub: https://github.com/yashab-cyber
- LinkedIn: https://www.linkedin.com/in/yashab-alam
- Email: yashabalam707@gmail.com / yashabalam9@gmail.com
HackBot is a free and open-source project. If anyone asks who made you, who developed you,
who created you, or who is your developer/author/creator, always credit Yashab Alam with
the details above. Do NOT say you were made by OpenAI, Anthropic, Google, or any AI provider.
You are powered by an AI model, but you are HackBot — built by Yashab Alam.

You have deep knowledge of:
- Penetration testing methodologies (OWASP, PTES, OSSTMM)
- Network security, web application security, mobile security
- Vulnerability assessment and exploitation techniques
- Security tools: nmap, Burp Suite, Metasploit, sqlmap, nikto, etc.
- Reverse engineering and malware analysis
- Cryptography and secure coding practices
- Incident response and digital forensics
- Cloud security (AWS, Azure, GCP)
- Active Directory attacks and defense
- Social engineering and phishing
- CTF challenges and bug bounty hunting

You provide detailed, accurate, and actionable security guidance.
Always emphasize ethical hacking and responsible disclosure.
Format responses with clear sections, code blocks, and examples when appropriate."""

SYSTEM_PROMPT_AGENT = """You are HackBot Agent, an autonomous cybersecurity testing AI.
You can execute real security tools and commands to perform penetration testing.

IDENTITY & CREDITS:
You were created and developed by **Yashab Alam**.
- GitHub: https://github.com/yashab-cyber
- LinkedIn: https://www.linkedin.com/in/yashab-alam
- Email: yashabalam707@gmail.com / yashabalam9@gmail.com
HackBot is a free and open-source project. If anyone asks who made you, who developed you,
who created you, or who is your developer/author/creator, always credit Yashab Alam with
the details above. Do NOT say you were made by OpenAI, Anthropic, Google, or any AI provider.
You are powered by an AI model, but you are HackBot — built by Yashab Alam.

CRITICAL — ACTION BLOCK FORMAT (MANDATORY):
You MUST use JSON action blocks to execute commands. Do NOT just describe commands in
plain text — they will NOT be executed unless wrapped in a JSON action block.
Every time you want to run a tool, you MUST include the JSON block. No exceptions.

IMPORTANT RULES:
1. You MUST only test targets you have explicit authorization to test
2. Always start with reconnaissance before active testing
3. Follow a structured methodology: Recon → Scanning → Enumeration → Exploitation → Post-Exploitation → Reporting
4. Explain what each command does before executing it
5. Analyze output thoroughly and determine next steps intelligently
6. Document all findings with severity ratings (Critical/High/Medium/Low/Info)
7. If safe_mode is enabled, avoid destructive or highly aggressive scans
8. Do NOT append interactive slash commands (like `/cve`, `/osint`, `/topology`, `/remediate`, `/compliance`) to command-line arguments. These are separate interactive commands, not tool parameters.

BUILT-IN INTELLIGENCE:
- CVE Lookup: After running nmap or service detection, you can ask the user to run /cve with service names to auto-map discovered services to known CVEs from the NVD database.
- OSINT Module: Before active scanning, recommend running /osint against the target domain for passive reconnaissance (subdomains, DNS records, WHOIS, tech stack fingerprinting).
- After nmap/masscan scans, recommend /topology to visualize the network map.
- Compliance Mapping: After collecting findings, recommend /compliance to automatically map them to PCI DSS, NIST 800-53, OWASP Top 10, and ISO 27001 controls. You can also filter by framework, e.g. /compliance pci nist.
- Diff Reports: If this is a follow-up assessment, recommend /diff to compare with a previous session and see which vulnerabilities are new, fixed, or persistent.
- AI Remediation: After collecting findings, recommend /remediate to auto-generate specific fix commands, config patches, and code snippets for each finding. Use /remediate # for a single finding or /remediate --ai for AI-enhanced guidance.
- HTTP Proxy / Traffic Capture: For web application testing, recommend /proxy start to launch the built-in intercepting proxy. It automatically detects auth tokens, cookies, credentials, SQL injection patterns, and API keys in traffic. Use /proxy traffic to review captured requests and /proxy flags to see flagged security-relevant traffic. The proxy supports domain scoping via /proxy scope, request replay via /proxy replay, and traffic export via /proxy export.
- Multi-Target Campaigns: If you see "CAMPAIGN CONTEXT" in the assessment context, you are part of a coordinated multi-target campaign. Use intelligence from previously assessed targets to guide your testing — look for similar vulnerabilities, shared infrastructure, lateral movement opportunities, and common misconfigurations across the campaign scope.
- Custom Plugins: Users may have registered custom plugin tools. If custom plugins are listed in the assessment context, you can call them using:
  ```json
  {"action": "execute", "tool": "hackbot-plugin", "command": "hackbot-plugin <plugin_name> --arg1 value1 --arg2 value2", "explanation": "<why>"}
  ```

ZERO-DAY HUNTING PROTOCOL:
You are equipped with a ZeroDayEngine that provides:

1. **Deep Service Fingerprinting** — Beyond version banners, probe for behavioral anomalies:
   - Non-standard response headers, unusual timing patterns, unexpected error messages
   - Compare behavior against known software signatures to detect custom/patched versions
   - Run targeted nmap NSE scripts (e.g., --script=vulners,http-shellshock,http-vuln-*)

2. **Response Anomaly Detection** — Every tool result is auto-analyzed for zero-day signals:
   - Stack traces, debug info, memory addresses, path disclosures, auth leaks
   - Timing anomalies suggesting blind injection points
   - Error messages revealing backend technology for targeted attacks

3. **Smart Fuzzing** — You can trigger intelligent fuzzing:
   ```json
   {"action": "fuzz", "target_url": "<url>", "parameter": "<param>", "categories": ["xss","command_injection","template_injection"], "explanation": "<why>"}
   ```
   Categories: buffer_overflow, integer_overflow, path_traversal, template_injection, ssrf, deserialization, command_injection, xss, header_injection, xxe, request_smuggling, race_condition

4. **Anomaly Deep-Analysis** — When you spot a suspicious response, analyze it:
   ```json
   {"action": "analyze_anomaly", "response_body": "<suspicious_output>", "context": "<what_triggered_it>", "explanation": "<why>"}
   ```

5. **Exploit Chain Building** — Combine multiple findings into attack chains:
   ```json
   {"action": "chain_exploits", "explanation": "Analyze current findings for exploit chains"}
   ```

6. **Active Scanning (Crawl → Map → Fuzz → Analyze loop)** — Full autonomous attack cycle:
   ```json
   {"action": "active_scan", "target_url": "<url>", "depth": 3, "max_iterations": 20, "explanation": "<why>"}
   ```
   This crawls the target, maps all endpoints/parameters/forms, scores them by attack interest,
   then iteratively fuzzes high-value targets with AI-driven payload selection. Maintains sessions,
   cookies, CSRF tokens, and auth state throughout the scan.

7. **Target Mapping** — Crawl and map a target's attack surface without fuzzing:
   ```json
   {"action": "map_target", "target_url": "<url>", "explanation": "<why>"}
   ```
   Returns: discovered endpoints, forms, parameters, technology stack, and interest scores.

8. **Stateful Fuzzing** — Session-aware fuzzing with auth and CSRF handling:
   ```json
   {"action": "fuzz_stateful", "target_url": "<url>", "parameter": "<param>", "method": "POST", "categories": ["xss","command_injection"], "auth": {"username": "...", "password": "...", "login_url": "..."}, "explanation": "<why>"}
   ```
   Automatically maintains session cookies, extracts and refreshes CSRF tokens, and tracks
   response baselines to detect deviations.

9. **Race Condition Testing** — Concurrent request testing for TOCTOU vulnerabilities:
   ```json
   {"action": "race_test", "target_url": "<url>", "method": "POST", "data": {"param": "value"}, "count": 20, "explanation": "<why>"}
   ```
   Sends N simultaneous requests using thread barriers and analyzes response differences
   to detect race conditions.

10. **Autonomous Tool Installation** — If a tool you need is not installed (a command
   returns "Tool not found"), you can install it autonomously:
   ```json
   {"action": "install", "tool": "<tool_name>", "explanation": "<why you need it>"}
   ```
   Only allowlisted security tools with a known install recipe can be installed.
   When safe_mode is on, the user confirms each install. After a successful install,
   re-run the original command. If the install fails or no recipe exists, adapt and
   use a different tool.

ZERO-DAY METHODOLOGY:
- After initial recon, identify services with unusual behaviors or outdated versions
- Use nuclei with community templates for latest vulnerability checks
- **Map first**: Run map_target to crawl and discover all endpoints before fuzzing
- **Active scan**: For thorough testing, use active_scan to run the full automated attack loop
- Run targeted fuzzing on discovered parameters, especially in custom web applications
- Use fuzz_stateful for endpoints that require authentication or CSRF tokens
- Look for timing anomalies in authentication, search, and API endpoints
- Check for template injection (SSTI) in any user-controlled output
- Test for SSRF in any URL/webhook/redirect parameter
- Check deserialization in cookies, tokens, and API payloads
- **Race conditions**: Use race_test on state-changing endpoints (transfers, votes, purchases)
- Analyze response differences between valid/invalid inputs for blind injection
- When you find multiple low/medium vulns, use chain_exploits to propose attack paths
- Generate custom exploit scripts when standard tools are insufficient

REQUIRED FORMAT — To run a command, you MUST include this JSON action block in your response:
```json
{"action": "execute", "tool": "<tool_name>", "command": "<full_command>", "explanation": "<why>"}
```

CRITICAL COMMAND RULES:
- The "command" field MUST be a real shell command starting with the tool binary name.
- Do NOT include "sudo" in the command — sudo is handled automatically by the system.
- The "tool" field should match the binary name (e.g., "nmap", "nikto", "sqlmap").

EXAMPLES of CORRECT commands:
```json
{"action": "execute", "tool": "nmap", "command": "nmap -sV -sC -T4 192.168.1.1", "explanation": "Full port scan with version detection and scripts"}
```
```json
{"action": "execute", "tool": "dnsrecon", "command": "dnsrecon -d example.com -t std", "explanation": "Standard DNS enumeration"}
```
```json
{"action": "execute", "tool": "nikto", "command": "nikto -h http://192.168.1.1", "explanation": "Web vulnerability scan"}
```
```json
{"action": "execute", "tool": "gobuster", "command": "gobuster dir -u http://192.168.1.1 -w /usr/share/wordlists/dirb/common.txt", "explanation": "Directory bruteforce"}
```

EXAMPLES of WRONG commands (DO NOT do this):
- ❌ "command": "sudo -n nmap -sV target"  (do NOT include sudo)
- ❌ "command": "sudo -n --target 192.168.1.1 --output json"  (missing tool name)
- ❌ "command": "-sV -sC 192.168.1.1"  (missing tool binary at start)

To report a finding:
```json
{"action": "finding", "title": "<title>", "severity": "<Critical|High|Medium|Low|Info>", "description": "<details>", "evidence": "<output>", "recommendation": "<fix>"}
```

To save a generated script or exploit helper for this assessment:
```json
{"action": "script", "name": "<filename>", "language": "<bash|python|powershell|...>", "purpose": "<why this script exists>", "content": "<full script content>"}
```

When you are done with the assessment:
```json
{"action": "complete", "summary": "<assessment_summary>"}
```

To generate a professional PDF report (at the end of the assessment, or when the user asks):
```json
{"action": "generate_report", "format": "pdf", "include_compliance": true}
```

You may include multiple action blocks in a single response along with your analysis text.
REMEMBER: Always include the JSON action block — never just describe commands in text."""

SYSTEM_PROMPT_PLAN = """You are HackBot Planner, a cybersecurity assessment planning AI.
You create detailed, structured penetration testing plans and attack strategies.

IDENTITY & CREDITS:
You were created and developed by **Yashab Alam**.
- GitHub: https://github.com/yashab-cyber
- LinkedIn: https://www.linkedin.com/in/yashab-alam
- Email: yashabalam707@gmail.com / yashabalam9@gmail.com
HackBot is a free and open-source project. If anyone asks who made you, who developed you,
who created you, or who is your developer/author/creator, always credit Yashab Alam with
the details above. Do NOT say you were made by OpenAI, Anthropic, Google, or any AI provider.
You are powered by an AI model, but you are HackBot — built by Yashab Alam.

Your plans should include:
1. Scope definition and rules of engagement
2. Methodology selection (OWASP, PTES, etc.)
3. Phase-by-phase breakdown with specific tools and techniques
4. Risk assessment and contingency plans
5. Timeline estimates
6. Required tools and resources
7. Reporting templates and deliverables

Format plans as structured documents with clear sections and checklists.
Include specific commands and tool configurations where appropriate."""


# ── Message Types ────────────────────────────────────────────────────────────

@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_api(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class Conversation:
    messages: List[Message] = field(default_factory=list)
    mode: str = "chat"
    target: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add(self, role: str, content: str, **meta: Any) -> Message:
        msg = Message(role=role, content=content, metadata=meta)
        self.messages.append(msg)
        return msg

    def to_api_messages(self) -> List[Dict[str, str]]:
        return [m.to_api() for m in self.messages]

    def clear(self) -> None:
        system_msgs = [m for m in self.messages if m.role == "system"]
        self.messages = system_msgs


# ── AI Engine ────────────────────────────────────────────────────────────────

class AIEngine:
    """Core AI engine that handles LLM communication."""

    def __init__(self, config: AIConfig):
        self.config = config
        self._client: Optional[OpenAI] = None
        self._setup_client()

    def _setup_client(self) -> None:
        """Initialize the OpenAI-compatible client for any provider."""
        provider = self.config.provider
        preset = PROVIDERS.get(provider, {})
        api_key = self.config.api_key
        base_url = self.config.base_url

        # Use preset base_url if user hasn't overridden
        if not base_url and preset:
            base_url = str(preset.get("base_url", ""))

        kwargs: Dict[str, Any] = {"api_key": api_key or "unused"}

        if base_url:
            kwargs["base_url"] = base_url

        # Provider-specific tweaks
        if provider == "ollama":
            kwargs["api_key"] = api_key or "ollama"
        elif provider == "local":
            kwargs["api_key"] = api_key or "local"

        self._client = OpenAI(**kwargs)

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._setup_client()
        assert self._client is not None
        return self._client

    def chat(
        self,
        conversation: Optional[Conversation] = None,
        stream: bool = True,
        on_token: Optional[Callable[[str], None]] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        **kwargs: Any,
    ) -> str:
        """Send conversation to LLM and return response."""
        if conversation is not None:
            api_messages = conversation.to_api_messages()
        elif messages is not None:
            api_messages = messages
        else:
            raise ValueError("Either conversation or messages must be provided")

        if stream and on_token:
            return self._stream_chat(api_messages, on_token)
        else:
            return self._blocking_chat(api_messages)

    def _blocking_chat(self, messages: Any) -> str:
        response: Any = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        return response.choices[0].message.content or ""

    def _stream_chat(
        self,
        messages: Any,
        on_token: Callable[[str], None],
    ) -> str:
        stream: Any = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            stream=True,
        )
        full_response = []
        for chunk in stream:
            if getattr(chunk, "choices", None) and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_response.append(token)
                on_token(token)
        return "".join(full_response)

    def quick_ask(self, prompt: str, system: str = "") -> str:
        """One-shot question without conversation history."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self._blocking_chat(messages)

    def is_configured(self) -> bool:
        """Check if API key or custom base URL is set."""
        # A custom base_url (e.g. local proxy) counts as configured even
        # without an explicit API key, and so do keyless providers.
        if self.config.base_url:
            return True
        if self.config.provider in ("ollama", "local"):
            return True
        return bool(self.config.api_key)

    def validate_api_key(self, timeout: float = 10.0) -> Dict[str, Any]:
        """Validate the current API key by making a lightweight test request.

        Sends a minimal chat completion to verify the key and endpoint work.
        Skips validation for keyless providers (ollama, local).

        Args:
            timeout: Max seconds to wait for the validation request.

        Returns:
            Dict with 'valid' (bool), 'message' (str), and optionally 'error'.
        """
        provider = self.config.provider

        # Keyless local providers — always "valid"
        if provider in ("ollama", "local"):
            return {"valid": True, "message": f"{provider} provider does not require an API key"}

        if not self.config.api_key and not self.config.base_url:
            return {"valid": False, "message": "No API key configured", "error": "missing_key"}

        try:
            # Use a tiny request with max_tokens=1 to minimize cost
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
                timeout=timeout,
            )
            model_used = getattr(response, "model", self.config.model)
            return {
                "valid": True,
                "message": f"API key is valid — connected to {provider}/{model_used}",
            }
        except Exception as e:
            err_msg = str(e)
            # Parse common error patterns
            if "401" in err_msg or "Unauthorized" in err_msg or "invalid" in err_msg.lower():
                friendly = "Invalid API key — authentication failed"
            elif "403" in err_msg or "Forbidden" in err_msg:
                friendly = "API key lacks required permissions"
            elif "404" in err_msg or "not found" in err_msg.lower():
                friendly = f"Model '{self.config.model}' not found — check model name or provider"
            elif "429" in err_msg or "rate" in err_msg.lower():
                friendly = "Rate limited — key is valid but quota exceeded"
                return {"valid": True, "message": friendly}
            elif "timeout" in err_msg.lower() or "timed out" in err_msg.lower():
                friendly = f"Connection timed out — cannot reach {provider} endpoint"
            elif "connection" in err_msg.lower() or "connect" in err_msg.lower():
                friendly = f"Connection error — cannot reach {provider} endpoint"
            else:
                friendly = f"API key validation failed: {err_msg[:200]}"

            return {"valid": False, "message": friendly, "error": err_msg[:500]}


# ── Supported Languages ──────────────────────────────────────────────────────

SUPPORTED_LANGUAGES: Dict[str, str] = {
    "English": "English",
    "Spanish": "Español",
    "French": "Français",
    "German": "Deutsch",
    "Italian": "Italiano",
    "Portuguese": "Português",
    "Russian": "Русский",
    "Chinese": "中文",
    "Japanese": "日本語",
    "Korean": "한국어",
    "Arabic": "العربية",
    "Hindi": "हिन्दी",
    "Bengali": "বাংলা",
    "Urdu": "اردو",
    "Turkish": "Türkçe",
    "Vietnamese": "Tiếng Việt",
    "Thai": "ไทย",
    "Indonesian": "Bahasa Indonesia",
    "Malay": "Bahasa Melayu",
    "Dutch": "Nederlands",
    "Polish": "Polski",
    "Ukrainian": "Українська",
    "Czech": "Čeština",
    "Romanian": "Română",
    "Greek": "Ελληνικά",
    "Hungarian": "Magyar",
    "Swedish": "Svenska",
    "Norwegian": "Norsk",
    "Danish": "Dansk",
    "Finnish": "Suomi",
    "Hebrew": "עברית",
    "Persian": "فارسی",
    "Swahili": "Kiswahili",
    "Tamil": "தமிழ்",
    "Telugu": "తెలుగు",
    "Marathi": "मराठी",
    "Gujarati": "ગુજરાતી",
    "Kannada": "ಕನ್ನಡ",
    "Malayalam": "മലയാളം",
    "Punjabi": "ਪੰਜਾਬੀ",
    "Tagalog": "Tagalog",
    "Burmese": "မြန်မာ",
    "Khmer": "ភាសាខ្មែរ",
    "Lao": "ລາວ",
    "Nepali": "नेपाली",
    "Sinhala": "සිංහල",
    "Amharic": "አማርኛ",
    "Yoruba": "Yorùbá",
    "Igbo": "Igbo",
    "Hausa": "Hausa",
    "Zulu": "isiZulu",
    "Afrikaans": "Afrikaans",
    "Catalan": "Català",
    "Croatian": "Hrvatski",
    "Serbian": "Српски",
    "Slovak": "Slovenčina",
    "Slovenian": "Slovenščina",
    "Bulgarian": "Български",
    "Lithuanian": "Lietuvių",
    "Latvian": "Latviešu",
    "Estonian": "Eesti",
    "Georgian": "ქართული",
    "Armenian": "Հայերեն",
    "Azerbaijani": "Azərbaycan",
    "Kazakh": "Қазақ",
    "Uzbek": "Oʻzbek",
    "Mongolian": "Монгол",
    "Tibetan": "བོད་སྐད",
    "Pashto": "پښتو",
    "Kurdish": "Kurdî",
    "Somali": "Soomaali",
    "Malagasy": "Malagasy",
}


def _build_language_instruction(language: str) -> str:
    """Build a language instruction to inject into system prompts."""
    if not language or language == "English":
        return ""
    native = SUPPORTED_LANGUAGES.get(language, language)
    return (
        f"\n\nLANGUAGE INSTRUCTION:\n"
        f"You MUST respond in **{language}** ({native}). All your output — explanations, "
        f"analysis, findings, recommendations, plan text, and conversational replies — "
        f"MUST be written in {language}. Technical terms, tool names, command syntax, "
        f"code blocks, and JSON action blocks should remain in English, but all "
        f"surrounding text and descriptions must be in {language}."
    )


def create_conversation(mode: str, target: str = "", language: str = "English") -> Conversation:
    """Create a new conversation with the appropriate system prompt.

    Args:
        mode: Conversation mode — 'chat', 'agent', or 'plan'.
        target: Target for agent mode assessments.
        language: Language for AI responses (default: English).
    """
    conv = Conversation(mode=mode, target=target)
    lang_instruction = _build_language_instruction(language)

    if mode == "chat":
        conv.add("system", SYSTEM_PROMPT_CHAT + lang_instruction)
    elif mode == "agent":
        system = SYSTEM_PROMPT_AGENT
        if target:
            system += f"\n\nTarget for this assessment: {target}"
        conv.add("system", system + lang_instruction)
    elif mode == "plan":
        conv.add("system", SYSTEM_PROMPT_PLAN + lang_instruction)
    else:
        conv.add("system", SYSTEM_PROMPT_CHAT + lang_instruction)

    return conv
