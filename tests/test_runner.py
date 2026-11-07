"""Tests for HackBot Tool Runner."""

import asyncio
import platform
import shlex
import subprocess
import sys

import pytest

from hackbot.core.runner import ToolResult, ToolRunner


def _python_print_command(text):
    """Build a shell-free command that prints text using the active Python."""
    args = [sys.executable, "-c", f"print({text!r})"]
    if platform.system() == "Windows":
        return subprocess.list2cmdline(args)
    return shlex.join(args)


@pytest.fixture
def runner():
    """Create a tool runner with test configuration."""
    return ToolRunner(
        allowed_tools=["echo", "cat", "ls", "nmap", "python3", sys.executable, "curl", "ping"],
        timeout=10,
        safe_mode=True,
        auto_confirm=False,
    )


def test_tool_validation_allowed(runner):
    """Test that allowed commands pass validation."""
    is_safe, reason = runner.validate_command("echo hello")
    assert is_safe
    assert reason == "OK"


def test_tool_validation_blocked(runner):
    """Test that disallowed tools are blocked."""
    is_safe, reason = runner.validate_command("metasploit some-args")
    assert not is_safe
    assert "not in the allowed list" in reason


def test_blocked_commands(runner):
    """Test that dangerous commands are blocked."""
    for blocked in ["rm -rf /", "mkfs something"]:
        is_safe, reason = runner.validate_command(blocked)
        assert not is_safe, f"Should block: {blocked}"


def test_execute_simple_command(runner):
    """Test executing a simple command."""
    result = runner.execute(_python_print_command("hackbot_test"), tool_name="python")
    assert result.success
    assert "hackbot_test" in result.stdout
    assert result.return_code == 0
    assert result.duration >= 0


def test_execute_nonexistent_tool(runner):
    """Test executing a nonexistent tool."""
    runner.allowed_tools.append("nonexistent_tool_abc")
    result = runner.execute("nonexistent_tool_abc", tool_name="nonexistent_tool_abc")
    assert not result.success


def test_execute_with_timeout(runner):
    """Test timeout handling."""
    runner.timeout = 2
    if platform.system() != "Windows":
        result = runner.execute("ping -c 100 127.0.0.1", tool_name="ping")
        # Should either timeout or succeed quickly
        assert isinstance(result, ToolResult)


def test_tool_result_output():
    """Test ToolResult output property."""
    result = ToolResult(
        tool="test",
        command="test cmd",
        stdout="hello\n",
        stderr="",
        return_code=0,
        duration=1.0,
        success=True,
    )
    assert "hello" in result.output


def test_tool_result_combined_output():
    """Test ToolResult with both stdout and stderr."""
    result = ToolResult(
        tool="test",
        command="test cmd",
        stdout="output\n",
        stderr="warning\n",
        return_code=0,
        duration=1.0,
        success=True,
    )
    assert "output" in result.output
    assert "warning" in result.output


def test_empty_command(runner):
    """Test empty command handling."""
    is_safe, reason = runner.validate_command("")
    assert not is_safe


def test_history_tracking(runner):
    """Test that execution history is tracked."""
    runner.execute("echo test1", tool_name="echo")
    runner.execute("echo test2", tool_name="echo")
    assert len(runner.history) == 2


def test_get_available_tools(runner):
    """Test tool availability detection."""
    tools = runner.get_available_tools()
    assert isinstance(tools, dict)
    assert "echo" in tools


def test_sudo_mode_disabled():
    """Test that sudo_mode=False does not modify commands."""
    r = ToolRunner(
        allowed_tools=["echo"],
        timeout=10,
        safe_mode=False,
        sudo_mode=False,
    )
    assert r._apply_sudo("echo hello") == "echo hello"


