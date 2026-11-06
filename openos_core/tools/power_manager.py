"""
OpenOS Power Manager Tool.

Provides battery, brightness, and power profile controls for the OpenOS Brain,
especially useful for proactive power-saving triggers.
"""

from __future__ import annotations

import subprocess

from openos_core.tools.base import BaseTool, tool_function


class PowerManagerTool(BaseTool):
    """Manage battery, brightness, and power profiles."""

    @property
    def name(self) -> str:
        return "power_manager"

    @property
    def description(self) -> str:
        return "Manage battery, screen brightness, and power profiles"

    def _run_cmd(self, cmd: list[str]) -> str:
        """Run a command and return stdout or stderr."""
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return f"Command failed: {result.stderr.strip()}"
        except FileNotFoundError:
            return f"Command '{cmd[0]}' not found. It may need to be installed."
        except Exception as e:
            return f"Error executing {cmd[0]}: {str(e)}"

    @tool_function(
        description="Get the current battery status, including percentage and charging state.",
        parameters={},
    )
    def get_battery_status(self) -> str:
        """Get battery status using upower."""
        # Find the battery device
        out = self._run_cmd(["upower", "-e"])
        if "Command failed" in out or "not found" in out:
            return out

        battery_dev = None
        for line in out.splitlines():
            if "battery" in line or "BAT" in line:
                battery_dev = line.strip()
                break

        if not battery_dev:
            return "No battery found on this system."

        # Get battery info
        info = self._run_cmd(["upower", "-i", battery_dev])
        if "Command failed" in info or "not found" in info:
            return info

        # Parse relevant info
        percentage = "Unknown"
        state = "Unknown"
        time_to_empty = ""

        for line in info.splitlines():
            line = line.strip()
            if line.startswith("percentage:"):
                percentage = line.split(":", 1)[1].strip()
            elif line.startswith("state:"):
                state = line.split(":", 1)[1].strip()
            elif line.startswith("time to empty:"):
                time_to_empty = f", Time remaining: {line.split(':', 1)[1].strip()}"

        return f"Battery: {percentage} ({state}){time_to_empty}"

    @tool_function(
        description="Set the screen brightness as a percentage (0-100).",
        parameters={
            "level": {"type": "integer", "description": "Brightness level (0-100)"},
        },
    )
    def set_brightness(self, level: int) -> str:
        """Set screen brightness using brightnessctl."""
        level = max(1, min(100, level))  # Prevent completely turning off the screen (0)
        out = self._run_cmd(["brightnessctl", "set", f"{level}%"])
        if "Command failed" in out or "not found" in out:
            return out
        return f"✅ Brightness set to {level}%."

    @tool_function(
        description="Set the system power profile (power-saver, balanced, performance).",
        parameters={
            "profile": {"type": "string", "description": "One of: power-saver, balanced, performance"},
        },
    )
    def set_power_profile(self, profile: str) -> str:
        """Set power profile using powerprofilesctl."""
        valid_profiles = ["power-saver", "balanced", "performance"]
        if profile not in valid_profiles:
            return f"Invalid profile '{profile}'. Must be one of: {', '.join(valid_profiles)}"

        out = self._run_cmd(["powerprofilesctl", "set", profile])
        if "Command failed" in out or "not found" in out:
            return out
        return f"✅ Power profile set to {profile}."

    @tool_function(
        description="Get the current system power profile.",
        parameters={},
    )
    def get_power_profile(self) -> str:
        """Get power profile using powerprofilesctl."""
        out = self._run_cmd(["powerprofilesctl", "get"])
        if "Command failed" in out or "not found" in out:
            return out
        return f"Current power profile: {out}"
