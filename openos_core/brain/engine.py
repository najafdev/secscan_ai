"""
OpenOS AI Brain Engine.

Main LLM orchestrator supporting multiple backends:
  - Ollama (local, function calling via ollama SDK)
  - OpenAI-compatible (copilot-api, LM Studio, vLLM, OpenAI, etc.)
  - Anthropic (Claude API)

Implements the agentic function-calling loop with automatic fallback.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from openos_core.config import get_config

logger = logging.getLogger(__name__)


# ─── Backend Abstraction ───


class LLMBackend:
    """Abstract base for LLM backends."""

    def chat(self, model: str, messages: list[dict], tools: list[dict], **kwargs) -> dict:
        raise NotImplementedError


class OllamaBackend(LLMBackend):
    """Ollama local LLM backend."""

    def __init__(self, host: str):
        import ollama
        self._client = ollama.Client(host=host)
        # Test connection
        self._client.list()
        logger.info(f"Ollama backend connected: {host}")

    def chat(self, model: str, messages: list[dict], tools: list[dict], **kwargs) -> dict:
        response = self._client.chat(
            model=model,
            messages=messages,
            tools=tools or [],
            options={
                "temperature": kwargs.get("temperature", 0.3),
                "num_predict": kwargs.get("max_tokens", 2048),
            },
        )
        msg = response.message
        # Normalize to common format
        tool_calls = None
        if msg.tool_calls:
            tool_calls = [
                {
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                }
                for tc in msg.tool_calls
            ]
        return {
            "role": msg.role,
            "content": msg.content or "",
            "tool_calls": tool_calls,
        }


class OpenAIBackend(LLMBackend):
    """OpenAI-compatible API backend (works with copilot-api, LM Studio, vLLM, OpenAI, etc.)."""

    def __init__(self, host: str, api_key: str = ""):
        from openai import OpenAI

        # Use provided key, env var, or dummy for local proxies
        key = api_key or "sk-local-proxy"
        base_url = host.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"

        self._client = OpenAI(base_url=base_url, api_key=key)
        self._supports_tools: bool | None = None  # Auto-detect
        logger.info(f"OpenAI-compatible backend connected: {base_url}")

    def _clean_messages(self, messages: list[dict]) -> list[dict]:
        """Clean messages for the API — remove tool-related fields if tools unsupported."""
        clean = []
        import json
        for m in messages:
            role = m["role"]
            # Skip tool messages if tools aren't supported
            if role == "tool" and self._supports_tools is False:
                continue
            cm = {"role": role, "content": m.get("content") or ""}

            if m.get("tool_calls") and self._supports_tools is not False:
                # OpenAI requires arguments to be a string in history
                tcs = []
                for tc in m["tool_calls"]:
                    tc_copy = dict(tc)
                    if "function" in tc_copy:
                        func_copy = dict(tc_copy["function"])
                        if not isinstance(func_copy.get("arguments"), str):
                            func_copy["arguments"] = json.dumps(func_copy.get("arguments", {}))
                        tc_copy["function"] = func_copy
                    tcs.append(tc_copy)
                cm["tool_calls"] = tcs

            if role == "tool" and m.get("tool_call_id"):
                cm["tool_call_id"] = m["tool_call_id"]
            clean.append(cm)
        return clean

    def chat(self, model: str, messages: list[dict], tools: list[dict], **kwargs) -> dict:
        call_kwargs = {
            "model": model,
            "messages": self._clean_messages(messages),
            "temperature": kwargs.get("temperature", 0.3),
            "max_tokens": kwargs.get("max_tokens", 2048),
        }

        # Only add tools if supported (or if we haven't checked yet)
        if tools and self._supports_tools is not False:
            openai_tools = []
            for t in tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": t["function"]["name"],
                        "description": t["function"].get("description", ""),
                        "parameters": t["function"].get("parameters", {}),
                    },
                })
            call_kwargs["tools"] = openai_tools
            call_kwargs["tool_choice"] = "auto"

        try:
            response = self._client.chat.completions.create(**call_kwargs)
            # If we got here with tools, they're supported
            if tools and self._supports_tools is None:
                self._supports_tools = True
        except Exception as e:
            # If tools caused the error, retry without them
            if tools and self._supports_tools is None:
                logger.info(f"API rejected tools, switching to prompt-only mode: {e}")
                self._supports_tools = False
                call_kwargs.pop("tools", None)
                call_kwargs.pop("tool_choice", None)
                call_kwargs["messages"] = self._clean_messages(messages)
                response = self._client.chat.completions.create(**call_kwargs)
            else:
                raise

        choice = response.choices[0]
        msg = choice.message

        # Normalize to common format
        tool_calls = None
        if msg.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": (
                            json.loads(tc.function.arguments)
                            if isinstance(tc.function.arguments, str)
                            else tc.function.arguments
                        ),
                    },
                }
                for tc in msg.tool_calls
            ]

        return {
            "role": msg.role,
            "content": msg.content or "",
            "tool_calls": tool_calls,
        }


# ─── Main Brain Engine ───


class OpenOSBrain:
    """
    Core AI engine — translates natural language into system actions.

    Supports multiple LLM backends with automatic fallback.
    Flow: User Input → LLM → Tool Call → Execute → Result → LLM → Response
    """

    def __init__(self):
        self.config = get_config()
        self._model = self.config.llm.default_model
        self._messages: list[dict] = []
        self._router = None
        self._memory = None
        self._backend: Optional[LLMBackend] = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the brain: connect to LLM backend, load tools and memory."""
        try:
            # Try primary backend
            self._backend = self._create_backend(
                self.config.llm.backend,
                self.config.llm.host,
                self.config.llm.api_key,
            )
            self._model = self.config.llm.default_model
            logger.info(f"Using {self.config.llm.backend} backend, model: {self._model}")

        except Exception as e:
            logger.warning(f"Primary backend ({self.config.llm.backend}) failed: {e}")

            # Try fallback if configured
            if self.config.llm.fallback_backend:
                try:
                    self._backend = self._create_backend(
                        self.config.llm.fallback_backend,
                        self.config.llm.fallback_host,
                        "",
                    )
                    self._model = self.config.llm.fallback_model
                    logger.info(f"Using fallback: {self.config.llm.fallback_backend}")
                except Exception as e2:
                    logger.error(f"Fallback also failed: {e2}")
                    return False
            else:
                return False

        try:
            # Initialize memory
            from openos_core.brain.memory import MemoryStore
            self._memory = MemoryStore()

            # Initialize and discover tools
            from openos_core.brain.router import ToolRouter
            self._router = ToolRouter()
            self._router.discover_and_register()

            # Build system prompt
            from openos_core.brain.prompts import build_system_prompt
            system_prompt = build_system_prompt(
                tool_descriptions=self._router.get_tool_descriptions(),
                memory=self._memory,
                include_routine=True,
            )
            self._messages = [{"role": "system", "content": system_prompt}]
            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"Brain init failed: {e}")
            return False

    def _create_backend(self, backend_type: str, host: str, api_key: str) -> LLMBackend:
        """Factory for creating LLM backends."""
        if backend_type == "ollama":
            return OllamaBackend(host=host)
        elif backend_type in ("openai", "copilot-api", "lmstudio", "vllm"):
            return OpenAIBackend(host=host, api_key=api_key)
        elif backend_type == "anthropic":
            # Could add Anthropic SDK here in the future
            return OpenAIBackend(host=host, api_key=api_key)
        else:
            raise ValueError(f"Unknown backend: {backend_type}")

    @property
    def is_ready(self) -> bool:
        return bool(self._initialized)

    @property
    def backend_name(self) -> str:
        return self.config.llm.backend if self._backend else "none"

    async def process(self, user_input: str) -> dict[str, Any]:
        """
        Process a natural language input and return a response.

        Returns dict with:
          - response: str (text response to show user)
          - actions: list[dict] (tool actions taken)
          - requires_confirmation: bool
          - confirm_message: str (if confirmation needed)
        """
        if not self._initialized:
            ok = await self.initialize()
            if not ok:
                return {
                    "response": "⚠️  I can't connect to any AI backend. Check your config:\n"
                    f"  Backend: {self.config.llm.backend}\n"
                    f"  Host: {self.config.llm.host}\n"
                    "  Run: openos --help for setup instructions.",
                    "actions": [],
                }

        self._messages.append({"role": "user", "content": user_input})
        actions_taken: list[Any] = []
        max_rounds = 10  # Safety limit on tool-call loops

        for _ in range(max_rounds):
            try:
                assert self._backend is not None
                result = self._backend.chat(
                    model=self._model,
                    messages=self._messages,
                    tools=self._router.get_schemas() if self._router else [],
                    temperature=self.config.llm.temperature,
                    max_tokens=self.config.llm.max_tokens,
                )
            except Exception as e:
                error_msg = f"LLM error: {e}"
                logger.error(error_msg)
                self._messages.pop()  # Remove failed user msg
                return {"response": f"⚠️  {error_msg}", "actions": []}

            # Add assistant message to history
            self._messages.append(result)

            # If no tool calls, we have the final response
            if not result.get("tool_calls"):
                if self._memory:
                    self._memory.record_command(
                        user_input,
                        result.get("content", "no response"),
                        success=True,
                    )
                return {
                    "response": result.get("content", "Done."),
                    "actions": actions_taken,
                }

            # Process each tool call
            for tool_call in result["tool_calls"]:
                func_name = tool_call["function"]["name"]
                func_args = tool_call["function"]["arguments"]
                tool_call_id = tool_call.get("id", func_name)

                logger.info(f"Tool call: {func_name}({func_args})")

                exec_result = await self._router.execute(func_name, func_args)

                # Handle confirmation-required actions
                if exec_result.get("requires_confirmation"):
                    return {
                        "response": "",
                        "actions": actions_taken,
                        "requires_confirmation": True,
                        "confirm_message": exec_result["confirm_message"],
                        "pending_function": func_name,
                        "pending_arguments": func_args,
                    }

                actions_taken.append({
                    "tool": func_name,
                    "args": func_args,
                    "result": exec_result,
                })

                # Feed result back to LLM
                self._messages.append({
                    "role": "tool",
                    "content": exec_result.get("result", exec_result.get("error", "No output")),
                    "tool_call_id": tool_call_id,
                })

        return {
            "response": "I completed the available actions.",
            "actions": actions_taken,
        }

    async def confirm_and_execute(self, func_name: str, args: dict) -> dict:
        """Execute a previously confirmed destructive action."""
        if not self._router:
            return {"response": "Not initialized", "actions": []}

        result = await self._router.execute_confirmed(func_name, args)

        self._messages.append({
            "role": "tool",
            "content": result.get("result", result.get("error", "")),
            "tool_call_id": func_name,
        })

        try:
            assert self._backend is not None
            resp = self._backend.chat(
                model=self._model,
                messages=self._messages,
                tools=[],
            )
            final = resp.get("content", "Done.")
        except Exception:
            final = result.get("result", "Action completed.")

        return {"response": final, "actions": [{"tool": func_name, "result": result}]}

    def set_model(self, model_name: str) -> str:
        """Switch the active LLM model."""
        self._model = model_name
        return f"Switched to model: {model_name}"

    def set_backend(self, backend: str, host: str, api_key: str = "") -> str:
        """Switch the LLM backend at runtime."""
        try:
            self._backend = self._create_backend(backend, host, api_key)
            self.config.llm.backend = backend
            self.config.llm.host = host
            if api_key:
                self.config.llm.api_key = api_key
            return f"Switched to {backend} backend at {host}"
        except Exception as e:
            return f"Failed to switch backend: {e}"

    def clear_context(self) -> None:
        """Clear conversation history (keep system prompt)."""
        if self._messages:
            self._messages = self._messages[:1]

    def shutdown(self) -> None:
        """Clean shutdown."""
        if self._memory:
            self._memory.close()
