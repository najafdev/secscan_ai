"""
OpenOS System Maintenance Tool.

Auto-clean junk, update packages, monitor performance, and optimize the system.
"""

from __future__ import annotations

import subprocess
from datetime import datetime

import psutil

from openos_core.tools.base import BaseTool, tool_function


class SystemMaintenanceTool(BaseTool):
    """System self-maintenance: clean, update, monitor, optimize."""

    @property
    def name(self) -> str:
        return "system_maintenance"

    @property
    def description(self) -> str:
        return "System maintenance — clean junk, update packages, check health, optimize"

    @tool_function(
        description="Check overall system health: CPU, RAM, disk usage, temperature, uptime",
        parameters={},
    )
    def check_health(self) -> str:
        cpu_percent = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        boot = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot

        lines = [
            "🖥️  System Health Report",
            "━" * 35,
            f"  CPU Usage:    {cpu_percent:5.1f}% {'🔴' if cpu_percent > 90 else '🟡' if cpu_percent > 70 else '🟢'}",
            f"  RAM Usage:    {mem.percent:5.1f}% ({_hs(mem.used)} / {_hs(mem.total)}) {'🔴' if mem.percent > 85 else '🟢'}",
            f"  Disk Usage:   {disk.percent:5.1f}% ({_hs(disk.used)} / {_hs(disk.total)}) {'🔴' if disk.percent > 90 else '🟢'}",
            f"  Uptime:       {uptime.days}d {uptime.seconds//3600}h {(uptime.seconds%3600)//60}m",
            f"  Processes:    {len(psutil.pids())}",
        ]

        # CPU temperature (if available)
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        t = entries[0].current
                        lines.append(f"  Temperature:  {t:.0f}°C ({name}) {'🔴' if t > 80 else '🟢'}")
                        break
        except (AttributeError, Exception):
            pass

        # Top processes by CPU
        procs = sorted(psutil.process_iter(["name", "cpu_percent"]),
                       key=lambda p: p.info.get("cpu_percent", 0) or 0, reverse=True)[:5]
        lines.append("\n  Top Processes:")
        for p in procs:
            lines.append(f"    {p.info.get('cpu_percent', 0):5.1f}%  {p.info.get('name', '?')}")

        return "\n".join(lines)

    @tool_function(
        description="Clean system junk: apt cache, temp files, old logs, trash",
        parameters={},
        destructive=True,
        confirm_message="🧹 This will clean apt cache, temp files, and old logs. Proceed?",
    )
    def clean_system(self) -> str:
        results = []

        cmds = [
            ("Cleaning apt cache", ["sudo", "apt-get", "clean"]),
            ("Removing unused packages", ["sudo", "apt-get", "autoremove", "-y"]),
            ("Cleaning temp files", ["sudo", "find", "/tmp", "-type", "f", "-atime", "+7", "-delete"]),
            ("Cleaning old journal logs", ["sudo", "journalctl", "--vacuum-time=7d"]),
        ]

        for desc, cmd in cmds:
            try:
                subprocess.run(cmd, capture_output=True, timeout=120)
                results.append(f"  ✅ {desc}")
            except Exception as e:
                results.append(f"  ⚠️ {desc}: {e}")

        return "🧹 System Cleanup Complete\n" + "\n".join(results)

    @tool_function(
        description="Check for and install system updates (apt update + upgrade)",
        parameters={
            "apply": {"type": "boolean", "description": "If true, install updates. If false, just check.", "optional": True},
        },
        destructive=True,
        confirm_message="📦 This will update system packages. Proceed?",
    )
    def update_system(self, apply: bool = False) -> str:
        try:
            subprocess.run(["sudo", "apt-get", "update"], capture_output=True, timeout=120)
            result = subprocess.run(
                ["apt", "list", "--upgradable"],
                capture_output=True, text=True, timeout=30,
            )
            upgradable = [l for l in result.stdout.splitlines() if "/" in l]

            if not upgradable:
                return "✅ System is up to date — no updates available."

            if not apply:
                lines = [f"📦 {len(upgradable)} updates available:"]
                for pkg in upgradable[:15]:
                    lines.append(f"  • {pkg.split('/')[0]}")
                if len(upgradable) > 15:
                    lines.append(f"  ... and {len(upgradable)-15} more")
                lines.append("\nSay 'update my system' to install them.")
                return "\n".join(lines)

            subprocess.run(["sudo", "apt-get", "upgrade", "-y"], capture_output=True, timeout=600)
            return f"✅ Installed {len(upgradable)} updates successfully."

        except Exception as e:
            return f"⚠️ Update failed: {e}"

    @tool_function(
        description="Get detailed info about running processes, optionally filtered by name",
        parameters={
            "filter_name": {"type": "string", "description": "Process name to filter by", "optional": True},
        },
    )
    def list_processes(self, filter_name: str = "") -> str:
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
            info = p.info
            if filter_name and filter_name.lower() not in (info.get("name") or "").lower():
                continue
            procs.append(info)

        procs.sort(key=lambda x: x.get("cpu_percent", 0) or 0, reverse=True)

        lines = [f"{'PID':>7}  {'CPU%':>6}  {'MEM%':>6}  {'STATUS':<10}  NAME"]
        lines.append("─" * 55)
        for p in procs[:20]:
            lines.append(
                f"{p.get('pid','?'):>7}  {p.get('cpu_percent',0) or 0:>5.1f}%  "
                f"{p.get('memory_percent',0) or 0:>5.1f}%  {p.get('status','?'):<10}  "
                f"{p.get('name','?')}"
            )
        return "\n".join(lines)


def _hs(b: int) -> str:
    val = float(b)
    for u in ["B", "KB", "MB", "GB", "TB"]:
        if val < 1024:
            return f"{val:.1f}{u}"
        val /= 1024
    return f"{val:.1f}PB"
