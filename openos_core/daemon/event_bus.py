"""
OpenOS Event Bus — D-Bus System Event Listener.

Monitors the Linux desktop session for meaningful state changes via D-Bus:
  - UPower: battery level, charging state, lid open/close
  - NetworkManager: connectivity changes
  - UDisks2: USB device plug/unplug
  - D-Bus NameOwnerChanged: application launch/close

Runs a GLib main loop in a background thread and dispatches SystemEvent
objects to subscribers via asyncio.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Awaitable, Callable
from typing import Any

from openos_core.daemon.events import EventType, Severity, SystemEvent

logger = logging.getLogger(__name__)

# Threshold constants
BATTERY_LOW_THRESHOLD = 20
BATTERY_CRITICAL_THRESHOLD = 10


class EventBus:
    """
    Async-compatible D-Bus event listener.

    Starts a GLib main loop in a background thread and bridges events
    into the asyncio event loop via run_coroutine_threadsafe.
    """

    def __init__(self) -> None:
        self._subscribers: list[Callable[[SystemEvent], Awaitable[None]]] = []
        self._glib_loop: Any = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._loop: asyncio.AbstractEventLoop | None = None

        # Track previous states to detect transitions (not spam)
        self._prev_battery_level: int | None = None
        self._prev_on_battery: bool | None = None
        self._prev_lid_closed: bool | None = None
        self._prev_network_state: int | None = None

    def subscribe(self, callback: Callable[[SystemEvent], Awaitable[None]]) -> None:
        """Register a coroutine to receive SystemEvent objects."""
        self._subscribers.append(callback)

    async def start(self) -> None:
        """Start listening to D-Bus signals in a background thread."""
        self._loop = asyncio.get_running_loop()
        self._running = True

        try:
            from gi.repository import GLib
            self._glib_loop = GLib.MainLoop()
        except ImportError:
            logger.warning(
                "PyGObject (gi) not available — proactive event bus disabled. "
                "Install with: pip install PyGObject"
            )
            return

        self._thread = threading.Thread(
            target=self._run_glib_loop,
            name="openos-event-bus",
            daemon=True,
        )
        self._thread.start()
        logger.info("Event bus started — listening for system events")

    def _run_glib_loop(self) -> None:
        """Run the GLib main loop (called in background thread)."""
        try:
            self._setup_monitors()
            self._glib_loop.run()
        except Exception as e:
            logger.error(f"Event bus GLib loop crashed: {e}")

    def _setup_monitors(self) -> None:
        """Set up all D-Bus signal monitors."""
        self._setup_battery_monitor()
        self._setup_network_monitor()
        self._setup_app_monitor()
        self._setup_usb_monitor()

    # ─── Battery / Power (UPower) ────────────────────────────────────

    def _setup_battery_monitor(self) -> None:
        """Monitor UPower for battery and lid changes."""
        try:
            import pydbus
            bus = pydbus.SystemBus()

            # Find the display battery device
            upower = bus.get("org.freedesktop.UPower", "/org/freedesktop/UPower")

            # Monitor UPower properties (OnBattery, LidIsClosed)
            upower.PropertiesChanged.connect(self._on_upower_props_changed)

            # Monitor the display device for battery level
            try:
                display_dev = bus.get(
                    "org.freedesktop.UPower",
                    "/org/freedesktop/UPower/devices/DisplayDevice",
                )
                display_dev.PropertiesChanged.connect(self._on_battery_props_changed)
            except Exception:
                # Try to find battery device by enumerating
                for dev_path in upower.EnumerateDevices():
                    try:
                        dev = bus.get("org.freedesktop.UPower", dev_path)
                        # Type 2 = Battery
                        if dev.Type == 2:
                            dev.PropertiesChanged.connect(self._on_battery_props_changed)
                            logger.info(f"Monitoring battery device: {dev_path}")
                            break
                    except Exception:
                        continue

            logger.info("Battery monitor active")
        except Exception as e:
            logger.warning(f"Battery monitor unavailable: {e}")

    def _on_upower_props_changed(
        self, interface: str, changed: dict, invalidated: list
    ) -> None:
        """Handle UPower property changes (lid, AC/battery)."""
        if "OnBattery" in changed:
            on_battery = bool(changed["OnBattery"])
            if on_battery != self._prev_on_battery:
                self._prev_on_battery = on_battery
                event_type = EventType.POWER_BATTERY if on_battery else EventType.POWER_AC
                self._emit(SystemEvent(
                    event_type=event_type,
                    source="upower",
                    data={"on_battery": on_battery},
                    severity=Severity.INFO,
                ))

        if "LidIsClosed" in changed:
            lid_closed = bool(changed["LidIsClosed"])
            if lid_closed != self._prev_lid_closed:
                self._prev_lid_closed = lid_closed
                event_type = EventType.LID_CLOSED if lid_closed else EventType.LID_OPENED
                self._emit(SystemEvent(
                    event_type=event_type,
                    source="upower",
                    data={"lid_closed": lid_closed},
                    severity=Severity.INFO,
                ))

    def _on_battery_props_changed(
        self, interface: str, changed: dict, invalidated: list
    ) -> None:
        """Handle battery device property changes (level, state)."""
        percentage = changed.get("Percentage")
        state = changed.get("State")

        if percentage is not None:
            pct = int(percentage)

            # Detect charging state change
            # UPower State: 1=Charging, 2=Discharging, 3=Empty, 4=FullyCharged
            if state is not None:
                if state == 1:
                    self._emit(SystemEvent(
                        event_type=EventType.BATTERY_CHARGING,
                        source="upower",
                        data={"percentage": pct, "state": "charging"},
                        severity=Severity.INFO,
                    ))
                elif state == 4:
                    self._emit(SystemEvent(
                        event_type=EventType.BATTERY_FULL,
                        source="upower",
                        data={"percentage": pct, "state": "full"},
                        severity=Severity.INFO,
                    ))

            # Detect low battery (only emit on threshold crossings)
            if pct <= BATTERY_LOW_THRESHOLD:
                prev = self._prev_battery_level
                if prev is None or prev > BATTERY_LOW_THRESHOLD or (
                    pct <= BATTERY_CRITICAL_THRESHOLD and prev > BATTERY_CRITICAL_THRESHOLD
                ):
                    severity = (
                        Severity.CRITICAL if pct <= BATTERY_CRITICAL_THRESHOLD
                        else Severity.WARNING
                    )
                    self._emit(SystemEvent(
                        event_type=EventType.BATTERY_LOW,
                        source="upower",
                        data={
                            "percentage": pct,
                            "discharging": state == 2 if state is not None else True,
                        },
                        severity=severity,
                    ))

            self._prev_battery_level = pct

    # ─── Network (NetworkManager) ────────────────────────────────────

    def _setup_network_monitor(self) -> None:
        """Monitor NetworkManager for connectivity changes."""
        try:
            import pydbus
            bus = pydbus.SystemBus()
            nm = bus.get(
                "org.freedesktop.NetworkManager",
                "/org/freedesktop/NetworkManager",
            )
            nm.PropertiesChanged.connect(self._on_nm_props_changed)
            logger.info("Network monitor active")
        except Exception as e:
            logger.warning(f"Network monitor unavailable: {e}")

    def _on_nm_props_changed(
        self, interface: str, changed: dict, invalidated: list
    ) -> None:
        """Handle NetworkManager state changes."""
        # NM Connectivity: 0=Unknown, 1=None, 2=Portal, 3=Limited, 4=Full
        connectivity = changed.get("Connectivity")
        if connectivity is not None:
            if connectivity != self._prev_network_state:
                self._prev_network_state = connectivity
                if connectivity >= 3:
                    self._emit(SystemEvent(
                        event_type=EventType.NETWORK_CONNECTED,
                        source="networkmanager",
                        data={"state": "connected", "connectivity": connectivity},
                        severity=Severity.INFO,
                    ))
                elif connectivity <= 1:
                    self._emit(SystemEvent(
                        event_type=EventType.NETWORK_DISCONNECTED,
                        source="networkmanager",
                        data={"state": "disconnected", "connectivity": connectivity},
                        severity=Severity.WARNING,
                    ))

    # ─── Application Launch/Close ────────────────────────────────────

    def _setup_app_monitor(self) -> None:
        """Monitor D-Bus for application launch and close events."""
        try:
            import pydbus
            bus = pydbus.SessionBus()
            dbus_obj = bus.get("org.freedesktop.DBus", "/org/freedesktop/DBus")
            dbus_obj.NameOwnerChanged.connect(self._on_name_owner_changed)
            logger.info("App monitor active")
        except Exception as e:
            logger.warning(f"App monitor unavailable: {e}")

    def _on_name_owner_changed(
        self, name: str, old_owner: str, new_owner: str
    ) -> None:
        """Handle D-Bus name ownership changes (app start/stop)."""
        # Only care about well-known names (not :1.xxx connection IDs)
        if name.startswith(":"):
            return

        # Filter to interesting application names
        interesting_prefixes = (
            "org.gnome.", "org.kde.", "org.mozilla.", "com.visualstudio.",
            "org.libreoffice.", "com.spotify.", "org.videolan.",
            "org.gimp.", "com.github.", "org.telegram.",
        )

        # Also detect by executable name in the bus name
        app_keywords = (
            "code", "firefox", "chrome", "chromium", "thunderbird",
            "nautilus", "dolphin", "terminal", "konsole", "gimp",
            "vlc", "spotify", "slack", "discord", "steam",
        )

        is_interesting = (
            any(name.startswith(p) for p in interesting_prefixes)
            or any(kw in name.lower() for kw in app_keywords)
        )

        if not is_interesting:
            return

        # Extract a human-friendly app name from the D-Bus name
        app_name = name.split(".")[-1]

        if old_owner == "" and new_owner != "":
            # New name appeared → app launched
            self._emit(SystemEvent(
                event_type=EventType.APP_OPENED,
                source="dbus",
                data={"app_name": app_name, "bus_name": name},
                severity=Severity.INFO,
            ))
        elif old_owner != "" and new_owner == "":
            # Name disappeared → app closed
            self._emit(SystemEvent(
                event_type=EventType.APP_CLOSED,
                source="dbus",
                data={"app_name": app_name, "bus_name": name},
                severity=Severity.INFO,
            ))

    # ─── USB Devices (UDisks2) ───────────────────────────────────────

    def _setup_usb_monitor(self) -> None:
        """Monitor UDisks2 for USB device plug/unplug."""
        try:
            import pydbus
            bus = pydbus.SystemBus()
            udisks = bus.get(
                "org.freedesktop.UDisks2",
                "/org/freedesktop/UDisks2",
            )
            udisks.InterfacesAdded.connect(self._on_udisks_added)
            udisks.InterfacesRemoved.connect(self._on_udisks_removed)
            logger.info("USB monitor active")
        except Exception as e:
            logger.warning(f"USB monitor unavailable: {e}")

    def _on_udisks_added(self, object_path: str, interfaces: dict) -> None:
        """Handle new UDisks2 interfaces (USB plugged in)."""
        fs_iface = interfaces.get("org.freedesktop.UDisks2.Filesystem")
        block_iface = interfaces.get("org.freedesktop.UDisks2.Block")

        if fs_iface or block_iface:
            label = ""
            device_type = "block"
            if block_iface:
                label = block_iface.get("IdLabel", "")
                if isinstance(label, bytes):
                    label = label.decode("utf-8", errors="ignore")
            if fs_iface:
                device_type = "filesystem"

            self._emit(SystemEvent(
                event_type=EventType.USB_CONNECTED,
                source="udisks2",
                data={
                    "object_path": object_path,
                    "label": label or "Unknown Device",
                    "device_type": device_type,
                },
                severity=Severity.INFO,
            ))

    def _on_udisks_removed(self, object_path: str, interfaces: list) -> None:
        """Handle removed UDisks2 interfaces (USB unplugged)."""
        interesting = (
            "org.freedesktop.UDisks2.Filesystem",
            "org.freedesktop.UDisks2.Block",
        )
        if any(iface in interfaces for iface in interesting):
            self._emit(SystemEvent(
                event_type=EventType.USB_REMOVED,
                source="udisks2",
                data={"object_path": object_path},
                severity=Severity.INFO,
            ))

    # ─── Event Dispatch ──────────────────────────────────────────────

    def _emit(self, event: SystemEvent) -> None:
        """Dispatch a SystemEvent to all subscribers (thread-safe)."""
        logger.info(f"Event: {event}")
        if self._loop is None or not self._subscribers:
            return

        for callback in self._subscribers:
            try:
                coro: Any = callback(event)
                asyncio.run_coroutine_threadsafe(coro, self._loop)
            except Exception as e:
                logger.error(f"Failed to dispatch event to subscriber: {e}")

    def stop(self) -> None:
        """Stop the event bus and GLib main loop."""
        self._running = False
        if self._glib_loop and self._glib_loop.is_running():
            self._glib_loop.quit()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("Event bus stopped")
