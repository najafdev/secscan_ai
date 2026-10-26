import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _offline_env():
    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)
    env.pop("ANTHROPIC_API_KEY", None)
    return env


def test_ci_installation_profile_is_offline_and_succeeds():
    result = subprocess.run(
        [sys.executable, "test_installation.py", "--ci"],
        cwd=str(REPO_ROOT),
        env=_offline_env(),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CI/offline" in result.stdout
    assert (
        "Optional scanners, Ollama and external provider access were not required."
        in result.stdout
    )


def test_legacy_entrypoints_import_without_network_calls():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from secscan_ai import SecScanAI, AIEngine, ToolManager; print('ok')",
        ],
        cwd=str(REPO_ROOT),
        env=_offline_env(),
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ok" in result.stdout
