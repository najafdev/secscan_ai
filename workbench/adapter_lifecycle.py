"""Durable approval lifecycle for bounded execution adapters.

The lifecycle persists only minimized plans, cryptographic request digests and normalized
receipts. Raw adapter requests (for example full local paths) are never stored here.
Execution authority remains in the reviewed ExecutionRegistry; this module cannot add
adapters, commands or permissions.
"""

from __future__ import annotations

import copy
import hashlib
import json
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .execution_receipts import normalize_execution_receipt

ADAPTER_LIFECYCLE_SCHEMA = "secscan_ai.adapter-lifecycle/v1"
_ALLOWED_STATES = {
    "planned",
    "approved",
    "executing",
    "completed",
    "failed",
    "cancelled",
    "interrupted",
}
_MAX_RECORD_BYTES = 2_000_000


class AdapterLifecyclePersistenceError(RuntimeError):
    """A terminal adapter outcome could not be durably recorded."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_request(value: Any) -> Any:
    """Convert a typed adapter request to stable JSON without mutating it."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("adapter request keys must be text")
            result[key] = _canonical_request(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_canonical_request(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError("adapter request contains unsupported values")


def _digest(value: Any) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def request_digest(request: Any) -> str:
    if not isinstance(request, dict):
        raise ValueError("adapter request must be an object")
    return _digest(_canonical_request(request))


def _plan_digest(
    adapter_id: str,
    declaration: dict[str, Any],
    request_summary: dict[str, Any],
    request_sha256: str,
) -> str:
    return _digest(
        {
            "adapter_id": adapter_id,
            "declaration": declaration,
            "request_summary": request_summary,
            "request_sha256": request_sha256,
        }
    )


def _seal(record: dict[str, Any]) -> dict[str, Any]:
    sealed = copy.deepcopy(record)
    sealed.pop("record_sha256", None)
    sealed["record_sha256"] = _digest(sealed)
    raw = json.dumps(
        sealed, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    if len(raw) > _MAX_RECORD_BYTES:
        raise ValueError("adapter lifecycle record is too large")
    return sealed


def verify_lifecycle_record(record: Any) -> bool:
    if not isinstance(record, dict) or record.get("schema") != ADAPTER_LIFECYCLE_SCHEMA:
        return False
    if record.get("status") not in _ALLOWED_STATES:
        return False
    expected = record.get("record_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        return False
    candidate = copy.deepcopy(record)
    candidate.pop("record_sha256", None)
    return secrets.compare_digest(expected, _digest(candidate))


def _failure_code(exc: BaseException) -> str:
    if isinstance(exc, PermissionError):
        return "policy_denied"
    if isinstance(exc, TimeoutError):
        return "deadline_exceeded"
    if isinstance(exc, InterruptedError):
        return "cancelled"
    if isinstance(exc, ValueError):
        return "execution_rejected"
    return "execution_failed"


class AdapterLifecycleStore:
    """Tamper-evident SQLite storage for reviewed adapter plans and receipts."""

    def __init__(self, database: str | Path):
        self.path = Path(database)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS adapter_lifecycle ("
                "id TEXT PRIMARY KEY, created TEXT NOT NULL, updated TEXT NOT NULL, status TEXT NOT NULL, content TEXT NOT NULL)"
            )
            connection.commit()
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    def _encode(self, record: dict[str, Any]) -> str:
        sealed = _seal(record)
        if not verify_lifecycle_record(sealed):
            raise ValueError("adapter lifecycle record failed integrity validation")
        return json.dumps(sealed, sort_keys=True, separators=(",", ":"))

    def create(self, record: dict[str, Any]) -> dict[str, Any]:
        raw = self._encode(record)
        sealed = json.loads(raw)
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO adapter_lifecycle VALUES (?, ?, ?, ?, ?)",
                (
                    sealed["id"],
                    sealed["created_at"],
                    sealed["updated_at"],
                    sealed["status"],
                    raw,
                ),
            )
            connection.commit()
        return sealed

    def get(self, lifecycle_id: str) -> dict[str, Any] | None:
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            row = connection.execute(
                "SELECT content FROM adapter_lifecycle WHERE id = ?", (lifecycle_id,)
            ).fetchone()
        if not row:
            return None
        record = json.loads(row[0])
        if not verify_lifecycle_record(record):
            raise ValueError("stored adapter lifecycle record checksum mismatch")
        return record

    def replace(
        self, lifecycle_id: str, expected_status: str, record: dict[str, Any]
    ) -> dict[str, Any]:
        if not isinstance(record, dict) or record.get("id") != lifecycle_id:
            raise ValueError("adapter lifecycle identity cannot change")
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status, content FROM adapter_lifecycle WHERE id = ?",
                (lifecycle_id,),
            ).fetchone()
            if not row:
                raise KeyError("adapter lifecycle record not found")
            current = json.loads(row[1])
            if not verify_lifecycle_record(current):
                raise ValueError("stored adapter lifecycle record checksum mismatch")
            if row[0] != expected_status:
                raise ValueError(
                    f"adapter lifecycle is {row[0]}, expected {expected_status}"
                )
            immutable = (
                "schema",
                "id",
                "adapter_id",
                "created_at",
                "declaration",
                "request_summary",
                "request_sha256",
                "plan_sha256",
            )
            if any(record.get(key) != current.get(key) for key in immutable):
                raise ValueError("approved adapter plan fields are immutable")
            raw = self._encode(record)
            sealed = json.loads(raw)
            connection.execute(
                "UPDATE adapter_lifecycle SET updated = ?, status = ?, content = ? WHERE id = ?",
                (sealed["updated_at"], sealed["status"], raw, lifecycle_id),
            )
            connection.commit()
        return sealed

    def recover_interrupted(self) -> int:
        recovered = 0
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT id, content FROM adapter_lifecycle WHERE status = 'executing'"
            ).fetchall()
            for lifecycle_id, raw in rows:
                record = json.loads(raw)
                if not verify_lifecycle_record(record):
                    continue
                record["status"] = "interrupted"
                record["updated_at"] = _now()
                record["outcome"] = {"code": "interrupted_after_restart"}
                sealed_raw = self._encode(record)
                sealed = json.loads(sealed_raw)
                connection.execute(
                    "UPDATE adapter_lifecycle SET updated = ?, status = ?, content = ? WHERE id = ?",
                    (sealed["updated_at"], sealed["status"], sealed_raw, lifecycle_id),
                )
                recovered += 1
            connection.commit()
        return recovered

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 100
        ):
            raise ValueError("adapter lifecycle limit must be between 1 and 100")
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            rows = connection.execute(
                "SELECT content FROM adapter_lifecycle ORDER BY created DESC LIMIT ?",
                (limit,),
            ).fetchall()
        result = []
        for (raw,) in rows:
            record = json.loads(raw)
            if not verify_lifecycle_record(record):
                raise ValueError("stored adapter lifecycle record checksum mismatch")
            result.append(
                {
                    "id": record["id"],
                    "adapter_id": record["adapter_id"],
                    "status": record["status"],
                    "created_at": record["created_at"],
                    "updated_at": record["updated_at"],
                    "plan_sha256": record["plan_sha256"],
                    "request_summary": copy.deepcopy(record["request_summary"]),
                }
            )
        return result


