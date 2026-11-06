"""
OpenOS Function-Calling Router.

Dynamically discovers tool modules, registers them as Ollama-compatible function
schemas, and dispatches LLM function calls to the correct tool handler.
"""

from __future__ import annotations

import importlib
import inspect
import logging
from pathlib import Path
from typing import Any

from openos_core.config import get_config

logger = logging.getLogger(__name__)


class ToolRouter:
    """Central registry and dispatcher for all OpenOS tools."""

    def __init__(self):
        self._tools: dict[str, Any] = {}
        self._schemas: list[dict] = []

    def discover_and_register(self) -> None:
        """Auto-discover and register all enabled tool modules."""
        config = get_config()
        tools_dir = Path(__file__).parent.parent / "tools"

        for module_name in config.enabled_modules:
            if not (tools_dir / f"{module_name}.py").exists():
                logger.warning(f"Tool module not found: {module_name}")
                continue
            try:
                module = importlib.import_module(f"openos_core.tools.{module_name}")
                from openos_core.tools.base import BaseTool
                for _name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseTool) and obj is not BaseTool:
                        instance = obj()
                        self._register_tool(instance)
            except Exception as e:
                logger.error(f"Failed to load tool '{module_name}': {e}")

    def _register_tool(self, tool: Any) -> None:
        for method_name in dir(tool):
            method = getattr(tool, method_name)
            if callable(method) and hasattr(method, "_tool_function"):
                func_name = f"{tool.name}.{method_name}"
                self._tools[func_name] = method
                self._schemas.append({
                    "type": "function",
                    "function": {
                        "name": func_name,
                        "description": method._tool_description,
                        "parameters": method._tool_parameters,
                    },
                })
                logger.info(f"Registered: {func_name}")

    def get_schemas(self) -> list[dict]:
        return self._schemas

    def get_tool_descriptions(self) -> str:
        lines = []
        for s in self._schemas:
            f = s["function"]
            params = ", ".join(
                f"{n}: {i.get('type','any')}"
                for n, i in f["parameters"].get("properties", {}).items()
            )
            lines.append(f"- **{f['name']}**({params}): {f['description']}")
        return "\n".join(lines)

    async def execute(self, function_name: str, arguments: dict) -> dict:
        if function_name not in self._tools:
            return {"success": False, "error": f"Unknown: {function_name}"}

        method = self._tools[function_name]

        if getattr(method, "_is_destructive", False):
            msg = (
                method._confirm_message(arguments)
                if hasattr(method, "_confirm_message")
                else f"⚠️  Destructive op: {function_name}. Proceed?"
            )
            return {
                "success": False,
                "requires_confirmation": True,
                "confirm_message": msg,
                "function_name": function_name,
                "arguments": arguments,
            }

        try:
            if inspect.iscoroutinefunction(method):
                result = await method(**arguments)
            else:
                result = method(**arguments)
            return {"success": True, "result": str(result) if result is not None else "Done."}
        except Exception as e:
            logger.error(f"Tool failed: {function_name} — {e}")
            return {"success": False, "error": str(e)}

    async def execute_confirmed(self, function_name: str, arguments: dict) -> dict:
        if function_name not in self._tools:
            return {"success": False, "error": f"Unknown: {function_name}"}
        method = self._tools[function_name]
        try:
            if inspect.iscoroutinefunction(method):
                result = await method(**arguments)
            else:
                result = method(**arguments)
            return {"success": True, "result": str(result) if result is not None else "Done."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())
