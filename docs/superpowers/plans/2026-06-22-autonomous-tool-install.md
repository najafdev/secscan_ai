# Autonomous Security-Tool Installation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let HackBot's agent autonomously install missing security tools mid-assessment via a new `install` action, plus a manual `/install` / `hackbot install` surface.

**Architecture:** A new `ToolInstaller` (`hackbot/core/installer.py`) turns "I need tool X" into a verified install by selecting an available package manager from a curated `TOOL_INSTALL_MAP` and running the constructed argv through the existing hardened `ToolRunner`. The agent gains an `install` action that is allowlist-bounded, respects `safe_mode` confirmation, and feeds results back into the loop. Installs reuse the runner's shell-free execution, sudo authority, and validation — no new privilege path.

**Tech Stack:** Python 3.9+, `shutil.which` for manager detection, existing `ToolRunner`/`subprocess`, `pytest` with `monkeypatch`/mocks.

## Global Constraints

- Minimum Python is **3.9** — no 3.10+ only syntax (no `match`, no `X | Y` type unions in annotations; use `Optional[...]`/`Dict[...]` from `typing`).
- Execution MUST flow through `ToolRunner.execute` — never a new `subprocess` call. Preserve the shell-free boundary (`shell=False`, `shlex`), `BLOCKED_COMMANDS`, allowlist, and centralized `_apply_sudo`.
- Sudo is applied only by the runner. `InstallPlan.needs_sudo` is metadata; actual sudo happens only when the runner has `sudo_mode` (or the process is root). Do not strip/re-add sudo elsewhere.
- Allowlist-bounded by default: only tools in `agent.allowed_tools` AND present in `TOOL_INSTALL_MAP` are installable. `agent.allow_arbitrary_install` (default `False`) relaxes the allowlist check.
- Respect `safe_mode`: when on, an install requires one `on_confirm` y/n; when off (`--no-safe-mode`), installs run unattended.
- Line length 100; code passes `ruff check` and `black`. Branding rules in CLAUDE.md unchanged.
- Tests MUST NOT install real packages — mock `shutil.which`, `resolve_tool_path`, and the runner.

---

### Task 1: Config — install map, allowlist drivers, and opt-in flag

**Files:**
- Modify: `hackbot/config.py` (DEFAULT_CONFIG `agent.allowed_tools` ~line 119-137; add `TOOL_INSTALL_MAP` near `TOOL_ALIASES` ~line 479; `AgentConfig` ~line 176-184; `save_config` agent dict ~line 392-401)
- Test: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `TOOL_INSTALL_MAP: Dict[str, Dict[str, object]]` — keys are lowercase tool names; each value has an `"order": List[str]` of manager keys plus one entry per manager key (`"apt"`, `"dnf"`, `"pacman"`, `"brew"`, `"pipx"`, `"pip"`, `"go"`) mapping to that manager's package/module string.
  - `AgentConfig.allow_arbitrary_install: bool = False`
  - Manager binaries `apt-get`, `dnf`, `pacman`, `brew`, `pipx`, `pip` added to `agent.allowed_tools` (`go`, `python3` already present).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_config.py`:

```python
from hackbot.config import (
    TOOL_INSTALL_MAP,
    DEFAULT_CONFIG,
    AgentConfig,
)


def test_install_map_entries_are_well_formed():
    assert "nuclei" in TOOL_INSTALL_MAP
    for tool, recipe in TOOL_INSTALL_MAP.items():
        assert tool == tool.lower()
        assert "order" in recipe and recipe["order"], f"{tool} missing order"
        for mgr in recipe["order"]:
            assert mgr in recipe, f"{tool} order names {mgr} with no package"


def test_install_managers_are_allowlisted():
    allowed = set(DEFAULT_CONFIG["agent"]["allowed_tools"])
    for mgr in ("apt-get", "dnf", "pacman", "brew", "pipx", "pip", "go"):
        assert mgr in allowed, f"{mgr} must be allowlisted to run installs"


