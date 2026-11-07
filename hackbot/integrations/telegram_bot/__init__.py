"""
HackBot Telegram Bot
=====================
Full remote control of HackBot via Telegram with QR code authentication.

Package layout::

    telegram_bot/
    ├── __init__.py      ← Public API re-exports (you are here)
    ├── auth.py          ← QR code generation & pairing state
    ├── bot.py           ← Main HackBotTelegram class + singleton
    ├── constants.py     ← Shared constants & dependency checks
    ├── handlers.py      ← All /command handlers
    ├── session.py       ← Per-user session dataclass
    └── utils.py         ← Message splitting & HTML formatting

Quick start::

    from hackbot.integrations.telegram_bot import HackBotTelegram
    bot = HackBotTelegram(config, token="<BOT_TOKEN>")
    bot.run_polling()
"""

# ── Public API (backwards-compatible with the old single-file module) ────────

from hackbot.integrations.telegram_bot.constants import (
    MAX_TG_MESSAGE_LENGTH,
    PAIR_CODE_EXPIRY,
    SESSION_TTL,
    DEFAULT_BOT_TOKEN,
    AUTH_FILE,
    _TG_AVAILABLE,
    _QR_AVAILABLE,
    check_telegram_deps,
    check_qr_deps,
)

from hackbot.integrations.telegram_bot.auth import (
    PairingState,
    generate_qr_code,
    generate_qr_terminal,
)

from hackbot.integrations.telegram_bot.session import (
    TelegramUserSession,
)

from hackbot.integrations.telegram_bot.utils import (
    split_message as _split_message,
    format_html as _format_html,
)

from hackbot.integrations.telegram_bot.bot import (
    HackBotTelegram,
    get_telegram_bot,
    reset_telegram_bot,
)

__all__ = [
    # Constants
    "MAX_TG_MESSAGE_LENGTH",
    "PAIR_CODE_EXPIRY",
    "SESSION_TTL",
    "DEFAULT_BOT_TOKEN",
    "AUTH_FILE",
    "check_telegram_deps",
    "check_qr_deps",
    "_TG_AVAILABLE",
    "_QR_AVAILABLE",
    # Auth
    "PairingState",
    "generate_qr_code",
    "generate_qr_terminal",
    # Session
    "TelegramUserSession",
    # Utils
    "_split_message",
    "_format_html",
    # Bot
    "HackBotTelegram",
    "get_telegram_bot",
    "reset_telegram_bot",
]
