"""
OpenOS Background Daemon.

Systemd user service that runs continuously, managing system monitoring,
intelligent notifications, scheduled maintenance, and Ollama health checks.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

import click

from openos_core.config import OPENOS_CACHE_DIR, get_config

logger = logging.getLogger("openos-daemon")


class OpenOSDaemon:
    """Main background daemon for OpenOS intelligence."""

    def __init__(self):
        self.config = get_config()
        self._running = False
        self._monitor = None
        self._notifier = None
        self._scheduler = None
        self._event_bus = None
        self._trigger_engine = None
        self._proactive_agent = None

    async def start(self) -> None:
        """Start all daemon services."""
        self._running = True
        logger.info("OpenOS Daemon starting...")

        # Initialize subsystems
        from openos_core.daemon.monitor import SystemMonitor
        from openos_core.daemon.notifier import SmartNotifier
        from openos_core.daemon.scheduler import TaskScheduler

        self._monitor = SystemMonitor(self.config.daemon)
        self._notifier = SmartNotifier()
        self._scheduler = TaskScheduler()

        # Initialize proactive system
        if self.config.daemon.proactive_enabled:
            from openos_core.daemon.event_bus import EventBus
            from openos_core.daemon.proactive_agent import ProactiveAgent
            from openos_core.daemon.triggers import TriggerEngine

            self._event_bus = EventBus()
            self._trigger_engine = TriggerEngine.load_rules(self.config.daemon)
            self._proactive_agent = ProactiveAgent(self._notifier)

            await self._proactive_agent.initialize()
            self._event_bus.subscribe(self._on_system_event)

        # Run all services concurrently
        tasks = [
            asyncio.create_task(self._monitor_loop()),
            asyncio.create_task(self._scheduler_loop()),
            asyncio.create_task(self._ollama_watchdog()),
        ]

        if self._event_bus:
            tasks.append(asyncio.create_task(self._event_bus.start()))

        logger.info("OpenOS Daemon running.")

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("OpenOS Daemon shutting down...")

    async def _monitor_loop(self) -> None:
        """Continuous system health monitoring."""
        interval = self.config.daemon.monitor_interval
        while self._running:
            try:
                alerts = self._monitor.check()
                for alert in alerts:
                    await self._notifier.send(
                        title=alert["title"],
                        message=alert["message"],
                        urgency=alert.get("urgency", "normal"),
                    )
            except Exception as e:
                logger.error(f"Monitor error: {e}")
            await asyncio.sleep(interval)

    async def _scheduler_loop(self) -> None:
        """Check for scheduled tasks every minute."""
        while self._running:
            try:
                self._scheduler.check_and_run()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            await asyncio.sleep(60)

    async def _ollama_watchdog(self) -> None:
        """Ensure Ollama is running and responsive."""
        while self._running:
            try:
                import ollama
                ollama.list()
            except Exception:
                logger.warning("Ollama is not responding")
                await self._notifier.send(
                    title="AI Engine Offline",
                    message="Ollama is not running. Some AI features are unavailable.",
                    urgency="normal",
                )
            await asyncio.sleep(300)  # Check every 5 minutes

    async def _on_system_event(self, event) -> None:
        """Handle incoming system events from the event bus."""
        if not self._trigger_engine or not self._proactive_agent:
            return

        rule = self._trigger_engine.evaluate(event)
        if rule:
            await self._proactive_agent.handle_trigger(rule, event)

    def stop(self) -> None:
        self._running = False
        if self._event_bus:
            self._event_bus.stop()
        if self._proactive_agent:
            self._proactive_agent.shutdown()


def _setup_logging() -> None:
    log_file = OPENOS_CACHE_DIR / "openos-daemon.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler(str(log_file)),
            logging.StreamHandler(),
        ],
    )


@click.command()
def main() -> None:
    """OpenOS Background Daemon."""
    _setup_logging()
    daemon = OpenOSDaemon()

    def handle_signal(sig, frame):
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    asyncio.run(daemon.start())


if __name__ == "__main__":
    main()
