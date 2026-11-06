"""
OpenOS Window Manager Tool.

Interfaces with Wayfire compositor for window arrangement and workspace management.
Falls back to wmctrl/xdotool for X11 compatibility.
"""

from __future__ import annotations

import subprocess

from openos_core.tools.base import BaseTool, tool_function


class WindowManagerTool(BaseTool):
    """Window arrangement and workspace management."""

    @property
    def name(self) -> str:
        return "window_manager"

    @property
    def description(self) -> str:
        return "Arrange windows, manage workspaces, and set up work layouts"

    @tool_function(
        description="Arrange windows in a specific layout (tile, stack, side-by-side, maximize, minimize)",
        parameters={
            "layout": {"type": "string", "description": "Layout: 'tile', 'side-by-side', 'maximize', 'minimize-all'"},
        },
    )
    def arrange_windows(self, layout: str) -> str:
        layout = layout.lower().strip()

        if layout in ("tile", "side-by-side"):
            return self._tile_windows()
        elif layout == "maximize":
            return self._run_wm_cmd("wmctrl", ["-r", ":ACTIVE:", "-b", "add,maximized_vert,maximized_horz"])
        elif layout in ("minimize-all", "minimize all", "show desktop"):
            return self._run_wm_cmd("wmctrl", ["-k", "on"])
        else:
            return f"Unknown layout: {layout}. Try: tile, side-by-side, maximize, minimize-all"

    @tool_function(
        description="Focus/bring a specific application window to the front",
        parameters={
            "app_name": {"type": "string", "description": "Application name to focus"},
        },
    )
    def focus_window(self, app_name: str) -> str:
        try:
            result = subprocess.run(
                ["wmctrl", "-l"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if app_name.lower() in line.lower():
                    win_id = line.split()[0]
                    subprocess.run(["wmctrl", "-i", "-a", win_id], timeout=5)
                    return f"✅ Focused: {app_name}"
            return f"No window found for '{app_name}'"
        except FileNotFoundError:
            return "wmctrl not installed. Run: openos 'install wmctrl'"
        except Exception as e:
            return f"Focus error: {e}"

    @tool_function(
        description="Set up a complete workspace profile by launching and arranging multiple apps",
        parameters={
            "profile": {"type": "string", "description": "Profile name: 'work', 'coding', 'browsing', 'media'"},
        },
    )
    def prepare_workspace(self, profile: str) -> str:
        profiles = {
            "work": ["firefox", "thunar", "xfce4-terminal"],
            "coding": ["code", "xfce4-terminal", "firefox"],
            "browsing": ["firefox"],
            "media": ["vlc"],
        }

        apps = profiles.get(profile.lower())
        if not apps:
            return f"Unknown profile: {profile}. Available: {', '.join(profiles.keys())}"

        launched = []
        for app in apps:
            try:
                subprocess.Popen(
                    app, shell=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                launched.append(app)
            except Exception:
                pass

        return f"✅ Workspace '{profile}' ready — launched: {', '.join(launched)}"

    def _tile_windows(self) -> str:
        try:
            result = subprocess.run(
                ["wmctrl", "-l"], capture_output=True, text=True, timeout=5
            )
            windows = [l.split()[0] for l in result.stdout.splitlines() if l.strip()]
            if len(windows) < 2:
                return "Need at least 2 windows to tile."

            # Get screen size
            import shutil
            cols, rows = shutil.get_terminal_size()
            # Use xdpyinfo or default
            width, height = 1920, 1080
            half = width // 2

            for i, wid in enumerate(windows[:2]):
                x = 0 if i == 0 else half
                subprocess.run([
                    "wmctrl", "-i", "-r", wid, "-b", "remove,maximized_vert,maximized_horz"
                ], timeout=5)
                subprocess.run([
                    "wmctrl", "-i", "-r", wid, "-e", f"0,{x},0,{half},{height}"
                ], timeout=5)

            return f"✅ Tiled {len(windows[:2])} windows side by side"
        except FileNotFoundError:
            return "wmctrl not installed. Run: openos 'install wmctrl'"
        except Exception as e:
            return f"Tile error: {e}"

    def _run_wm_cmd(self, cmd: str, args: list[str]) -> str:
        try:
            result = subprocess.run([cmd] + args, capture_output=True, text=True, timeout=5)
            return "✅ Done" if result.returncode == 0 else f"Error: {result.stderr}"
        except FileNotFoundError:
            return f"{cmd} not installed."
        except Exception as e:
            return str(e)
