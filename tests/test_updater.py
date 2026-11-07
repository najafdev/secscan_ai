"""Tests for HackBot Auto-Updater."""

import json
from unittest.mock import patch, MagicMock

import pytest

from hackbot.core.updater import (
    UpdateInfo,
    check_for_updates,
    perform_update,
    _parse_version,
)


# ── Version parsing ──────────────────────────────────────────────────────────

def test_parse_version_simple():
    assert _parse_version("1.0.0") == (1, 0, 0)

def test_parse_version_with_v_prefix():
    assert _parse_version("v1.0.1") == (1, 0, 1)

def test_parse_version_with_V_prefix():
    assert _parse_version("V2.3.4") == (2, 3, 4)

def test_parse_version_two_parts():
    assert _parse_version("1.2") == (1, 2)

def test_parse_version_comparison():
    assert _parse_version("1.0.1") > _parse_version("1.0.0")
    assert _parse_version("2.0.0") > _parse_version("1.9.9")
    assert _parse_version("1.0.0") == _parse_version("v1.0.0")
    assert _parse_version("1.0.1") < _parse_version("1.1.0")


# ── Check for updates ───────────────────────────────────────────────────────

@patch("hackbot.core.updater.urlopen")
def test_check_for_updates_newer_available(mock_urlopen):
    """Test that a newer version is detected."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "tag_name": "v99.0.0",
        "html_url": "https://github.com/yashab-cyber/hackbot/releases/tag/v99.0.0",
        "body": "## Release Notes\n- New feature",
        "published_at": "2026-03-01T12:00:00Z",
    }).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_resp

    info = check_for_updates()
    assert info.update_available is True
    assert info.latest_version == "99.0.0"
    assert info.error is None
    assert "Release Notes" in info.release_notes


@patch("hackbot.core.updater.urlopen")
def test_check_for_updates_already_latest(mock_urlopen):
    """Test that current = latest returns no update."""
    from hackbot import __version__
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "tag_name": f"v{__version__}",
        "html_url": "https://example.com",
        "body": "",
        "published_at": "2026-01-01T00:00:00Z",
    }).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_resp

    info = check_for_updates()
    assert info.update_available is False
    assert info.error is None


@patch("hackbot.core.updater.urlopen", side_effect=OSError("No network"))
def test_check_for_updates_network_error(mock_urlopen):
    """Test graceful handling of network errors."""
    info = check_for_updates()
    assert info.update_available is False
    assert info.error is not None
    assert "No network" in info.error


# ── Perform update ───────────────────────────────────────────────────────────

@patch("hackbot.core.updater.check_for_updates")
def test_perform_update_already_up_to_date(mock_check):
    """Test that perform_update skips when already current."""
    mock_check.return_value = UpdateInfo(
        current_version="1.0.1",
        latest_version="1.0.1",
        update_available=False,
    )
    result = perform_update()
    assert result["success"] is True
    assert "up to date" in result["message"]


@patch("hackbot.core.updater.check_for_updates")
def test_perform_update_error_in_check(mock_check):
    """Test that check errors are propagated."""
    mock_check.return_value = UpdateInfo(
        current_version="1.0.1",
        latest_version="",
        update_available=False,
        error="Network unreachable",
    )
    result = perform_update()
    assert result["success"] is False
    assert "Network unreachable" in result["message"]


@patch("hackbot.core.updater.subprocess.run")
@patch("hackbot.core.updater.check_for_updates")
def test_perform_update_success(mock_check, mock_run):
    """Test successful update via pip."""
    mock_check.return_value = UpdateInfo(
        current_version="1.0.0",
        latest_version="1.0.1",
        update_available=True,
    )
    mock_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")

    result = perform_update()
    assert result["success"] is True
    assert "1.0.1" in result["message"]
    mock_run.assert_called_once()


@patch("hackbot.core.updater.subprocess.run")
@patch("hackbot.core.updater.check_for_updates")
def test_perform_update_pip_failure(mock_check, mock_run):
    """Test pip install failure."""
    mock_check.return_value = UpdateInfo(
        current_version="1.0.0",
        latest_version="1.0.1",
        update_available=True,
    )
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="ERROR: bad package")

    result = perform_update()
    assert result["success"] is False
    assert "pip install failed" in result["message"]


@patch("hackbot.core.updater.subprocess.run", side_effect=Exception("spawn failed"))
@patch("hackbot.core.updater.check_for_updates")
def test_perform_update_exception(mock_check, mock_run):
    """Test exception during update."""
    mock_check.return_value = UpdateInfo(
        current_version="1.0.0",
        latest_version="1.0.1",
        update_available=True,
    )
    result = perform_update()
    assert result["success"] is False
    assert "spawn failed" in result["message"]


@patch("hackbot.core.updater.subprocess.run")
@patch("hackbot.core.updater.check_for_updates")
def test_perform_update_force(mock_check, mock_run):
    """Test force reinstall even when up to date."""
    mock_check.return_value = UpdateInfo(
        current_version="1.0.1",
        latest_version="1.0.1",
        update_available=False,
    )
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    result = perform_update(force=True)
    assert result["success"] is True
    mock_run.assert_called_once()
