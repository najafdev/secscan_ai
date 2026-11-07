"""
Telegram Bot — Authentication & QR Pairing
============================================
Handles QR code generation and user pairing to connect
Telegram users to their HackBot instance securely.

Flow:
  1. User searches "HackBot" on Telegram and taps Start
  2. Bot shows "Scan QR code to connect"
  3. User runs `hackbot telegram` on their machine → QR code appears
  4. User scans QR with Telegram camera → deep-link opens the bot with pairing code
  5. Bot verifies code → user is authorized
  6. Authorization persists to disk so re-pairing isn't needed
"""

from __future__ import annotations

import io
import json
import secrets
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from hackbot.integrations.telegram_bot.constants import (
    AUTH_FILE,
    PAIR_CODE_EXPIRY,
    SESSION_TTL,
    _QR_AVAILABLE,
)


# ── Pairing State ────────────────────────────────────────────────────────────

@dataclass
class PairingState:
    """Manages QR code pairing between a local HackBot and Telegram users.

    Each authorized user has a timestamp. Sessions expire after SESSION_TTL
    (default 7 days).  Users can also explicitly log out.
    """

    code: str = ""
    created_at: float = 0.0
    # user_id -> authorization timestamp
    authorized_users: Dict[int, float] = field(default_factory=dict)

    # ── Code lifecycle ───────────────────────────────────────────────────

    def generate_code(self) -> str:
        """Generate a fresh pairing code (URL-safe, 22 chars)."""
        self.code = secrets.token_urlsafe(16)
        self.created_at = time.time()
        return self.code

    def is_expired(self) -> bool:
        """Has the current code passed its expiry window?"""
        return time.time() - self.created_at > PAIR_CODE_EXPIRY

    def verify(self, code: str) -> bool:
        """Constant-time verification of a pairing code."""
        if self.is_expired():
            return False
        return secrets.compare_digest(self.code, code)

    # ── User authorization ───────────────────────────────────────────────

    def authorize(self, user_id: int, ttl: int = 0) -> None:
        """Authorize a user.  ``ttl`` overrides the default SESSION_TTL."""
        self.authorized_users[user_id] = time.time()

    def is_authorized(self, user_id: int, ttl: int = 0) -> bool:
        """Check if user is authorized and session is still valid."""
        ts = self.authorized_users.get(user_id)
        if ts is None:
            return False
        max_age = ttl if ttl > 0 else SESSION_TTL
        if time.time() - ts > max_age:
            # Session expired — remove automatically
            self.revoke(user_id)
            self.save()
            return False
        return True

    def revoke(self, user_id: int) -> bool:
        """Revoke (logout) a user. Returns True if the user was authorized."""
        if user_id in self.authorized_users:
            del self.authorized_users[user_id]
            return True
        return False

    def refresh(self, user_id: int) -> None:
        """Refresh the session timestamp for a user (resets 7-day clock)."""
        if user_id in self.authorized_users:
            self.authorized_users[user_id] = time.time()

    def purge_expired(self, ttl: int = 0) -> int:
        """Remove all expired sessions. Returns count of purged users."""
        max_age = ttl if ttl > 0 else SESSION_TTL
        now = time.time()
        expired = [uid for uid, ts in self.authorized_users.items()
                   if now - ts > max_age]
        for uid in expired:
            del self.authorized_users[uid]
        if expired:
            self.save()
        return len(expired)

    # ── Persistence ──────────────────────────────────────────────────────

    def save(self) -> None:
        """Persist authorized users (with timestamps) to disk."""
        AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "authorized_users": {
                str(uid): ts for uid, ts in self.authorized_users.items()
            }
        }
        AUTH_FILE.write_text(json.dumps(data))

    def load(self) -> None:
        """Load authorized users from disk."""
        if AUTH_FILE.exists():
            try:
                data = json.loads(AUTH_FILE.read_text())
                raw = data.get("authorized_users", {})
                # Support both old format (list) and new format (dict w/ timestamps)
                if isinstance(raw, list):
                    # Migration from old format: treat as authorized now
                    now = time.time()
                    self.authorized_users = {int(uid): now for uid in raw}
                    self.save()  # Re-save in new format
                elif isinstance(raw, dict):
                    self.authorized_users = {
                        int(uid): float(ts) for uid, ts in raw.items()
                    }
                else:
                    self.authorized_users = {}
            except (json.JSONDecodeError, KeyError, ValueError):
                pass


# ── QR Code Generation ───────────────────────────────────────────────────────

def generate_qr_code(bot_username: str, pair_code: str) -> Optional[bytes]:
    """Generate a QR code PNG image for Telegram bot pairing.

    The QR encodes a deep link: ``https://t.me/<bot>?start=<code>``
    When scanned from Telegram's camera, it opens the bot and sends
    ``/start <code>`` automatically.

    Returns PNG bytes or None if qrcode is not installed.
    """
    if not _QR_AVAILABLE:
        return None

    import qrcode as _qr

    url = f"https://t.me/{bot_username}?start={pair_code}"
    qr = _qr.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


def generate_qr_terminal(bot_username: str, pair_code: str) -> str:
    """Generate an ASCII art QR code for terminal display.

    Returns a multi-line string of Unicode block characters,
    or empty string if qrcode is not installed.
    """
    if not _QR_AVAILABLE:
        return ""

    import qrcode as _qr

    url = f"https://t.me/{bot_username}?start={pair_code}"
    qr = _qr.QRCode(version=1, box_size=1, border=2)
    qr.add_data(url)
    qr.make(fit=True)

    matrix = qr.get_matrix()
    lines = []
    for row in matrix:
        line = ""
        for cell in row:
            line += "██" if cell else "  "
        lines.append(line)
    return "\n".join(lines)
