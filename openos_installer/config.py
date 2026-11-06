"""
OpenOS Installer Configuration State.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class InstallConfig:
    """Holds the user's installation preferences."""

    username: str = ""
    password: str = ""
    timezone: str = ""
    target_disk: str = ""
    hostname: str = "openos"

    def is_ready(self) -> bool:
        """Check if all required fields are filled."""
        return all([
            self.username,
            self.password,
            self.timezone,
            self.target_disk,
            self.hostname
        ])

    def get_summary(self) -> dict[str, str]:
        """Return a summary of the current configuration."""
        return {
            "Username": self.username or "❌ Pending",
            "Password": "✅ Set" if self.password else "❌ Pending",
            "Timezone": self.timezone or "❌ Pending",
            "Target Disk": self.target_disk or "❌ Pending",
            "Hostname": self.hostname or "❌ Pending",
        }
