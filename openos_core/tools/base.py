"""
OpenOS Base Tool Interface.

All tool modules inherit from BaseTool and use the @tool_function decorator
to expose methods to the LLM via Ollama's function-calling API.
"""

from __future__ import annotations

import functools
from abc import ABC, abstractmethod
from typing import Any, Callable


class BaseTool(ABC):
    """Abstract base class for all OpenOS tool modules."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name (e.g., 'file_manager')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of this tool's capabilities."""
        ...


def tool_function(
    description: str,
    parameters: dict[str, Any],
    destructive: bool = False,
    confirm_message: str = "",
) -> Callable:
    """
    Decorator to mark a method as an LLM-callable tool function.

    Args:
        description: What this function does (shown to the LLM).
        parameters: JSON Schema for the function parameters.
        destructive: If True, requires user confirmation before execution.
        confirm_message: Template for the confirmation prompt.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper_any: Any = wrapper
        wrapper_any._tool_function = True
        wrapper_any._tool_description = description
        # Clean up non-standard 'optional' keys for strict JSON Schema compliance
        cleaned_parameters = {}
        required = []
        for k, v in parameters.items():
            cleaned_v = dict(v)
            is_optional = cleaned_v.pop("optional", False)
            if not is_optional:
                required.append(k)
            cleaned_parameters[k] = cleaned_v

        wrapper_any._tool_parameters = {
            "type": "object",
            "properties": cleaned_parameters,
            "required": required,
        }
        wrapper_any._is_destructive = destructive
        if confirm_message:
            wrapper_any._confirm_message = lambda args: confirm_message.format(**args)
        return wrapper

    return decorator
