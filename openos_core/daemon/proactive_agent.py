"""
OpenOS Proactive Agent.

Autonomous agent that bridges the trigger system to the OpenOS Brain.
When a trigger fires with an action prompt, this agent initializes a
dedicated Brain instance and executes the action without user interaction.

Maintains an action log so the user can later ask "what did you do?"
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from openos_core.daemon.events import SystemEvent
from openos_core.daemon.triggers import TriggerRule

logger = logging.getLogger(__name__)

# Maximum number of action log entries to keep in memory
_MAX_LOG_ENTRIES = 200


@dataclass
class ActionLogEntry:
    """Record of an autonomous action taken by the proactive agent."""

    timestamp: datetime
    trigger_name: str
    event_type: str
    event_data: dict[str, Any]
    prompt: str
    response: str
    actions: list[dict]
    success: bool


class ProactiveAgent:
    """
    Autonomous agent that executes Brain actions in response to triggers.

    Operates a dedicated OpenOSBrain instance (separate from the interactive
    shell) with a specialized system prompt explaining it's in proactive mode.
    """

    def __init__(self, notifier: Any) -> None:
        self._brain: Any = None
        self._notifier = notifier
        self._action_log: list[ActionLogEntry] = []
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def initialize(self) -> bool:
        """Initialize the dedicated Brain instance for proactive actions."""
        async with self._init_lock:
            if self._initialized:
                return True

            try:
                from openos_core.brain.engine import OpenOSBrain
                self._brain = OpenOSBrain()
                ok = await self._brain.initialize()
                if ok:
                    # Inject proactive context into the Brain's system prompt
                    self._brain._messages[0]["content"] += _PROACTIVE_SYSTEM_ADDENDUM
                    self._initialized = True
                    logger.info("Proactive agent Brain initialized")
                    return True
                else:
                    logger.warning(
                        "Proactive agent could not connect to LLM backend — "
                        "actions will be skipped until backend is available"
                    )
                    return False
            except Exception as e:
                logger.error(f"Proactive agent init failed: {e}")
                return False

    async def handle_trigger(self, rule: TriggerRule, event: SystemEvent) -> None:
        """
        Handle a matched trigger rule.

        1. Send notification (if rule.notify is True)
        2. Execute Brain action (if rule.action is non-empty and not require_confirmation)
        """
        # Send notification
        if rule.notify and rule.notification_message:
            message = event.format_template(rule.notification_message)
            try:
                await self._notifier.send(
                    title="OpenOS — Proactive",
                    message=message,
                    urgency="critical" if event.severity.value == "critical" else "normal",
                )
            except Exception as e:
                logger.error(f"Notification failed for trigger {rule.name}: {e}")

        # Execute Brain action (if any)
        if rule.action and not rule.require_confirmation:
            await self._execute_brain_action(rule, event)
        elif rule.action and rule.require_confirmation:
            # Just notify, don't execute
            logger.info(
                f"Trigger {rule.name} requires confirmation — skipping auto-execute"
            )

    async def _execute_brain_action(
        self, rule: TriggerRule, event: SystemEvent
    ) -> None:
        """Execute a Brain action for the given trigger."""
        # Lazy-initialize the Brain on first action
        if not self._initialized:
            ok = await self.initialize()
            if not ok:
                logger.warning(
                    f"Cannot execute trigger {rule.name} — Brain not available"
                )
                self._log_action(rule, event, "", [], success=False)
                return

        # Format the action prompt with event data
        prompt = event.format_template(rule.action)

        logger.info(f"Proactive action [{rule.name}]: {prompt[:120]}...")

        try:
            # Clear previous context to keep each action independent
            self._brain.clear_context()
            # Re-inject the proactive system addendum
            if self._brain._messages:
                if _PROACTIVE_SYSTEM_ADDENDUM not in self._brain._messages[0]["content"]:
                    self._brain._messages[0]["content"] += _PROACTIVE_SYSTEM_ADDENDUM

            result = await self._brain.process(prompt)

            response = result.get("response", "")
            actions = result.get("actions", [])

            logger.info(
                f"Proactive action [{rule.name}] completed: "
                f"{len(actions)} tool calls, response: {response[:100]}"
            )

            self._log_action(rule, event, response, actions, success=True)

            # Notify user about what was done (if there were actual tool actions)
            if actions and self._notifier:
                action_summary = ", ".join(a.get("tool", "?") for a in actions[:3])
                try:
                    await self._notifier.send(
                        title="OpenOS — Action Taken",
                        message=f"[{rule.name}] Executed: {action_summary}",
                        urgency="normal",
                    )
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Proactive action [{rule.name}] failed: {e}")
            self._log_action(rule, event, str(e), [], success=False)

    def _log_action(
        self,
        rule: TriggerRule,
        event: SystemEvent,
        response: str,
        actions: list[dict],
        success: bool,
    ) -> None:
        """Record an action in the log."""
        entry = ActionLogEntry(
            timestamp=datetime.now(),
            trigger_name=rule.name,
            event_type=event.event_type.value,
            event_data=dict(event.data),
            prompt=rule.action[:200],
            response=response[:500],
            actions=actions[:5],
            success=success,
        )
        self._action_log.append(entry)

        # Trim log if too large
        if len(self._action_log) > _MAX_LOG_ENTRIES:
            self._action_log = self._action_log[-_MAX_LOG_ENTRIES:]

    def get_action_log(self) -> list[ActionLogEntry]:
        """Get the full action log (most recent last)."""
        return list(self._action_log)

    def get_recent_actions(self, count: int = 10) -> list[ActionLogEntry]:
        """Get the N most recent action log entries."""
        return self._action_log[-count:]

    def shutdown(self) -> None:
        """Clean shutdown."""
        if self._brain:
            self._brain.shutdown()
        logger.info("Proactive agent shut down")


# ─── Proactive System Prompt Addendum ────────────────────────────────

_PROACTIVE_SYSTEM_ADDENDUM = """

## Proactive Mode

You are currently operating in PROACTIVE MODE. This means:
- You have been triggered automatically by a system event (battery change, app launch, etc.)
- You should execute the requested actions immediately without asking for confirmation.
- Be efficient — take the necessary actions and report what you did concisely.
- Do NOT ask follow-up questions. Just act and report results.
- If a requested tool is not available, skip it and mention what you couldn't do.
"""
