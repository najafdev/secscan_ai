"""
HackBot Auto-Updater
=====================
Check for new releases on GitHub and self-update via pip.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

from hackbot import __version__

REPO = "yashab-cyber/hackbot"
GITHUB_API = f"https://api.github.com/repos/{REPO}/releases/latest"
PIP_INSTALL_URL = f"git+https://github.com/{REPO}.git"


@dataclass
class UpdateInfo:
    """Information about an available update."""
    current_version: str
    latest_version: str
    update_available: bool
    release_url: str = ""
    release_notes: str = ""
    published_at: str = ""
    error: Optional[str] = None


def _parse_version(v: str) -> tuple:
    """Parse a version string like '1.0.1' or 'v1.0.1' into a comparable tuple."""
    v = v.lstrip("vV").strip()
    parts = []
    for p in v.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def check_for_updates() -> UpdateInfo:
    """
    Check GitHub for the latest release.
    Returns an UpdateInfo with comparison against current version.
    """
    try:
        req = Request(GITHUB_API, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"HackBot/{__version__}",
        })
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        latest_tag = data.get("tag_name", "")
        latest_ver = latest_tag.lstrip("vV")

        current_tuple = _parse_version(__version__)
        latest_tuple = _parse_version(latest_ver)
        update_available = latest_tuple > current_tuple

        return UpdateInfo(
            current_version=__version__,
            latest_version=latest_ver,
            update_available=update_available,
            release_url=data.get("html_url", ""),
            release_notes=data.get("body", "")[:500],
            published_at=data.get("published_at", ""),
        )

    except (URLError, OSError, json.JSONDecodeError, KeyError) as exc:
        return UpdateInfo(
            current_version=__version__,
            latest_version="",
            update_available=False,
            error=f"Failed to check for updates: {exc}",
        )


def perform_update(force: bool = False, extras: str = "all") -> dict:
    """
    Update HackBot by reinstalling from GitHub via pip.

    Args:
        force: If True, reinstall even if already up to date.
        extras: pip extras to install (e.g. "all", "gui", "" for minimal).

    Returns:
        dict with keys: success, message, version_before, version_after
    """
    info = check_for_updates()
    version_before = __version__

    if info.error:
        return {
            "success": False,
            "message": info.error,
            "version_before": version_before,
            "version_after": version_before,
        }

    if not info.update_available and not force:
        return {
            "success": True,
            "message": f"Already up to date (v{__version__})",
            "version_before": version_before,
            "version_after": version_before,
        }

    # Build pip install command
    python = sys.executable or "python3"
    pkg = f"hackbot[{extras}] @ {PIP_INSTALL_URL}" if extras else PIP_INSTALL_URL

    cmd = [python, "-m", "pip", "install", "--upgrade", "--force-reinstall", pkg]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0:
            # Try to detect new version from pip output
            new_version = info.latest_version or "unknown"
            return {
                "success": True,
                "message": (
                    f"Updated from v{version_before} → v{new_version}\n"
                    f"Restart HackBot to use the new version."
                ),
                "version_before": version_before,
                "version_after": new_version,
            }
        else:
            stderr = result.stderr.strip()[-500:] if result.stderr else "Unknown error"
            return {
                "success": False,
                "message": f"pip install failed:\n{stderr}",
                "version_before": version_before,
                "version_after": version_before,
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Update timed out after 300 seconds",
            "version_before": version_before,
            "version_after": version_before,
        }
    except Exception as exc:
        return {
            "success": False,
            "message": f"Update failed: {exc}",
            "version_before": version_before,
            "version_after": version_before,
        }
