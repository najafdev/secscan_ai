"""
OpenOS Smart Notifier.

Sends desktop notifications via D-Bus (org.freedesktop.Notifications).
Filters noise — only shows useful, non-spammy alerts.
"""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)


class SmartNotifier:
    """Intelligent notification system — only useful alerts."""

    def __init__(self):
        self._suppressed: set[str] = set()

    async def send(
        self,
        title: str,
        message: str,
        urgency: str = "normal",
        icon: str = "dialog-information",
        timeout_ms: int = 10000,
    ) -> None:
        """Send a desktop notification."""
        urgency_map = {"low": "low", "normal": "normal", "critical": "critical"}
        urg = urgency_map.get(urgency, "normal")

        try:
            subprocess.run(
                [
                    "notify-send",
                    "--urgency", urg,
                    "--icon", icon,
                    "--expire-time", str(timeout_ms),
                    "--app-name", "OpenOS",
                    title,
                    message,
                ],
                timeout=5,
                capture_output=True,
            )
            logger.info(f"Notification: {title}")
        except FileNotFoundError:
            logger.warning("notify-send not available")
        except Exception as e:
            logger.error(f"Notification failed: {e}")
