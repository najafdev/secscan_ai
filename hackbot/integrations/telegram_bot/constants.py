"""
Telegram Bot Constants
=======================
Shared constants for the HackBot Telegram integration.
"""

from hackbot.config import CONFIG_DIR

# Telegram API limits
MAX_TG_MESSAGE_LENGTH = 4096

# QR code pairing
PAIR_CODE_EXPIRY = 300  # 5 minutes

# Session duration — 7 days (in seconds)
SESSION_TTL = 7 * 24 * 60 * 60  # 604800

# Default public bot token — the shared "HackBot" bot on Telegram.
# Every HackBot installation connects through this bot; QR pairing
# ensures only the correct host machine receives commands.
DEFAULT_BOT_TOKEN = "8668614486:AAGG_N7jedhV6FaeWaRE_nkS5eYb8thqErc"

# Persistent auth store
AUTH_FILE = CONFIG_DIR / "telegram_auth.json"

# Bot display info
BOT_NAME = "HackBot"
BOT_DESCRIPTION = "AI Cybersecurity Assistant — Control HackBot remotely via Telegram"

# Lazy dependency flags — set at module load time
_TG_AVAILABLE = False
_QR_AVAILABLE = False

try:
    import telegram  # noqa: F401
    _TG_AVAILABLE = True
except ImportError:
    pass

try:
    import qrcode  # noqa: F401
    _QR_AVAILABLE = True
except ImportError:
    pass


def check_telegram_deps() -> bool:
    """Check if python-telegram-bot is installed."""
    return _TG_AVAILABLE


def check_qr_deps() -> bool:
    """Check if qrcode library is installed."""
    return _QR_AVAILABLE
