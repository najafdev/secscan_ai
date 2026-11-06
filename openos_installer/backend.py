"""
OpenOS Mock Installation Backend.

Simulates the heavy lifting of `debootstrap`, partitioning, and system cloning.
In a real environment, this would call bash scripts or use python-parted.
"""

from __future__ import annotations

import asyncio
from typing import Callable

from openos_installer.config import InstallConfig


class InstallationBackend:
    """Handles the actual OS installation process."""

    def __init__(self, config: InstallConfig):
        self.config = config

    async def run_installation(self, progress_callback: Callable[[float, str], None]) -> bool:
        """
        Execute the installation steps.
        Calls progress_callback with (percentage, status_message).
        """
        steps = [
            (0.05, "Partitioning target disk..."),
            (0.10, f"Formatting partitions on {self.config.target_disk}..."),
            (0.15, "Mounting target filesystem..."),
            (0.20, "Extracting base system (this may take a while)..."),
            (0.40, "Installing core packages..."),
            (0.60, "Configuring hardware drivers..."),
            (0.70, f"Setting timezone to {self.config.timezone}..."),
            (0.80, f"Creating user account '{self.config.username}'..."),
            (0.90, "Installing bootloader (GRUB)..."),
            (0.95, "Cleaning up..."),
            (1.00, "Installation complete!"),
        ]

        # Simulate work
        for pct, msg in steps:
            progress_callback(pct, msg)

            # Simulate long-running steps
            if "Extracting base system" in msg:
                await asyncio.sleep(4.0)
            elif "Installing core packages" in msg:
                await asyncio.sleep(3.0)
            else:
                await asyncio.sleep(1.0)

        return True
