# Design: Autonomous Security-Tool Installation

Date: 2026-06-22
Status: Approved (pending spec review)

## Problem

HackBot drives real security tools (nmap, nikto, sqlmap, nuclei, …) during an
autonomous assessment. When a tool the agent wants to use is not installed, the
runner returns `Tool not found` and the agent is stuck — the user must leave the
session, install the tool by hand, and start over. We want HackBot to install
missing security tools itself.

## Goals

- The agent can autonomously install a missing tool mid-assessment via a new
  `install` action, then continue using it.
- Installation reuses HackBot's existing, deliberately hardened execution and
  privilege boundary rather than introducing a new one.
- Cross-distro / cross-manager reality is handled: many security tools ship via
  `go install` or `pipx`, not just `apt`.
- The capability is bounded by default (allowlist-only) and respects the user's
  existing `safe_mode` trust dial.

## Non-Goals

- Removing or installing arbitrary system packages unrelated to security tooling
  (only allowed when the user explicitly opts in — see `allow_arbitrary_install`).
- Self-updating HackBot itself (that already exists in `core/updater.py`).
- Managing tool *versions* / upgrades. First version installs if missing; it does
  not upgrade an already-present tool.

## Decisions (from brainstorming)

| Question | Decision |
| --- | --- |
| Trigger | Fully autonomous — new `install` agent action. Plus a manual `/install` + `hackbot install` surface for testing/users. |
| What can be installed | Allowlist-bounded (tools already in `agent.allowed_tools`) with a curated tool→package map. Opt-in `allow_arbitrary_install` relaxes this. |
| Managers / platforms | Layered: system manager (`apt-get`/`dnf`/`pacman`/`brew`) + language managers (`pipx`/`pip`, `go install`), pluggable. |
| Privilege | Reuse centralized `_apply_sudo` in `ToolRunner`. No new privilege path. |
| Confirmation | Respect `safe_mode`: on (default) → one y/n confirmation per install; `--no-safe-mode` → unattended. |
| `allow_arbitrary_install` default | Off (allowlist-only). |

## Architecture

### 1. `hackbot/core/installer.py` — `ToolInstaller`

A self-contained engine, structured like other `core/` modules.

- **Manager detection (once, cached):** probe `apt-get`, `dnf`, `pacman`, `brew`,
  `pipx`, `pip`, `go` via `shutil.which`. Expose `available_managers()`.
- **`plan_install(tool) -> Optional[InstallPlan]`:** consult `TOOL_INSTALL_MAP`,
  pick the first manager in the tool's preferred order that is available on this
  system, and build an `InstallPlan`. Returns `None` if the tool is unmappable or
  no suitable manager is present (caller surfaces a clear reason).
- **`install(tool, runner) -> InstallResult`:** execute the plan's argument vector
  through the supplied `ToolRunner` (NOT a fresh subprocess), then re-check
  `resolve_tool_path(tool)` to confirm the binary now exists. Returns success +
  resolved path, or failure + captured output.

**`InstallPlan` (dataclass):** `tool`, `manager`, `package`, `command` (list[str],
already split — no shell), `needs_sudo: bool`.

**`InstallResult` (dataclass):** `tool`, `success: bool`, `manager`, `path:
Optional[str]`, `message`, `stdout`/`stderr` (truncated).

**Dependencies:** `ToolRunner`, `resolve_tool_path`, `TOOL_INSTALL_MAP`. One job:
turn "I need tool X" into a verified install or a clear, structured failure.

### 2. `TOOL_INSTALL_MAP` — in `config.py` (beside `TOOL_ALIASES`)

```python
TOOL_INSTALL_MAP = {
    "nuclei":    {"order": ["go", "apt"],
                  "go": "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
                  "apt": "nuclei"},
    "subfinder": {"order": ["go"],
                  "go": "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"},
    "sqlmap":    {"order": ["apt", "pipx"], "apt": "sqlmap", "pipx": "sqlmap"},
    # ...one entry per supported tool...
}
```

- `order` lists preferred managers; the installer picks the first one available.
- Per-manager values are the package/module identifier for that manager.
- `apt` entries are also used for `dnf`/`pacman` when the package name matches;
  where names differ, the map carries `dnf`/`pacman` keys explicitly. `brew` and
  `pip` are keyed the same way.
- Only tools present in `agent.allowed_tools` are installable. The initial map
  covers the commonly-missing tools first; it does not need an entry for every one
  of the ~80 allowlisted tools on day one, but unmapped tools simply report
  "no install recipe" rather than failing silently.

### 3. New agent action — `install`

Format (documented in `engine.py`'s agent system prompt alongside the other
actions):

```json
{"action": "install", "tool": "nuclei", "explanation": "needed to scan for known CVEs"}
```

Dispatch flow added to `agent.py` (`_parse_actions` recognizes it;
`_process_actions_loop` handles it):

1. **Allowlist check** — reject if `tool` not in `allowed_tools`, unless
   `allow_arbitrary_install` is set. Rejection text is fed back to the AI.
2. **Already installed?** — if `resolve_tool_path(tool)` already resolves, report
   "already installed" back to the AI (no-op) and continue.
