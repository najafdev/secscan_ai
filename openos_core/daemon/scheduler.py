"""
OpenOS Task Scheduler.

Learns user routines, schedules automated maintenance, and triggers
time-based actions like "start my day" routines.
"""

from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Schedule and execute recurring tasks and learned routines."""

    def __init__(self):
        self._last_maintenance: datetime | None = None

    def check_and_run(self) -> None:
        """Check for scheduled tasks and run any that are due."""
        now = datetime.now()

        # Weekly maintenance check (Sundays at 3am)
        if (
            now.weekday() == 6
            and now.hour == 3
            and (
                self._last_maintenance is None
                or (now - self._last_maintenance).days >= 7
            )
        ):
            self._run_maintenance()
            self._last_maintenance = now

    def _run_maintenance(self) -> None:
        """Run scheduled system maintenance."""
        logger.info("Running scheduled maintenance...")
        try:
            import subprocess
            subprocess.run(["sudo", "apt-get", "update"], capture_output=True, timeout=120)
            subprocess.run(["sudo", "apt-get", "autoremove", "-y"], capture_output=True, timeout=120)
            subprocess.run(["sudo", "apt-get", "clean"], capture_output=True, timeout=60)
            logger.info("Scheduled maintenance complete.")
        except Exception as e:
            logger.error(f"Maintenance failed: {e}")
