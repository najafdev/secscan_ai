"""
OpenOS Application Launcher Tool.

Launch apps by name (fuzzy-matched), list installed apps, manage .desktop files.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from thefuzz import fuzz, process

from openos_core.tools.base import BaseTool, tool_function

DESKTOP_DIRS = [
    Path("/usr/share/applications"),
    Path("/usr/local/share/applications"),
    Path.home() / ".local" / "share" / "applications",
]


def _parse_desktop_file(path: Path) -> dict | None:
    """Parse a .desktop file into a dict."""
    try:
        data = {"path": str(path)}
        for line in path.read_text(errors="ignore").splitlines():
            if "=" in line and not line.startswith("#"):
                key, _, value = line.partition("=")
                key = key.strip()
                if key in ("Name", "Exec", "Icon", "Comment", "Categories", "Terminal"):
                    data[key] = value.strip()
        if "Name" in data and "Exec" in data:
            return data
    except Exception:
        pass
    return None


def _get_all_apps() -> list[dict]:
    """Get all installed applications from .desktop files."""
    apps = []
    seen = set()
    for d in DESKTOP_DIRS:
        if not d.is_dir():
            continue
        for f in d.glob("*.desktop"):
            if f.name in seen:
                continue
            seen.add(f.name)
            info = _parse_desktop_file(f)
            if info:
                apps.append(info)
    return apps


class AppLauncherTool(BaseTool):
    """Launch applications by natural language name."""

    @property
    def name(self) -> str:
        return "app_launcher"

    @property
    def description(self) -> str:
        return "Launch, list, and manage applications"

    @tool_function(
        description="Launch an application by name. Uses fuzzy matching to find the right app.",
        parameters={
            "app_name": {"type": "string", "description": "Name of the application to launch (e.g., 'firefox', 'code', 'terminal')"},
        },
    )
    def launch_app(self, app_name: str) -> str:
        apps = _get_all_apps()
        if not apps:
            return "No applications found on this system."

        # Fuzzy match against app names
        app_names = {a["Name"]: a for a in apps}
        match = process.extractOne(app_name, app_names.keys(), scorer=fuzz.token_sort_ratio)

        if not match or match[1] < 50:
            return f"Could not find an app matching '{app_name}'. Try 'list apps' to see what's available."

        app = app_names[match[0]]
        exec_cmd = app["Exec"]
        # Remove %u, %f, %U, %F placeholders from Exec
        for placeholder in ["%u", "%U", "%f", "%F", "%i", "%c", "%k"]:
            exec_cmd = exec_cmd.replace(placeholder, "")
        exec_cmd = exec_cmd.strip()

        try:
            subprocess.Popen(
                exec_cmd,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return f"✅ Launched {app['Name']}"
        except Exception as e:
            return f"Failed to launch {app['Name']}: {e}"

    @tool_function(
        description="List all installed applications, optionally filtered by category or search term",
        parameters={
            "search": {"type": "string", "description": "Optional search filter", "optional": True},
        },
    )
    def list_apps(self, search: str = "") -> str:
        apps = _get_all_apps()
        if search:
            apps = [a for a in apps if search.lower() in a["Name"].lower()
                    or search.lower() in a.get("Comment", "").lower()]

        if not apps:
            return "No applications found."

        apps.sort(key=lambda a: a["Name"])
        lines = [f"📱 Installed Applications ({len(apps)}):"]
        for a in apps[:30]:
            comment = a.get("Comment", "")
            if comment:
                lines.append(f"  • {a['Name']} — {comment[:60]}")
            else:
                lines.append(f"  • {a['Name']}")
        if len(apps) > 30:
            lines.append(f"  ... and {len(apps)-30} more")
        return "\n".join(lines)

    @tool_function(
        description="Close/kill a running application by name",
        parameters={
            "app_name": {"type": "string", "description": "Name of the application to close"},
        },
        destructive=True,
        confirm_message="Close {app_name}?",
    )
    def close_app(self, app_name: str) -> str:
        try:
            result = subprocess.run(
                ["pkill", "-f", app_name],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return f"✅ Closed {app_name}"
            return f"No running process matching '{app_name}' found."
        except Exception as e:
            return f"Failed to close {app_name}: {e}"
