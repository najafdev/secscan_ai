"""
OpenOS System Events.

Defines the event types and SystemEvent dataclass used by the proactive
trigger system. Events are emitted by the EventBus when D-Bus signals
indicate meaningful system state changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(str, Enum):
    """System event types that the proactive engine can react to."""

    # ─── Power / Battery ───
    BATTERY_LOW = "BATTERY_LOW"
    BATTERY_CHARGING = "BATTERY_CHARGING"
    BATTERY_FULL = "BATTERY_FULL"
    POWER_AC = "POWER_AC"
    POWER_BATTERY = "POWER_BATTERY"

    # ─── Network ───
    NETWORK_CONNECTED = "NETWORK_CONNECTED"
    NETWORK_DISCONNECTED = "NETWORK_DISCONNECTED"
    WIFI_CHANGED = "WIFI_CHANGED"

    # ─── Applications ───
    APP_OPENED = "APP_OPENED"
    APP_CLOSED = "APP_CLOSED"

    # ─── Hardware ───
    USB_CONNECTED = "USB_CONNECTED"
    USB_REMOVED = "USB_REMOVED"
    LID_CLOSED = "LID_CLOSED"
    LID_OPENED = "LID_OPENED"

    # ─── Session ───
    SCREEN_LOCKED = "SCREEN_LOCKED"
    SCREEN_UNLOCKED = "SCREEN_UNLOCKED"

    # ─── Generic ───
    CUSTOM = "CUSTOM"


class Severity(str, Enum):
    """Event severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class SystemEvent:
    """
    Normalized system event emitted by the EventBus.

    Attributes:
        event_type:  The kind of event (battery, network, app, etc.).
        source:      Which D-Bus service produced the event.
        data:        Event-specific payload (percentage, app_name, etc.).
        timestamp:   When the event was detected.
        severity:    How important this event is.
    """

    event_type: EventType
    source: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    severity: Severity = Severity.INFO

    def __str__(self) -> str:
        payload = ", ".join(f"{k}={v}" for k, v in self.data.items())
        return f"[{self.severity.value.upper()}] {self.event_type.value}: {payload} (via {self.source})"

    def format_template(self, template: str) -> str:
        """Format a string template with event data values.

        Example: "Battery at {percentage}%" → "Battery at 8%"
        """
        try:
            return template.format(**self.data)
        except (KeyError, IndexError, ValueError):
            return template
