"""
OpenOS Media Player Tool.

Controls media playback via MPRIS D-Bus protocol — works with any MPRIS-compatible
player (VLC, Spotify, Rhythmbox, etc.).
"""

from __future__ import annotations

import subprocess

from openos_core.tools.base import BaseTool, tool_function


class MediaPlayerTool(BaseTool):
    """Control media playback via MPRIS D-Bus."""

    @property
    def name(self) -> str:
        return "media_player"

    @property
    def description(self) -> str:
        return "Control music/video playback — play, pause, skip, volume"

    def _playerctl(self, *args: str) -> str:
        """Run a playerctl command."""
        try:
            result = subprocess.run(
                ["playerctl"] + list(args),
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
        except FileNotFoundError:
            return "playerctl not installed. Run: openos 'install playerctl'"
        except Exception as e:
            return str(e)

    @tool_function(
        description="Play media. If query provided, opens it in the default media player.",
        parameters={
            "query": {"type": "string", "description": "Song/video name or file path to play", "optional": True},
        },
    )
    def play_music(self, query: str = "") -> str:
        if query:
            # Try to open in default player
            try:
                subprocess.Popen(
                    ["xdg-open", query],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return f"🎵 Opening: {query}"
            except Exception as e:
                return f"Could not play: {e}"
        else:
            result = self._playerctl("play")
            return "▶️  Playing" if not result else result

    @tool_function(
        description="Pause current media playback",
        parameters={},
    )
    def pause(self) -> str:
        result = self._playerctl("pause")
        return "⏸️  Paused" if not result else result

    @tool_function(
        description="Toggle play/pause",
        parameters={},
    )
    def play_pause(self) -> str:
        result = self._playerctl("play-pause")
        return "⏯️  Toggled play/pause" if not result else result

    @tool_function(
        description="Skip to next track",
        parameters={},
    )
    def next_track(self) -> str:
        result = self._playerctl("next")
        return "⏭️  Next track" if not result else result

    @tool_function(
        description="Go to previous track",
        parameters={},
    )
    def previous_track(self) -> str:
        result = self._playerctl("previous")
        return "⏮️  Previous track" if not result else result

    @tool_function(
        description="Set playback volume (0-100)",
        parameters={
            "level": {"type": "integer", "description": "Volume level 0-100"},
        },
    )
    def set_volume(self, level: int) -> str:
        vol = max(0, min(100, level)) / 100.0
        result = self._playerctl("volume", str(vol))
        return f"🔊 Volume set to {level}%" if not result else result

    @tool_function(
        description="Show info about what's currently playing",
        parameters={},
    )
    def now_playing(self) -> str:
        title = self._playerctl("metadata", "title")
        artist = self._playerctl("metadata", "artist")
        status = self._playerctl("status")
        if "No players found" in title:
            return "No media is currently playing."
        return f"🎵 {status}: {artist} — {title}"