3. **Plan** — `installer.plan_install(tool)`. If `None`, feed "can't install,
   here's why (unmapped / no manager)" back to the AI so it can adapt.
4. **Confirmation gate** — if `safe_mode` is on, pause for one y/n confirmation
   using the existing confirmation UI, showing the exact command. If declined,
   feed the decline back to the AI. With `--no-safe-mode`, proceed unattended.
5. **Execute** — `installer.install(...)`; feed the structured result (success +
   new path, or failure output) back into the loop so the agent retries the tool
   or adapts.

The existing loop guards (dedupe, repeat caps, repeated-failure stop) apply to
`install` actions too, preventing install retry storms.

The `engine.py` prompt is updated to tell the agent that when a tool run returns
`Tool not found`, it may emit an `install` action for that tool. No separate
runner hook is required — the "Tool not found" string is already fed back to the
AI.

### 4. Security integration (preserve the hardened boundary)

- Installs execute through `ToolRunner`, so `validate_command`, `BLOCKED_COMMANDS`,
  and shell-operator rejection remain in force.
- Package managers used as install drivers (`apt-get`, `dnf`, `pacman`, `brew`,
  `pipx`, `pip`, `go`) are **NOT** in the global `agent.allowed_tools` list.
  `ToolInstaller.install` runs them via a dedicated `allow_install_drivers`
  bypass on `ToolRunner.validate_command`/`execute` that permits only the
  binaries listed in `config.INSTALL_DRIVERS`, so a normal `execute` action
  from the agent cannot invoke them. Their argument vectors are constructed by
  the installer from the curated map — never from raw LLM text — except in
  opt-in `allow_arbitrary_install` mode, where the AI-named package string is
  still `shlex`-safe-validated and passed as a single argument (no shell).
- Sudo handling stays centralized in `ToolRunner._apply_sudo`. The installer sets
  `needs_sudo` on the plan; the runner remains the single sudo authority.
- `RISKY_PATTERNS` / `safe_mode` confirmation behavior is reused, not bypassed.

### 5. Config

Add to the `agent` config section (`config.py`):

- `allow_arbitrary_install: bool = False` — when true, the agent may install a
  package the LLM names even if it is not in the curated map / allowlist.

No other config changes. `safe_mode` and `sudo_*` already exist and are reused.

### 6. Manual surface (reuses the installer module)

- **REPL:** `/install <tool>` slash command → `_install_tool` method on
  `HackBotApp`, registered in the command table. Plans, confirms (respecting
  `safe_mode`), installs, prints result.
- **CLI:** `hackbot install <tool>` subcommand in the Click group, same path.

These exist because the installer is a clean module and this makes the feature
testable and directly usable; they add negligible surface.

## Data Flow

```
agent LLM emits {"action":"install","tool":"nuclei"}
  -> agent._process_actions_loop
       -> allowlist + already-installed checks
       -> ToolInstaller.plan_install("nuclei") -> InstallPlan(go install ...)
       -> safe_mode? confirm y/n
       -> ToolInstaller.install(plan, runner)
            -> ToolRunner.execute(["go","install",...])  (shlex, sudo if needed)
            -> resolve_tool_path("nuclei") to verify
       -> InstallResult fed back into conversation
  -> agent re-runs the original tool command
```

## Error Handling

- **Unmapped tool / no available manager:** structured "no install recipe"
  message back to the AI; agent adapts (different tool or `complete`).
- **Install command fails (nonzero exit):** captured stdout/stderr (truncated)
  returned; loop guards stop repeated identical failures.
- **Binary still missing after "successful" install:** treated as failure
  (re-check via `resolve_tool_path`), reported as such.
- **User declines confirmation:** decline fed back; no install.
- **No package managers at all:** `available_managers()` empty → every plan is
  `None` → clear message.

## Testing — `tests/test_installer.py`

All tests mock `shutil.which` and the `ToolRunner`; **no real packages installed.**

- Manager detection with various `which` availabilities.
- `plan_install`: correct manager chosen by `order`; correct command vector;
  `needs_sudo` set correctly; `None` for unmapped tool; `None` when no manager.
- Allowlist enforcement: install of non-allowlisted tool rejected unless
  `allow_arbitrary_install`.
- `safe_mode` gate: confirmation requested when on; skipped when off (mock the
  confirmation callback).
- Install round-trip with a mocked runner: success path (binary "appears") and
  failure path (nonzero exit / binary still missing).
- Agent dispatch: `_parse_actions` recognizes the `install` action; already-
  installed short-circuit.

## Files Touched

- `hackbot/core/installer.py` — new module.
- `hackbot/config.py` — `TOOL_INSTALL_MAP`, `allow_arbitrary_install` flag,
  add managers to allowlist as install drivers.
- `hackbot/modes/agent.py` — parse + dispatch `install` action.
- `hackbot/core/engine.py` — document the `install` action in the agent prompt.
- `hackbot/cli.py` — `/install` slash command + `hackbot install` subcommand.
- `tests/test_installer.py` — new tests.
