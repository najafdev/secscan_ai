"""Tests for HackBot CLI command handling."""

from hackbot.cli import HackBotApp
from hackbot.config import HackBotConfig


def test_key_deepseek_prefix_switches_provider_before_validation(monkeypatch):
    saved = {}

    def fake_validate(self):
        saved["provider_at_validation"] = self.config.provider
        saved["model_at_validation"] = self.config.model
        saved["api_key_at_validation"] = self.config.api_key
        return {"valid": True, "message": "ok"}

    monkeypatch.setattr("hackbot.cli.save_config", lambda cfg: saved.setdefault("saved", cfg))
    monkeypatch.setattr("hackbot.core.engine.AIEngine.validate_api_key", fake_validate)

    app = HackBotApp(HackBotConfig())

    assert app._set_key("deepseek sk-deepseek-test") is True
    assert app.config.ai.provider == "deepseek"
    assert app.config.ai.model == "deepseek-chat"
    assert app.config.ai.api_key == "sk-deepseek-test"
    assert saved["provider_at_validation"] == "deepseek"
    assert saved["model_at_validation"] == "deepseek-chat"
    assert saved["api_key_at_validation"] == "sk-deepseek-test"


def test_key_deep_alias_requires_key_and_does_not_save(monkeypatch):
    saved = {"called": False}
    monkeypatch.setattr("hackbot.cli.save_config", lambda cfg: saved.update(called=True))

    app = HackBotApp(HackBotConfig())

    assert app._set_key("deep") is True
    assert app.config.ai.provider == "openai"
    assert app.config.ai.api_key == ""
    assert saved["called"] is False


def test_install_tool_requires_argument():
    app = HackBotApp(HackBotConfig())
    assert app._install_tool("") is True  # returns True (stay in REPL), prints usage


def test_install_tool_delegates_to_agent(monkeypatch):
    app = HackBotApp(HackBotConfig())
    captured = {}

    class _StubAgent:
        def _process_install_action(self, action):
            captured["action"] = action
            return "**[install]** SUCCESS — Installed nuclei"

    app.agent = _StubAgent()
    app.mode = "agent"
    result = app._install_tool("nuclei")
    assert result is True
    assert captured["action"] == {"action": "install", "tool": "nuclei"}


def test_handle_cvss_valid_vector():
    app = HackBotApp(HackBotConfig())
    assert app._handle_cvss("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H") is True


def test_handle_cvss_empty_prints_usage():
    app = HackBotApp(HackBotConfig())
    assert app._handle_cvss("") is True


def test_show_topology_mermaid():
    app = HackBotApp(HackBotConfig())
    scan_output = """
Nmap scan report for 192.168.1.1
Host is up (0.001s latency).
PORT   STATE SERVICE
80/tcp open  http
"""
    assert app._show_topology(f"mermaid {scan_output}") is True
