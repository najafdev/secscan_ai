# SecScan AI core module
"""ToolManager command execution (no shell=True)."""

import sys

import pytest


@pytest.fixture
def tool_manager():
    from advance_secscan_ai import ToolManager

    return ToolManager()


def test_run_command_simple_without_shell(tool_manager):
    result = tool_manager.run_command([sys.executable, "-c", "print('ok')"])
    assert result["success"] is True
    assert "ok" in result["stdout"]


def test_run_command_rejects_unsupported_metacharacters(tool_manager):
    result = tool_manager.run_command("echo hi; rm -rf /")
    assert result["success"] is False
    assert "Unsupported" in result["stderr"]


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX shlex pipeline parsing")
def test_run_command_pipe_without_shell(tool_manager):
    cmd = f"{sys.executable} -c \"print('pipe')\" | {sys.executable} -c \"import sys; print(sys.stdin.read().strip())\""
    result = tool_manager.run_command(cmd)
    assert result["success"] is True
    assert "pipe" in result["stdout"]


def test_pipeline_parser_preserves_quoted_pipe(tool_manager):
    result = tool_manager._split_pipeline('grep -E "foo|bar" file.txt')
    assert result == [["grep", "-E", "foo|bar", "file.txt"]]


def test_pipeline_parser_splits_only_unquoted_pipes(tool_manager):
    result = tool_manager._split_pipeline('cat file.txt | grep -E "foo|bar"')
    assert result == [["cat", "file.txt"], ["grep", "-E", "foo|bar"]]