def test_sudo_mode_enabled():
    """Test that sudo_mode=True prepends sudo -n (non-interactive) to commands."""
    r = ToolRunner(
        allowed_tools=["echo"],
        timeout=10,
        safe_mode=False,
        sudo_mode=True,
    )
    if platform.system() != "Windows":
        # Without password: uses sudo -n (non-interactive, fails if password needed)
        assert r._apply_sudo("echo hello") == "sudo -n echo hello"
        # Should not double-prefix
        assert r._apply_sudo("sudo echo hello") == "sudo echo hello"

    # With password: uses sudo -S (reads password from stdin)
    r2 = ToolRunner(
        allowed_tools=["echo"],
        timeout=10,
        safe_mode=False,
        sudo_mode=True,
        sudo_password="secret",
    )
    if platform.system() != "Windows":
        assert r2._apply_sudo("echo hello") == "sudo -S echo hello"
        assert r2._apply_sudo("sudo echo hello") == "sudo echo hello"
        assert r2._feed_sudo_password() == "secret\n"

    # Password not fed when sudo_mode off
    r3 = ToolRunner(
        allowed_tools=["echo"],
        timeout=10,
        safe_mode=False,
        sudo_mode=False,
        sudo_password="secret",
    )
    assert r3._apply_sudo("echo hello") == "echo hello"


def test_check_sudo_not_needed():
    """check_sudo returns OK when sudo_mode is off."""
    r = ToolRunner(allowed_tools=["echo"], timeout=10, safe_mode=False, sudo_mode=False)
    ok, msg = r.check_sudo()
    assert ok
    assert "not required" in msg


def test_check_sudo_caches_result():
    """check_sudo only validates once per runner lifetime."""
    r = ToolRunner(allowed_tools=["echo"], timeout=10, safe_mode=False, sudo_mode=True)
    r._sudo_validated = True  # Simulate prior success
    ok, msg = r.check_sudo()
    assert ok
    assert "already validated" in msg


def test_validate_command_with_sudo_prefix(runner):
    """Test that validate_command handles sudo-prefixed commands correctly."""
    is_safe, reason = runner.validate_command("sudo nmap -sV target")
    assert is_safe
    assert reason == "OK"


def test_validate_command_with_sudo_flag_prefix(runner):
    """sudo flags like -n should not be treated as the executable."""
    is_safe, reason = runner.validate_command("sudo -n nmap -sV target")
    assert is_safe
    assert reason == "OK"


def test_validate_command_with_sudo_end_of_options(runner):
    """sudo '--' end-of-options marker should still resolve the real tool."""
    is_safe, reason = runner.validate_command("sudo -- nmap -sV target")
    assert is_safe
    assert reason == "OK"


def test_validate_command_with_backticks_and_prompt(runner):
    """Backticks and shell prompt prefixes should not break validation."""
    is_safe, reason = runner.validate_command("`$ nmap -sV 127.0.0.1`")
    assert is_safe
    assert reason == "OK"


def test_tool_allowed_case_insensitive():
    """Allowed tool checks should be case-insensitive."""
    r = ToolRunner(allowed_tools=["nmap", "curl"], timeout=10)
    assert r.is_tool_allowed("NMAP")
    assert r.is_tool_allowed("nmap")


def test_tool_allowed_via_resolved_alias(monkeypatch):
    """Alias binary (alive6) should be allowed when thc-ipv6 is whitelisted."""
    r = ToolRunner(allowed_tools=["thc-ipv6"], timeout=10)

    def fake_resolve(tool: str):
        if tool == "thc-ipv6":
            return "/usr/bin/alive6"
        return None

    monkeypatch.setattr("hackbot.core.runner.resolve_tool_path", fake_resolve)
    assert r.is_tool_allowed("alive6")


# ── New tests for double-sudo, malformed commands, and sudo stripping ──


def test_validate_double_sudo_command(runner):
    """Double-sudo commands should be normalized and the real tool extracted."""
    is_safe, reason = runner.validate_command("sudo -n nmap -sV 192.168.1.1")
    assert is_safe
    assert reason == "OK"


def test_validate_nested_sudo(runner):
    """Nested sudo (sudo -n sudo -n nmap) should resolve to the real tool."""
    is_safe, reason = runner.validate_command("sudo -n sudo -n nmap -sV target")
    assert is_safe
    assert reason == "OK"


def test_validate_malformed_flags_only():
    """Command with only flags and no tool binary should be rejected."""
    r = ToolRunner(allowed_tools=["nmap", "dnsrecon"], timeout=10)
    is_safe, reason = r.validate_command("--target 192.168.1.1 --output json")
    assert not is_safe


