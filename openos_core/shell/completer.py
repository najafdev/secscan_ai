"""
OpenOS Smart Completer.

Provides intelligent auto-completion for the OpenOS Shell using command history,
installed apps, and common natural language patterns.
"""

from __future__ import annotations

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

# Common OpenOS command patterns for completion
COMMON_COMMANDS = [
    "open ", "launch ", "close ", "install ", "remove ",
    "search ", "find ", "organize ", "clean ", "update ",
    "check system health", "check disk space",
    "play music", "pause music", "next track",
    "open youtube", "open firefox", "open terminal",
    "organize my downloads", "clean my system",
    "update my system", "start my day",
    "list apps", "list processes",
    "show files in ", "find duplicates in ",
    "prepare work setup", "prepare coding setup",
    "tile windows", "maximize window",
    "set volume to ", "what time is it",
    "help", "exit", "clear",
]


class OpenOSCompleter(Completer):
    """Auto-completion for the OpenOS Shell."""

    def __init__(self):
        self._history: list[str] = []

    def add_to_history(self, command: str) -> None:
        """Add a command to the completion history."""
        if command and command not in self._history:
            self._history.insert(0, command)
            if len(self._history) > 200:
                self._history.pop()

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor.lower().strip()
        if not text:
            return

        # Match against common commands
        for cmd in COMMON_COMMANDS:
            if cmd.startswith(text) and cmd != text:
                yield Completion(
                    cmd,
                    start_position=-len(text),
                    display_meta="command",
                )

        # Match against history
        for hist in self._history[:20]:
            if hist.lower().startswith(text) and hist.lower() != text:
                yield Completion(
                    hist,
                    start_position=-len(text),
                    display_meta="history",
                )
