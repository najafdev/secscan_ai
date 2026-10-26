from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "Dockerfile"
INSTALLER = ROOT / "install.sh"
DOCKERIGNORE = ROOT / ".dockerignore"


def test_docker_build_uses_explicit_side_effect_free_install_context():
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    installer = INSTALLER.read_text(encoding="utf-8")

    assert "SECSCAN_AI_INSTALL_CONTEXT=container ./install.sh" in dockerfile
    assert 'INSTALL_CONTEXT="${SECSCAN_AI_INSTALL_CONTEXT:-host}"' in installer
    assert 'if [ "$INSTALL_CONTEXT" = "host" ]; then' in installer
    assert "apt-get upgrade -y" in installer
    assert "ollama pull llama2:7b" in installer
    assert "Container install: skipping full distribution upgrade" in installer
    assert (
        "Container install: skipping Ollama installer, daemon start and model download"
        in installer
    )


def test_docker_build_keeps_cached_requirements_layer_and_runtime_directories():
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    requirements_copy = dockerfile.index("COPY requirements.txt .")
    requirements_install = dockerfile.index("pip3 install -r requirements.txt")
    source_copy = dockerfile.index("COPY . .")
    assert requirements_copy < requirements_install < source_copy
    assert "/secscan_ai/logs" in dockerfile
    assert "/secscan_ai/reports" in dockerfile


def test_dockerignore_excludes_local_secrets_and_generated_state_but_keeps_template():
    entries = {
        line.strip()
        for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert ".env" in entries
    assert ".env.*" in entries
    assert "!.env.example" in entries
    assert "logs/" in entries
    assert "reports/" in entries
    assert "workspaces/" in entries
    assert ".git" in entries


def test_container_mode_does_not_change_host_mode_default():
    installer = INSTALLER.read_text(encoding="utf-8")

    assert "SECSCAN_AI_INSTALL_CONTEXT:-host" in installer
    assert "ROOT=(sudo)" in installer
    assert 'run_root ln -sf "$(pwd)/secscan_ai.py" /usr/local/bin/secscan_ai' in installer


def test_container_install_mode_has_no_model_download_or_privilege_escalation(tmp_path):
    import os
    import subprocess

    installer = tmp_path / "install.sh"
    installer.write_text(INSTALLER.read_text(encoding="utf-8"), encoding="utf-8")
    installer.chmod(0o755)

    for filename in (
        "secscan_ai.py",
        "secscan_ai_v2.py",
        "usage_examples.sh",
        "test_installation.py",
        "requirements.txt",
        "config.ini",
        ".env.example",
    ):
        (tmp_path / filename).write_text("# fixture\n", encoding="utf-8")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls.log"
    fake_commands = (("apt-get", 0), ("sudo", 91), ("curl", 92), ("ollama", 93))
    for command, exit_code in fake_commands:
        path = fake_bin / command
        path.write_text(
            "#!/bin/sh\n" f'echo "{command} $*" >> "{calls}"\n' f"exit {exit_code}\n",
            encoding="utf-8",
        )
        path.chmod(0o755)

    env = os.environ.copy()
    env["SECSCAN_AI_INSTALL_CONTEXT"] = "container"
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    completed = subprocess.run(
        ["bash", str(installer)],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    observed = calls.read_text(encoding="utf-8")
    assert "apt-get update" in observed
    assert "apt-get install -y" in observed
    observed_lines = observed.splitlines()
    assert not any(line.startswith("sudo ") for line in observed_lines)
    assert not any(line.startswith("curl ") for line in observed_lines)
    assert not any(line.startswith("ollama ") for line in observed_lines)
    assert (
        "skipping Ollama installer, daemon start and model download" in completed.stdout
    )


def test_host_install_mode_as_root_does_not_call_sudo(tmp_path):
    import os
    import subprocess

    installer = tmp_path / "install.sh"
    installer.write_text(INSTALLER.read_text(encoding="utf-8"), encoding="utf-8")
    installer.chmod(0o755)

    for filename in (
        "secscan_ai.py",
        "secscan_ai_v2.py",
        "usage_examples.sh",
        "test_installation.py",
        "requirements.txt",
        "config.ini",
        ".env.example",
    ):
        (tmp_path / filename).write_text("# fixture\n", encoding="utf-8")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls.log"

    # sudo exits with 91 so if it gets called, execution fails or records it
    fake_commands = (("apt-get", 0), ("sudo", 91), ("curl", 0), ("ollama", 0), ("pip", 0), ("pip3", 0))
    for command, exit_code in fake_commands:
        path = fake_bin / command
        path.write_text(
            "#!/bin/sh\n" f'echo "{command} $*" >> "{calls}"\n' f"exit {exit_code}\n",
            encoding="utf-8",
        )
        path.chmod(0o755)

    # Fake id command to simulate running as root (UID 0)
    fake_id = fake_bin / "id"
    fake_id.write_text("#!/bin/sh\necho 0\n", encoding="utf-8")
    fake_id.chmod(0o755)

    env = os.environ.copy()
    env["SECSCAN_AI_INSTALL_CONTEXT"] = "host"
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"

    completed = subprocess.run(
        ["bash", str(installer)],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    observed = calls.read_text(encoding="utf-8")
    observed_lines = observed.splitlines()
    assert any("apt-get update" in line for line in observed_lines)
    assert not any(line.startswith("sudo ") for line in observed_lines)