class AdapterLifecycle:
    """Plan -> exact approval -> execute workflow for a reviewed ExecutionRegistry."""

    def __init__(self, database: str | Path, registry):
        self.registry = registry
        self.store = AdapterLifecycleStore(database)
        self.recovered_interruptions = self.store.recover_interrupted()

    def plan(self, adapter_id: str, request: dict[str, Any]) -> dict[str, Any]:
        plan = self.registry.plan(adapter_id, request)
        request_sha256 = request_digest(request)
        created = _now()
        lifecycle_id = secrets.token_hex(16)
        record = {
            "schema": ADAPTER_LIFECYCLE_SCHEMA,
            "id": lifecycle_id,
            "adapter_id": adapter_id,
            "status": "planned",
            "created_at": created,
            "updated_at": created,
            "declaration": copy.deepcopy(plan["declaration"]),
            "request_summary": copy.deepcopy(plan["request_summary"]),
            "request_sha256": request_sha256,
            "plan_sha256": _plan_digest(
                adapter_id, plan["declaration"], plan["request_summary"], request_sha256
            ),
            "receipt": None,
            "outcome": None,
        }
        return self.store.create(record)

    def approve(self, lifecycle_id: str, plan_sha256: str) -> dict[str, Any]:
        record = self.store.get(lifecycle_id)
        if record is None:
            raise KeyError("adapter lifecycle record not found")
        if not isinstance(plan_sha256, str) or not secrets.compare_digest(
            record["plan_sha256"], plan_sha256
        ):
            raise ValueError("approval does not match the planned adapter authority")
        updated = copy.deepcopy(record)
        updated["status"] = "approved"
        updated["updated_at"] = _now()
        updated["outcome"] = {"code": "approved_exact_plan"}
        return self.store.replace(lifecycle_id, "planned", updated)

    def execute(
        self,
        lifecycle_id: str,
        adapter_id: str,
        request: dict[str, Any],
        *,
        cancel=None,
        web_reader=None,
    ) -> dict[str, Any]:
        record = self.store.get(lifecycle_id)
        if record is None:
            raise KeyError("adapter lifecycle record not found")
        if record["status"] != "approved":
            raise ValueError("adapter execution requires an approved lifecycle plan")
        if adapter_id != record["adapter_id"]:
            raise ValueError("adapter identity changed after approval")

        plan = self.registry.plan(adapter_id, request)
        request_sha256 = request_digest(request)
        candidate_sha256 = _plan_digest(
            adapter_id, plan["declaration"], plan["request_summary"], request_sha256
        )
        if not secrets.compare_digest(record["plan_sha256"], candidate_sha256):
            raise ValueError("adapter request changed after approval")

        executing = copy.deepcopy(record)
        executing["status"] = "executing"
        executing["updated_at"] = _now()
        executing["outcome"] = {"code": "execution_started"}
        self.store.replace(lifecycle_id, "approved", executing)

        try:
            receipt = normalize_execution_receipt(
                self.registry.execute_with_receipt(
                    adapter_id, request, cancel=cancel, web_reader=web_reader
                )
            )
            if (
                receipt["declaration"] != record["declaration"]
                or receipt["request_summary"] != record["request_summary"]
            ):
                raise ValueError("execution receipt does not match the approved plan")
        except Exception as exc:
            outcome_code = _failure_code(exc)
            terminal = copy.deepcopy(executing)
            terminal["status"] = (
                "cancelled" if isinstance(exc, InterruptedError) else "failed"
            )
            terminal["updated_at"] = _now()
            terminal["outcome"] = {"code": outcome_code}
            try:
                self.store.replace(lifecycle_id, "executing", terminal)
            except Exception as persistence_exc:
                uncertain = copy.deepcopy(executing)
                uncertain["status"] = "interrupted"
                uncertain["updated_at"] = _now()
                uncertain["outcome"] = {
                    "code": "terminal_persistence_failed",
                    "prior_outcome_code": outcome_code,
                }
                try:
                    self.store.replace(lifecycle_id, "executing", uncertain)
                except Exception:
                    pass
                raise AdapterLifecyclePersistenceError(
                    "adapter execution ended but its terminal state could not be durably recorded"
                ) from persistence_exc
            raise

        completed = copy.deepcopy(executing)
        completed["status"] = "completed"
        completed["updated_at"] = _now()
        completed["receipt"] = receipt
        completed["outcome"] = {"code": "completed_with_candidate_result"}
        try:
            return self.store.replace(lifecycle_id, "executing", completed)
        except Exception as persistence_exc:
            # The adapter returned, but without a durable receipt we must not claim a
            # durable success or invite an automatic retry. Preserve an explicit
            # interrupted state when storage recovers; otherwise restart recovery
            # will convert the still-executing row to interrupted.
            uncertain = copy.deepcopy(executing)
            uncertain["status"] = "interrupted"
            uncertain["updated_at"] = _now()
            uncertain["outcome"] = {"code": "terminal_persistence_failed"}
            try:
                self.store.replace(lifecycle_id, "executing", uncertain)
            except Exception:
                pass
            raise AdapterLifecyclePersistenceError(
                "adapter execution returned but its terminal receipt could not be durably recorded"
            ) from persistence_exc

    def get(self, lifecycle_id: str) -> dict[str, Any] | None:
        return self.store.get(lifecycle_id)

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.store.recent(limit)
