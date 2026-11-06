"""
OpenOS System Monitor.

Continuously monitors CPU, RAM, disk, and temperature.
Generates alerts when thresholds are crossed, with intelligent debouncing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import psutil

from openos_core.config import DaemonConfig


@dataclass
class Alert:
    title: str
    message: str
    urgency: str = "normal"  # low, normal, critical


class SystemMonitor:
    """System health monitor with intelligent alerting."""

    def __init__(self, config: DaemonConfig):
        self.config = config
        self._last_alerts: dict[str, float] = {}  # key -> timestamp
        self._cooldown = 300  # 5 min between repeated alerts

    def check(self) -> list[dict]:
        """Run all health checks and return any alerts."""
        alerts = []

        # CPU check
        cpu = psutil.cpu_percent(interval=1)
        if cpu > self.config.cpu_threshold:
            alert = self._make_alert(
                "cpu_high",
                "⚡ High CPU Usage",
                f"CPU at {cpu:.0f}%. Top processes may be slowing your system.",
                "normal" if cpu < 95 else "critical",
            )
            if alert:
                alerts.append(alert)

        # RAM check
        mem = psutil.virtual_memory()
        if mem.percent > self.config.ram_threshold:
            alert = self._make_alert(
                "ram_high",
                "🧠 High Memory Usage",
                f"RAM at {mem.percent:.0f}% ({_hs(mem.used)} used). "
                "Consider closing some applications.",
                "normal" if mem.percent < 95 else "critical",
            )
            if alert:
                alerts.append(alert)

        # Disk check
        disk = psutil.disk_usage("/")
        if disk.percent > self.config.disk_threshold:
            alert = self._make_alert(
                "disk_high",
                "💾 Low Disk Space",
                f"Disk at {disk.percent:.0f}% — only {_hs(disk.free)} free. "
                "Say 'clean my system' to free up space.",
                "critical" if disk.percent > 95 else "normal",
            )
            if alert:
                alerts.append(alert)

        # Temperature check
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current > self.config.temp_threshold:
                            alert = self._make_alert(
                                f"temp_{name}",
                                "🌡️ High Temperature",
                                f"{name}: {entry.current:.0f}°C. System may throttle.",
                                "critical",
                            )
                            if alert:
                                alerts.append(alert)
                            break
        except (AttributeError, Exception):
            pass

        return alerts

    def _make_alert(self, key: str, title: str, message: str, urgency: str) -> dict | None:
        """Create an alert with cooldown debouncing."""
        now = time.time()
        last = self._last_alerts.get(key, 0)
        if now - last < self._cooldown:
            return None
        self._last_alerts[key] = now
        return {"title": title, "message": message, "urgency": urgency}


def _hs(b: int) -> str:
    val = float(b)
    for u in ["B", "KB", "MB", "GB", "TB"]:
        if val < 1024:
            return f"{val:.1f}{u}"
        val /= 1024
    return f"{val:.1f}PB"
