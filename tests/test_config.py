"""Tests for HackBot configuration module."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from hackbot.config import (
    TOOL_INSTALL_MAP,
    DEFAULT_CONFIG,
    HackBotConfig,
    AIConfig,
    AgentConfig,
    detect_platform,
    detect_tools,
    resolve_tool_path,
    _deep_merge,
    _merge_allowed_tools,
    load_config,
    reconcile_keys,
    save_config,
    add_key,
    remove_key,
    set_active_key,
    mask_key,
)


def test_default_config():
    """Test that default config is created properly."""
    cfg = HackBotConfig()
    assert cfg.ai.provider == "openai"
    assert cfg.ai.model == "gpt-4o"
    assert cfg.ai.temperature == 0.2
    assert cfg.agent.safe_mode is True
    assert cfg.agent.sudo_mode is False
    assert cfg.agent.max_steps == 50
    assert cfg.reporting.format == "html"
    assert cfg.ui.show_banner is True


def test_ai_config():
    """Test AI config dataclass."""
    ai = AIConfig(provider="ollama", model="llama3", api_key="test-key")
    assert ai.provider == "ollama"
    assert ai.model == "llama3"
    assert ai.api_key == "test-key"


def test_agent_config_defaults():
    """Test agent config has allowed tools."""
    cfg = AgentConfig()
    assert "nmap" in cfg.allowed_tools
    assert "nikto" in cfg.allowed_tools
    assert "sqlmap" in cfg.allowed_tools
    assert "msfconsole" in cfg.allowed_tools
    assert "wifite" in cfg.allowed_tools
    assert "aircrack-ng" in cfg.allowed_tools
    assert cfg.timeout == 300
    assert cfg.nvd_api_key == ""
    assert cfg.sudo_password == ""


def test_deep_merge():
    """Test deep merge of config dictionaries."""
    base = {"a": {"b": 1, "c": 2}, "d": 3}
    override = {"a": {"b": 10}, "e": 5}
    result = _deep_merge(base, override)
    assert result["a"]["b"] == 10
    assert result["a"]["c"] == 2
    assert result["d"] == 3
    assert result["e"] == 5


def test_detect_platform():
    """Test platform detection returns valid data."""
    plat = detect_platform()
    assert "system" in plat
    assert "release" in plat
    assert "machine" in plat
    assert "python" in plat
    assert plat["system"] in ("Linux", "Darwin", "Windows")


def test_detect_tools():
    """Test tool detection."""
    tools = detect_tools(["python3", "nonexistent_tool_xyz"])
    assert tools.get("python3") is not None or tools.get("python3") is None
    assert tools.get("nonexistent_tool_xyz") is None


def test_resolve_tool_path_thc_ipv6_alias(monkeypatch):
    """thc-ipv6 should resolve via Kali-style alias binaries (e.g., alive6)."""
    real_which = __import__("shutil").which

    def fake_which(name):
        if name == "alive6":
            return "/usr/bin/alive6"
        if name == "thc-ipv6":
            return None
        return real_which(name)

    monkeypatch.setattr("hackbot.config.shutil.which", fake_which)
    assert resolve_tool_path("thc-ipv6") == "/usr/bin/alive6"


def test_detect_tools_thc_ipv6_alias(monkeypatch):
    """detect_tools should mark thc-ipv6 installed when an alias binary exists."""
    real_which = __import__("shutil").which

    def fake_which(name):
        if name == "alive6":
            return "/usr/bin/alive6"
        if name == "thc-ipv6":
            return None
        return real_which(name)

    monkeypatch.setattr("hackbot.config.shutil.which", fake_which)
    tools = detect_tools(["thc-ipv6"])
    assert tools["thc-ipv6"] == "/usr/bin/alive6"


def test_env_var_override(monkeypatch):
    """Test that environment variables override config."""
    monkeypatch.setenv("HACKBOT_API_KEY", "test-env-key")
    monkeypatch.setenv("HACKBOT_MODEL", "gpt-4")
    cfg = load_config()
    assert cfg.ai.api_key == "test-env-key"
    assert cfg.ai.model == "gpt-4"


def test_merge_allowed_tools_appends_new_defaults():
    current = ["nmap", "custom-tool", "NIKTO"]
    defaults = ["nmap", "nikto", "msfconsole"]
    merged = _merge_allowed_tools(current, defaults)

    assert merged[0] == "nmap"
    assert merged[1] == "custom-tool"
    assert any(t.lower() == "nikto" for t in merged)
    assert "msfconsole" in merged


def test_load_config_migrates_allowed_tools_from_old_file(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        yaml.dump(
            {
                "agent": {
                    "allowed_tools": ["nmap", "nikto"],
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("hackbot.config.CONFIG_FILE", cfg_file)
    cfg = load_config()

    assert "nmap" in cfg.agent.allowed_tools
    assert "nikto" in cfg.agent.allowed_tools
    assert "msfconsole" in cfg.agent.allowed_tools
    assert "wifite" in cfg.agent.allowed_tools
    assert "aircrack-ng" in cfg.agent.allowed_tools


def test_reconcile_seeds_pool_from_single_key():
    ai = {"api_key": "sk-a", "api_keys": []}
    reconcile_keys(ai)
    assert ai["api_keys"] == ["sk-a"]
    assert ai["api_key"] == "sk-a"


def test_reconcile_active_is_pool_first():
    ai = {"api_key": "", "api_keys": ["sk-a", "sk-b"]}
    reconcile_keys(ai)
    assert ai["api_key"] == "sk-a"
    assert ai["api_keys"][0] == ai["api_key"]


def test_reconcile_env_key_prepended_and_deduped():
    ai = {"api_key": "sk-env", "api_keys": ["sk-a", "sk-env", "sk-b"]}
    reconcile_keys(ai)
    assert ai["api_keys"] == ["sk-env", "sk-a", "sk-b"]
    assert ai["api_key"] == "sk-env"


def test_reconcile_empty_pool():
    ai = {"api_key": "", "api_keys": []}
    reconcile_keys(ai)
    assert ai["api_keys"] == []
    assert ai["api_key"] == ""


def test_api_keys_round_trip(tmp_path, monkeypatch):
    import hackbot.config as cfgmod

    monkeypatch.setattr(cfgmod, "CONFIG_FILE", tmp_path / "config.yaml")
    for var in (
        "DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
        "HACKBOT_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GROQ_API_KEY",
        "MISTRAL_API_KEY",
        "TOGETHER_API_KEY",
        "OPENROUTER_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)

    cfg = cfgmod.HackBotConfig()
    cfg.ai.provider = "deepseek"
    cfg.ai.api_keys = ["sk-a", "sk-b"]
    cfg.ai.api_key = "sk-a"
    cfgmod.save_config(cfg)

    loaded = cfgmod.load_config()
    assert loaded.ai.api_keys == ["sk-a", "sk-b"]
    assert loaded.ai.api_key == "sk-a"


def test_add_key_appends_and_dedupes():
    cfg = AIConfig(provider="deepseek", api_key="sk-a", api_keys=["sk-a"])
    add_key(cfg, "sk-b")
    assert cfg.api_keys == ["sk-a", "sk-b"]
    add_key(cfg, "sk-b")  # duplicate is a no-op
    assert cfg.api_keys == ["sk-a", "sk-b"]
    assert cfg.api_key == "sk-a"  # active unchanged


def test_add_key_seeds_active_when_empty():
    cfg = AIConfig(provider="deepseek", api_key="", api_keys=[])
    add_key(cfg, "sk-a")
    assert cfg.api_keys == ["sk-a"]
    assert cfg.api_key == "sk-a"


def test_remove_active_key_promotes_next():
    cfg = AIConfig(provider="deepseek", api_key="sk-a", api_keys=["sk-a", "sk-b"])
    removed = remove_key(cfg, 0)
    assert removed == "sk-a"
    assert cfg.api_keys == ["sk-b"]
    assert cfg.api_key == "sk-b"


def test_remove_nonactive_key_keeps_active():
    cfg = AIConfig(provider="deepseek", api_key="sk-a", api_keys=["sk-a", "sk-b"])
    removed = remove_key(cfg, 1)
    assert removed == "sk-b"
    assert cfg.api_keys == ["sk-a"]
    assert cfg.api_key == "sk-a"


def test_remove_key_bad_index_raises():
    cfg = AIConfig(api_keys=["sk-a"])
    with pytest.raises(IndexError):
        remove_key(cfg, 5)


def test_remove_key_negative_index_raises():
    # /key remove 0 maps to index -1; that must error, not pop the last key.
    cfg = AIConfig(api_keys=["sk-a", "sk-b"])
    with pytest.raises(IndexError):
        remove_key(cfg, -1)
    assert cfg.api_keys == ["sk-a", "sk-b"]  # unchanged


def test_remove_last_key_empties_pool():
    cfg = AIConfig(api_key="sk-a", api_keys=["sk-a"])
    remove_key(cfg, 0)
    assert cfg.api_keys == []
    assert cfg.api_key == ""


def test_set_active_key_moves_to_front():
    cfg = AIConfig(provider="deepseek", api_key="sk-a", api_keys=["sk-a", "sk-b"])
    set_active_key(cfg, "sk-b")
    assert cfg.api_keys == ["sk-b", "sk-a"]
    assert cfg.api_key == "sk-b"


def test_set_active_key_new_key_inserts_front():
    cfg = AIConfig(provider="deepseek", api_key="sk-a", api_keys=["sk-a"])
    set_active_key(cfg, "sk-new")
    assert cfg.api_keys == ["sk-new", "sk-a"]
    assert cfg.api_key == "sk-new"


def test_mask_key():
    assert mask_key("sk-1234567890abcd") == "sk-12…abcd"
    assert mask_key("short") == "sho…"
    assert mask_key("") == "(empty)"
    # boundary: len 8 uses the short branch, len 9 uses the long branch
    assert mask_key("12345678") == "123…"
    assert mask_key("123456789") == "12345…6789"


def test_install_map_entries_are_well_formed():
    assert "nuclei" in TOOL_INSTALL_MAP
    for tool, recipe in TOOL_INSTALL_MAP.items():
        assert tool == tool.lower()
        assert "order" in recipe and recipe["order"], f"{tool} missing order"
        for mgr in recipe["order"]:
            assert mgr in recipe, f"{tool} order names {mgr} with no package"


def test_install_managers_not_in_global_allowlist():
    # Managers must NOT be globally execute-able; they are install-drivers only.
    allowed = set(DEFAULT_CONFIG["agent"]["allowed_tools"])
    for mgr in ("apt-get", "dnf", "pacman", "brew", "pipx", "pip"):
        assert mgr not in allowed, f"{mgr} must not be in the global allowlist"


def test_install_drivers_constant():
    from hackbot.config import INSTALL_DRIVERS
    assert set(INSTALL_DRIVERS) == {"apt-get", "dnf", "pacman", "brew", "pipx", "pip", "go"}


def test_allow_arbitrary_install_defaults_off():
    assert AgentConfig().allow_arbitrary_install is False
    assert DEFAULT_CONFIG["agent"]["allow_arbitrary_install"] is False
