"""
HackBot Tool Runner
===================
Executes security tools in a sandboxed subprocess with timeout, logging, and output capture.
Cross-platform compatible (Linux, macOS, Windows).
"""

from __future__ import annotations

import asyncio
import os
import platform
import shlex
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from hackbot.config import INSTALL_DRIVERS, LOGS_DIR, resolve_tool_path

# Lazy reference — filled at runtime to avoid circular imports
_plugin_manager = None

def _get_plugin_manager():
    """Lazy-load the plugin manager."""
    global _plugin_manager
    if _plugin_manager is None:
        try:
            from hackbot.core.plugins import get_plugin_manager
            _plugin_manager = get_plugin_manager()
        except Exception:
            pass
    return _plugin_manager


@dataclass
class ToolResult:
    """Result of a tool execution."""
    tool: str
    command: str
    stdout: str
    stderr: str
    return_code: int
    duration: float
    success: bool
    timestamp: float = field(default_factory=time.time)
    truncated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "command": self.command,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "return_code": self.return_code,
            "duration": round(self.duration, 2),
            "success": self.success,
            "timestamp": self.timestamp,
        }

    @property
    def output(self) -> str:
        """Combined stdout + stderr."""
        parts = []
        if self.stdout.strip():
            parts.append(self.stdout.strip())
        if self.stderr.strip():
            parts.append(f"[STDERR]\n{self.stderr.strip()}")
        return "\n".join(parts) if parts else "(no output)"


# Commands that are NEVER allowed (destructive to host system)
BLOCKED_COMMANDS = [
    "rm -rf /",
    "mkfs",
    "dd if=/dev/zero",
    ":(){ :|:& };:",
    "chmod -R 777 /",
    "mv /* /dev/null",
    "> /dev/sda",
    "shutdown",
    "reboot",
    "halt",
    "init 0",
    "init 6",
]

# Dangerous patterns that require confirmation
RISKY_PATTERNS = [
    "rm -rf",
    "rm -r",
    "format",
    "fdisk",
    "mkfs",
    "dd ",
    "exploit",
    "payload",
    "reverse_tcp",
    "meterpreter",
    "chmod 777",
    "wget.*|.*sh",
    "curl.*|.*sh",
    "nc -e",
    "netcat -e",
    "bash -i",
]

# Standalone shell-operator tokens that indicate command chaining or redirection.
# Detected as discrete tokens (via shlex), so characters inside a single argument
# (e.g. an '&' in a URL query string) are never flagged.
#
# Pipes ("|") are allowed when BOTH sides are validated tools — they are executed
# as a safe subprocess pipeline without invoking a shell.
PIPE_TOKENS = frozenset({"|"})
DANGEROUS_OPERATOR_TOKENS = frozenset({";", "||", "&", "&&", ">", ">>", "<", "<<"})
SHELL_OPERATOR_TOKENS = PIPE_TOKENS | DANGEROUS_OPERATOR_TOKENS


