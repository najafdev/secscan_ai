"""
HackBot Plugin System
======================
A Python plugin system that lets users register custom scripts as agent-callable tools.

Plugins are Python files placed in the plugins directory (~/.config/hackbot/plugins/).
Each plugin is a Python module that defines a ``register()`` function returning a
``PluginDefinition``, or uses the ``@hackbot_plugin`` decorator on a callable.

Minimal Plugin Example
----------------------
::

    from hackbot.core.plugins import hackbot_plugin

    @hackbot_plugin(
        name="port_check",
        description="Check if a port is open on a host",
        args={"host": "Target hostname or IP", "port": "Port number to check"},
    )
    def run(host: str, port: str = "80") -> str:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        return f"Port {port} on {host}: {'OPEN' if result == 0 else 'CLOSED'}"

Advanced Plugin Example (using register function)
--------------------------------------------------
::

    from hackbot.core.plugins import PluginDefinition

    def register() -> PluginDefinition:
        return PluginDefinition(
            name="my_scanner",
            description="Custom vulnerability scanner",
            author="user",
            version="1.0.0",
            args={"target": "Host to scan", "intensity": "Scan intensity (1-5)"},
            run=do_scan,
        )

    def do_scan(target: str, intensity: str = "3") -> str:
        # ... scanning logic ...
        return "Scan complete: 0 vulnerabilities found"
"""

from __future__ import annotations

import importlib.util
import inspect
import logging
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from hackbot.config import CONFIG_DIR

logger = logging.getLogger(__name__)

# ── Plugin Directory ─────────────────────────────────────────────────────────

PLUGINS_DIR = CONFIG_DIR / "plugins"


def ensure_plugins_dir() -> Path:
    """Create the plugins directory if it doesn't exist."""
    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    return PLUGINS_DIR


# ── Plugin Definition ────────────────────────────────────────────────────────

