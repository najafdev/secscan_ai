"""
OpenOS Package Manager Tool.

Natural language to apt/flatpak commands with progress and error translation.
"""

from __future__ import annotations

import subprocess

from openos_core.tools.base import BaseTool, tool_function


class PackageManagerTool(BaseTool):
    """Install, remove, and search packages with natural language."""

    @property
    def name(self) -> str:
        return "package_manager"

    @property
    def description(self) -> str:
        return "Install, remove, and search system packages"

    @tool_function(
        description="Install a package using apt. Translates common app names to package names.",
        parameters={
            "package": {"type": "string", "description": "Package or app name to install (e.g., 'vscode', 'vlc', 'nodejs')"},
        },
        destructive=True,
        confirm_message="📦 Install {package}?",
    )
    def install(self, package: str) -> str:
        # Common name translations
        aliases = {
            "vscode": "code", "visual studio code": "code",
            "chrome": "chromium", "google chrome": "chromium",
            "node": "nodejs", "python": "python3",
            "pip": "python3-pip", "docker": "docker.io",
        }
        pkg = aliases.get(package.lower(), package.lower())

        try:
            result = subprocess.run(
                ["sudo", "apt-get", "install", "-y", pkg],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode == 0:
                return f"✅ Successfully installed {pkg}"
            if "Unable to locate package" in result.stderr:
                return f"Package '{pkg}' not found. Try: openos \"search package {package}\""
            return f"Install failed: {result.stderr[:200]}"
        except subprocess.TimeoutExpired:
            return "⚠️ Installation timed out"
        except Exception as e:
            return f"Install error: {e}"

    @tool_function(
        description="Remove/uninstall a package",
        parameters={
            "package": {"type": "string", "description": "Package name to remove"},
        },
        destructive=True,
        confirm_message="🗑️ Remove package {package}?",
    )
    def remove(self, package: str) -> str:
        try:
            result = subprocess.run(
                ["sudo", "apt-get", "remove", "-y", package],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                return f"✅ Removed {package}"
            return f"Remove failed: {result.stderr[:200]}"
        except Exception as e:
            return f"Remove error: {e}"

    @tool_function(
        description="Search for available packages matching a query",
        parameters={
            "query": {"type": "string", "description": "Search term for packages"},
        },
    )
    def search(self, query: str) -> str:
        try:
            result = subprocess.run(
                ["apt-cache", "search", query],
                capture_output=True, text=True, timeout=30,
            )
            lines = result.stdout.strip().splitlines()
            if not lines:
                return f"No packages found matching '{query}'"
            output = [f"📦 Packages matching '{query}' ({len(lines)} results):"]
            for line in lines[:15]:
                name, _, desc = line.partition(" - ")
                output.append(f"  • {name.strip()} — {desc.strip()[:60]}")
            if len(lines) > 15:
                output.append(f"  ... and {len(lines)-15} more")
            return "\n".join(output)
        except Exception as e:
            return f"Search error: {e}"

    @tool_function(
        description="Check if a package is installed",
        parameters={
            "package": {"type": "string", "description": "Package name to check"},
        },
    )
    def is_installed(self, package: str) -> str:
        try:
            result = subprocess.run(
                ["dpkg", "-l", package],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and "ii" in result.stdout:
                return f"✅ {package} is installed"
            return f"❌ {package} is NOT installed"
        except Exception as e:
            return f"Check error: {e}"
