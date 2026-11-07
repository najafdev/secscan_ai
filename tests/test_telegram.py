"""Tests for HackBot Telegram bot integration."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hackbot.config import HackBotConfig, load_config


# ── Module Availability ──────────────────────────────────────────────────────

def test_telegram_module_import():
    """Integration module can always be imported."""
    from hackbot.integrations import telegram_bot
    assert hasattr(telegram_bot, "HackBotTelegram")
    assert hasattr(telegram_bot, "check_telegram_deps")
    assert hasattr(telegram_bot, "generate_qr_code")
    assert hasattr(telegram_bot, "generate_qr_terminal")
    assert hasattr(telegram_bot, "PairingState")
    assert hasattr(telegram_bot, "TelegramUserSession")
    assert hasattr(telegram_bot, "get_telegram_bot")
    assert hasattr(telegram_bot, "reset_telegram_bot")


def test_check_telegram_deps():
    """check_telegram_deps returns a boolean."""
    from hackbot.integrations.telegram_bot import check_telegram_deps
    result = check_telegram_deps()
    assert isinstance(result, bool)


def test_check_qr_deps():
    """check_qr_deps returns a boolean."""
    from hackbot.integrations.telegram_bot import check_qr_deps
    result = check_qr_deps()
    assert isinstance(result, bool)


# ── PairingState ─────────────────────────────────────────────────────────────

class TestPairingState:
    """Tests for the QR code pairing system."""

    def test_generate_code(self):
        from hackbot.integrations.telegram_bot import PairingState
        ps = PairingState()
        code = ps.generate_code()
        assert len(code) > 10
        assert ps.code == code
        assert ps.created_at > 0

    def test_verify_valid_code(self):
        from hackbot.integrations.telegram_bot import PairingState
        ps = PairingState()
        code = ps.generate_code()
        assert ps.verify(code) is True

    def test_verify_wrong_code(self):
        from hackbot.integrations.telegram_bot import PairingState
        ps = PairingState()
        ps.generate_code()
        assert ps.verify("wrong-code") is False

    def test_verify_expired_code(self):
        from hackbot.integrations.telegram_bot import PairingState, PAIR_CODE_EXPIRY
        ps = PairingState()
        code = ps.generate_code()
        ps.created_at -= PAIR_CODE_EXPIRY + 1  # Expire it
        assert ps.verify(code) is False

    def test_authorize_user(self):
        from hackbot.integrations.telegram_bot import PairingState
        ps = PairingState()
        assert ps.is_authorized(12345) is False
        ps.authorize(12345)
        assert ps.is_authorized(12345) is True

    def test_authorize_multiple_users(self):
        from hackbot.integrations.telegram_bot import PairingState
        ps = PairingState()
        ps.authorize(111)
        ps.authorize(222)
        assert ps.is_authorized(111) is True
        assert ps.is_authorized(222) is True
        assert ps.is_authorized(333) is False

    def test_save_and_load(self, tmp_path):
        from hackbot.integrations.telegram_bot import PairingState
        auth_file = tmp_path / "auth.json"
        ps = PairingState()
        ps.authorize(123)
        ps.authorize(456)

        with patch("hackbot.integrations.telegram_bot.auth.AUTH_FILE", auth_file):
            ps.save()
            assert auth_file.exists()

            ps2 = PairingState()
            ps2.load()
            data = json.loads(auth_file.read_text())
            # authorized_users is now a dict of {str(user_id): timestamp}
            assert "123" in data["authorized_users"]
            assert "456" in data["authorized_users"]
            # Loaded state should have both users
            assert ps2.is_authorized(123)
            assert ps2.is_authorized(456)

    def test_load_missing_file(self):
        from hackbot.integrations.telegram_bot import PairingState
        ps = PairingState()
        with patch("hackbot.integrations.telegram_bot.auth.AUTH_FILE", Path("/nonexistent/auth.json")):
            ps.load()  # Should not raise
        assert len(ps.authorized_users) == 0


# ── TelegramUserSession ─────────────────────────────────────────────────────

class TestTelegramUserSession:
    def test_default_values(self):
        from hackbot.integrations.telegram_bot import TelegramUserSession
        s = TelegramUserSession(user_id=123)
        assert s.user_id == 123
        assert s.mode == "chat"
        assert s.chat_mode is None
        assert s.agent_mode is None
        assert s.plan_mode is None

    def test_touch_updates_activity(self):
        from hackbot.integrations.telegram_bot import TelegramUserSession
        import time
        s = TelegramUserSession(user_id=123)
        old = s.last_activity
        time.sleep(0.01)
        s.touch()
        assert s.last_activity > old


# ── Message Splitting ────────────────────────────────────────────────────────

class TestMessageSplitting:
    def test_short_message(self):
        from hackbot.integrations.telegram_bot import _split_message
        result = _split_message("hello")
        assert result == ["hello"]

    def test_long_message_splits(self):
        from hackbot.integrations.telegram_bot import _split_message
        text = "a" * 5000
        result = _split_message(text, max_len=4096)
        assert len(result) == 2
        assert len(result[0]) <= 4096

    def test_split_at_newline(self):
        from hackbot.integrations.telegram_bot import _split_message
        text = "x" * 2000 + "\n" + "y" * 2000 + "\n" + "z" * 2000
        result = _split_message(text, max_len=4096)
        assert len(result) >= 2

    def test_empty_message(self):
        from hackbot.integrations.telegram_bot import _split_message
        assert _split_message("") == [""]


# ── HTML Formatting ─────────────────────────────────────────────────────────

class TestFormatHTML:
    def test_escapes_html(self):
        from hackbot.integrations.telegram_bot import _format_html
        result = _format_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_code_blocks(self):
        from hackbot.integrations.telegram_bot import _format_html
        result = _format_html("```python\nprint('hello')\n```")
        assert "<pre><code>" in result
        assert "</code></pre>" in result

    def test_inline_code(self):
        from hackbot.integrations.telegram_bot import _format_html
        result = _format_html("Use `nmap` command")
        assert "<code>nmap</code>" in result

    def test_bold_text(self):
        from hackbot.integrations.telegram_bot import _format_html
        result = _format_html("**important**")
        assert "<b>important</b>" in result


# ── QR Generation ───────────────────────────────────────────────────────────

class TestQRGeneration:
    def test_generate_qr_code_without_deps(self):
        from hackbot.integrations.telegram_bot import generate_qr_code
        with patch("hackbot.integrations.telegram_bot.auth._QR_AVAILABLE", False):
            result = generate_qr_code("testbot", "abc123")
            assert result is None

    def test_generate_qr_terminal_without_deps(self):
        from hackbot.integrations.telegram_bot import generate_qr_terminal
        with patch("hackbot.integrations.telegram_bot.auth._QR_AVAILABLE", False):
            result = generate_qr_terminal("testbot", "abc123")
            assert result == ""

    @pytest.mark.skipif(
        not __import__("hackbot.integrations.telegram_bot", fromlist=["check_qr_deps"]).check_qr_deps(),
        reason="qrcode not installed",
    )
    def test_generate_qr_code_with_deps(self):
        from hackbot.integrations.telegram_bot import generate_qr_code
        result = generate_qr_code("testbot", "abc123")
        assert result is not None
        assert isinstance(result, bytes)
        # PNG magic bytes
        assert result[:4] == b"\x89PNG"

    @pytest.mark.skipif(
        not __import__("hackbot.integrations.telegram_bot", fromlist=["check_qr_deps"]).check_qr_deps(),
        reason="qrcode not installed",
    )
    def test_generate_qr_terminal_with_deps(self):
        from hackbot.integrations.telegram_bot import generate_qr_terminal
        result = generate_qr_terminal("testbot", "abc123")
        assert isinstance(result, str)
        assert len(result) > 10  # Has content


# ── Singleton ────────────────────────────────────────────────────────────────

class TestSingleton:
    def test_get_and_reset(self):
        from hackbot.integrations.telegram_bot import (
            get_telegram_bot, reset_telegram_bot, _TG_AVAILABLE,
        )
        reset_telegram_bot()

        if not _TG_AVAILABLE:
            with pytest.raises(ImportError):
                get_telegram_bot()
        else:
            bot = get_telegram_bot()
            assert bot is not None
            reset_telegram_bot()


# ── Bot Construction (requires python-telegram-bot) ──────────────────────────

class TestHackBotTelegram:
    @pytest.fixture
    def config(self):
        return HackBotConfig()

    def test_init_without_telegram_deps(self, config):
        """If python-telegram-bot is not installed, constructor raises ImportError."""
        from hackbot.integrations.telegram_bot import HackBotTelegram, _TG_AVAILABLE
        if _TG_AVAILABLE:
            pytest.skip("python-telegram-bot is installed")
        with pytest.raises(ImportError, match="Telegram bot dependencies"):
            HackBotTelegram(config, token="fake:token")

    def test_init_with_telegram_deps(self, config):
        """If python-telegram-bot is installed, constructor succeeds."""
        from hackbot.integrations.telegram_bot import HackBotTelegram, _TG_AVAILABLE
        if not _TG_AVAILABLE:
            pytest.skip("python-telegram-bot not installed")
        bot = HackBotTelegram(config, token="fake:token")
        assert bot.token == "fake:token"
        assert bot.is_running is False
        assert bot.bot_username == ""
        assert len(bot.sessions) == 0

    def test_get_session_creates_new(self, config):
        from hackbot.integrations.telegram_bot import HackBotTelegram, _TG_AVAILABLE
        if not _TG_AVAILABLE:
            pytest.skip("python-telegram-bot not installed")
        bot = HackBotTelegram(config, token="fake:token")
        session = bot._get_session(111)
        assert session.user_id == 111
        assert session.mode == "chat"
        assert session.chat_mode is not None

    def test_get_session_reuses_existing(self, config):
        from hackbot.integrations.telegram_bot import HackBotTelegram, _TG_AVAILABLE
        if not _TG_AVAILABLE:
            pytest.skip("python-telegram-bot not installed")
        bot = HackBotTelegram(config, token="fake:token")
        s1 = bot._get_session(222)
        s2 = bot._get_session(222)
        assert s1 is s2

    def test_reset_session(self, config):
        from hackbot.integrations.telegram_bot import HackBotTelegram, _TG_AVAILABLE
        if not _TG_AVAILABLE:
            pytest.skip("python-telegram-bot not installed")
        bot = HackBotTelegram(config, token="fake:token")
        s1 = bot._get_session(333)
        old_chat = s1.chat_mode
        bot._reset_session(333)
        s2 = bot._get_session(333)
        assert s2.chat_mode is not old_chat
        assert s2.mode == "chat"

    def test_build_app(self, config):
        from hackbot.integrations.telegram_bot import HackBotTelegram, _TG_AVAILABLE
        if not _TG_AVAILABLE:
            pytest.skip("python-telegram-bot not installed")
        bot = HackBotTelegram(config, token="fake:token")
        app = bot.build_app()
        assert app is not None
        assert bot._app is app

    def test_tools_command_registered(self, config):
        from hackbot.integrations.telegram_bot import HackBotTelegram, _TG_AVAILABLE
        if not _TG_AVAILABLE:
            pytest.skip("python-telegram-bot not installed")
        bot = HackBotTelegram(config, token="fake:token")
        app = bot.build_app()
        cmd_handlers = [h for h in app.handlers.get(0, []) if hasattr(h, "commands")]
        commands = {cmd for h in cmd_handlers for cmd in getattr(h, "commands", [])}
        assert "tools" in commands

    def test_default_token_applied(self, config):
        """When no explicit token is given, the built-in default is used."""
        from hackbot.integrations.telegram_bot import HackBotTelegram, _TG_AVAILABLE
        from hackbot.integrations.telegram_bot.constants import DEFAULT_BOT_TOKEN
        if not _TG_AVAILABLE:
            pytest.skip("python-telegram-bot not installed")
        bot = HackBotTelegram(config, token="")
        assert bot.token == DEFAULT_BOT_TOKEN

    def test_stop_when_not_running(self, config):
        from hackbot.integrations.telegram_bot import HackBotTelegram, _TG_AVAILABLE
        if not _TG_AVAILABLE:
            pytest.skip("python-telegram-bot not installed")
        bot = HackBotTelegram(config, token="fake:token")
        result = bot.stop()
        assert result.get("ok") is False

    def test_pairing_info(self, config):
        from hackbot.integrations.telegram_bot import HackBotTelegram, _TG_AVAILABLE
        if not _TG_AVAILABLE:
            pytest.skip("python-telegram-bot not installed")
        bot = HackBotTelegram(config, token="fake:token")
        bot._bot_username = "test_hackbot"
        info = bot.get_pairing_info()
        assert info["code"]
        assert info["bot_username"] == "test_hackbot"
        assert "https://t.me/test_hackbot" in info["link"]
        assert info["expires_in"] > 0


# ── CLI Integration ──────────────────────────────────────────────────────────

class TestCLIIntegration:
    def test_telegram_command_in_dispatch(self):
        """The /telegram command is registered in the CLI command dispatch."""
        try:
            from hackbot.cli import HackBotApp
        except ImportError:
            pytest.skip("CLI dependencies not installed")
        config = HackBotConfig()
        app = HackBotApp(config)
        # The command should exist in _handle_command dispatch
        assert hasattr(app, "_handle_telegram")

    def test_click_telegram_subcommand(self):
        """The 'telegram' Click subcommand is registered."""
        try:
            from hackbot.cli import main
        except ImportError:
            pytest.skip("CLI dependencies not installed")
        # Check that telegram is in the group commands
        assert "telegram" in main.commands


def test_report_generator_accepts_tool_history_kwarg():
    """Regression: Telegram export should pass tool_history, not tools_used."""
    from hackbot.reporting import ReportGenerator
    with tempfile.TemporaryDirectory() as td:
        with patch("hackbot.reporting.REPORTS_DIR", Path(td)):
            rg = ReportGenerator(report_format="json")
            path = rg.generate(
                target="example.com",
                findings=[],
                tool_history=[{"tool": "nmap", "command": "nmap -sV example.com", "success": True}],
            )
            assert path.endswith(".json")