def test_strip_sudo_prefix():
    """_strip_sudo_prefix should remove sudo and its flags."""
    assert ToolRunner._strip_sudo_prefix("sudo -n nmap -sV target") == "nmap -sV target"
    assert ToolRunner._strip_sudo_prefix("sudo -S nmap 10.0.0.1") == "nmap 10.0.0.1"
    assert ToolRunner._strip_sudo_prefix("sudo nmap 10.0.0.1") == "nmap 10.0.0.1"
    assert ToolRunner._strip_sudo_prefix("sudo -n -u root nmap 10.0.0.1") == "nmap 10.0.0.1"
    assert ToolRunner._strip_sudo_prefix("nmap 10.0.0.1") == "nmap 10.0.0.1"  # no-op
    assert ToolRunner._strip_sudo_prefix("sudo -- nmap 10.0.0.1") == "nmap 10.0.0.1"


def test_normalize_strips_sudo(runner):
    """_normalize_command should strip AI-generated sudo prefix."""
    assert runner._normalize_command("sudo -n nmap -sV 10.0.0.1") == "nmap -sV 10.0.0.1"
    assert runner._normalize_command("sudo -S dnsrecon -d example.com") == "dnsrecon -d example.com"


def test_validate_sudo_only_no_tool():
    """sudo with only flags and no actual tool should be rejected."""
    r = ToolRunner(allowed_tools=["nmap"], timeout=10)
    is_safe, reason = r.validate_command("sudo -n")
    assert not is_safe


# ── Shell-free execution & metacharacter rejection ──


def test_windows_exec_is_shell_free(runner, monkeypatch):
    """execute() must never spawn a shell (guards against shell=is_windows)."""
    captured = {}

    class FakePopen:
        def __init__(self, *args, **kwargs):
            captured["shell"] = kwargs.get("shell")
            self.returncode = 0

        def communicate(self, input=None, timeout=None):
            return ("ok", "")

    monkeypatch.setattr("hackbot.core.runner.subprocess.Popen", FakePopen)
    runner.execute("echo hi", tool_name="echo")
    assert captured["shell"] is False


def test_validate_rejects_semicolon_operator(runner):
    """Command chaining with ';' is rejected as a shell metacharacter."""
    is_safe, reason = runner.validate_command("echo a ; echo b")
    assert not is_safe
    assert "metacharacter" in reason.lower()
    assert "';'" in reason


def test_validate_rejects_pipe_operator(runner):
    """A pipe operator command is validated stage-by-stage."""
    # When a tool in the pipeline is not allowed, it's rejected
    is_safe, reason = runner.validate_command("nmap 127.0.0.1 | grep open")
    assert not is_safe
    assert "grep" in reason.lower()

    # When all tools in the pipeline are allowed, it's accepted
    is_safe2, reason2 = runner.validate_command("echo hello | cat")
    assert is_safe2
    assert reason2 == "OK"


def test_execute_pipeline(runner):
    """Test executing a pipeline with two allowed commands."""
    if platform.system() != "Windows":
        result = runner.execute("echo 'piped_test_data' | cat", tool_name="echo")
        assert result.success
        assert "piped_test_data" in result.stdout


def test_validate_rejects_and_operator(runner):
    """Logical-and chaining is rejected."""
    is_safe, reason = runner.validate_command("echo a && echo b")
    assert not is_safe
    assert "&&" in reason


def test_validate_rejects_redirect_operator(runner):
    """Output redirection is rejected."""
    is_safe, reason = runner.validate_command("nmap 127.0.0.1 > /tmp/out")
    assert not is_safe
    assert ">" in reason


def test_validate_rejects_command_substitution_dollar_paren(runner):
    """$(...) command substitution is rejected."""
    is_safe, reason = runner.validate_command("nmap $(whoami)")
    assert not is_safe
    assert "$(" in reason


def test_validate_rejects_embedded_backticks(runner):
    """Embedded backtick substitution is rejected (distinct from wrapping backticks)."""
    is_safe, reason = runner.validate_command("nmap `whoami`")
    assert not is_safe
    assert "`" in reason


def test_validate_allows_url_with_ampersand(runner):
    """A URL with '&'/'?'/'=' in a quoted arg is NOT flagged (token-based check)."""
    is_safe, reason = runner.validate_command("curl 'http://example.com/?a=1&b=2'")
    assert is_safe
    assert reason == "OK"
    is_safe2, _ = runner.validate_command('curl "http://example.com/?x=1&y=2"')
    assert is_safe2


