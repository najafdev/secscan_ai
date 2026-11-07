"""
Telegram Bot — Main Bot Class
===============================
The ``HackBotTelegram`` class wires together auth, sessions, handlers,
and the python-telegram-bot ``Application`` for a complete bot lifecycle.

Usage:
  bot = HackBotTelegram(config, token="...")
  bot.run_polling()           # blocking
  # or
  bot.start_background()      # non-blocking (from REPL / GUI)
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Any, Dict, Optional

from hackbot.config import HackBotConfig, load_config
from hackbot.core.engine import AIEngine
from hackbot.modes.chat import ChatMode
from hackbot.modes.plan import PlanMode

from hackbot.integrations.telegram_bot.auth import (
    PairingState,
    generate_qr_code,
    generate_qr_terminal,
)
from hackbot.integrations.telegram_bot.constants import (
    DEFAULT_BOT_TOKEN,
    PAIR_CODE_EXPIRY,
    _TG_AVAILABLE,
)
from hackbot.integrations.telegram_bot.session import TelegramUserSession

logger = logging.getLogger(__name__)

# ── Conditional imports ──────────────────────────────────────────────────────
if _TG_AVAILABLE:
    from telegram import Bot
    from telegram.constants import ParseMode
    from telegram.ext import (
        Application,
        CallbackQueryHandler,
        CommandHandler,
        MessageHandler,
        filters,
    )


class HackBotTelegram:
    """
    Full HackBot Telegram bot.

    - Users search "HackBot" on Telegram and press Start.
    - Bot tells them to scan a QR code displayed on their terminal.
    - After scanning, the Telegram user is paired and has full control
      of their HackBot instance (chat, agent, plan, intel…).
    """

    def __init__(self, config: HackBotConfig, token: str = ""):
        if not _TG_AVAILABLE:
            raise ImportError(
                "Telegram bot dependencies not installed. Install with:\n"
                "  pip install 'python-telegram-bot>=21.0' qrcode[pil]\n"
                "  or: pip install hackbot[telegram]"
            )

        self.config = config
        # Token resolution order: explicit > config file > env var > built-in default
        self.token = (
            token
            or getattr(config.telegram, "token", "")
            or os.environ.get("TELEGRAM_BOT_TOKEN", "")
            or DEFAULT_BOT_TOKEN
        )
        self.engine = AIEngine(config.ai)
        self.sessions: Dict[int, TelegramUserSession] = {}
        self.pairing = PairingState()
        self.pairing.load()
        # Purge any expired sessions on startup
        self.pairing.purge_expired(
            getattr(config.telegram, "session_ttl_days", 7) * 86400
        )
        self._app: Optional[Application] = None
        self._running = False
        self._bot_username = ""
        self._thread: Optional[threading.Thread] = None

    # ── Session helpers ──────────────────────────────────────────────────

    def _get_session(self, user_id: int) -> TelegramUserSession:
        if user_id not in self.sessions:
            session = TelegramUserSession(user_id=user_id)
            session.chat_mode = ChatMode(self.engine, self.config)
            session.plan_mode = PlanMode(self.engine, self.config)
            self.sessions[user_id] = session
        session = self.sessions[user_id]
        session.touch()
        return session

    def _reset_session(self, user_id: int) -> None:
        session = self._get_session(user_id)
        session.chat_mode = ChatMode(self.engine, self.config)
        session.plan_mode = PlanMode(self.engine, self.config)
        session.agent_mode = None
        session.mode = "chat"

    def _refresh_all_sessions(self) -> None:
        """Rebuild engine + every user session (after config change)."""
        self.engine = AIEngine(self.config.ai)
        for _uid, session in self.sessions.items():
            session.chat_mode = ChatMode(self.engine, self.config)
            session.plan_mode = PlanMode(self.engine, self.config)
            if session.agent_mode:
                session.agent_mode.engine = self.engine

    # ── Auth wrapper ─────────────────────────────────────────────────────

    def _require_auth(self, handler):
        """Wrap a handler so unauthorized users get a pairing prompt.

        Uses the configured session_ttl_days for expiry checks.
        When a session is still valid the 7-day clock is refreshed so
        active users never get logged out mid-conversation.
        """
        ttl = getattr(self.config.telegram, "session_ttl_days", 7) * 86400

        async def wrapper(update, context):
            user_id = update.effective_user.id
            if not self.pairing.is_authorized(user_id, ttl=ttl):
                # Session expired or never authorized
                if user_id in self.sessions:
                    del self.sessions[user_id]
                text = (
                    "🔒 <b>Session expired or not connected.</b>\n\n"
                    "Run <code>hackbot telegram</code> on your machine "
                    "and scan the QR code to reconnect."
                )
                if update.message:
                    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
                elif update.callback_query:
                    await update.callback_query.answer("Session expired", show_alert=True)
                return
            # Refresh session clock on each interaction
            self.pairing.refresh(user_id)
            return await handler(update, context)
        return wrapper

    # ── Application builder ──────────────────────────────────────────────

    def build_app(self) -> Application:
        """Build the ``telegram.ext.Application`` with all handlers."""
        from hackbot.integrations.telegram_bot import handlers as h

        app = Application.builder().token(self.token).build()
        auth = self._require_auth

        # Bind handlers — each handler receives (bot, update, context)
        def _bind(fn):
            async def _wrapped(update, context):
                return await fn(self, update, context)
            return _wrapped

        app.add_handler(CommandHandler("start", _bind(h.cmd_start)))
        app.add_handler(CommandHandler("help", auth(_bind(h.cmd_help))))
        app.add_handler(CommandHandler("chat", auth(_bind(h.cmd_chat))))
        app.add_handler(CommandHandler("agent", auth(_bind(h.cmd_agent))))
        app.add_handler(CommandHandler("step", auth(_bind(h.cmd_step))))
        app.add_handler(CommandHandler("findings", auth(_bind(h.cmd_findings))))
        app.add_handler(CommandHandler("stop", auth(_bind(h.cmd_stop))))
        app.add_handler(CommandHandler("plan", auth(_bind(h.cmd_plan))))
        app.add_handler(CommandHandler("cve", auth(_bind(h.cmd_cve))))
        app.add_handler(CommandHandler("osint", auth(_bind(h.cmd_osint))))
        app.add_handler(CommandHandler("compliance", auth(_bind(h.cmd_compliance))))
        app.add_handler(CommandHandler("model", auth(_bind(h.cmd_model))))
        app.add_handler(CommandHandler("provider", auth(_bind(h.cmd_provider))))
        app.add_handler(CommandHandler("language", auth(_bind(h.cmd_language))))
        app.add_handler(CommandHandler("lang", auth(_bind(h.cmd_language))))
        app.add_handler(CommandHandler("tools", auth(_bind(h.cmd_tools))))
        app.add_handler(CommandHandler("config", auth(_bind(h.cmd_config))))
        app.add_handler(CommandHandler("reset", auth(_bind(h.cmd_reset))))
        app.add_handler(CommandHandler("logout", _bind(h.cmd_logout)))
        app.add_handler(CommandHandler("export", auth(_bind(h.cmd_export))))
        app.add_handler(CommandHandler("version", auth(_bind(h.cmd_version))))
        app.add_handler(CommandHandler("status", auth(_bind(h.cmd_status))))
        app.add_handler(CommandHandler("vulndb", auth(_bind(h.cmd_vulndb))))
        app.add_handler(CommandHandler("attack", auth(_bind(h.cmd_attack))))

        app.add_handler(CallbackQueryHandler(auth(_bind(h.callback_handler))))
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            auth(_bind(h.message_handler)),
        ))

        self._app = app
        return app

    # ── Bot identity ─────────────────────────────────────────────────────

    async def _get_bot_username(self) -> str:
        bot = Bot(self.token)
        me = await bot.get_me()
        self._bot_username = str(me.username or "")
        return self._bot_username

    # ── Pairing info ─────────────────────────────────────────────────────

    def get_pairing_info(self) -> Dict[str, Any]:
        """Generate fresh pairing info (code, QR, link)."""
        code = self.pairing.generate_code()
        qr_bytes = None
        qr_ascii = ""

        if self._bot_username:
            qr_bytes = generate_qr_code(self._bot_username, code)
            qr_ascii = generate_qr_terminal(self._bot_username, code)

        return {
            "code": code,
            "bot_username": self._bot_username,
            "link": f"https://t.me/{self._bot_username}?start={code}" if self._bot_username else "",
            "qr_png": qr_bytes,
            "qr_ascii": qr_ascii,
            "expires_in": PAIR_CODE_EXPIRY,
            "authorized_users": len(self.pairing.authorized_users),
        }

    # ── Run (blocking) ───────────────────────────────────────────────────

    def run_polling(self) -> None:
        """Run the bot with polling (blocks the calling thread)."""
        if not self.token:
            raise ValueError(
                "Telegram bot token not set.\n"
                "Set TELEGRAM_BOT_TOKEN env var or pass --token."
            )

        self.build_app()

        loop = asyncio.new_event_loop()
        self._bot_username = loop.run_until_complete(self._get_bot_username())
        loop.close()

        self._running = True
        logger.info("Starting Telegram bot: @%s", self._bot_username)
        if self._app:
            self._app.run_polling(drop_pending_updates=True)

    # ── Run (background) ─────────────────────────────────────────────────

    def start_background(self) -> Dict[str, Any]:
        """Start the bot in a daemon thread. Returns pairing info."""
        if self._running:
            return {"ok": False, "error": "Bot is already running"}
        if not self.token:
            return {"ok": False, "error": "Telegram bot token not set"}

        loop = asyncio.new_event_loop()
        try:
            self._bot_username = loop.run_until_complete(self._get_bot_username())
        except Exception as e:
            return {"ok": False, "error": f"Invalid bot token: {e}"}
        finally:
            loop.close()

        self.build_app()

        def _run():
            self._running = True
            try:
                if self._app:
                    self._app.run_polling(drop_pending_updates=True)
            finally:
                self._running = False

        self._thread = threading.Thread(target=_run, daemon=True, name="hackbot-telegram")
        self._thread.start()

        info = self.get_pairing_info()
        info["ok"] = True
        info["message"] = f"Bot started: @{self._bot_username}"
        return info

    # ── Stop ─────────────────────────────────────────────────────────────

    def stop(self) -> Dict[str, Any]:
        if not self._running:
            return {"ok": False, "message": "Bot is not running"}
        self._running = False
        if self._app:
            try:
                self._app.stop_running()
            except Exception:
                pass
        return {"ok": True, "message": "Telegram bot stopped"}

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def bot_username(self) -> str:
        return self._bot_username


# ── Singleton ────────────────────────────────────────────────────────────────

_telegram_bot: Optional[HackBotTelegram] = None


def get_telegram_bot(config: Optional[HackBotConfig] = None, token: str = "") -> HackBotTelegram:
    """Get or create the singleton HackBotTelegram instance."""
    global _telegram_bot
    if _telegram_bot is None:
        if config is None:
            config = load_config()
        _telegram_bot = HackBotTelegram(config, token)
    return _telegram_bot


def reset_telegram_bot() -> None:
    """Reset the singleton (stops the bot if running)."""
    global _telegram_bot
    if _telegram_bot and _telegram_bot.is_running:
        _telegram_bot.stop()
    _telegram_bot = None
