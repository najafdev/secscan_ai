#!/usr/bin/env python3
"""
SecScan AI installation readiness checks.

The default profile checks the legacy application's core local prerequisites and
reports optional workstation capabilities separately. ``--ci`` is deterministic
and offline: it never calls external AI APIs, never requires Ollama, and only
requires the system tools installed by the CI workflow.
"""

import argparse
import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

CORE_IMPORTS = {
    "requests": "requests",
    "openai": "openai",
    "rich": "rich",
    "python-dotenv": "dotenv",
    "SpeechRecognition": "speech_recognition",
    "pyttsx3": "pyttsx3",
    "pypandoc": "pypandoc",
    "Flask": "flask",
    "flask-cors": "flask_cors",
    "redis": "redis",
    "psycopg2": "psycopg2",
    "SQLAlchemy": "sqlalchemy",
    "Celery": "celery",
    "docker": "docker",
    "kubernetes": "kubernetes",
    "python-consul": "consul",
    "PyJWT": "jwt",
    "bcrypt": "bcrypt",
    "ldap3": "ldap3",
    "psutil": "psutil",
    "numpy": "numpy",
    "pandas": "pandas",
    "matplotlib": "matplotlib",
    "seaborn": "seaborn",
    "scikit-learn": "sklearn",
    "websockets": "websockets",
    "aiohttp": "aiohttp",
}

CI_REQUIRED_TOOLS = ("nmap", "nikto", "gobuster")
OPTIONAL_WORKSTATION_TOOLS = (
    "masscan",
    "sqlmap",
    "hydra",
    "theharvester",
    "enum4linux",
    "whatweb",
)


def _print_result(ok, label):
    print("  {0} {1}".format("OK" if ok else "MISSING", label))


def test_python_dependencies(imports=None):
    """Import the packages used directly by the legacy entry point."""
    print("Testing Python dependencies...")
    imports = CORE_IMPORTS if imports is None else imports
    missing = []
    for package_name, module_name in imports.items():
        try:
            importlib.import_module(module_name)
            _print_result(True, package_name)
        except (ImportError, ModuleNotFoundError):
            missing.append(package_name)
            _print_result(False, package_name)
    return not missing, missing


def test_system_tools(
    required_tools=CI_REQUIRED_TOOLS, optional_tools=OPTIONAL_WORKSTATION_TOOLS
):
    """Require the CI-provisioned tools and report broader workstation tools."""
    print("\nTesting system tools...")
    missing = []
    for tool in required_tools:
        found = shutil.which(tool) is not None
        _print_result(found, tool)
        if not found:
            missing.append(tool)

    for tool in optional_tools:
        found = shutil.which(tool) is not None
        status = "available" if found else "optional/unavailable"
        print("  INFO {0}: {1}".format(tool, status))

    return not missing, missing


