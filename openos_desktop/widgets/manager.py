"""
OpenOS Widget Manager.

Manages the lifecycle of desktop widgets and listens to system events
to dynamically change widget context.
"""

from __future__ import annotations

import asyncio
import logging
import threading

try:
    from gi.repository import GLib
    HAS_GLIB = True
except ImportError:
    HAS_GLIB = False

from openos_core.daemon.event_bus import EventBus
from openos_core.daemon.events import EventType, SystemEvent
from openos_desktop.widgets.dynamic_widget import DynamicWidget

logger = logging.getLogger(__name__)


class WidgetManager:
    """Manages dynamic desktop widgets and system context."""

    def __init__(self):
        self.widget = DynamicWidget()
        self.event_bus = EventBus()
        self._async_loop = asyncio.new_event_loop()
        self._thread = None

        # IDE and gaming process names
        self.coding_apps = ["code", "cursor", "nvim", "pycharm", "idea", "sublime"]
        self.gaming_apps = ["steam", "lutris", "wine", "retroarch", "heroic"]

        self.active_apps = set()

    def start(self) -> None:
        """Start the widget manager and event listeners."""
        self.widget.show()

        # Start the async loop and event bus in a background thread
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()
        logger.info("Widget Manager started.")

    def _run_async_loop(self) -> None:
        asyncio.set_event_loop(self._async_loop)
        self.event_bus.subscribe(self._on_system_event)

        # Run event bus start which spawns its own thread for dbus
        self._async_loop.run_until_complete(self.event_bus.start())
        self._async_loop.run_forever()

    async def _on_system_event(self, event: SystemEvent) -> None:
        """Handle incoming system events."""
        if event.event_type == EventType.APP_OPENED:
            app_name = event.data.get("app_name", "").lower()
            if app_name:
                self.active_apps.add(app_name)
                self._evaluate_state()

        elif event.event_type == EventType.APP_CLOSED:
            app_name = event.data.get("app_name", "").lower()
            if app_name in self.active_apps:
                self.active_apps.remove(app_name)
                self._evaluate_state()

    def _evaluate_state(self) -> None:
        """Determine context based on active apps and update widget."""
        new_state = "idle"

        # Gaming takes precedence over coding for now (or vice versa depending on pref)
        for app in self.gaming_apps:
            if any(app in active for active in self.active_apps):
                new_state = "gaming"
                break

        if new_state == "idle":
            for app in self.coding_apps:
                if any(app in active for active in self.active_apps):
                    new_state = "coding"
                    break

        if new_state != self.widget.current_state:
            # Safely update GTK widget from background thread
            if HAS_GLIB:
                GLib.idle_add(self.widget.set_state, new_state)

    def stop(self) -> None:
        """Stop the widget manager."""
        self.event_bus.stop()
        if self._async_loop.is_running():
            self._async_loop.call_soon_threadsafe(self._async_loop.stop)