class ToolRunner:
    """
    Executes security tools in controlled subprocesses.
    Features:
    - Command validation and safety checks
    - Timeout enforcement
    - Output capture and truncation
    - Execution logging
    - Cross-platform support
    """

    MAX_OUTPUT_SIZE = 100_000  # 100KB max output per command

    def __init__(
        self,
        allowed_tools: List[str],
        timeout: int = 300,
        safe_mode: bool = True,
        auto_confirm: bool = False,
        sudo_mode: bool = False,
        sudo_password: str = "",
        on_confirm: Optional[Callable[[str, str], bool]] = None,
        on_output: Optional[Callable[[str], None]] = None,
    ):
        self.allowed_tools = allowed_tools
        self.timeout = timeout
        self.safe_mode = safe_mode
        self.auto_confirm = auto_confirm
        self.sudo_mode = sudo_mode
        self.sudo_password = sudo_password
        self.on_confirm = on_confirm
        self.on_output = on_output
        self.history: List[ToolResult] = []
        self._sudo_validated = False

    def _normalize_command(self, command: str) -> str:
        """Normalize AI-generated command text into an executable command string."""
        cmd = (command or "").strip()
        if not cmd:
            return ""

        # Accept fenced snippets by extracting the first non-fence line.
        if cmd.startswith("```"):
            lines = [ln.strip() for ln in cmd.splitlines()]
            body = [ln for ln in lines if ln and not ln.startswith("```")]
            if body:
                cmd = body[0]

        # Strip surrounding inline backticks (must come before $ prompt check).
        if len(cmd) >= 2 and cmd[0] == "`" and cmd[-1] == "`":
            cmd = cmd[1:-1].strip()

        # Strip shell prompt prefixes commonly emitted by LLMs.
        if cmd.startswith("$ "):
            cmd = cmd[2:].strip()

        # Strip any AI-generated sudo prefix so _apply_sudo() can handle it
        # cleanly and consistently.  This prevents the double-sudo problem
        # where the AI emits "sudo -n nmap ..." and _apply_sudo adds another.
        cmd = self._strip_sudo_prefix(cmd)

        # Strip trailing interactive slash commands accidentally appended by LLMs
        slash_commands = {"/cve", "/osint", "/topology", "/compliance", "/diff", "/remediate", "/proxy"}
        parts = cmd.split()
        if len(parts) > 1 and parts[-1].lower() in slash_commands:
            parts = parts[:-1]
            cmd = " ".join(parts).strip()

        # Fix dirb invalid flag order or hallucinated flags:
        # e.g. "dirb -a http://..." -> "dirb http://..."
        if len(parts) >= 3 and parts[0].lower() == "dirb" and parts[1].lower() == "-a" and (parts[2].lower().startswith("http://") or parts[2].lower().startswith("https://")):
            parts.pop(1)
            cmd = " ".join(parts)

        # Fix amass invalid syntax and URL targets:
        # e.g. "amass -a http://111.90.156.228" -> "amass intel -addr 111.90.156.228"
        # e.g. "amass intel -addr http://111.90.156.228" -> "amass intel -addr 111.90.156.228"
        if len(parts) >= 2 and parts[0].lower() == "amass":
            valid_subs = {"assoc", "db", "enum", "intel", "track", "viz"}
            has_sub = any(p.lower() in valid_subs for p in parts)
            
            # Find the target (URL, domain, or IP)
            target = None
            target_idx = -1
            for i, part in enumerate(parts):
                if part.startswith("http://") or part.startswith("https://") or "." in part:
                    if not part.startswith("-"):
                        target = part
                        target_idx = i
                        break
            
            if target:
                clean_target = target
                if clean_target.startswith("http://"):
                    clean_target = clean_target[7:]
                elif clean_target.startswith("https://"):
                    clean_target = clean_target[8:]
                clean_target = clean_target.split('/')[0].split(':')[0]
                
                # Check if clean_target is an IP address
                is_ip = False
                dot_parts = clean_target.split('.')
                if len(dot_parts) == 4:
                    try:
                        is_ip = all(0 <= int(p) <= 255 for p in dot_parts)
                    except ValueError:
                        pass
                
                # Case A: Missing subcommand or has invalid "-a" flag
                if not has_sub or "-a" in [p.lower() for p in parts]:
                    if is_ip:
                        cmd = f"amass intel -addr {clean_target}"
                    else:
                        cmd = f"amass enum -d {clean_target}"
                # Case B: Correct subcommand but has URL instead of domain/IP
                elif target != clean_target:
                    parts[target_idx] = clean_target
                    cmd = " ".join(parts)

        return cmd

    @staticmethod
    def _strip_sudo_prefix(command: str) -> str:
        """Remove a leading ``sudo [-flags]`` from *command*.

        This is used during normalization so that ``_apply_sudo`` is the single
        authority on whether to prepend sudo.  The stripping handles common
        patterns emitted by LLMs:
          - ``sudo nmap …``
          - ``sudo -n nmap …``
          - ``sudo -S nmap …``
          - ``sudo -n -u root nmap …``
        """
        parts = command.split()
        if not parts or parts[0] != "sudo":
            return command

        # sudo options that consume a following argument token
        takes_arg = {
            "-A", "-a", "-C", "-c", "-g", "-h", "-p", "-R", "-r", "-t", "-U", "-u",
            "--askpass", "--chdir", "--close-from", "--group", "--host", "--prompt",
            "--chroot", "--role", "--type", "--other-user", "--user",
        }

        idx = 1
        while idx < len(parts):
            token = parts[idx]
            if token == "--":
                idx += 1
                break
            if token.startswith("-"):
                if token in takes_arg:
                    idx += 2
                else:
                    idx += 1
                continue
            break

        if idx >= len(parts):
            return command  # nothing left after stripping — return original

        return " ".join(parts[idx:])

    def _infer_tool_name(self, command: str, tool_name: str = "") -> str:
        """Resolve a stable tool label for result reporting."""
        if tool_name:
            return tool_name
        parts = command.split()
        return parts[0] if parts else "unknown"

    def is_tool_available(self, tool: str) -> bool:
        """Check if a tool is installed on the system."""
        return resolve_tool_path(tool) is not None

    def is_tool_allowed(self, tool: str) -> bool:
        """Check if a tool is in the allowed list."""
        normalized = os.path.basename(tool).lower()
        if normalized.endswith(".exe"):
            normalized = normalized[:-4]

        allowed = {
            os.path.basename(t).lower()[:-4] if os.path.basename(t).lower().endswith(".exe")
            else os.path.basename(t).lower()
            for t in self.allowed_tools
        }
        if normalized in allowed:
            return True

        # Allow concrete alias binaries for logical package-level tools
        # in the allowlist (e.g., `thc-ipv6` -> `alive6` on Kali).
        for logical_tool in self.allowed_tools:
            resolved = resolve_tool_path(logical_tool)
            if not resolved:
                continue
            resolved_name = os.path.basename(resolved).lower()
            if resolved_name.endswith(".exe"):
                resolved_name = resolved_name[:-4]
            if normalized == resolved_name:
                return True

        return False

    def _extract_validated_tool(self, parts: List[str]) -> str:
        """Extract the real executable name from parsed command parts.

        Handles sudo-prefixed commands with sudo options (for example
        ``sudo -n nmap ...``) so validation checks the intended tool rather
        than a sudo flag token.  Also handles nested sudo (e.g.,
        ``sudo -n sudo -n nmap``) and rejects flag-like tokens (``--target``)
        that clearly aren't tool names.
        """
        if not parts:
            return ""

        first = os.path.basename(parts[0])
        if first != "sudo":
            # Reject flag-like tokens as tool names (malformed AI commands)
            if first.startswith("-"):
                return ""
            return first

        # sudo options that consume a following argument token
        takes_arg = {
            "-A", "-a", "-C", "-c", "-g", "-h", "-p", "-R", "-r", "-t", "-U", "-u",
            "--askpass", "--chdir", "--close-from", "--group", "--host", "--prompt",
            "--chroot", "--role", "--type", "--other-user", "--user",
        }

        idx = 1
        while idx < len(parts):
            token = parts[idx]

            # End of sudo options; next token should be the real command.
            if token == "--":
                idx += 1
                break

            # Still parsing sudo options.
            if token.startswith("-"):
                if token in takes_arg:
                    idx += 2
                else:
                    idx += 1
                continue

            break

        if idx >= len(parts):
            return ""

        candidate = os.path.basename(parts[idx])

        # Handle nested sudo (e.g., sudo -n sudo -n nmap ...)
        if candidate == "sudo":
            return self._extract_validated_tool(parts[idx:])

        # Reject flag-like tokens that are clearly not tool names
        if candidate.startswith("-"):
            return ""

        return candidate

    @staticmethod
    def _strip_wrapping_quotes(value: str) -> str:
        """Remove one layer of matching shell quotes from a token."""
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            return value[1:-1]
        return value

    @staticmethod
    def _split_command(command: str) -> List[str]:
        """Split command text for validation without invoking a shell."""
        if platform.system() == "Windows":
            return [
                ToolRunner._strip_wrapping_quotes(part)
                for part in shlex.split(command, posix=False)
            ]
        return shlex.split(command)

    @staticmethod
    def _contains_shell_operators(command: str) -> tuple[Optional[str], bool]:
        """Return ``(offending_token, is_pipe_only)``.

        * ``(None, False)`` — no shell operators found; command is safe.
        * ``(token, False)`` — a dangerous operator was found; reject.
        * ``("|", True)`` — only pipe(s) found; caller may allow controlled
          pipeline execution after validating each stage.
        * ``("<unparseable>", False)`` — tokenization failed (e.g.
          unbalanced quotes); reject.

        Operates on the NORMALIZED command (wrapping backticks and a leading
        ``$ `` prompt have already been stripped by ``_normalize_command``), so
        only *embedded* substitution survives to be rejected here.  Detection is
        token-based to avoid false positives on legitimate arguments such as URL
        query strings (``http://x/?a=1&b=2`` stays inside a single shlex token).
        """
        # Command substitution: any remaining backtick or "$(" is rejected.
        if "`" in command:
            return "`", False
        if "$(" in command:
            return "$(", False

        try:
            tokens = ToolRunner._split_command(command)
        except ValueError:
            return "<unparseable>", False

        has_pipe = False
        for tok in tokens:
            if tok in DANGEROUS_OPERATOR_TOKENS:
                return tok, False
            if tok in PIPE_TOKENS:
                has_pipe = True

        if has_pipe:
            return "|", True
        return None, False

    def validate_command(
        self, command: str, allow_install_drivers: bool = False,
    ) -> tuple[bool, str]:
        """
        Validate a command for safety.
        Returns (is_safe, reason).
        """
        command = self._normalize_command(command)
        cmd_lower = command.lower().strip()

        # Plugin commands are always allowed
        if cmd_lower.startswith("hackbot-plugin "):
            return True, "OK"

        # Check blocked commands
        for blocked in BLOCKED_COMMANDS:
            if blocked in cmd_lower:
                return False, f"Blocked command detected: {blocked}"

        # Reject shell command-substitution and standalone operator tokens.
        # Unconditional (not safe_mode-gated): execution is shell-free, so this
        # is a clear, early hard-reject of unsupported syntax rather than a
        # confirmable RISKY warning.
        #
        # Pipes are allowed: each stage is validated independently, and the
        # pipeline is executed as chained subprocesses (no shell).
        offender, is_pipe_only = self._contains_shell_operators(command)
        if offender == "<unparseable>":
            return False, "Invalid command: unbalanced quotes"
        if offender is not None and not is_pipe_only:
            return False, f"Shell metacharacter not allowed: '{offender}'"

        # ── Pipeline commands: validate every stage ──────────────────
        if is_pipe_only:
            return self._validate_pipeline(
                command, allow_install_drivers=allow_install_drivers,
            )

        # ── Single command ───────────────────────────────────────────
        # Extract tool name (skip 'sudo' prefix for validation)
        try:
            parts = self._split_command(command)
        except ValueError:
            return False, "Invalid command: unbalanced quotes"
        if not parts:
            return False, "Empty command"

        tool = self._extract_validated_tool(parts)
        if not tool:
            return False, "Empty command"

        # Check if tool is allowed
        if not self._is_tool_or_script_allowed(tool, command, allow_install_drivers):
            return False, f"Tool '{tool}' is not in the allowed list"

        # Check risky patterns in safe mode
        if self.safe_mode:
            for pattern in RISKY_PATTERNS:
                if pattern in cmd_lower:
                    return True, f"RISKY: Contains '{pattern}' — requires confirmation"

        return True, "OK"

    def _is_tool_or_script_allowed(
        self, tool: str, command: str = "", allow_install_drivers: bool = False,
    ) -> bool:
        """Check if *tool* is allowed, including HackBot-generated scripts."""
        if self.is_tool_allowed(tool):
            return True

        # Allow install drivers when the flag is set (used by ToolInstaller)
        if allow_install_drivers and os.path.basename(tool).lower() in INSTALL_DRIVERS:
            return True

        # Allow HackBot-generated scripts in the reports/scripts directory.
        # The agent saves remediation / exploit scripts there and then tries
        # to execute them — they must be permitted.
        if command:
            try:
                parts = self._split_command(command)
            except ValueError:
                return False
            for part in parts:
                # Check if any argument is a path inside the scripts dir
                if self._is_hackbot_script(part):
                    return True

        return False

    @staticmethod
    def _is_hackbot_script(path_str: str) -> bool:
        """Return True if *path_str* looks like a HackBot-generated script."""
        try:
            p = Path(path_str)
            if not p.is_absolute():
                return False
            # Match both the default REPORTS_DIR and common user overrides
            parts_lower = [part.lower() for part in p.parts]
            if "scripts" in parts_lower and (
                "hackbot" in parts_lower
                or "reports" in parts_lower
                or ".local" in parts_lower
            ):
                return True
        except (OSError, ValueError):
            pass
        return False

    # ── Pipeline support ─────────────────────────────────────────────

    @staticmethod
    def _split_pipeline(command: str) -> List[str]:
        """Split *command* at top-level pipe (``|``) tokens into stages.

        Each returned string is a single command (whitespace-trimmed).
        Raises ``ValueError`` if tokenization fails.
        """
        tokens = ToolRunner._split_command(command)
        stages: List[List[str]] = [[]]
        for tok in tokens:
            if tok == "|":
                stages.append([])
            else:
                stages[-1].append(tok)
        # Re-join tokens with proper quoting
        return [
            shlex.join(stage) if platform.system() != "Windows"
            else " ".join(stage)
            for stage in stages
            if stage  # drop empty stages from trailing pipes
        ]

    def _validate_pipeline(
        self, command: str, allow_install_drivers: bool = False,
    ) -> tuple[bool, str]:
        """Validate every stage of a piped command independently."""
        try:
            stages = self._split_pipeline(command)
        except ValueError:
            return False, "Invalid pipeline: unbalanced quotes"

        if len(stages) < 2:
            return False, "Invalid pipeline: expected at least two stages"

        for i, stage in enumerate(stages, 1):
            stage_lower = stage.lower().strip()

            # Check blocked commands in each stage
            for blocked in BLOCKED_COMMANDS:
                if blocked in stage_lower:
                    return False, f"Blocked command detected in pipeline stage {i}: {blocked}"

            try:
                parts = self._split_command(stage)
            except ValueError:
                return False, f"Invalid pipeline stage {i}: unbalanced quotes"
            if not parts:
                return False, f"Empty pipeline stage {i}"

            tool = self._extract_validated_tool(parts)
            if not tool:
                return False, f"Empty command in pipeline stage {i}"

            if not self._is_tool_or_script_allowed(tool, stage, allow_install_drivers):
                return False, f"Tool '{tool}' in pipeline stage {i} is not in the allowed list"

        # Check risky patterns across the full command
        cmd_lower = command.lower().strip()
        if self.safe_mode:
            for pattern in RISKY_PATTERNS:
                if pattern in cmd_lower:
                    return True, f"RISKY: Contains '{pattern}' — requires confirmation"

        return True, "OK"

    def _apply_sudo(self, command: str) -> str:
        """Prepend sudo to command if sudo_mode is enabled and not already present.

        Uses ``sudo -S`` (stdin password) when a password is configured, or
        ``sudo -n`` (non-interactive / passwordless) otherwise so the
        subprocess never hangs waiting for a TTY password prompt.
        """
        stripped = command.strip()
        if not self.sudo_mode or stripped.startswith("sudo ") or platform.system() == "Windows":
            return command

        if self.sudo_password:
            # -S reads password from stdin; runner feeds it via proc.communicate()
            return f"sudo -S {stripped}"
        else:
            # -n = non-interactive; fails instantly if a password is required
            return f"sudo -n {stripped}"

    def _feed_sudo_password(self) -> Optional[str]:
        """Return the password string to feed to ``sudo -S`` via stdin, or None."""
        if self.sudo_mode and self.sudo_password:
            return self.sudo_password + "\n"
        return None

    def check_sudo(self) -> tuple[bool, str]:
        """Validate that sudo access works before running any commands.

        Returns (ok, message).  Sets ``_sudo_validated`` on success so the
        check is only performed once per runner lifetime.
        """
        if not self.sudo_mode:
            return True, "sudo not required"

        if self._sudo_validated:
            return True, "sudo already validated"

        if platform.system() == "Windows":
            return True, "sudo not required"

        try:
            if self.sudo_password:
                proc = subprocess.Popen(
                    ["sudo", "-S", "-v"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                _, stderr = proc.communicate(input=self.sudo_password + "\n", timeout=10)
            else:
                proc = subprocess.Popen(
                    ["sudo", "-n", "true"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                _, stderr = proc.communicate(timeout=10)

            if proc.returncode == 0:
                self._sudo_validated = True
                return True, "sudo access validated"
            else:
                hint = (
                    "Set sudo_password in config or run 'sudo -v' before starting HackBot"
                    if not self.sudo_password
                    else "Incorrect sudo password"
                )
                return False, f"sudo authentication failed — {hint}"
        except subprocess.TimeoutExpired:
            return False, "sudo validation timed out"
        except FileNotFoundError:
            return False, "sudo command not found"
        except Exception as e:
            return False, f"sudo check error: {e}"

    def _is_pipeline(self, command: str) -> bool:
        """Return True if *command* is a multi-stage pipeline."""
        try:
            tokens = self._split_command(command)
        except ValueError:
            return False
        return "|" in tokens

    def _execute_pipeline(
        self, command: str, tool_name: str = "", explanation: str = "",
    ) -> ToolResult:
        """Execute a piped command as chained subprocesses (no shell)."""
        start = time.time()
        try:
            stages = self._split_pipeline(command)
        except ValueError as e:
            return ToolResult(
                tool=self._infer_tool_name(command, tool_name),
                command=command,
                stdout="",
                stderr=f"Pipeline parse error: {e}",
                return_code=-4,
                duration=time.time() - start,
                success=False,
            )

        is_windows = platform.system() == "Windows"
        procs: list = []
        try:
            for i, stage in enumerate(stages):
                args = stage if is_windows else shlex.split(stage)
                stdin_src = procs[-1].stdout if procs else None
                # Only the first stage may receive sudo password via stdin
                stdin_data_for_stage = None
                if i == 0 and "sudo -S" in stage:
                    stdin_src = subprocess.PIPE
                    stdin_data_for_stage = self._feed_sudo_password()

                proc = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=stdin_src if stdin_src else (
                        subprocess.PIPE if stdin_data_for_stage else None
                    ),
                    shell=False,
                    text=True,
                    env=self._get_env(),
                )
                # Feed sudo password to the first stage if needed
                if stdin_data_for_stage and i == 0 and proc.stdin:
                    proc.stdin.write(stdin_data_for_stage)
                    proc.stdin.close()

                # Close the previous proc's stdout so it can receive SIGPIPE
                if procs and procs[-1].stdout:
                    procs[-1].stdout.close()

                procs.append(proc)

            # Read output from last process
            last_proc = procs[-1]
            try:
                stdout, stderr = last_proc.communicate(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                for p in procs:
                    self._kill_process(p)
                stdout, stderr = "", f"[TIMEOUT after {self.timeout}s]"

            # Wait for all procs
            for p in procs[:-1]:
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._kill_process(p)

            # Collect stderr from all stages
            all_stderr = []
            for i, p in enumerate(procs[:-1]):
                try:
                    _, stage_err = p.communicate(timeout=2)
                    if stage_err and stage_err.strip():
                        all_stderr.append(f"[stage {i+1}] {stage_err.strip()}")
                except Exception:
                    pass
            if stderr and stderr.strip():
                all_stderr.append(stderr.strip())
            combined_stderr = "\n".join(all_stderr)

            duration = time.time() - start
            stdout, truncated = self._truncate_output(stdout)

            result = ToolResult(
                tool=self._infer_tool_name(command, tool_name),
                command=command,
                stdout=stdout,
                stderr=combined_stderr,
                return_code=last_proc.returncode,
                duration=duration,
                success=last_proc.returncode == 0,
                truncated=truncated,
            )

        except FileNotFoundError:
            duration = time.time() - start
            result = ToolResult(
                tool=self._infer_tool_name(command, tool_name),
                command=command,
                stdout="",
                stderr=f"Tool not found in pipeline: {self._infer_tool_name(command, tool_name)}",
                return_code=-3,
                duration=duration,
                success=False,
            )
        except Exception as e:
            duration = time.time() - start
            result = ToolResult(
                tool=self._infer_tool_name(command, tool_name),
                command=command,
                stdout="",
                stderr=f"Pipeline execution error: {str(e)}",
                return_code=-4,
                duration=duration,
                success=False,
            )

        self.history.append(result)
        self._log_execution(result)
        if self.on_output:
            self.on_output(result.output)
        return result

    def execute(
        self, command: str, tool_name: str = "", explanation: str = "",
        allow_install_drivers: bool = False,
    ) -> ToolResult:
        """
        Execute a command synchronously with timeout and output capture.
        Supports piped commands (e.g. ``nmap ... | grep open``) by chaining
        subprocesses without invoking a shell.
        """
        command = self._normalize_command(command)

        # Plugin execution — intercept hackbot-plugin commands
        if command.strip().startswith("hackbot-plugin "):
            return self._execute_plugin(command, tool_name)

        # Apply sudo prefix if enabled
        command = self._apply_sudo(command)

        # Validate
        is_safe, reason = self.validate_command(
            command, allow_install_drivers=allow_install_drivers,
        )

        if not is_safe:
            return ToolResult(
                tool=self._infer_tool_name(command, tool_name),
                command=command,
                stdout="",
                stderr=f"BLOCKED: {reason}",
                return_code=-1,
                duration=0,
                success=False,
            )

        # Check for risky commands
        if "RISKY" in reason and not self.auto_confirm:
            if self.on_confirm:
                confirmed = self.on_confirm(command, reason)
                if not confirmed:
                    return ToolResult(
                        tool=self._infer_tool_name(command, tool_name),
                        command=command,
                        stdout="",
                        stderr="User declined execution",
                        return_code=-2,
                        duration=0,
                        success=False,
                    )

        # ── Pipeline execution (piped commands) ──────────────────────
        if self._is_pipeline(command):
            return self._execute_pipeline(command, tool_name=tool_name, explanation=explanation)

        # ── Single command execution ─────────────────────────────────
        start = time.time()
        stdin_data = self._feed_sudo_password() if "sudo -S" in command else None

        try:
            is_windows = platform.system() == "Windows"
            proc = subprocess.Popen(
                # Windows: pass the raw string to CreateProcess (no cmd.exe, so
                # shell metacharacters are NOT interpreted). POSIX: split to argv.
                command if is_windows else shlex.split(command),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE if stdin_data else None,
                shell=False,
                text=True,
                env=self._get_env(),
            )

            try:
                stdout, stderr = proc.communicate(input=stdin_data, timeout=self.timeout)
            except subprocess.TimeoutExpired:
                self._kill_process(proc)
                stdout, stderr = proc.communicate()
                stderr += f"\n[TIMEOUT after {self.timeout}s]"

            duration = time.time() - start

            # Truncate if needed
            stdout, truncated = self._truncate_output(stdout)

            result = ToolResult(
                tool=self._infer_tool_name(command, tool_name),
                command=command,
                stdout=stdout,
                stderr=stderr,
                return_code=proc.returncode,
                duration=duration,
                success=proc.returncode == 0,
                truncated=truncated,
            )

        except FileNotFoundError:
            duration = time.time() - start
            result = ToolResult(
                tool=self._infer_tool_name(command, tool_name),
                command=command,
                stdout="",
                stderr=f"Tool not found: {self._infer_tool_name(command, tool_name)}",
                return_code=-3,
                duration=duration,
                success=False,
            )
        except Exception as e:
            duration = time.time() - start
            result = ToolResult(
                tool=self._infer_tool_name(command, tool_name),
                command=command,
                stdout="",
                stderr=f"Execution error: {str(e)}",
                return_code=-4,
                duration=duration,
                success=False,
            )

        # Log and store
        self.history.append(result)
        self._log_execution(result)

        if self.on_output:
            self.on_output(result.output)

        return result

    async def execute_async(self, command: str, tool_name: str = "") -> ToolResult:
        """Execute a command asynchronously (shell-free; parity with execute())."""
        command = self._normalize_command(command)

        # Plugin execution — intercept hackbot-plugin commands
        if command.strip().startswith("hackbot-plugin "):
            return self._execute_plugin(command, tool_name)

        # Apply sudo prefix if enabled
        command = self._apply_sudo(command)

        # Validate
        is_safe, reason = self.validate_command(command)
        if not is_safe:
            return ToolResult(
                tool=self._infer_tool_name(command, tool_name),
                command=command,
                stdout="",
                stderr=f"BLOCKED: {reason}",
                return_code=-1,
                duration=0,
                success=False,
            )

        # Check for risky commands
        if "RISKY" in reason and not self.auto_confirm:
            if self.on_confirm:
                confirmed = self.on_confirm(command, reason)
                if not confirmed:
                    return ToolResult(
                        tool=self._infer_tool_name(command, tool_name),
                        command=command,
                        stdout="",
                        stderr="User declined execution",
                        return_code=-2,
                        duration=0,
                        success=False,
                    )

        # Pipeline execution — delegate to sync pipeline executor in a thread
        if self._is_pipeline(command):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._execute_pipeline, command, tool_name,
            )

        start = time.time()
        stdin_data = self._feed_sudo_password() if "sudo -S" in command else None

        # Tokenize without a shell so /bin/sh is never invoked (parity with execute()).
        try:
            args = shlex.split(command)
        except ValueError as e:
            result = ToolResult(
                tool=self._infer_tool_name(command, tool_name),
                command=command,
                stdout="",
                stderr=f"Execution error: {e}",
                return_code=-4,
                duration=time.time() - start,
                success=False,
            )
            self.history.append(result)
            self._log_execution(result)
            if self.on_output:
                self.on_output(result.output)
            return result

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE if stdin_data else None,
                env=self._get_env(),
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(input=stdin_data.encode() if stdin_data else None),
                    timeout=self.timeout,
                )
                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")
            except asyncio.TimeoutError:
                proc.kill()
                stdout, stderr = "", f"[TIMEOUT after {self.timeout}s]"

            duration = time.time() - start

            # Truncate if needed
            stdout, truncated = self._truncate_output(stdout)

            result = ToolResult(
                tool=self._infer_tool_name(command, tool_name),
                command=command,
                stdout=stdout,
                stderr=stderr,
                return_code=proc.returncode or 0,
                duration=duration,
                success=(proc.returncode or 0) == 0,
                truncated=truncated,
            )
        except FileNotFoundError:
            duration = time.time() - start
            result = ToolResult(
                tool=self._infer_tool_name(command, tool_name),
                command=command,
                stdout="",
                stderr=f"Tool not found: {self._infer_tool_name(command, tool_name)}",
                return_code=-3,
                duration=duration,
                success=False,
            )
        except Exception as e:
            duration = time.time() - start
            result = ToolResult(
                tool=self._infer_tool_name(command, tool_name),
                command=command,
                stdout="",
                stderr=f"Execution error: {str(e)}",
                return_code=-4,
                duration=duration,
                success=False,
            )

        self.history.append(result)
        self._log_execution(result)
        if self.on_output:
            self.on_output(result.output)
        return result

    def _truncate_output(self, stdout: str) -> tuple[str, bool]:
        """Cap *stdout* at MAX_OUTPUT_SIZE. Returns (text, truncated)."""
        if len(stdout) <= self.MAX_OUTPUT_SIZE:
            return stdout, False
        notice = f"\n\n[OUTPUT TRUNCATED at {self.MAX_OUTPUT_SIZE} bytes]"
        return stdout[: self.MAX_OUTPUT_SIZE] + notice, True

    def _get_env(self) -> Dict[str, str]:
        """Get sanitized environment for subprocess execution."""
        env = os.environ.copy()
        # Remove sensitive vars from subprocess env
        for key in ["HACKBOT_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
            env.pop(key, None)
        return env

    def _kill_process(self, proc: subprocess.Popen) -> None:
        """Cross-platform process killing."""
        try:
            if platform.system() == "Windows":
                proc.kill()
            else:
                pid = proc.pid
                pgid = os.getpgid(pid)
                if pgid == os.getpgrp():
                    # Same process group! Do NOT killpg, otherwise we kill ourselves.
                    # Just kill the process itself.
                    proc.terminate()
                    time.sleep(1)
                    if proc.poll() is None:
                        proc.kill()
                else:
                    os.killpg(pgid, signal.SIGTERM)
                    time.sleep(1)
                    if proc.poll() is None:
                        os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except Exception:
                pass

    def _log_execution(self, result: ToolResult) -> None:
        """Log tool execution to disk."""
        try:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            log_file = LOGS_DIR / "execution.log"
            with open(log_file, "a") as f:
                ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(result.timestamp))
                f.write(
                    f"[{ts}] [{result.tool}] rc={result.return_code} "
                    f"t={result.duration:.1f}s cmd={result.command}\n"
                )
        except Exception:
            pass

    def get_available_tools(self) -> Dict[str, bool]:
        """Get all allowed tools and their availability status."""
        return {tool: self.is_tool_available(tool) for tool in self.allowed_tools}

    def _execute_plugin(self, command: str, tool_name: str = "") -> ToolResult:
        """
        Execute a hackbot-plugin command by delegating to the PluginManager.

        Command format: hackbot-plugin <name> [--arg1 val1 --arg2 val2 ...]
        """
        start = time.time()
        parts = command.strip().split()
        # parts[0] = "hackbot-plugin", parts[1] = plugin_name, rest = --key val pairs
        if len(parts) < 2:
            return ToolResult(
                tool=tool_name or "hackbot-plugin",
                command=command,
                stdout="",
                stderr="Usage: hackbot-plugin <name> [--arg value ...]",
                return_code=-1,
                duration=0,
                success=False,
            )

        plugin_name = parts[1]
        # Parse --key value pairs
        kwargs: Dict[str, str] = {}
        i = 2
        while i < len(parts):
            token = parts[i]
            if token.startswith("--") and i + 1 < len(parts):
                key = token[2:]  # strip --
                kwargs[key] = parts[i + 1]
                i += 2
            else:
                i += 1

        pm = _get_plugin_manager()
        if pm is None:
            duration = time.time() - start
            return ToolResult(
                tool=tool_name or plugin_name,
                command=command,
                stdout="",
                stderr="Plugin system is not available",
                return_code=-1,
                duration=duration,
                success=False,
            )

        result = pm.execute(plugin_name, **kwargs)
        duration = time.time() - start

        tool_result = ToolResult(
            tool=tool_name or plugin_name,
            command=command,
            stdout=result.output if result.success else "",
            stderr=result.error if not result.success else "",
            return_code=0 if result.success else -1,
            duration=duration,
            success=result.success,
        )

        self.history.append(tool_result)
        self._log_execution(tool_result)

        if self.on_output:
            self.on_output(tool_result.output)

        return tool_result