def test_allow_arbitrary_install_defaults_off():
    assert AgentConfig().allow_arbitrary_install is False
    assert DEFAULT_CONFIG["agent"]["allow_arbitrary_install"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py::test_install_map_entries_are_well_formed tests/test_config.py::test_install_managers_are_allowlisted tests/test_config.py::test_allow_arbitrary_install_defaults_off -v`
Expected: FAIL — `ImportError: cannot import name 'TOOL_INSTALL_MAP'` (and the other asserts).

- [ ] **Step 3: Write minimal implementation**

In `hackbot/config.py`:

1. Add the six manager binaries to the `DEFAULT_CONFIG["agent"]["allowed_tools"]` list (after `"go"`):

```python
            "go",
            # Package managers — used by ToolInstaller as install drivers only.
            "apt-get",
            "dnf",
            "pacman",
            "brew",
            "pipx",
            "pip",
        ],
```

2. Add `allow_arbitrary_install` to `DEFAULT_CONFIG["agent"]` (after `"allowed_tools"` is fine; put it before the list for readability):

```python
    "agent": {
        "auto_confirm": False,
        "max_steps": 50,
        "timeout": 300,
        "safe_mode": True,
        "sudo_mode": False,
        "sudo_password": "",
        "nvd_api_key": "",
        "allow_arbitrary_install": False,
        "allowed_tools": [
```

3. Add the field to `AgentConfig` (after `nvd_api_key`):

```python
    nvd_api_key: str = ""
    allow_arbitrary_install: bool = False
    allowed_tools: List[str] = field(default_factory=lambda: DEFAULT_CONFIG["agent"]["allowed_tools"])
```

4. Persist it in `save_config`'s agent dict (after `"nvd_api_key"`):

```python
            "nvd_api_key": cfg.agent.nvd_api_key,
            "allow_arbitrary_install": cfg.agent.allow_arbitrary_install,
            "allowed_tools": cfg.agent.allowed_tools,
```

5. Add `TOOL_INSTALL_MAP` immediately after the `TOOL_ALIASES` dict (before `def resolve_tool_path`):

```python
# Curated tool -> package recipes for autonomous installation.
# `order` lists preferred managers; ToolInstaller picks the first one available
# on the host. Per-manager values are the package/module identifier for that
# manager. Only tools also present in agent.allowed_tools are installable.
TOOL_INSTALL_MAP: Dict[str, Dict[str, object]] = {
    "nuclei": {
        "order": ["go", "apt"],
        "go": "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
        "apt": "nuclei",
    },
    "subfinder": {
        "order": ["go"],
        "go": "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
    },
    "httpx": {
        "order": ["go"],
        "go": "github.com/projectdiscovery/httpx/cmd/httpx@latest",
    },
    "ffuf": {
        "order": ["go", "apt"],
        "go": "github.com/ffuf/ffuf/v2@latest",
        "apt": "ffuf",
    },
    "gobuster": {
        "order": ["go", "apt"],
        "go": "github.com/OJ/gobuster/v3@latest",
        "apt": "gobuster",
    },
    "katana": {
        "order": ["go"],
        "go": "github.com/projectdiscovery/katana/cmd/katana@latest",
    },
    "sqlmap": {"order": ["apt", "pipx"], "apt": "sqlmap", "pipx": "sqlmap"},
    "nikto": {"order": ["apt"], "apt": "nikto"},
    "nmap": {"order": ["apt", "dnf", "pacman", "brew"], "apt": "nmap",
             "dnf": "nmap", "pacman": "nmap", "brew": "nmap"},
    "whatweb": {"order": ["apt"], "apt": "whatweb"},
    "wpscan": {"order": ["apt"], "apt": "wpscan"},
    "hydra": {"order": ["apt"], "apt": "hydra"},
    "dnsrecon": {"order": ["apt", "pipx"], "apt": "dnsrecon", "pipx": "dnsrecon"},
    "amass": {"order": ["apt", "go"], "apt": "amass",
              "go": "github.com/owasp-amass/amass/v4/...@master"},
    "feroxbuster": {"order": ["apt"], "apt": "feroxbuster"},
    "masscan": {"order": ["apt", "dnf", "pacman"], "apt": "masscan",
                "dnf": "masscan", "pacman": "masscan"},
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (all config tests, including the three new ones).

- [ ] **Step 5: Lint and commit**

```bash
ruff check hackbot/config.py && black hackbot/config.py tests/test_config.py
git add hackbot/config.py tests/test_config.py
git commit -m "feat(config): add TOOL_INSTALL_MAP, allow_arbitrary_install flag, install drivers"
```

---

### Task 2: ToolInstaller — manager detection and install planning

**Files:**
- Create: `hackbot/core/installer.py`
- Test: `tests/test_installer.py`

**Interfaces:**
- Consumes: `TOOL_INSTALL_MAP`, `resolve_tool_path` (from `hackbot.config`); `ToolRunner`, `ToolResult` (from `hackbot.core.runner`).
- Produces:
  - `@dataclass InstallPlan(tool: str, manager: str, package: str, command: List[str], needs_sudo: bool)`
  - `@dataclass InstallResult(tool: str, success: bool, manager: str = "", path: Optional[str] = None, message: str = "", stdout: str = "", stderr: str = "")`
  - `class ToolInstaller(runner: ToolRunner, install_map: Optional[Dict] = None)` with:
    - `available_managers() -> Dict[str, str]` (logical manager key → binary path; cached)
    - `plan_install(tool: str) -> Optional[InstallPlan]`
    - `install(plan: InstallPlan) -> InstallResult` (Task 3)
  - Module constant `_SUDO_MANAGERS = {"apt", "dnf", "pacman"}`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_installer.py`:

```python
import pytest

from hackbot.core import installer as inst
from hackbot.core.installer import ToolInstaller, InstallPlan


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_installer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'hackbot.core.installer'`.

- [ ] **Step 3: Write minimal implementation**

Create `hackbot/core/installer.py`:

```python
"""Autonomous installation of missing security tools.

ToolInstaller turns a logical tool name into a verified install by choosing an
available package manager from config.TOOL_INSTALL_MAP and executing the
constructed argv through the existing ToolRunner (shell-free, sudo-aware).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import Dict, List, Optional

from hackbot.config import TOOL_INSTALL_MAP, resolve_tool_path

# Logical manager key -> binary probed via shutil.which.
_MANAGER_BINARY: Dict[str, str] = {
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
    command: List[str]
    needs_sudo: bool


@dataclass
class InstallResult:
    tool: str
    success: bool
    manager: str = ""
    path: Optional[str] = None
    message: str = ""
    stdout: str = ""
    stderr: str = ""


def _build_command(manager: str, package: str) -> List[str]:
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
    def __init__(self, runner, install_map: Optional[Dict] = None):
        self.runner = runner
        self.install_map = install_map if install_map is not None else TOOL_INSTALL_MAP
        self._available: Optional[Dict[str, str]] = None

    def available_managers(self) -> Dict[str, str]:
        if self._available is None:
            found: Dict[str, str] = {}
            for mgr, binary in _MANAGER_BINARY.items():
                path = shutil.which(binary)
                if path:
                    found[mgr] = path
            self._available = found
        return self._available

    def plan_install(self, tool: str) -> Optional[InstallPlan]:
        recipe = self.install_map.get(tool.lower())
        if not recipe:
            return None
        available = self.available_managers()
        order = recipe.get("order") or [k for k in recipe if k != "order"]
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_installer.py -v`
Expected: PASS (all 7 tests).

- [ ] **Step 5: Lint and commit**

```bash
ruff check hackbot/core/installer.py && black hackbot/core/installer.py tests/test_installer.py
git add hackbot/core/installer.py tests/test_installer.py
git commit -m "feat(installer): ToolInstaller manager detection and install planning"
```

---

### Task 3: ToolInstaller.install — execute via runner and verify

**Files:**
- Modify: `hackbot/core/installer.py`
- Test: `tests/test_installer.py`

**Interfaces:**
- Consumes: `InstallPlan` (Task 2); `ToolResult` (from `hackbot.core.runner`); `resolve_tool_path`.
- Produces: `ToolInstaller.install(plan: InstallPlan) -> InstallResult` — runs `plan.command` (joined to a string) through `self.runner.execute(...)`, then verifies via `resolve_tool_path(plan.tool)`. Success is `runner result success AND binary now resolves`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_installer.py`:

```python
from hackbot.core.runner import ToolResult
from hackbot.core.installer import InstallPlan


class _FakeRunner:
    def __init__(self, success=True):
        self._success = success
        self.commands = []

    def execute(self, command, tool_name="", explanation=""):
        self.commands.append(command)
        return ToolResult(
            tool=tool_name, command=command,
            stdout="installed" if self._success else "",
            stderr="" if self._success else "E: permission denied",
            return_code=0 if self._success else 1,
            duration=0.1, success=self._success,
        )


_PLAN = InstallPlan(tool="nuclei", manager="go",
                    command=["go", "install", "x@latest"], needs_sudo=False)


def test_install_success_when_runner_ok_and_binary_resolves(monkeypatch):
    monkeypatch.setattr(inst, "resolve_tool_path", lambda t: "/usr/bin/nuclei")
    runner = _FakeRunner(success=True)
    ti = ToolInstaller(runner=runner)
    res = ti.install(_PLAN)
    assert res.success is True
    assert res.path == "/usr/bin/nuclei"
    assert runner.commands == ["go install x@latest"]


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_installer.py -k install -v`
Expected: FAIL — `AttributeError: 'ToolInstaller' object has no attribute 'install'`.

- [ ] **Step 3: Write minimal implementation**

Add the `install` method to `ToolInstaller` in `hackbot/core/installer.py`:

```python
    def install(self, plan: InstallPlan) -> InstallResult:
        command_str = " ".join(plan.command)
        result = self.runner.execute(
            command_str,
            tool_name=plan.manager,
            explanation=f"Install {plan.tool}",
        )
        path = resolve_tool_path(plan.tool)
        success = result.success and path is not None
        if success:
            message = f"Installed {plan.tool} via {plan.manager} ({path})"
        elif result.success:
            message = (
                f"{plan.manager} reported success but {plan.tool} is still not on PATH"
            )
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_installer.py -v`
Expected: PASS (all installer tests).

- [ ] **Step 5: Lint and commit**

```bash
ruff check hackbot/core/installer.py && black hackbot/core/installer.py tests/test_installer.py
git add hackbot/core/installer.py tests/test_installer.py
git commit -m "feat(installer): execute install via runner and verify binary resolves"
```

---

### Task 4: Agent `install` action — parse and dispatch

**Files:**
- Modify: `hackbot/modes/agent.py` (`_parse_actions` allowed set ~line 717; `_process_actions_loop` dispatch ~line 591-645; `__init__` ~line 154-176 to construct the installer)
- Test: `tests/test_modes.py`

**Interfaces:**
- Consumes: `ToolInstaller`, `InstallResult` (Task 3); `resolve_tool_path` (from `hackbot.config`); `self.runner` (ToolRunner — has `is_tool_allowed`, `on_confirm`); `self.config.agent.allow_arbitrary_install`, `self.config.agent.safe_mode`.
- Produces:
  - `"install"` added to the `allowed_actions` set in `_parse_actions`.
  - `AgentMode._process_install_action(self, action: Dict[str, Any]) -> str` — returns a human/AI-readable result string.
  - `self.installer: ToolInstaller` created in `__init__`.
  - `_process_actions_loop` handles `atype == "install"` by appending `_process_install_action(action)` to `results_text`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_modes.py` (reuse existing AgentMode construction helpers in that file; if none, build via `AgentMode(engine=<mock>, config=load_config())`). The tests below drive `_process_install_action` directly with monkeypatched dependencies:

```python
import hackbot.modes.agent as agent_mod


def _agent(monkeypatch, tmp_path):
    """Minimal AgentMode with a stub engine; safe for unit-testing helpers."""
    from hackbot.config import load_config
    cfg = load_config()
    cfg.agent.safe_mode = False  # default off for these unit tests
    eng = type("E", (), {"chat": lambda self, *a, **k: ""})()
    return AgentMode(engine=eng, config=cfg)


def test_parse_actions_recognizes_install(monkeypatch, tmp_path):
    a = _agent(monkeypatch, tmp_path)
    actions = a._parse_actions('{"action": "install", "tool": "nuclei"}')
    assert actions == [{"action": "install", "tool": "nuclei"}]


def test_install_action_already_installed_short_circuits(monkeypatch, tmp_path):
    a = _agent(monkeypatch, tmp_path)
    monkeypatch.setattr(agent_mod, "resolve_tool_path", lambda t: "/usr/bin/nuclei")
    msg = a._process_install_action({"action": "install", "tool": "nuclei"})
    assert "already installed" in msg.lower()


def test_install_action_rejects_non_allowlisted_tool(monkeypatch, tmp_path):
    a = _agent(monkeypatch, tmp_path)
    a.config.agent.allow_arbitrary_install = False
    monkeypatch.setattr(agent_mod, "resolve_tool_path", lambda t: None)
    msg = a._process_install_action({"action": "install", "tool": "evilpkg"})
    assert "allowlist" in msg.lower()


def test_install_action_unmapped_reports_no_recipe(monkeypatch, tmp_path):
    a = _agent(monkeypatch, tmp_path)
    monkeypatch.setattr(agent_mod, "resolve_tool_path", lambda t: None)
    # gcc is allowlisted but has no install recipe -> plan is None
    monkeypatch.setattr(a.runner, "is_tool_allowed", lambda t: True)
    msg = a._process_install_action({"action": "install", "tool": "gcc"})
    assert "no install recipe" in msg.lower()


def test_install_action_runs_installer_and_reports(monkeypatch, tmp_path):
    a = _agent(monkeypatch, tmp_path)
    monkeypatch.setattr(agent_mod, "resolve_tool_path", lambda t: None)
    monkeypatch.setattr(a.runner, "is_tool_allowed", lambda t: True)

    from hackbot.core.installer import InstallPlan, InstallResult
    plan = InstallPlan("nuclei", "go", ["go", "install", "x"], False)
    monkeypatch.setattr(a.installer, "plan_install", lambda t: plan)
    monkeypatch.setattr(
        a.installer, "install",
        lambda p: InstallResult("nuclei", True, "go", "/usr/bin/nuclei",
                                "Installed nuclei via go (/usr/bin/nuclei)"),
    )
    msg = a._process_install_action({"action": "install", "tool": "nuclei"})
    assert "installed nuclei" in msg.lower()


def test_install_action_safe_mode_decline(monkeypatch, tmp_path):
    a = _agent(monkeypatch, tmp_path)
    a.config.agent.safe_mode = True
    a.runner.on_confirm = lambda cmd, reason: False  # user declines
    monkeypatch.setattr(agent_mod, "resolve_tool_path", lambda t: None)
    monkeypatch.setattr(a.runner, "is_tool_allowed", lambda t: True)
    from hackbot.core.installer import InstallPlan
    plan = InstallPlan("nuclei", "go", ["go", "install", "x"], False)
    monkeypatch.setattr(a.installer, "plan_install", lambda t: plan)
    called = {"installed": False}
    monkeypatch.setattr(a.installer, "install",
                        lambda p: called.__setitem__("installed", True))
    msg = a._process_install_action({"action": "install", "tool": "nuclei"})
    assert "declined" in msg.lower()
    assert called["installed"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_modes.py -k install -v`
Expected: FAIL — `'install'` not parsed / `AgentMode` has no `_process_install_action` / no `installer` attribute.

- [ ] **Step 3: Write minimal implementation**

In `hackbot/modes/agent.py`:

1. Ensure the import line for config includes `resolve_tool_path` (it imports from `hackbot.config` already; add `resolve_tool_path` to that import) and add the installer import near the top with the other `hackbot.core` imports:

```python
from hackbot.config import resolve_tool_path
from hackbot.core.installer import ToolInstaller, InstallResult
```
(If `hackbot.config` is already imported with specific names, append `resolve_tool_path` to that existing import instead of adding a duplicate line.)

2. Construct the installer in `__init__`, right after the `self.runner = ToolRunner(...)` block (~line 163):

```python
        self.installer = ToolInstaller(self.runner)
```

3. Add `"install"` to the `allowed_actions` set in `_parse_actions` (~line 717):

```python
        allowed_actions = {"execute", "finding", "script", "complete", "generate_report", "fuzz", "analyze_anomaly", "chain_exploits", "install"}
```

4. Add the dispatch branch in `_process_actions_loop` — place it alongside the other `elif atype == ...` branches (e.g. after the `chain_exploits` branch ~line 645):

```python
                elif atype == "install":
                    install_result = self._process_install_action(action)
                    results_text.append(install_result)
```

5. Add the handler method (place it near `_execute_action`):

```python
    def _process_install_action(self, action: Dict[str, Any]) -> str:
        """Autonomously install a missing security tool (allowlist-bounded)."""
        tool = (action.get("tool") or "").strip()
        if not tool:
            return "**[install]** No tool specified."

        # Allowlist bound (unless the user opted into arbitrary installs).
        if not self.config.agent.allow_arbitrary_install and not self.runner.is_tool_allowed(tool):
            return (
                f"**[install]** `{tool}` is not in the allowlist; cannot auto-install. "
                f"Use a different tool or ask the user to install it manually."
            )

        if resolve_tool_path(tool):
            return f"**[install]** `{tool}` is already installed — proceed to use it."

        plan = self.installer.plan_install(tool)
        if plan is None:
            return (
                f"**[install]** No install recipe for `{tool}` on this system "
                f"(unmapped tool or no supported package manager available). "
                f"Try a different tool."
            )

        # Respect safe_mode: one confirmation before installing.
        if self.config.agent.safe_mode and not self.config.agent.auto_confirm:
            confirm = getattr(self.runner, "on_confirm", None)
            cmd_str = " ".join(plan.command)
            reason = f"INSTALL {tool} via {plan.manager}"
            if confirm and not confirm(cmd_str, reason):
                return f"**[install]** User declined installation of `{tool}`."

        result: InstallResult = self.installer.install(plan)
        if result.success:
            return f"**[install]** SUCCESS — {result.message}. You may now use `{tool}`."
        detail = (result.stderr or result.stdout or "").strip()[:500]
        sudo_hint = ""
        if plan.needs_sudo and not self.runner.sudo_mode:
            sudo_hint = " (system installs need --sudo / sudo_mode; it appears disabled)"
        return f"**[install]** FAILED — {result.message}{sudo_hint}.\n```\n{detail}\n```"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_modes.py -k install -v`
Expected: PASS (6 install tests).

- [ ] **Step 5: Run the full agent/runner suite for regressions**

Run: `pytest tests/test_modes.py tests/test_runner.py -v`
Expected: PASS (no regressions in existing agent behavior).

- [ ] **Step 6: Lint and commit**

```bash
ruff check hackbot/modes/agent.py && black hackbot/modes/agent.py tests/test_modes.py
git add hackbot/modes/agent.py tests/test_modes.py
git commit -m "feat(agent): add allowlist-bounded install action with safe_mode gate"
```

---

### Task 5: Document the `install` action in the agent system prompt

**Files:**
- Modify: `hackbot/core/engine.py` (agent action documentation block, ~line 254-260, after the `chain_exploits`/`active_scan` examples)
- Test: `tests/test_engine.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: the agent system prompt now describes the `install` action so the LLM emits it when a tool run returns `Tool not found`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_engine.py` (use the existing prompt-construction entry point in that file — locate how other tests obtain the agent system prompt, e.g. `AIEngine.get_system_prompt("agent", ...)` or the module-level prompt constant, and mirror it):

```python
def test_agent_prompt_documents_install_action():
    from hackbot.core.engine import AIEngine
    prompt = AIEngine.build_agent_prompt()  # match the actual accessor used elsewhere in this file
    assert '"action": "install"' in prompt
    assert "Tool not found" in prompt
```

> Implementer note: `tests/test_engine.py` already exercises the agent prompt. Use whatever accessor those existing tests use to fetch the agent system prompt instead of `build_agent_prompt` if the name differs — the assertion content stays the same.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_engine.py::test_agent_prompt_documents_install_action -v`
Expected: FAIL — `"action": "install"` not present in the prompt.

- [ ] **Step 3: Write minimal implementation**

In `hackbot/core/engine.py`, add a numbered subsection to the agent prompt action documentation (after the `active_scan` block, before `ZERO-DAY` content ends / wherever the action list continues):

```python
7. **Autonomous Tool Installation** — If a tool you need is not installed (a command
   returns "Tool not found"), you can install it autonomously:
   ```json
   {"action": "install", "tool": "<tool_name>", "explanation": "<why you need it>"}
   ```
   Only allowlisted security tools with a known install recipe can be installed.
   When safe_mode is on, the user confirms each install. After a successful install,
   re-run the original command. If the install fails or no recipe exists, adapt and
   use a different tool.
```

(Renumber if `7` collides with an existing item; the content is what matters.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_engine.py -v`
Expected: PASS.

- [ ] **Step 5: Lint and commit**

```bash
ruff check hackbot/core/engine.py && black hackbot/core/engine.py tests/test_engine.py
git add hackbot/core/engine.py tests/test_engine.py
git commit -m "docs(engine): document install action in agent system prompt"
```

---

### Task 6: Manual surface — `/install` slash command and `hackbot install` subcommand

**Files:**
- Modify: `hackbot/cli.py` (command table ~line 181-220 add `/install`; add `_install_tool` method near `_show_tools` ~line 411; add Click `install` subcommand near the `tools` command ~line 2630)
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `AgentMode` (already imported in cli), its `.installer`, `.runner`, `_process_install_action`; `HackBotApp._on_confirm` (~line 151).
- Produces:
  - `HackBotApp._install_tool(self, args: str) -> bool` — REPL handler; ensures an agent exists (same lazy-create pattern as `_run_command` ~line 963-971), then delegates to `self.agent._process_install_action({"action": "install", "tool": args.strip()})` and prints the returned string. Usage error when `args` empty.
  - `"/install": lambda: self._install_tool(args)` entry in the command table.
  - Click `install` subcommand (`hackbot install <tool>`) that builds a `HackBotApp` and calls `_install_tool`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py` (mirror the construction style already used there for `HackBotApp`):

```python
def test_install_tool_requires_argument(make_app):
    app = make_app()  # use the existing HackBotApp fixture/factory in this file
    assert app._install_tool("") is True  # returns True (stay in REPL), prints usage


def test_install_tool_delegates_to_agent(monkeypatch, make_app):
    app = make_app()
    captured = {}

    class _StubAgent:
        def _process_install_action(self, action):
            captured["action"] = action
            return "**[install]** SUCCESS — Installed nuclei"

    app.agent = _StubAgent()
    app.mode = "agent"
    result = app._install_tool("nuclei")
    assert result is True
    assert captured["action"] == {"action": "install", "tool": "nuclei"}
```

> Implementer note: `tests/test_cli.py` already constructs `HackBotApp` for other command tests. Use that existing helper/fixture (named here `make_app`); do not invent a new construction path. If the file builds the app inline, build it inline the same way.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -k install -v`
Expected: FAIL — `HackBotApp` has no attribute `_install_tool`.

- [ ] **Step 3: Write minimal implementation**

In `hackbot/cli.py`:

1. Add to the `commands` dict (after `"/tools"` ~line 193):

```python
            "/install": lambda: self._install_tool(args),
```

2. Add the method (after `_show_tools` ~line 414):

```python
    def _install_tool(self, args: str) -> bool:
        tool = args.strip()
        if not tool:
            print_error("Usage: /install <tool>")
            return True
        if self.mode != "agent" or not self.agent:
            self.agent = AgentMode(
                engine=self.engine,
                config=self.config,
                on_step=self._on_agent_step,
                on_confirm=self._on_confirm,
                on_output=self._on_tool_output,
            )
        result = self.agent._process_install_action({"action": "install", "tool": tool})
        console.print(Markdown(result))
        return True
```

3. Add the Click subcommand (after the `tools` command ~line 2637):

```python
@main.command(name="install")
@click.argument("tool")
@click.pass_context
def install_cmd(ctx, tool):
    """Install a security tool that isn't present."""
    config = ctx.obj["config"]
    app = HackBotApp(config)
    app._install_tool(tool)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -k install -v`
Expected: PASS.

- [ ] **Step 5: Full suite + smoke test**

```bash
pytest tests/ -q
hackbot --version
```
Expected: full suite passes; version prints.

- [ ] **Step 6: Lint and commit**

```bash
ruff check hackbot/cli.py && black hackbot/cli.py tests/test_cli.py
git add hackbot/cli.py tests/test_cli.py
git commit -m "feat(cli): add /install command and hackbot install subcommand"
```

---

## Self-Review

**Spec coverage:**
- `installer.py` / `ToolInstaller` + `InstallPlan`/`InstallResult` → Tasks 2, 3. ✓
- `TOOL_INSTALL_MAP` + layered managers (apt/dnf/pacman/brew/pipx/pip/go) → Task 1 (map) + Task 2 (`_build_command`, `_MANAGER_BINARY`). ✓
- `install` agent action (parse + dispatch, allowlist, already-installed, plan, safe_mode confirm, feed-back) → Task 4. ✓
- Engine prompt documents the action + "Tool not found" guidance → Task 5. ✓
- Security: execution via `ToolRunner`, managers allowlisted as drivers, sudo via `_apply_sudo` only (`needs_sudo` is metadata + honest sudo hint) → Tasks 1, 3, 4. ✓
- `allow_arbitrary_install` flag default off → Task 1; enforced in Task 4. ✓
- Manual `/install` + `hackbot install` → Task 6. ✓
- Tests with mocks, no real installs → every task. ✓
- Error handling (unmapped, nonzero exit, binary still missing, declined, no managers) → Tasks 3 + 4 tests. ✓

**Placeholder scan:** No TBD/TODO; every code step shows full code. Two "implementer notes" (Tasks 5, 6) point at existing test accessors/fixtures rather than guessing their exact names — the assertion content and behavior are fully specified, so this is a lookup, not an unfinished spec.

**Type consistency:** `InstallPlan(tool, manager, package, command, needs_sudo)` and `InstallResult(tool, success, manager, path, message, stdout, stderr)` are used identically across Tasks 2–4 and tests. `plan_install`/`install`/`available_managers`/`_process_install_action` signatures match between definition and callers. `_MANAGER_BINARY` keys (`apt`,`dnf`,…) align with `TOOL_INSTALL_MAP` per-manager keys and `_SUDO_MANAGERS`.
