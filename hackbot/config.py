"""
HackBot Configuration Management
=================================
Handles config loading, API key management, and platform-specific paths.
"""

from __future__ import annotations

import os
import platform
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from platformdirs import user_config_dir, user_data_dir

APP_NAME = "hackbot"

# ── paths ────────────────────────────────────────────────────────────────────

CONFIG_DIR = Path(user_config_dir(APP_NAME))
DATA_DIR = Path(user_data_dir(APP_NAME))
REPORTS_DIR = DATA_DIR / "reports"
LOGS_DIR = DATA_DIR / "logs"
SESSIONS_DIR = DATA_DIR / "sessions"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


def ensure_dirs() -> None:
    """Create all required directories."""
    for d in (CONFIG_DIR, DATA_DIR, REPORTS_DIR, LOGS_DIR, SESSIONS_DIR):
        d.mkdir(parents=True, exist_ok=True)


# ── default config ───────────────────────────────────────────────────────────

DEFAULT_CONFIG: Dict[str, Any] = {
    "ai": {
        "provider": "openai",
        "model": "gpt-4o",
        "api_key": "",
        "api_keys": [],
        "base_url": "",
        "temperature": 0.2,
        "max_tokens": 4096,
    },
    "agent": {
        "auto_confirm": False,
        "max_steps": 50,
        "timeout": 300,
        "safe_mode": True,
        "sudo_mode": False,
        "sudo_password": "",
        "nvd_api_key": "",
        "allow_arbitrary_install": False,
        "allowed_tools": [
            "nmap",
            "masscan",
            "nikto",
            "gobuster",
            "feroxbuster",
            "sqlmap",
            "wfuzz",
            "ffuf",
            "nuclei",
            "subfinder",
            "httpx",
            "amass",
            "dnsrecon",
            "dnsenum",
            "whatweb",
            "dirb",
            "searchsploit",
            "msfconsole",
            "msfvenom",
            "hydra",
            "john",
            "hashcat",
            "wifite",
            "aircrack-ng",
            "airodump-ng",
            "aireplay-ng",
            "airbase-ng",
            "reaver",
            "wash",
            "hcxdumptool",
            "hcxpcapngtool",
            "bettercap",
            "ettercap",
            "responder",
            "nxc",
            "crackmapexec",
            "smbclient",
            "enum4linux",
            "enum4linux-ng",
            "ldapsearch",
            "nbtscan",
            "onesixtyone",
            "snmpwalk",
            "curl",
            "wget",
            "tcpdump",
            "tshark",
            "dig",
            "whois",
            "traceroute",
            "ping",
            "fping",
            "arp-scan",
            "netdiscover",
            "netcat",
            "openssl",
            "testssl",
            "sslscan",
            "thc-ipv6",
            "wpscan",
            "dalfox",
            "commix",
            "tplmap",
            "ghauri",
            "arjun",
            "paramspider",
            "katana",
            "gau",
            "waybackurls",
            "crlfuzz",
            "jwt_tool",
            "xxeinjector",
            "ysoserial",
            "python3",
            "python",
            "ruby",
            "perl",
            "php",
            "gcc",
            "go",
            "bash",
            "sh",
            "chmod",
            "grep",
            "egrep",
            "head",
            "tail",
            "sort",
            "uniq",
            "wc",
            "awk",
            "sed",
            "cut",
            "tr",
            "cat",
            "tee",
            "find",
            "xargs",
        ],
    },
    "reporting": {
        "format": "html",
        "auto_save": True,
        "include_raw_output": True,
    },
    "ui": {
        "theme": "dark",
        "show_banner": True,
        "verbose": False,
        "language": "English",
    },
    "telegram": {
        "token": "",
        "session_ttl_days": 7,
    },
    "rag": {
        "enabled": True,
        "max_results": 5,
        "max_context_tokens": 1500,
        "chunk_size": 500,
        "chunk_overlap": 50,
    },
}


