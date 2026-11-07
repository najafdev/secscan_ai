## HackBot v1.2.4

### 🚀 Shell-Free Pipeline Support (Piped Commands)
- **Pipeline Execution:** Implemented safe, shell-free pipeline execution (`execute()` and `execute_async()`) using chained subprocesses. Piped commands (e.g. `nmap ... | grep open`) are split and run without invoking a shell (`shell=False`), preventing command injection while enabling advanced filtering.
- **Allowed Utilities:** Added common text-processing utilities (`grep`, `egrep`, `head`, `tail`, `sort`, `uniq`, `wc`, `awk`, `sed`, `cut`, `tr`, `cat`, `tee`, `find`, `xargs`) to the default allowed tools list so they can be safely used as pipeline targets.

### 🛡️ Improved Allowlist & Script Handling
- **Remediation Scripts:** Added `bash`, `sh`, and `chmod` to the default allowed tools list. Implemented auto-detection in `runner.py` to automatically allow execution of HackBot-generated remediation/exploit scripts saved in the `reports/scripts` directory.
- **Python Compatibility:** Added `python` to the allowed list alongside `python3` to prevent commands using the `python` alias from being blocked.

### 🐛 Bug Fixes
- **Process Group Terminate Bug:** Fixed a critical bug in the process termination logic (`_kill_process`) where subprocess timeouts would terminate the entire parent process group (killing pytest or HackBot itself). It now safely detects the process group ID and terminates the child process group without affecting the parent runner.
- **Accidental Slash Commands:** Added normalization rules to automatically strip accidental trailing chat slash commands (like `/cve`, `/osint`, `/topology`) when appended to tool execution commands by the AI.
- **Dirb Syntax Auto-Correction:** Added normalization rules to auto-correct invalid `dirb` syntax (specifically stripping misplaced `-a` flags immediately preceding a URL).
- **Amass Syntax Auto-Correction:** Added auto-correction for invalid `amass` subcommand/flag syntax and URL-format targets, automatically translating them into correct `amass intel` or `amass enum` commands.

### 🛠️ Wfuzz Python 3.12+ Dependency Fix
- **setuptools Dependency:** Installed `setuptools` in the Dockerfile to supply the `pkg_resources` module which was removed in Python 3.12+, resolving the wfuzz startup crash.
- **Pre-Install Hooks:** Added support for `pre_install` commands in `ToolInstaller` (allowing `pip install setuptools` to run automatically before `wfuzz`).
- **Runtime Auto-Repair:** Added `ToolInstaller.check_and_fix_wfuzz()` to verify and dynamically fix the `pkg_resources` import at runtime.

### Files Changed
| File | Description |
|------|-------------|
| `hackbot/core/runner.py` | Added pipeline execution, script validation, process group fix, and dirb/amass/slash command auto-correction |
| `hackbot/config.py` | Updated default allowed tools list and added `wfuzz` installation recipe with `pre_install` hook |
| `hackbot/core/installer.py` | Added `pre_install` hook support and `check_and_fix_wfuzz()` runtime auto-repair |
| `Dockerfile` | Installed `setuptools` to fix wfuzz dependency issues |
| `tests/test_runner.py` | Updated and added unit tests for pipeline execution, Amass/Dirb auto-correction, and slash command stripping |

---

**Full Changelog**: https://github.com/yashab-cyber/hackbot/compare/v1.2.3...v1.2.4
