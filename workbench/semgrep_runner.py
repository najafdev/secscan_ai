"""Pinned, local-only Semgrep CE project runner.

The runner is intentionally narrow: it executes one reviewed Semgrep CE container image
against one operator-selected project root mounted read-only. The scanner container has
no network, no target writes, no dynamic rule source and no model-selected command line.
The image must already exist locally; this module never pulls or updates it.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .adapters import MAX_OUTPUT_BYTES, parse_semgrep_json
from .contracts import ADAPTER_SCHEMA, normalize_adapter_result
from .execution_contracts import EXECUTION_SCHEMA, normalize_execution_declaration

ADAPTER_ID = "semgrep-project-local"
ADAPTER_VERSION = "1.177.0-r1"
TOOL_PIN_PATH = Path(__file__).resolve().parent / "tooling" / "semgrep-1.177.0.json"
RULES_PATH = Path(__file__).resolve().parent / "rules" / "semgrep_workbench.yml"
DEFAULT_EXCLUDED_DIRS = frozenset(
    {".git", ".hg", ".svn", "node_modules", "vendor", "dist", "build", "__pycache__"}
)
_STDERR_LIMIT = 65536


def _load_tool_pin() -> dict[str, Any]:
    try:
        document = json.loads(TOOL_PIN_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Semgrep tool pin is unavailable or invalid") from exc
    required = {
        "schema",
        "id",
        "version",
        "source_repository",
        "release_url",
        "license",
        "container",
        "rules",
    }
    if (
        not required.issubset(document)
        or document.get("schema") != "secscan_ai.tool-pin/v1"
        or document.get("id") != "semgrep-ce"
    ):
        raise RuntimeError("Semgrep tool pin does not match the reviewed contract")
    container = document.get("container")
    license_data = document.get("license")
    rules = document.get("rules")
    if (
        not isinstance(container, dict)
        or not isinstance(license_data, dict)
        or not isinstance(rules, dict)
    ):
        raise RuntimeError("Semgrep tool pin metadata is incomplete")
    if container.get("platform") != "linux/amd64" or not str(
        container.get("reference", "")
    ).startswith("semgrep/semgrep@sha256:"):
        raise RuntimeError(
            "Semgrep tool pin must identify the reviewed linux/amd64 image by digest"
        )
    if license_data.get("spdx") != "LGPL-2.1-or-later":
        raise RuntimeError("Semgrep tool pin has an unexpected engine license")
    if (
        rules.get("external_registry") is not False
        or rules.get("source") != "repository-authored"
    ):
        raise RuntimeError("Semgrep runner requires repository-authored offline rules")
    return document


TOOL_PIN = _load_tool_pin()
SEMGREP_VERSION = str(TOOL_PIN["version"])
SEMGREP_IMAGE = str(TOOL_PIN["container"]["reference"])
SEMGREP_IMAGE_DIGEST = str(TOOL_PIN["container"]["manifest_digest"])


@dataclass(frozen=True)
class SemgrepPolicy:
    """Operator-owned limits for the local Semgrep project scan."""

    max_files: int = 250
    max_depth: int = 12
    timeout_seconds: int = 90
    max_target_bytes: int = 500_000

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_files, bool)
            or not isinstance(self.max_files, int)
            or not 1 <= self.max_files <= 5000
        ):
            raise ValueError("max_files must be an integer from 1 to 5000")
        if (
            isinstance(self.max_depth, bool)
            or not isinstance(self.max_depth, int)
            or not 0 <= self.max_depth <= 16
        ):
            raise ValueError("max_depth must be an integer from 0 to 16")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, int)
            or not 1 <= self.timeout_seconds <= 300
        ):
            raise ValueError("timeout_seconds must be an integer from 1 to 300")
        if (
            isinstance(self.max_target_bytes, bool)
            or not isinstance(self.max_target_bytes, int)
            or not 1024 <= self.max_target_bytes <= 5_000_000
        ):
            raise ValueError("max_target_bytes must be an integer from 1024 to 5000000")


class SemgrepContainerAdapter:
    """Read-only Semgrep CE runner using one preinstalled digest-pinned container image."""

    identity = {"id": ADAPTER_ID, "version": ADAPTER_VERSION}

    def __init__(self, policy: SemgrepPolicy | None = None):
        self.policy = policy or SemgrepPolicy()

    @staticmethod
    def _check_cancel(cancel) -> None:
        if cancel is not None and cancel.is_set():
            raise InterruptedError("Semgrep project scan cancelled")

    def execution_declaration(self) -> dict[str, Any]:
        return normalize_execution_declaration(
            {
                "schema": EXECUTION_SCHEMA,
                "adapter": dict(self.identity),
                "launcher": "fixed_container",
                "effect_level": "read_only",
                "filesystem": "read_only_content",
                "network": "none",
                "subprocess": True,
                "writes": False,
                "follows_symlinks": False,
                "limits": {
                    "max_objects": self.policy.max_files,
                    "max_requests": 0,
                    "timeout_seconds": self.policy.timeout_seconds,
                },
                "coverage_unit": "semgrep_scanned_files",
            }
        )

    def plan_metadata(
        self, root: str | os.PathLike[str], *, asset_key: str
    ) -> dict[str, Any]:
        resolved = self._validate_root(root)
        return {
            "adapter_id": ADAPTER_ID,
            "asset_key": asset_key,
            "project_label": resolved.name or "project-root",
            "full_path_included": False,
            "tool": "semgrep-ce",
            "tool_version": SEMGREP_VERSION,
            "image_digest": SEMGREP_IMAGE_DIGEST,
            "ruleset": "repository-authored/workbench-v1",
            "container_network": "none",
            "source_mount": "read-only",
            "max_files": self.policy.max_files,
            "max_target_bytes": self.policy.max_target_bytes,
        }

    def run(
        self, root: str | os.PathLike[str], *, asset_key: str, cancel=None
    ) -> dict[str, Any]:
        self._check_cancel(cancel)
        if not sys.platform.startswith("linux"):
            raise RuntimeError(
                "Semgrep container execution is currently validated only on Linux"
            )
        resolved = self._validate_root(root)
        deadline = time.monotonic() + self.policy.timeout_seconds
        eligible = self._bounded_preflight(resolved, deadline=deadline, cancel=cancel)
        self._check_cancel(cancel)
        docker = self._docker_path()
        self._ensure_image_present(docker)
        self._check_cancel(cancel)
        if time.monotonic() >= deadline:
            raise TimeoutError("Semgrep project scan deadline reached before launch")

        container_name = "secscan_ai-semgrep-" + secrets.token_hex(6)
        command = self._build_command(docker, resolved, container_name)
        return_code, stdout = self._execute_docker(
            docker,
            command,
            container_name=container_name,
            deadline=deadline,
            cancel=cancel,
        )
        if return_code != 0:
            return normalize_adapter_result(
                {
                    "schema": ADAPTER_SCHEMA,
                    "adapter": dict(self.identity),
                    "status": "error",
                    "coverage": {
                        "objects_tested": 0,
                        "objects_total": eligible,
                        "notes": [
                            "Pinned Semgrep CE container exited unsuccessfully; raw diagnostic output is omitted.",
                            "The runner did not contact a scanner registry or assessment target.",
                        ],
                    },
                    "findings": [],
                    "error": f"Semgrep runner exited with code {return_code}",
                },
                asset_key=asset_key,
            )

        result = parse_semgrep_json(
            stdout, version=ADAPTER_VERSION, asset_key=asset_key, adapter_id=ADAPTER_ID
        )
        tested = result.get("coverage", {}).get("objects_tested")
        if type(tested) is int and tested > eligible:
            raise RuntimeError(
                "Semgrep reported more scanned files than the bounded preflight admitted"
            )
        coverage = result["coverage"]
        coverage["objects_total"] = eligible
        coverage["notes"].extend(
            [
                f"Semgrep CE {SEMGREP_VERSION} executed from a digest-pinned preinstalled container.",
                "Container network was disabled and the project plus repository-authored rules were mounted read-only.",
                "The scanner process used the calling Linux operator UID/GID so host file permissions remain authoritative.",
                "Semgrep metrics and version checks were disabled, with writable cache/log paths confined to the ephemeral tmpfs.",
                "The eligible-file preflight is an upper bound; Semgrep may skip unsupported or ignored files.",
                "Raw source snippets and metavariable values were discarded before the normalized result was returned.",
            ]
        )
        return result

    def _validate_root(self, root: str | os.PathLike[str]) -> Path:
        root_path = Path(root)
        if root_path.is_symlink():
            raise ValueError("project root must not be a symlink")
        try:
            resolved = root_path.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ValueError("project root is unavailable") from exc
        if not resolved.is_dir():
            raise ValueError("project root must be a directory")
        return resolved

    def _bounded_preflight(self, root: Path, *, deadline: float, cancel=None) -> int:
        count = 0
        stack: list[tuple[Path, int]] = [(root, 0)]
        while stack:
            self._check_cancel(cancel)
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    "Semgrep project preflight exceeded the execution deadline"
                )
            directory, depth = stack.pop()
            try:
                with os.scandir(directory) as iterator:
                    entries = list(iterator)
            except OSError as exc:
                raise ValueError(
                    "Semgrep project preflight could not enumerate the approved root"
                ) from exc
            for entry in entries:
                self._check_cancel(cancel)
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if entry.name in DEFAULT_EXCLUDED_DIRS:
                        continue
                    if depth >= self.policy.max_depth:
                        raise ValueError(
                            "project exceeds the approved Semgrep directory-depth bound"
                        )
                    stack.append((Path(entry.path), depth + 1))
                elif entry.is_file(follow_symlinks=False):
                    count += 1
                    if count > self.policy.max_files:
                        raise ValueError(
                            "project exceeds the approved Semgrep file-count bound"
                        )
        return count

    @staticmethod
    def _docker_path() -> str:
        docker = shutil.which("docker")
        if not docker:
            raise RuntimeError("Docker is required for the pinned Semgrep runner")
        return docker

    @staticmethod
    def _ensure_image_present(docker: str) -> None:
        try:
            check = subprocess.run(
                [docker, "image", "inspect", SEMGREP_IMAGE],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError("could not verify the local Semgrep image") from exc
        if check.returncode != 0:
            raise RuntimeError(
                "pinned Semgrep image is not preinstalled; automatic pull is disabled"
            )

    def _build_command(self, docker: str, root: Path, container_name: str) -> list[str]:
        if not RULES_PATH.is_file():
            raise RuntimeError("repository-authored Semgrep rules are missing")
        if not hasattr(os, "getuid") or not hasattr(os, "getgid"):
            raise RuntimeError(
                "Semgrep container execution requires Linux UID/GID mapping"
            )
        command = [
            docker,
            "run",
            "--rm",
            "--pull",
            "never",
            "--name",
            container_name,
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "128",
            "--memory",
            "1024m",
            "--cpus",
            "1",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev,size=256m,mode=1777",
            "-e",
            "SEMGREP_SEND_METRICS=off",
            "-e",
            "SEMGREP_ENABLE_VERSION_CHECK=0",
            "-e",
            "SEMGREP_VERSION_CACHE_PATH=/tmp/semgrep_version",
            "-e",
            "SEMGREP_LOG_FILE=/tmp/semgrep.log",
            "-e",
            "XDG_CACHE_HOME=/tmp/.cache",
            "-e",
            "HOME=/tmp",
            "-v",
            f"{root}:/src:ro",
            # Mount the reviewed config at the container root. Semgrep prefixes local
            # rule IDs with parent directories; a root-level config keeps rule IDs
            # stable instead of coupling evidence fingerprints to our mount path.
            "-v",
            f"{RULES_PATH.resolve()}:/workbench.yml:ro",
            "-w",
            "/src",
            SEMGREP_IMAGE,
            "semgrep",
            "scan",
            "--config",
            "/workbench.yml",
            "--json",
            "--metrics",
            "off",
            "--disable-version-check",
            "--max-target-bytes",
            str(self.policy.max_target_bytes),
        ]
        for excluded in sorted(DEFAULT_EXCLUDED_DIRS):
            command.extend(["--exclude", excluded])
        command.append("/src")
        return command

    def _execute_docker(
        self,
        docker: str,
        command: list[str],
        *,
        container_name: str,
        deadline: float,
        cancel=None,
    ) -> tuple[int, bytes]:
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
            )
        except OSError as exc:
            raise RuntimeError("could not launch the pinned Semgrep container") from exc

        stdout = bytearray()
        stderr = bytearray()
        overflow = threading.Event()

        def drain(stream, sink: bytearray, limit: int) -> None:
            if stream is None:
                return
            try:
                while True:
                    chunk = stream.read(65536)
                    if not chunk:
                        break
                    remaining = limit - len(sink)
                    if remaining > 0:
                        sink.extend(chunk[:remaining])
                    if len(chunk) > max(remaining, 0):
                        overflow.set()
            finally:
                try:
                    stream.close()
                except OSError:
                    pass

        out_thread = threading.Thread(
            target=drain, args=(process.stdout, stdout, MAX_OUTPUT_BYTES), daemon=True
        )
        err_thread = threading.Thread(
            target=drain, args=(process.stderr, stderr, _STDERR_LIMIT), daemon=True
        )
        out_thread.start()
        err_thread.start()
        abnormal = False
        try:
            while process.poll() is None:
                if overflow.is_set():
                    abnormal = True
                    raise ValueError(
                        "Semgrep process output exceeded the bounded capture limit"
                    )
                self._check_cancel(cancel)
                if time.monotonic() >= deadline:
                    abnormal = True
                    raise TimeoutError(
                        "Semgrep project scan exceeded the execution deadline"
                    )
                time.sleep(0.05)
            out_thread.join(timeout=2)
            err_thread.join(timeout=2)
            if overflow.is_set():
                abnormal = True
                raise ValueError(
                    "Semgrep process output exceeded the bounded capture limit"
                )
            return int(process.returncode or 0), bytes(stdout)
        except (InterruptedError, TimeoutError, ValueError):
            abnormal = True
            raise
        finally:
            if abnormal:
                try:
                    process.terminate()
                except OSError:
                    pass
                try:
                    subprocess.run(
                        [docker, "rm", "-f", container_name],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=5,
                        check=False,
                    )
                except (OSError, subprocess.TimeoutExpired):
                    pass
                try:
                    process.wait(timeout=2)
                except (OSError, subprocess.TimeoutExpired):
                    try:
                        process.kill()
                    except OSError:
                        pass


def semgrep_tool_public_metadata() -> dict[str, Any]:
    """Return non-secret pin/licensing metadata suitable for review surfaces."""
    return {
        "id": TOOL_PIN["id"],
        "version": TOOL_PIN["version"],
        "release_url": TOOL_PIN["release_url"],
        "license": dict(TOOL_PIN["license"]),
        "container": {
            "platform": TOOL_PIN["container"]["platform"],
            "manifest_digest": TOOL_PIN["container"]["manifest_digest"],
            "automatic_pull": False,
        },
        "rules": {
            "source": TOOL_PIN["rules"]["source"],
            "external_registry": False,
        },
    }
