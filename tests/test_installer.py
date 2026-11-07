import pytest

from hackbot.core import installer as inst
from hackbot.core.installer import ToolInstaller, InstallPlan
from hackbot.core.runner import ToolResult


def _installer(monkeypatch, present_binaries, install_map=None):
    """ToolInstaller whose available managers are exactly `present_binaries`."""

    def fake_which(binary):
        return f"/usr/bin/{binary}" if binary in present_binaries else None

    monkeypatch.setattr(inst.shutil, "which", fake_which)
    return ToolInstaller(runner=object(), install_map=install_map)


def test_available_managers_detects_present_binaries(monkeypatch):
    ti = _installer(monkeypatch, {"apt-get", "go"})
    mgrs = ti.available_managers()
    assert mgrs.keys() == {"apt", "go"}
    assert mgrs["apt"] == "/usr/bin/apt-get"


def test_plan_install_picks_first_available_in_order(monkeypatch):
    # nuclei order is ["go", "apt"]; only apt present -> apt chosen
    ti = _installer(monkeypatch, {"apt-get"})
    plan = ti.plan_install("nuclei")
    assert plan is not None
    assert plan.manager == "apt"
    assert plan.command == ["apt-get", "install", "-y", "nuclei"]
    assert plan.needs_sudo is True


def test_plan_install_prefers_go_when_available(monkeypatch):
    ti = _installer(monkeypatch, {"go", "apt-get"})
    plan = ti.plan_install("nuclei")
    assert plan.manager == "go"
    assert plan.command[0] == "go" and plan.command[1] == "install"
    assert plan.needs_sudo is False


def test_plan_install_unmapped_tool_returns_none(monkeypatch):
    ti = _installer(monkeypatch, {"apt-get"})
    assert ti.plan_install("definitely-not-a-tool") is None


def test_plan_install_no_available_manager_returns_none(monkeypatch):
    # subfinder only ships via go; if go absent -> None
    ti = _installer(monkeypatch, {"apt-get"})
    assert ti.plan_install("subfinder") is None


def test_plan_install_is_case_insensitive(monkeypatch):
    ti = _installer(monkeypatch, {"apt-get"})
    assert ti.plan_install("NIKTO").manager == "apt"


def test_pacman_command_uses_noconfirm(monkeypatch):
    ti = _installer(monkeypatch, {"pacman"})
    plan = ti.plan_install("nmap")
    assert plan.command == ["pacman", "-S", "--noconfirm", "nmap"]


class _FakeRunner:
    def __init__(self, success=True):
        self._success = success
        self.commands = []

    def execute(self, command, tool_name="", explanation="", allow_install_drivers=False):
        self.commands.append(command)
        self.last_allow_install_drivers = allow_install_drivers
        return ToolResult(
            tool=tool_name,
            command=command,
            stdout="installed" if self._success else "",
            stderr="" if self._success else "E: permission denied",
            return_code=0 if self._success else 1,
            duration=0.1,
            success=self._success,
        )


_PLAN = InstallPlan(
    tool="nuclei",
    manager="go",
    package="github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
    command=["go", "install", "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"],
    needs_sudo=False,
)


def test_install_success_when_runner_ok_and_binary_resolves(monkeypatch):
    monkeypatch.setattr(inst, "resolve_tool_path", lambda t: "/usr/bin/nuclei")
    runner = _FakeRunner(success=True)
    ti = ToolInstaller(runner=runner)
    res = ti.install(_PLAN)
    assert res.success is True
    assert res.path == "/usr/bin/nuclei"
    assert runner.commands == ["go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"]


def test_install_fails_when_runner_returns_nonzero(monkeypatch):
    monkeypatch.setattr(inst, "resolve_tool_path", lambda t: None)
    ti = ToolInstaller(runner=_FakeRunner(success=False))
    res = ti.install(_PLAN)
    assert res.success is False
    assert "permission denied" in res.stderr


def test_install_fails_when_binary_still_missing(monkeypatch):
    # Runner reports success but the binary is not on PATH afterward.
    monkeypatch.setattr(inst, "resolve_tool_path", lambda t: None)
    ti = ToolInstaller(runner=_FakeRunner(success=True))
    res = ti.install(_PLAN)
    assert res.success is False
    assert res.path is None


def test_install_passes_install_driver_flag(monkeypatch):
    monkeypatch.setattr(inst, "resolve_tool_path", lambda t: "/usr/bin/nuclei")
    runner = _FakeRunner(success=True)
    ti = ToolInstaller(runner=runner)
    ti.install(_PLAN)
    assert runner.last_allow_install_drivers is True
