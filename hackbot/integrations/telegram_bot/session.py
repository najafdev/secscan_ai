"""
Telegram Bot — Per-User Sessions
==================================
Each Telegram user gets an independent HackBot session with its own
Chat, Agent, and Plan mode instances.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from hackbot.modes.agent import AgentMode
from hackbot.modes.chat import ChatMode
from hackbot.modes.plan import PlanMode


@dataclass
class TelegramUserSession:
    """Per-user HackBot session state carried across messages."""

    user_id: int
    mode: str = "chat"  # "chat" | "agent" | "plan"
    chat_mode: Optional[ChatMode] = None
    agent_mode: Optional[AgentMode] = None
    plan_mode: Optional[PlanMode] = None
    last_activity: float = field(default_factory=time.time)

    def touch(self) -> None:
        """Update last-activity timestamp."""
        self.last_activity = time.time()
