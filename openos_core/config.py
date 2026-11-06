"""
OpenOS Global Configuration.

Manages all configuration for the OpenOS system, including LLM settings,
paths, and user preferences. Configuration is stored in TOML format at
~/.config/openos/config.toml
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import toml

# --- Default Paths ---
OPENOS_CONFIG_DIR = Path(os.environ.get("OPENOS_CONFIG_DIR", Path.home() / ".config" / "openos"))
OPENOS_DATA_DIR = Path(os.environ.get("OPENOS_DATA_DIR", Path.home() / ".local" / "share" / "openos"))
OPENOS_CACHE_DIR = Path(os.environ.get("OPENOS_CACHE_DIR", Path.home() / ".cache" / "openos"))
OPENOS_CONFIG_FILE = OPENOS_CONFIG_DIR / "config.toml"
OPENOS_MEMORY_DB = OPENOS_DATA_DIR / "memory.db"
OPENOS_LOG_FILE = OPENOS_CACHE_DIR / "openos.log"


@dataclass
class LLMConfig:
    """Configuration for the LLM engine.

    Supports multiple backends:
      - 'ollama'  : Local Ollama server (default localhost:11434)
      - 'openai'  : Any OpenAI-compatible API (copilot-api, LM Studio, vLLM, etc.)
      - 'anthropic': Anthropic Claude API (requires api_key)
    """

    # Backend selection: 'ollama', 'openai', 'copilot-api', 'anthropic'
    # Empty string means unconfigured — will prompt user for setup
    backend: str = ""
    # API endpoint
    host: str = "http://localhost:11434"
    # Model to use (depends on backend)
    default_model: str = "llama3.2:3b"
    full_model: str = "gpt-4o"
    temperature: float = 0.3
    max_tokens: int = 2048
    timeout: int = 120
    # API key (for openai/anthropic backends; leave empty for local/proxy)
    api_key: str = ""
    # Whether to try the full model when the default fails
    auto_upgrade: bool = True
    # Fallback backend if primary fails (e.g., 'ollama' as offline fallback)
    fallback_backend: str = ""
    fallback_host: str = "http://localhost:11434"
    fallback_model: str = "llama3.2:3b"


@dataclass
class ShellConfig:
    """Configuration for the OpenOS Shell."""

    prompt_symbol: str = "openos>"
    show_thinking: bool = False
    confirm_destructive: bool = True
    confirm_all: bool = False
    history_size: int = 1000
    color_theme: str = "dark"


@dataclass
class VoiceConfig:
    """Configuration for voice control."""

    enabled: bool = False
    wake_word: str = "hey openos"
    whisper_model: str = "base"
    language: str = "en"
    silence_threshold: float = 0.03
    listen_timeout: int = 10


@dataclass
class DaemonConfig:
    """Configuration for the background daemon."""

    enabled: bool = True
    monitor_interval: int = 30  # seconds
    # Thresholds for intelligent alerts
    cpu_threshold: float = 90.0
    ram_threshold: float = 85.0
    disk_threshold: float = 90.0
    temp_threshold: float = 80.0
    # Auto-maintenance
    auto_cleanup: bool = True
    cleanup_schedule: str = "weekly"
    auto_update_check: bool = True
    # Proactive triggers
    proactive_enabled: bool = True
    triggers_file: str = ""


@dataclass
class DesktopConfig:
    """Configuration for the desktop shell."""

    compositor: str = "wayfire"
    panel_position: str = "top"
    panel_height: int = 36
    launcher_shortcut: str = "Super_L"
    assistant_shortcut: str = "<Super>a"
    theme: str = "openos-dark"


@dataclass
class OpenOSConfig:
    """Root configuration for OpenOS."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    shell: ShellConfig = field(default_factory=ShellConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    daemon: DaemonConfig = field(default_factory=DaemonConfig)
    desktop: DesktopConfig = field(default_factory=DesktopConfig)
    # Modules to load
    enabled_modules: list[str] = field(
        default_factory=lambda: [
            "file_manager",
            "system_maintenance",
            "app_launcher",
            "window_manager",
            "package_manager",
            "media_player",
            "web_browser",
            "screen_reader",
            "power_manager",
        ]
    )

    @classmethod
    def load(cls, path: Optional[Path] = None) -> OpenOSConfig:
        """Load configuration from TOML file, with defaults for missing values."""
        config_path = path or OPENOS_CONFIG_FILE

        if config_path.exists():
            try:
                data = toml.load(config_path)
                return cls(
                    llm=LLMConfig(**data.get("llm", {})),
                    shell=ShellConfig(**data.get("shell", {})),
                    voice=VoiceConfig(**data.get("voice", {})),
                    daemon=DaemonConfig(**data.get("daemon", {})),
                    desktop=DesktopConfig(**data.get("desktop", {})),
                    enabled_modules=data.get("modules", {}).get(
                        "enabled", [
                            "file_manager",
                            "system_maintenance",
                            "app_launcher",
                            "window_manager",
                            "package_manager",
                            "media_player",
                            "web_browser",
                            "screen_reader",
                            "power_manager",
                        ]
                    ),
                )
            except Exception:
                # If config is malformed, use defaults
                pass

        return cls()

    def save(self, path: Optional[Path] = None) -> None:
        """Save current configuration to TOML file."""
        config_path = path or OPENOS_CONFIG_FILE
        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "llm": {
                "backend": self.llm.backend,
                "host": self.llm.host,
                "default_model": self.llm.default_model,
                "full_model": self.llm.full_model,
                "temperature": self.llm.temperature,
                "max_tokens": self.llm.max_tokens,
                "timeout": self.llm.timeout,
                "api_key": self.llm.api_key,
                "auto_upgrade": self.llm.auto_upgrade,
                "fallback_backend": self.llm.fallback_backend,
                "fallback_host": self.llm.fallback_host,
                "fallback_model": self.llm.fallback_model,
            },
            "shell": {
                "prompt_symbol": self.shell.prompt_symbol,
                "show_thinking": self.shell.show_thinking,
                "confirm_destructive": self.shell.confirm_destructive,
                "confirm_all": self.shell.confirm_all,
                "history_size": self.shell.history_size,
                "color_theme": self.shell.color_theme,
            },
            "voice": {
                "enabled": self.voice.enabled,
                "wake_word": self.voice.wake_word,
                "whisper_model": self.voice.whisper_model,
                "language": self.voice.language,
            },
            "daemon": {
                "enabled": self.daemon.enabled,
                "monitor_interval": self.daemon.monitor_interval,
                "cpu_threshold": self.daemon.cpu_threshold,
                "ram_threshold": self.daemon.ram_threshold,
                "disk_threshold": self.daemon.disk_threshold,
                "auto_cleanup": self.daemon.auto_cleanup,
                "auto_update_check": self.daemon.auto_update_check,
                "proactive_enabled": self.daemon.proactive_enabled,
                "triggers_file": self.daemon.triggers_file,
            },
            "desktop": {
                "compositor": self.desktop.compositor,
                "panel_position": self.desktop.panel_position,
                "panel_height": self.desktop.panel_height,
                "theme": self.desktop.theme,
            },
            "modules": {
                "enabled": self.enabled_modules,
            },
        }

        with open(config_path, "w") as f:
            toml.dump(data, f)


def ensure_dirs() -> None:
    """Ensure all OpenOS directories exist."""
    for d in [OPENOS_CONFIG_DIR, OPENOS_DATA_DIR, OPENOS_CACHE_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# Singleton config instance
_config: Optional[OpenOSConfig] = None


def get_config() -> OpenOSConfig:
    """Get the global OpenOS configuration (lazy-loaded singleton)."""
    global _config
    if _config is None:
        ensure_dirs()
        _config = OpenOSConfig.load()
    return _config