def test_ollama(required=False):
    """Check a local Ollama daemon without requiring it unless explicitly requested."""
    print("\nChecking optional local AI (Ollama)...")
    ollama = shutil.which("ollama")
    if not ollama:
        print(
            "  INFO Ollama is not installed; deterministic/no-AI operation remains available."
        )
        return (not required), ([] if not required else ["ollama"])

    try:
        result = subprocess.run(
            [ollama, "list"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        if required:
            return False, ["ollama: {0}".format(exc)]
        print("  INFO Ollama could not be queried: {0}".format(exc))
        return True, []

    if result.returncode != 0:
        if required:
            return False, ["ollama list returned {0}".format(result.returncode)]
        print(
            "  INFO Ollama is installed but unavailable; no-AI operation remains available."
        )
        return True, []

    model_lines = [line for line in result.stdout.splitlines()[1:] if line.strip()]
    print("  OK Ollama responded; {0} model row(s) reported.".format(len(model_lines)))
    if required and not model_lines:
        return False, ["ollama has no locally listed model"]
    return True, []


def test_permissions(project_root=PROJECT_ROOT, require_reports=False):
    """Validate repository-local paths; never assume an absolute /reports directory."""
    print("\nTesting local paths and permissions...")
    project_root = Path(project_root)
    issues = []

    script_path = project_root / "secscan_ai.py"
    script_ok = script_path.is_file()
    _print_result(script_ok, str(script_path))
    if not script_ok:
        issues.append("missing secscan_ai.py")

    if require_reports:
        reports_dir = project_root / "reports"
        reports_ok = reports_dir.is_dir() and os.access(str(reports_dir), os.W_OK)
        _print_result(reports_ok, str(reports_dir))
        if not reports_ok:
            issues.append("repository reports directory is missing or not writable")
    else:
        writable = project_root.is_dir() and os.access(str(project_root), os.W_OK)
        _print_result(writable, "repository working directory is writable")
        if not writable:
            issues.append("repository working directory is not writable")

    return not issues, issues


def test_external_api_configuration():
    """Report external inference configuration without sending a paid/network request."""
    print("\nChecking optional external AI configuration...")
    if os.getenv("OPENAI_API_KEY"):
        print("  INFO OPENAI_API_KEY is configured; no network request was sent.")
    else:
        print("  INFO no external AI credential configured.")
    return True, []


def _subprocess_detail(result, fallback="legacy import failed"):
    """Return bounded diagnostics without allowing stderr warnings to hide stdout errors."""
    parts = []
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    if stdout:
        parts.append("stdout:\n{0}".format(stdout))
    if stderr:
        parts.append("stderr:\n{0}".format(stderr))
    detail = "\n".join(parts) or fallback
    return detail[-2000:]


def run_basic_functionality_test(project_root=PROJECT_ROOT):
    """Import the legacy public entry points in an isolated subprocess."""
    print("\nTesting legacy entry-point imports...")
    code = (
        "from secscan_ai import SecScanAI, AIEngine, ToolManager; "
        "print('SecScan AI legacy imports successful')"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, ["legacy import smoke: {0}".format(exc)]

    if result.returncode != 0:
        return False, [_subprocess_detail(result)]

    print("  OK SecScan AI, AIEngine and ToolManager import successfully.")
    return True, []


def build_checks(ci=False, require_ollama=False, require_reports=False):
    """Return the named checks for the selected profile."""
    checks = [
        ("Python Dependencies", test_python_dependencies),
        ("System Tools", test_system_tools),
        (
            "Permissions",
            lambda: test_permissions(require_reports=(require_reports and not ci)),
        ),
        ("Legacy Import Smoke", run_basic_functionality_test),
    ]
    if not ci:
        checks.extend(
            [
                ("Local AI (Ollama)", lambda: test_ollama(required=require_ollama)),
                ("External AI Configuration", test_external_api_configuration),
            ]
        )
    return checks


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate SecScan AI local prerequisites")
    parser.add_argument(
        "--ci",
        action="store_true",
        help="run deterministic offline checks suitable for GitHub Actions",
    )
    parser.add_argument(
        "--require-ollama",
        action="store_true",
        help="fail the default profile if Ollama and at least one local model are unavailable",
    )
    parser.add_argument(
        "--require-reports",
        action="store_true",
        help="require the repository-local reports directory to exist and be writable",
    )
    args = parser.parse_args(argv)

    profile = "CI/offline" if args.ci else "local/core"
    print("SecScan AI Installation Readiness Checks ({0})".format(profile))
    print("=" * 52)

    all_issues = []
    for test_name, test_func in build_checks(
        ci=args.ci,
        require_ollama=args.require_ollama,
        require_reports=args.require_reports,
    ):
        passed, issues = test_func()
        if not passed:
            all_issues.extend("{0}: {1}".format(test_name, issue) for issue in issues)

    print("\n" + "=" * 52)
    if all_issues:
        print("Required checks failed:")
        for issue in all_issues:
            print("  - {0}".format(issue))
        return 1

    print("Required checks passed.")
    if args.ci:
        print(
            "Optional scanners, Ollama and external provider access were not required."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
