"""
OpenOS Installer Tools.

Specialized tools for the AI agent to gather system information
and configure the installation.
"""

from __future__ import annotations

import subprocess

from openos_core.tools.base import BaseTool, tool_function
from openos_installer.config import InstallConfig


class InstallerTool(BaseTool):
    """Tools for guiding the OS installation."""

    def __init__(self, config: InstallConfig):
        self.install_config = config
        self._on_state_change = None
        self._on_start_install = None

    @property
    def name(self) -> str:
        return "installer"

    @property
    def description(self) -> str:
        return "OS installation configuration and execution tools"

    def set_callbacks(self, on_state_change, on_start_install):
        self._on_state_change = on_state_change
        self._on_start_install = on_start_install

    @tool_function(
        description="List all available block devices (hard drives, SSDs) on the system. Use this to show the user where they can install the OS.",
        parameters={},
    )
    def list_disks(self) -> str:
        """List block devices."""
        try:
            result = subprocess.run(
                ["lsblk", "-d", "-n", "-o", "NAME,SIZE,MODEL,TYPE"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                disks = []
                for line in result.stdout.strip().splitlines():
                    if "disk" in line.lower() or "loop" not in line.lower():
                        disks.append(line.strip())
                if disks:
                    return "Available Disks:\n" + "\n".join(disks)
                return "No valid installation disks found."
            return "Failed to list disks."
        except Exception as e:
            return f"Error listing disks: {e}"

    @tool_function(
        description="Save the user's installation preferences. Call this whenever the user confirms a setting.",
        parameters={
            "username": {"type": "string", "description": "The chosen username (lowercase, no spaces)", "optional": True},
            "password": {"type": "string", "description": "The user's chosen password", "optional": True},
            "timezone": {"type": "string", "description": "The timezone (e.g., 'America/New_York')", "optional": True},
            "target_disk": {"type": "string", "description": "The chosen target disk (e.g., 'sda' or 'nvme0n1')", "optional": True},
            "hostname": {"type": "string", "description": "The system hostname", "optional": True},
        },
    )
    def set_install_config(
        self,
        username: str = "",
        password: str = "",
        timezone: str = "",
        target_disk: str = "",
        hostname: str = ""
    ) -> str:
        """Update the installation state."""
        changes = []
        if username:
            self.install_config.username = username
            changes.append("username")
        if password:
            self.install_config.password = password
            changes.append("password")
        if timezone:
            self.install_config.timezone = timezone
            changes.append("timezone")
        if target_disk:
            self.install_config.target_disk = target_disk
            changes.append("target_disk")
        if hostname:
            self.install_config.hostname = hostname
            changes.append("hostname")

        if self._on_state_change:
            self._on_state_change()

        if changes:
            return f"✅ Saved configuration: {', '.join(changes)}."
        return "No configuration changes made."

    @tool_function(
        description="Check what configuration items are still missing before installation can begin.",
        parameters={},
    )
    def get_missing_config(self) -> str:
        """Return a list of missing configuration fields."""
        missing = []
        if not self.install_config.username: missing.append("username")
        if not self.install_config.password: missing.append("password")
        if not self.install_config.timezone: missing.append("timezone")
        if not self.install_config.target_disk: missing.append("target_disk")

        if not missing:
            return "All configuration is complete! You can start the installation."
        return "Still missing: " + ", ".join(missing)

    @tool_function(
        description="Start the actual OS installation process. ONLY call this when all configuration is complete and the user has explicitly confirmed they want to begin installing.",
        parameters={},
    )
    def start_installation(self) -> str:
        """Trigger the installation backend."""
        if not self.install_config.is_ready():
            return "Cannot start installation: configuration is incomplete. Please check get_missing_config()."

        if self._on_start_install:
            self._on_start_install()
            return "Installation started. Please wait for the process to complete."

        return "Failed to trigger installation."