@dataclass
class PluginDefinition:
    """
    Metadata and callable for a user-registered plugin.

    Attributes:
        name: Unique identifier (used as the tool name in agent commands).
        description: Human-readable description shown to the AI agent.
        run: The callable that executes the plugin.  Receives keyword arguments
             matching ``args`` keys and must return a string result.
        args: Dict mapping argument names to description strings.
              The keys become the kwargs passed to ``run()``.
        author: Optional author name.
        version: Optional version string.
        category: Optional category for grouping (e.g. "recon", "exploit").
        enabled: Whether the plugin is active.
        source_path: Path to the plugin source file.
    """
    name: str
    description: str
    run: Callable[..., str]
    args: Dict[str, str] = field(default_factory=dict)
    author: str = ""
    version: str = "1.0.0"
    category: str = "custom"
    enabled: bool = True
    source_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize plugin metadata (not the callable)."""
        return {
            "name": self.name,
            "description": self.description,
            "args": self.args,
            "author": self.author,
            "version": self.version,
            "category": self.category,
            "enabled": self.enabled,
            "source_path": self.source_path,
        }


# ── Plugin Result ────────────────────────────────────────────────────────────

@dataclass
class PluginResult:
    """Result from executing a plugin."""
    plugin_name: str
    success: bool
    output: str
    duration: float
    error: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_name": self.plugin_name,
            "success": self.success,
            "output": self.output,
            "duration": round(self.duration, 2),
            "error": self.error,
            "timestamp": self.timestamp,
        }


# ── Decorator ────────────────────────────────────────────────────────────────

def hackbot_plugin(
    name: str,
    description: str,
    args: Optional[Dict[str, str]] = None,
    author: str = "",
    version: str = "1.0.0",
    category: str = "custom",
) -> Callable:
    """
    Decorator to register a function as a HackBot plugin.

    Usage::

        @hackbot_plugin(name="my_tool", description="Does something useful")
        def run(target: str) -> str:
            return f"Scanned {target}"

    The decorated function gets a ``_plugin_def`` attribute containing the
    :class:`PluginDefinition`, which the plugin loader uses for registration.
    """
    def decorator(func: Callable[..., str]) -> Callable[..., str]:
        plugin_args = args or {}
        # Auto-extract args from function signature if not provided
        if not plugin_args:
            sig = inspect.signature(func)
            for param_name, param in sig.parameters.items():
                if param_name in ("self", "cls"):
                    continue
                desc = f"Parameter: {param_name}"
                if param.default is not inspect.Parameter.empty:
                    desc += f" (default: {param.default})"
                plugin_args[param_name] = desc

        func._plugin_def = PluginDefinition(  # type: ignore[attr-defined]
            name=name,
            description=description,
            run=func,
            args=plugin_args,
            author=author,
            version=version,
            category=category,
        )
        return func
    return decorator


# ── Plugin Manager ───────────────────────────────────────────────────────────

class PluginManager:
    """
    Discovers, loads, validates, and executes user plugins.

    Usage::

        manager = PluginManager()
        manager.discover()
        result = manager.execute("my_tool", target="10.0.0.1")
    """

    # Maximum execution time for a single plugin call (seconds)
    PLUGIN_TIMEOUT = 120

    def __init__(self, plugins_dir: Optional[Path] = None):
        self.plugins_dir = plugins_dir or PLUGINS_DIR
        self.plugins: Dict[str, PluginDefinition] = {}
        self._load_errors: List[Dict[str, str]] = []

    # ── Discovery & Loading ──────────────────────────────────────────────

    def discover(self) -> int:
        """
        Scan the plugins directory for .py files and load them.

        Returns:
            Number of plugins successfully loaded.
        """
        self._load_errors = []

        if not self.plugins_dir.exists():
            return 0

        count = 0
        for path in sorted(self.plugins_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue
            try:
                plugin = self._load_plugin_file(path)
                if plugin:
                    self.register(plugin)
                    count += 1
            except Exception as e:
                self._load_errors.append({
                    "file": path.name,
                    "error": str(e),
                })
                logger.warning(f"Failed to load plugin {path.name}: {e}")

        return count

    def _load_plugin_file(self, path: Path) -> Optional[PluginDefinition]:
        """
        Load a single plugin file.

        Supports two registration methods:
        1. A ``register()`` function that returns a PluginDefinition
        2. A function decorated with ``@hackbot_plugin``
        """
        module_name = f"hackbot_plugin_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, str(path))
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot create module spec for {path}")

        module = importlib.util.module_from_spec(spec)

        # Temporarily add module to sys.modules so imports within the plugin work
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            sys.modules.pop(module_name, None)
            raise ImportError(f"Error executing {path.name}: {e}") from e

        # Method 1: register() function
        if hasattr(module, "register") and callable(module.register):
            plugin = module.register()
            if isinstance(plugin, PluginDefinition):
                plugin.source_path = str(path)
                return plugin
            raise TypeError(
                f"{path.name}: register() must return a PluginDefinition, "
                f"got {type(plugin).__name__}"
            )

        # Method 2: Find decorated functions
        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if callable(obj) and hasattr(obj, "_plugin_def"):
                plugin = obj._plugin_def
                if isinstance(plugin, PluginDefinition):
                    plugin.source_path = str(path)
                    return plugin

        raise ValueError(
            f"{path.name}: No register() function or @hackbot_plugin decorated callable found"
        )

    # ── Registration ─────────────────────────────────────────────────────

    def register(self, plugin: PluginDefinition) -> None:
        """Register a plugin definition."""
        if not plugin.name:
            raise ValueError("Plugin name cannot be empty")
        if not callable(plugin.run):
            raise ValueError(f"Plugin '{plugin.name}' run attribute is not callable")
        self.plugins[plugin.name] = plugin
        logger.info(f"Registered plugin: {plugin.name}")

    def unregister(self, name: str) -> bool:
        """Unregister a plugin by name."""
        if name in self.plugins:
            del self.plugins[name]
            return True
        return False

    # ── Execution ────────────────────────────────────────────────────────

    def execute(self, name: str, **kwargs: str) -> PluginResult:
        """
        Execute a registered plugin by name.

        Args:
            name: Plugin name.
            **kwargs: Arguments to pass to the plugin's run function.

        Returns:
            PluginResult with output or error.
        """
        if name not in self.plugins:
            return PluginResult(
                plugin_name=name,
                success=False,
                output="",
                duration=0.0,
                error=f"Plugin '{name}' not found",
            )

        plugin = self.plugins[name]
        if not plugin.enabled:
            return PluginResult(
                plugin_name=name,
                success=False,
                output="",
                duration=0.0,
                error=f"Plugin '{name}' is disabled",
            )

        start = time.time()
        try:
            # Filter kwargs to only those the plugin accepts
            sig = inspect.signature(plugin.run)
            valid_kwargs = {}
            for param_name in sig.parameters:
                if param_name in kwargs:
                    valid_kwargs[param_name] = kwargs[param_name]

            output = plugin.run(**valid_kwargs)
            duration = time.time() - start

            if not isinstance(output, str):
                output = str(output)

            return PluginResult(
                plugin_name=name,
                success=True,
                output=output,
                duration=duration,
            )
        except Exception as e:
            duration = time.time() - start
            tb = traceback.format_exc()
            return PluginResult(
                plugin_name=name,
                success=False,
                output="",
                duration=duration,
                error=f"{type(e).__name__}: {e}\n{tb}",
            )

    # ── Query ────────────────────────────────────────────────────────────

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all registered plugins as dicts."""
        return [p.to_dict() for p in self.plugins.values()]

    def get_plugin(self, name: str) -> Optional[PluginDefinition]:
        """Get a plugin by name."""
        return self.plugins.get(name)

    def get_load_errors(self) -> List[Dict[str, str]]:
        """Return any errors from the last discover() call."""
        return self._load_errors.copy()

    def get_plugin_names(self) -> List[str]:
        """Return list of registered plugin names."""
        return list(self.plugins.keys())

    def get_agent_tool_descriptions(self) -> str:
        """
        Generate a description string for the agent system prompt,
        listing all available custom plugins and their usage.
        """
        if not self.plugins:
            return ""

        lines = ["", "CUSTOM PLUGINS (registered by user — call via execute action with the plugin command):", ""]
        for p in self.plugins.values():
            if not p.enabled:
                continue
            args_str = ", ".join(
                f"--{k} <{v}>" for k, v in p.args.items()
            ) if p.args else "(no arguments)"
            lines.append(f"- **{p.name}**: {p.description}")
            lines.append(f"  Usage: `hackbot-plugin {p.name} {args_str}`")
            if p.category != "custom":
                lines.append(f"  Category: {p.category}")
            lines.append("")

        return "\n".join(lines)

    @property
    def count(self) -> int:
        return len(self.plugins)

    @property
    def enabled_count(self) -> int:
        return sum(1 for p in self.plugins.values() if p.enabled)


# ── Singleton Manager ────────────────────────────────────────────────────────

_global_manager: Optional[PluginManager] = None


def get_plugin_manager(plugins_dir: Optional[Path] = None) -> PluginManager:
    """
    Get (or create) the global PluginManager singleton.

    On first call, discovers plugins in the plugins directory.
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = PluginManager(plugins_dir=plugins_dir)
        _global_manager.discover()
    return _global_manager


def reset_plugin_manager() -> None:
    """Reset the global manager (for testing)."""
    global _global_manager
    _global_manager = None