@dataclass
class AIConfig:
    provider: str = "openai"
    model: str = "gpt-4o"
    api_key: str = ""
    api_keys: List[str] = field(default_factory=list)
    base_url: str = ""
    temperature: float = 0.2
    max_tokens: int = 4096


@dataclass
class AgentConfig:
    auto_confirm: bool = False
    max_steps: int = 50
    timeout: int = 300
    safe_mode: bool = True
    sudo_mode: bool = False
    sudo_password: str = ""
    nvd_api_key: str = ""
    allow_arbitrary_install: bool = False
    allowed_tools: List[str] = field(
        default_factory=lambda: DEFAULT_CONFIG["agent"]["allowed_tools"]
    )


@dataclass
class ReportingConfig:
    format: str = "html"
    auto_save: bool = True
    include_raw_output: bool = True


@dataclass
class UIConfig:
    theme: str = "dark"
    show_banner: bool = True
    verbose: bool = False
    language: str = "English"


@dataclass
class TelegramConfig:
    token: str = ""
    session_ttl_days: int = 7


@dataclass
class RAGConfig:
    enabled: bool = True
    max_results: int = 5
    max_context_tokens: int = 1500
    chunk_size: int = 500
    chunk_overlap: int = 50


@dataclass
class HackBotConfig:
    ai: AIConfig = field(default_factory=AIConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    reporting: ReportingConfig = field(default_factory=ReportingConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)


def reconcile_keys(ai: Dict[str, Any]) -> None:
    """Normalize the API key pool in an ``ai`` config dict, in place.

    Dedupes, drops empties, and keeps the active key first so the invariant
    ``api_key == api_keys[0]`` always holds. Seeds the pool from a legacy
    single ``api_key`` and lets an env-provided ``api_key`` take priority by
    placing it first.
    """
    pool = [k for k in dict.fromkeys([ai.get("api_key", "")] + list(ai.get("api_keys") or [])) if k]
    ai["api_keys"] = pool
    ai["api_key"] = pool[0] if pool else ""


def add_key(cfg: "AIConfig", key: str) -> None:
    """Append *key* to the pool if not already present; keep ``api_key`` valid."""
    key = key.strip()
    if not key or key in cfg.api_keys:
        return
    cfg.api_keys.append(key)
    if not cfg.api_key:
        cfg.api_key = cfg.api_keys[0]


def remove_key(cfg: "AIConfig", index: int) -> str:
    """Remove and return the pool entry at *index*. Raises IndexError if invalid.

    If the removed key was the active one, the new active key becomes the new
    ``api_keys[0]`` (or empty when the pool is exhausted).
    """
    if index < 0 or index >= len(cfg.api_keys):
        raise IndexError("API key index out of range")
    removed = cfg.api_keys.pop(index)
    cfg.api_key = cfg.api_keys[0] if cfg.api_keys else ""
    return removed


def set_active_key(cfg: "AIConfig", key: str) -> None:
    """Make *key* the active key by moving/inserting it at the front of the pool."""
    key = key.strip()
    if not key:
        return
    if key in cfg.api_keys:
        cfg.api_keys.remove(key)
    cfg.api_keys.insert(0, key)
    cfg.api_key = key


def mask_key(key: str) -> str:
    """Return a display-safe masked form of an API key."""
    if not key:
        return "(empty)"
    if len(key) <= 8:
        return key[:3] + "…"
    return f"{key[:5]}…{key[-4:]}"


def load_config() -> HackBotConfig:
    """Load configuration from disk, env vars, and defaults."""
    ensure_dirs()
    raw: Dict[str, Any] = {}

    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            raw = yaml.safe_load(f) or {}

    # Merge with defaults
    merged = _deep_merge(DEFAULT_CONFIG, raw)

    # Env-var overrides
    if os.environ.get("HACKBOT_API_KEY"):
        merged["ai"]["api_key"] = os.environ["HACKBOT_API_KEY"]
    if os.environ.get("HACKBOT_MODEL"):
        merged["ai"]["model"] = os.environ["HACKBOT_MODEL"]
    if os.environ.get("HACKBOT_PROVIDER"):
        merged["ai"]["provider"] = os.environ["HACKBOT_PROVIDER"]
    if os.environ.get("HACKBOT_BASE_URL"):
        merged["ai"]["base_url"] = os.environ["HACKBOT_BASE_URL"]
    if os.environ.get("OPENAI_API_KEY") and not merged["ai"]["api_key"]:
        merged["ai"]["api_key"] = os.environ["OPENAI_API_KEY"]
    if os.environ.get("ANTHROPIC_API_KEY") and not merged["ai"]["api_key"]:
        merged["ai"]["api_key"] = os.environ["ANTHROPIC_API_KEY"]
        if merged["ai"]["provider"] == "openai":
            merged["ai"]["provider"] = "anthropic"
            merged["ai"]["model"] = "claude-sonnet-4-20250514"
    if os.environ.get("GEMINI_API_KEY") and not merged["ai"]["api_key"]:
        merged["ai"]["api_key"] = os.environ["GEMINI_API_KEY"]
        if merged["ai"]["provider"] == "openai":
            merged["ai"]["provider"] = "gemini"
            merged["ai"]["model"] = "gemini-2.5-pro"
    if os.environ.get("GOOGLE_API_KEY") and not merged["ai"]["api_key"]:
        merged["ai"]["api_key"] = os.environ["GOOGLE_API_KEY"]
        if merged["ai"]["provider"] == "openai":
            merged["ai"]["provider"] = "gemini"
            merged["ai"]["model"] = "gemini-2.5-pro"
    if os.environ.get("GROQ_API_KEY") and not merged["ai"]["api_key"]:
        merged["ai"]["api_key"] = os.environ["GROQ_API_KEY"]
        if merged["ai"]["provider"] == "openai":
            merged["ai"]["provider"] = "groq"
            merged["ai"]["model"] = "llama-3.3-70b-versatile"
    if os.environ.get("MISTRAL_API_KEY") and not merged["ai"]["api_key"]:
        merged["ai"]["api_key"] = os.environ["MISTRAL_API_KEY"]
        if merged["ai"]["provider"] == "openai":
            merged["ai"]["provider"] = "mistral"
            merged["ai"]["model"] = "mistral-large-latest"
    if os.environ.get("DEEPSEEK_API_KEY") and not merged["ai"]["api_key"]:
        merged["ai"]["api_key"] = os.environ["DEEPSEEK_API_KEY"]
        if merged["ai"]["provider"] == "openai":
            merged["ai"]["provider"] = "deepseek"
            merged["ai"]["model"] = "deepseek-chat"
    if os.environ.get("TOGETHER_API_KEY") and not merged["ai"]["api_key"]:
        merged["ai"]["api_key"] = os.environ["TOGETHER_API_KEY"]
        if merged["ai"]["provider"] == "openai":
            merged["ai"]["provider"] = "together"
            merged["ai"]["model"] = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
    if os.environ.get("OPENROUTER_API_KEY") and not merged["ai"]["api_key"]:
        merged["ai"]["api_key"] = os.environ["OPENROUTER_API_KEY"]
        if merged["ai"]["provider"] == "openai":
            merged["ai"]["provider"] = "openrouter"
            merged["ai"]["model"] = "anthropic/claude-sonnet-4-20250514"

    # Language override
    if os.environ.get("HACKBOT_LANGUAGE"):
        merged.setdefault("ui", {})["language"] = os.environ["HACKBOT_LANGUAGE"]

    # Telegram token env override
    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        merged.setdefault("telegram", {})["token"] = os.environ["TELEGRAM_BOT_TOKEN"]

    # NVD API key env override
    if os.environ.get("NVD_API_KEY"):
        merged.setdefault("agent", {})["nvd_api_key"] = os.environ["NVD_API_KEY"]

    # Backward-compatible tool migration: keep user tools and append newly
    # introduced default tools so existing configs can use new capabilities.
    merged.setdefault("agent", {})["allowed_tools"] = _merge_allowed_tools(
        merged.get("agent", {}).get("allowed_tools", []),
        DEFAULT_CONFIG["agent"]["allowed_tools"],
    )

    reconcile_keys(merged.setdefault("ai", {}))

    cfg = HackBotConfig(
        ai=AIConfig(**merged.get("ai", {})),
        agent=AgentConfig(**merged.get("agent", {})),
        reporting=ReportingConfig(**merged.get("reporting", {})),
        ui=UIConfig(**merged.get("ui", {})),
        telegram=TelegramConfig(**merged.get("telegram", {})),
        rag=RAGConfig(**merged.get("rag", {})),
    )
    return cfg


def save_config(cfg: HackBotConfig) -> None:
    """Persist current configuration to disk."""
    ensure_dirs()
    data = {
        "ai": {
            "provider": cfg.ai.provider,
            "model": cfg.ai.model,
            "api_key": cfg.ai.api_key,
            "api_keys": cfg.ai.api_keys,
            "base_url": cfg.ai.base_url,
            "temperature": cfg.ai.temperature,
            "max_tokens": cfg.ai.max_tokens,
        },
        "agent": {
            "auto_confirm": cfg.agent.auto_confirm,
            "max_steps": cfg.agent.max_steps,
            "timeout": cfg.agent.timeout,
            "safe_mode": cfg.agent.safe_mode,
            "sudo_mode": cfg.agent.sudo_mode,
            "sudo_password": cfg.agent.sudo_password,
            "nvd_api_key": cfg.agent.nvd_api_key,
            "allow_arbitrary_install": cfg.agent.allow_arbitrary_install,
            "allowed_tools": cfg.agent.allowed_tools,
        },
        "reporting": {
            "format": cfg.reporting.format,
            "auto_save": cfg.reporting.auto_save,
            "include_raw_output": cfg.reporting.include_raw_output,
        },
        "ui": {
            "theme": cfg.ui.theme,
            "show_banner": cfg.ui.show_banner,
            "verbose": cfg.ui.verbose,
            "language": cfg.ui.language,
        },
        "telegram": {
            "token": cfg.telegram.token,
            "session_ttl_days": cfg.telegram.session_ttl_days,
        },
        "rag": {
            "enabled": cfg.rag.enabled,
            "max_results": cfg.rag.max_results,
            "max_context_tokens": cfg.rag.max_context_tokens,
            "chunk_size": cfg.rag.chunk_size,
            "chunk_overlap": cfg.rag.chunk_overlap,
        },
    }
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base."""
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _merge_allowed_tools(current: List[str], defaults: List[str]) -> List[str]:
    """Merge allowlists while preserving user order and appending new defaults."""
    merged: List[str] = []
    seen: set[str] = set()

    for tool in current or []:
        name = str(tool).strip()
        if not name:
            continue
        key = name.lower()
        if key not in seen:
            seen.add(key)
            merged.append(name)

    for tool in defaults or []:
        name = str(tool).strip()
        if not name:
            continue
        key = name.lower()
        if key not in seen:
            seen.add(key)
            merged.append(name)

    return merged


# ── tool detection ───────────────────────────────────────────────────────────


def detect_platform() -> Dict[str, str]:
    """Return platform information."""
    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
    }


# Logical tool names that may map to one of multiple concrete binaries.
TOOL_ALIASES: Dict[str, List[str]] = {
    # Kali/Debian package `thc-ipv6` usually installs tools like `alive6`,
    # not a single `thc-ipv6` executable.
    "thc-ipv6": [
        "thc-ipv6",
        "alive6",
        "address6",
        "detect-new-ip6",
        "dnsdict6",
        "dnsrevenum6",
        "fake_advertise6",
        "fake_dns6d",
        "flood_advertise6",
        "flood_dhcpc6",
        "flood_mld6",
        "flood_mld26",
        "flood_mldrouter6",
        "flood_redir6",
        "flood_router6",
        "flood_rs6",
        "flood_solicitate6",
        "implementation6",
        "ndpexhaust26",
        "parasite6",
        "randicmp6",
        "redir6",
        "smurf6",
    ],
}

# Package-manager binaries the ToolInstaller is permitted to invoke. These are
# deliberately NOT in agent.allowed_tools so the agent cannot run them via a
# normal `execute` action — only ToolInstaller.install() may, via the runner's
# allow_install_drivers bypass.
INSTALL_DRIVERS: List[str] = ["apt-get", "dnf", "pacman", "brew", "pipx", "pip", "go"]

# Curated tool -> package recipes for autonomous installation.
# `order` lists preferred managers; ToolInstaller picks the first one available
# on the host. Per-manager values are the package/module identifier for that
# manager. Only tools also present in agent.allowed_tools are installable.
TOOL_INSTALL_MAP: Dict[str, Dict[str, object]] = {
    "nuclei": {
        "order": ["go", "apt"],
        "go": "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
        "apt": "nuclei",
    },
    "subfinder": {
        "order": ["go"],
        "go": "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
    },
    "httpx": {
        "order": ["go"],
        "go": "github.com/projectdiscovery/httpx/cmd/httpx@latest",
    },
    "ffuf": {
        "order": ["go", "apt"],
        "go": "github.com/ffuf/ffuf/v2@latest",
        "apt": "ffuf",
    },
    "gobuster": {
        "order": ["go", "apt"],
        "go": "github.com/OJ/gobuster/v3@latest",
        "apt": "gobuster",
    },
    "katana": {
        "order": ["go"],
        "go": "github.com/projectdiscovery/katana/cmd/katana@latest",
    },
    "sqlmap": {"order": ["apt", "pipx"], "apt": "sqlmap", "pipx": "sqlmap"},
    "nikto": {"order": ["apt"], "apt": "nikto"},
    "nmap": {
        "order": ["apt", "dnf", "pacman", "brew"],
        "apt": "nmap",
        "dnf": "nmap",
        "pacman": "nmap",
        "brew": "nmap",
    },
    "whatweb": {"order": ["apt"], "apt": "whatweb"},
    "wpscan": {"order": ["apt"], "apt": "wpscan"},
    "hydra": {"order": ["apt"], "apt": "hydra"},
    "dnsrecon": {"order": ["apt", "pipx"], "apt": "dnsrecon", "pipx": "dnsrecon"},
    "amass": {
        "order": ["apt", "go"],
        "apt": "amass",
        "go": "github.com/owasp-amass/amass/v4/...@master",
    },
    "feroxbuster": {"order": ["apt"], "apt": "feroxbuster"},
    "masscan": {
        "order": ["apt", "dnf", "pacman"],
        "apt": "masscan",
        "dnf": "masscan",
        "pacman": "masscan",
    },
    "wfuzz": {
        "order": ["pip", "apt"],
        "pip": "wfuzz",
        "apt": "wfuzz",
        # wfuzz requires setuptools (pkg_resources) on Python 3.12+;
        # the pre_install hook ensures it's present before wfuzz.
        "pre_install": ["pip install setuptools"],
    },
}


def resolve_tool_path(tool: str) -> Optional[str]:
    """Resolve a logical tool name to an installed executable path.

    Returns the first executable path found for the given tool (including
    aliases), otherwise None.
    """
    candidates = TOOL_ALIASES.get(tool.lower(), [tool])
    for candidate in candidates:
        path = shutil.which(candidate)
        if path:
            return path
    return None


def detect_tools(allowed: List[str]) -> Dict[str, Optional[str]]:
    """Detect which security tools are installed."""
    found: Dict[str, Optional[str]] = {}
    for tool in allowed:
        found[tool] = resolve_tool_path(tool)
    return found
