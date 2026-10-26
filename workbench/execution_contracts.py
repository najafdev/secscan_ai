"""Typed execution declarations for bounded workbench adapters.

The declaration describes authority required by an adapter; it does not grant that
authority. Launchers must independently enforce these limits and never accept model-
generated command strings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

EXECUTION_SCHEMA = "secscan_ai.execution-declaration/v1"
_ID = re.compile(r"[a-z0-9][a-z0-9._/-]{0,95}")
_EFFECTS = {"read_only", "passive", "active_bounded"}
_FILESYSTEM = {"none", "read_only_metadata", "read_only_content"}
_NETWORK = {"none", "scoped_target"}
_LAUNCHERS = {"native_python", "fixed_binary", "fixed_container"}


def _text(value: Any, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    value = value.strip()
    if (
        not value
        or len(value) > maximum
        or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)
    ):
        raise ValueError(f"invalid {field}")
    return value


@dataclass(frozen=True)
class ExecutionDeclaration:
    adapter_id: str
    version: str
    launcher: str
    effect_level: str
    filesystem: str
    network: str
    subprocess: bool
    writes: bool
    follows_symlinks: bool
    max_objects: int
    max_requests: int
    timeout_seconds: int
    coverage_unit: str

    @classmethod
    def parse(cls, payload: Any) -> "ExecutionDeclaration":
        if not isinstance(payload, dict):
            raise ValueError("execution declaration must be an object")
        required = {
            "schema",
            "adapter",
            "launcher",
            "effect_level",
            "filesystem",
            "network",
            "subprocess",
            "writes",
            "follows_symlinks",
            "limits",
            "coverage_unit",
        }
        if set(payload) != required:
            raise ValueError(
                "execution declaration fields do not match the v1 contract"
            )
        if payload.get("schema") != EXECUTION_SCHEMA:
            raise ValueError("unsupported execution declaration schema")
        adapter = payload.get("adapter")
        if not isinstance(adapter, dict) or set(adapter) != {"id", "version"}:
            raise ValueError("adapter identity must contain exactly id and version")
        adapter_id = _text(adapter.get("id"), "adapter id", 96).lower()
        version = _text(adapter.get("version"), "adapter version", 64)
        if not _ID.fullmatch(adapter_id):
            raise ValueError("invalid adapter id")
        launcher = payload.get("launcher")
        effect = payload.get("effect_level")
        filesystem = payload.get("filesystem")
        network = payload.get("network")
        if (
            launcher not in _LAUNCHERS
            or effect not in _EFFECTS
            or filesystem not in _FILESYSTEM
            or network not in _NETWORK
        ):
            raise ValueError("unsupported execution authority")
        for field in ("subprocess", "writes", "follows_symlinks"):
            if type(payload.get(field)) is not bool:
                raise ValueError(f"{field} must be boolean")
        subprocess = payload["subprocess"]
        writes = payload["writes"]
        follows_symlinks = payload["follows_symlinks"]
        limits = payload.get("limits")
        if not isinstance(limits, dict) or set(limits) != {
            "max_objects",
            "max_requests",
            "timeout_seconds",
        }:
            raise ValueError("execution limits must be explicit")
        max_objects = limits["max_objects"]
        max_requests = limits["max_requests"]
        timeout_seconds = limits["timeout_seconds"]
        if (
            isinstance(max_objects, bool)
            or not isinstance(max_objects, int)
            or not 1 <= max_objects <= 100_000
        ):
            raise ValueError("invalid max_objects")
        if (
            isinstance(max_requests, bool)
            or not isinstance(max_requests, int)
            or not 0 <= max_requests <= 10_000
        ):
            raise ValueError("invalid max_requests")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, int)
            or not 1 <= timeout_seconds <= 3600
        ):
            raise ValueError("invalid timeout_seconds")
        coverage_unit = _text(payload.get("coverage_unit"), "coverage unit", 80)

        if network == "none" and max_requests != 0:
            raise ValueError("network-none adapters must have zero request budget")
        if network == "scoped_target" and max_requests == 0:
            raise ValueError("networked adapters require a positive request budget")
        if launcher == "native_python" and subprocess:
            raise ValueError(
                "native_python launcher cannot declare subprocess execution"
            )
        if launcher in {"fixed_binary", "fixed_container"} and not subprocess:
            raise ValueError("external launcher must declare subprocess execution")
        if effect == "read_only" and writes:
            raise ValueError("read_only adapters cannot write")
        if follows_symlinks and filesystem == "none":
            raise ValueError("symlink traversal requires filesystem authority")

        return cls(
            adapter_id,
            version,
            launcher,
            effect,
            filesystem,
            network,
            subprocess,
            writes,
            follows_symlinks,
            max_objects,
            max_requests,
            timeout_seconds,
            coverage_unit,
        )

    def public(self) -> dict[str, Any]:
        return {
            "schema": EXECUTION_SCHEMA,
            "adapter": {"id": self.adapter_id, "version": self.version},
            "launcher": self.launcher,
            "effect_level": self.effect_level,
            "filesystem": self.filesystem,
            "network": self.network,
            "subprocess": self.subprocess,
            "writes": self.writes,
            "follows_symlinks": self.follows_symlinks,
            "limits": {
                "max_objects": self.max_objects,
                "max_requests": self.max_requests,
                "timeout_seconds": self.timeout_seconds,
            },
            "coverage_unit": self.coverage_unit,
        }


def normalize_execution_declaration(payload: Any) -> dict[str, Any]:
    return ExecutionDeclaration.parse(payload).public()