def test_validate_rejects_unbalanced_quotes(runner):
    """Unbalanced quotes are rejected gracefully (no crash)."""
    is_safe, reason = runner.validate_command('nmap "unclosed')
    assert not is_safe
    assert "unbalanced" in reason.lower()


def test_chained_command_does_not_execute_second_half(runner, tmp_path):
    """The executor is shell-free: a chained command never runs its second half."""
    if platform.system() == "Windows":
        pytest.skip("POSIX-only shell-free proof")
    sentinel = tmp_path / "pwned"
    result = runner.execute(f"echo hi ; touch {sentinel}", tool_name="echo")
    # Blocked at validation, and the second command never ran.
    assert result.return_code == -1
    assert "metacharacter" in result.stderr.lower()
    assert not sentinel.exists()


def test_exec_does_not_interpolate_shell_variables(runner):
    """Content that passes validation is still not shell-interpolated."""
    if platform.system() == "Windows":
        pytest.skip("POSIX-only shell-free proof")
    result = runner.execute("echo $HOME", tool_name="echo")
    assert "$HOME" in result.stdout  # literal, not expanded


def test_execute_async_parity_blocked(runner):
    """execute_async runs validation and is shell-free (rejects chaining)."""
    result = asyncio.run(runner.execute_async("echo a ; echo b"))
    assert result.return_code == -1
    assert "metacharacter" in result.stderr.lower()


# ── Install-driver bypass tests ──


def test_install_driver_blocked_via_normal_execute():
    r = ToolRunner(allowed_tools=["nmap"])  # managers NOT allowed
    ok, reason = r.validate_command("apt-get install -y nmap")
    assert ok is False and "not in the allowed list" in reason
    ok, reason = r.validate_command("pip install requests")
    assert ok is False


def test_install_driver_allowed_with_flag():
    r = ToolRunner(allowed_tools=["nmap"])
    ok, reason = r.validate_command("apt-get install -y nmap", allow_install_drivers=True)
    assert ok is True
    ok, reason = r.validate_command("pip install requests", allow_install_drivers=True)
    assert ok is True


def test_install_driver_flag_does_not_allow_arbitrary_tool():
    # The bypass only whitelists install drivers, not any tool.
    r = ToolRunner(allowed_tools=["nmap"])
    ok, reason = r.validate_command("evilbinary --pwn", allow_install_drivers=True)
    assert ok is False


def test_normalize_command_strips_slash_commands(runner):
    """Test that trailing interactive slash commands are stripped from the command line."""
    cmd = runner._normalize_command("sudo -S nmap -sV -sC -T4 111.90.156.228 /cve")
    # sudo prefix is stripped by _strip_sudo_prefix in _normalize_command
    assert cmd == "nmap -sV -sC -T4 111.90.156.228"

    cmd2 = runner._normalize_command("nmap 127.0.0.1 /osint")
    assert cmd2 == "nmap 127.0.0.1"

    # Should not strip if it is not a trailing slash command
    cmd3 = runner._normalize_command("nmap 127.0.0.1 /notacommand")
    assert cmd3 == "nmap 127.0.0.1 /notacommand"


def test_normalize_command_fixes_dirb(runner):
    """Test that invalid dirb command syntax is auto-corrected."""
    cmd = runner._normalize_command("sudo -S dirb -a http://111.90.156.228")
    assert cmd == "dirb http://111.90.156.228"

    cmd2 = runner._normalize_command("dirb -a https://example.com")
    assert cmd2 == "dirb https://example.com"


def test_normalize_command_fixes_amass(runner):
    """Test that invalid amass command syntax is auto-corrected."""
    # Case A: Invalid flags / missing subcommands on IP target
    cmd1 = runner._normalize_command("sudo -S amass -a http://111.90.156.228")
    assert cmd1 == "amass intel -addr 111.90.156.228"

    # Case A: Invalid flags / missing subcommands on domain target
    cmd2 = runner._normalize_command("amass -a https://example.com/path")
    assert cmd2 == "amass enum -d example.com"

    # Case B: Correct subcommand but URL target
    cmd3 = runner._normalize_command("amass intel -addr http://111.90.156.228")
    assert cmd3 == "amass intel -addr 111.90.156.228"

    cmd4 = runner._normalize_command("amass enum -d https://example.com")
    assert cmd4 == "amass enum -d example.com"



