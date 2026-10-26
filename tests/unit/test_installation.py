import importlib.util
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parents[2] / "test_installation.py"
SPEC = importlib.util.spec_from_file_location("secscan_ai_install_checks", MODULE_PATH)
ti = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ti)


def test_dependency_aliases_use_real_import_names():
    imported = []

    def fake_import(name):
        imported.append(name)
        return object()

    with mock.patch.object(ti.importlib, "import_module", side_effect=fake_import):
        passed, missing = ti.test_python_dependencies(
            {
                "SpeechRecognition": "speech_recognition",
                "cvsslib": "cvsslib",
            }
        )

    assert passed
    assert missing == []
    assert imported == ["speech_recognition", "cvsslib"]


def test_runtime_dependency_table_includes_performance_monitor_requirement():
    assert ti.CORE_IMPORTS["psutil"] == "psutil"


def test_system_tools_only_fail_required_tools():
    availability = {
        "nmap": "/usr/bin/nmap",
        "nikto": "/usr/bin/nikto",
        "gobuster": "/usr/bin/gobuster",
        "masscan": None,
    }
    with mock.patch.object(
        ti.shutil, "which", side_effect=lambda name: availability.get(name)
    ):
        passed, missing = ti.test_system_tools(
            required_tools=("nmap", "nikto", "gobuster"),
            optional_tools=("masscan",),
        )

    assert passed
    assert missing == []


def test_missing_required_tool_fails():
    with mock.patch.object(ti.shutil, "which", return_value=None):
        passed, missing = ti.test_system_tools(
            required_tools=("nmap",),
            optional_tools=(),
        )

    assert not passed
    assert missing == ["nmap"]


def test_optional_ollama_absence_does_not_fail():
    with mock.patch.object(ti.shutil, "which", return_value=None):
        passed, missing = ti.test_ollama(required=False)

    assert passed
    assert missing == []


def test_required_ollama_absence_fails():
    with mock.patch.object(ti.shutil, "which", return_value=None):
        passed, missing = ti.test_ollama(required=True)

    assert not passed
    assert missing == ["ollama"]


def test_permissions_use_repository_relative_reports(tmp_path):
    (tmp_path / "secscan_ai.py").write_text("# test\n")
    (tmp_path / "reports").mkdir()

    passed, issues = ti.test_permissions(tmp_path, require_reports=True)

    assert passed
    assert issues == []
    assert (tmp_path / "reports").is_dir()


def test_permissions_return_real_issue_details(tmp_path):
    passed, issues = ti.test_permissions(tmp_path, require_reports=True)

    assert not passed
    assert "missing secscan_ai.py" in issues
    assert "repository reports directory is missing or not writable" in issues


def test_ci_profile_excludes_external_ai_and_ollama_checks():
    names = [name for name, _ in ti.build_checks(ci=True)]

    assert "Local AI (Ollama)" not in names
    assert "External AI Configuration" not in names
    assert "Legacy Import Smoke" in names


def test_basic_import_smoke_reports_subprocess_failure(tmp_path):
    result = mock.Mock(returncode=1, stdout="", stderr="missing dependency")
    with mock.patch.object(ti.subprocess, "run", return_value=result):
        passed, issues = ti.run_basic_functionality_test(project_root=Path(tmp_path))

    assert not passed
    assert issues == ["stderr:\nmissing dependency"]


def test_basic_import_smoke_preserves_stdout_error_when_stderr_has_optional_warnings(
    tmp_path,
):
    result = mock.Mock(
        returncode=1,
        stdout="Missing SecScan AI modules: No module named 'psutil'\n",
        stderr="WARNING:root:optional backend unavailable\n",
    )
    with mock.patch.object(ti.subprocess, "run", return_value=result):
        passed, issues = ti.run_basic_functionality_test(project_root=Path(tmp_path))

    assert not passed
    assert "No module named 'psutil'" in issues[0]
    assert "optional backend unavailable" in issues[0]
