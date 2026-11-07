"""
Telegram Bot — Message Utilities
==================================
Helpers for splitting long messages and formatting HackBot
output into Telegram-compatible HTML.
"""

from __future__ import annotations

import html as html_mod
import re
from typing import List

from hackbot.integrations.telegram_bot.constants import MAX_TG_MESSAGE_LENGTH


def split_message(text: str, max_len: int = MAX_TG_MESSAGE_LENGTH) -> List[str]:
    """Split a long message into Telegram-safe chunks.

    Tries to break at newlines so code blocks aren't cut mid-line.
    """
    if len(text) <= max_len:
        return [text]

    chunks: List[str] = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break

        # Try to split at a newline within the allowed window
        split_at = text.rfind("\n", 0, max_len)
        if split_at < max_len // 2:
            # No good newline found — hard-split
            split_at = max_len

        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")

    return chunks


def escape_md(text: str) -> str:
    """Escape Telegram MarkdownV2 special characters (reference only — we use HTML)."""
    special = r"_*[]()~`>#+-=|{}.!"
    for ch in special:
        text = text.replace(ch, f"\\{ch}")
    return text


def format_html(text: str) -> str:
    """Convert HackBot markdown-ish output to Telegram HTML.

    Handles:
    - HTML entity escaping (prevents XSS / parse errors)
    - Fenced code blocks  →  ``<pre><code>…</code></pre>``
    - Inline code          →  ``<code>…</code>``
    - Bold ``**text**``    →  ``<b>text</b>``
    - Italic ``*text*``    →  ``<i>text</i>``
    """
    escaped = html_mod.escape(text)

    # Fenced code blocks: ```lang\ncode\n``` → <pre><code>
    escaped = re.sub(
        r"```\w*\n(.*?)```",
        r"<pre><code>\1</code></pre>",
        escaped,
        flags=re.DOTALL,
    )

    # Inline code: `code` → <code>code</code>
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)

    # Bold: **text** → <b>text</b>
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)

    # Italic: *text* → <i>text</i>
    escaped = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", escaped)

    return escaped
