"""Autonomous installation of missing security tools.

ToolInstaller turns a logical tool name into a verified install by choosing an
available package manager from config.TOOL_INSTALL_MAP and executing the
constructed argv through the existing ToolRunner (shell-free, sudo-aware).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass

from hackbot.config import TOOL_INSTALL_MAP, resolve_tool_path

# Logical manager key -> binary probed via shutil.which.
_MANAGER_BINARY: dict[str, str] = {
    "apt": "apt-get",
    "dnf": "dnf",
    "pacman": "pacman",
    "brew": "brew",
    "pipx": "pipx",
    "pip": "pip",
    "go": "go",
}

# System managers that require root for a system-wide install.
_SUDO_MANAGERS = {"apt", "dnf", "pacman"}


@dataclass
class InstallPlan:
    tool: str
    manager: str
    package: str
    command: list[str]
    needs_sudo: bool


@dataclass
class InstallResult:
    tool: str
    success: bool
    manager: str = ""
    path: str | None = None
    message: str = ""
    stdout: str = ""
    stderr: str = ""


def _build_command(manager: str, package: str) -> list[str]:
    if manager == "apt":
        return ["apt-get", "install", "-y", package]
    if manager == "dnf":
        return ["dnf", "install", "-y", package]
    if manager == "pacman":
        return ["pacman", "-S", "--noconfirm", package]
    if manager == "brew":
        return ["brew", "install", package]
    if manager == "pipx":
        return ["pipx", "install", package]
    if manager == "pip":
        return ["pip", "install", package]
    if manager == "go":
        return ["go", "install", package]
    raise ValueError(f"unknown manager: {manager}")


class ToolInstaller:
    def __init__(self, runner, install_map: dict | None = None):
        self.runner = runner
        self.install_map = install_map if install_map is not None else TOOL_INSTALL_MAP
        self._available: dict[str, str] | None = None

    def available_managers(self) -> dict[str, str]:
        if self._available is None:
            found: dict[str, str] = {}
            for mgr, binary in _MANAGER_BINARY.items():
                path = shutil.which(binary)
                if path:
                    found[mgr] = path
            self._available = found
        return self._available

    def plan_install(self, tool: str) -> InstallPlan | None:
        recipe = self.install_map.get(tool.lower())
        if not recipe:
            return None
        available = self.available_managers()
        raw_order = recipe.get("order")
        order: list[str] = list(raw_order) if isinstance(raw_order, (list, tuple)) else [k for k in recipe if k != "order"]
        for mgr in order:
            package = recipe.get(mgr)
            if package and mgr in available:
                return InstallPlan(
                    tool=tool,
                    manager=mgr,
                    package=str(package),
                    command=_build_command(mgr, str(package)),
                    needs_sudo=mgr in _SUDO_MANAGERS,
                )
        return None

    def install(self, plan: InstallPlan) -> InstallResult:
        # Execute pre_install commands if defined in the recipe
        recipe = self.install_map.get(plan.tool.lower(), {})
        raw_pre = recipe.get("pre_install", [])
        pre_install: list[str] = list(raw_pre) if isinstance(raw_pre, (list, tuple)) else []
        for pre_cmd in pre_install:
            self.runner.execute(
                str(pre_cmd),
                tool_name="pre-install",
                explanation=f"Pre-install step for {plan.tool}",
                allow_install_drivers=True,
            )

        command_str = " ".join(plan.command)
        result = self.runner.execute(
            command_str,
            tool_name=plan.manager,
            explanation=f"Install {plan.tool}",
            allow_install_drivers=True,
        )
        path = resolve_tool_path(plan.tool)
        success = result.success and path is not None
        if success:
            message = f"Installed {plan.tool} via {plan.manager} ({path})"
        elif result.success:
            message = f"{plan.manager} reported success but {plan.tool} is still not on PATH"
        else:
            message = f"Install of {plan.tool} via {plan.manager} failed"
        return InstallResult(
            tool=plan.tool,
            success=success,
            manager=plan.manager,
            path=path,
            message=message,
            stdout=(result.stdout or "")[:2000],
            stderr=(result.stderr or "")[:2000],
        )

    @staticmethod
    def check_and_fix_wfuzz() -> str:
        """Check if wfuzz's pkg_resources dependency is satisfied and fix it.

        Returns a status message. Safe to call even if wfuzz is not installed.
        """
        try:
            import importlib
            importlib.import_module("pkg_resources")
            return "pkg_resources is available"
        except ImportError:
            import subprocess as sp
            try:
                sp.check_call(
                    [shutil.which("pip") or "pip", "install", "setuptools"],
                    stdout=sp.DEVNULL,
                    stderr=sp.DEVNULL,
                )
                return "Installed setuptools to fix pkg_resources for wfuzz"
            except Exception as e:
                return f"Failed to auto-fix pkg_resources: {e}"
