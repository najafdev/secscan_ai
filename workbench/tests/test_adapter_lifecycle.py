import json
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path

from workbench.adapter_lifecycle import (
    AdapterLifecycle,
    AdapterLifecyclePersistenceError,
    request_digest,
    verify_lifecycle_record,
)

DECL = {
    "schema": "secscan_ai.execution-declaration/v1",
    "adapter": {"id": "fake-safe", "version": "1"},
    "launcher": "native_python",
    "effect_level": "read_only",
    "filesystem": "read_only_metadata",
    "network": "none",
    "subprocess": False,
    "writes": False,
    "follows_symlinks": False,
    "limits": {"max_objects": 10, "max_requests": 0, "timeout_seconds": 5},
    "coverage_unit": "files",
}


def receipt(summary):
    return {
        "schema": "secscan_ai.execution-receipt/v1",
        "declaration": DECL,
        "request_summary": summary,
        "usage": {"objects_tested": 1, "network_requests": 0, "elapsed_ms": 2},
        "result": {
            "adapter": {"id": "fake-safe", "version": "1"},
            "findings": [],
            "verification_authority": "workbench_only",
        },
    }


class FakeRegistry:
    def __init__(self, error=None, mutate_receipt=False):
        self.error = error
        self.mutate_receipt = mutate_receipt
        self.executions = 0

    def plan(self, adapter_id, request):
        if adapter_id != "fake-safe":
            raise ValueError("bad adapter")
        return {
            "declaration": DECL,
            "request_summary": {
                "adapter_id": adapter_id,
                "asset_key": request["asset_key"],
                "project_label": "project",
                "full_path_included": False,
            },
        }

    def execute_with_receipt(self, adapter_id, request, **kwargs):
        self.executions += 1
        if self.error:
            raise self.error
        summary = self.plan(adapter_id, request)["request_summary"]
        if self.mutate_receipt:
            summary = {**summary, "project_label": "other"}
        return receipt(summary)


class BlockingRegistry(FakeRegistry):
    def __init__(self):
        super().__init__()
        self.started = threading.Event()
        self.release = threading.Event()

    def execute_with_receipt(self, adapter_id, request, **kwargs):
        self.executions += 1
        self.started.set()
        if not self.release.wait(2):
            raise TimeoutError("synthetic blocking registry timeout")
        summary = self.plan(adapter_id, request)["request_summary"]
        return receipt(summary)


class AdapterLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "reports.sqlite3"
        self.request = {"root": "/very/private/customer/project", "asset_key": "asset"}

    def tearDown(self):
        self.tmp.cleanup()

    def test_plan_persists_digest_not_raw_request(self):
        life = AdapterLifecycle(self.db, FakeRegistry())
        record = life.plan("fake-safe", self.request)
        self.assertTrue(verify_lifecycle_record(record))
        self.assertEqual(record["status"], "planned")
        self.assertNotIn(b"/very/private/customer/project", self.db.read_bytes())
        self.assertEqual(len(record["request_sha256"]), 64)

    def test_approval_is_bound_to_exact_plan_digest(self):
        life = AdapterLifecycle(self.db, FakeRegistry())
        record = life.plan("fake-safe", self.request)
        with self.assertRaises(ValueError):
            life.approve(record["id"], "0" * 64)
        approved = life.approve(record["id"], record["plan_sha256"])
        self.assertEqual(approved["status"], "approved")
        with self.assertRaises(ValueError):
            life.approve(record["id"], record["plan_sha256"])

    def test_changed_raw_request_is_blocked_before_execution(self):
        registry = FakeRegistry()
        life = AdapterLifecycle(self.db, registry)
        record = life.plan("fake-safe", self.request)
        life.approve(record["id"], record["plan_sha256"])
        changed = {"root": "/different/customer/project", "asset_key": "asset"}
        with self.assertRaises(ValueError):
            life.execute(record["id"], "fake-safe", changed)
        self.assertEqual(registry.executions, 0)
        self.assertEqual(life.get(record["id"])["status"], "approved")

    def test_completed_receipt_is_durable_and_candidate_only(self):
        life = AdapterLifecycle(self.db, FakeRegistry())
        record = life.plan("fake-safe", self.request)
        life.approve(record["id"], record["plan_sha256"])
        done = life.execute(record["id"], "fake-safe", self.request)
        self.assertEqual(done["status"], "completed")
        self.assertEqual(
            done["receipt"]["result"]["verification_authority"], "workbench_only"
        )
        reopened = AdapterLifecycle(self.db, FakeRegistry()).get(record["id"])
        self.assertEqual(reopened["record_sha256"], done["record_sha256"])

    def test_receipt_plan_mismatch_fails_closed(self):
        life = AdapterLifecycle(self.db, FakeRegistry(mutate_receipt=True))
        record = life.plan("fake-safe", self.request)
        life.approve(record["id"], record["plan_sha256"])
        with self.assertRaises(ValueError):
            life.execute(record["id"], "fake-safe", self.request)
        failed = life.get(record["id"])
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["outcome"]["code"], "execution_rejected")
        self.assertIsNone(failed["receipt"])

    def test_cancelled_execution_is_recorded_without_raw_error(self):
        life = AdapterLifecycle(
            self.db, FakeRegistry(error=InterruptedError("secret path /tmp/x"))
        )
        record = life.plan("fake-safe", self.request)
        life.approve(record["id"], record["plan_sha256"])
        with self.assertRaises(InterruptedError):
            life.execute(record["id"], "fake-safe", self.request)
        cancelled = life.get(record["id"])
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(cancelled["outcome"], {"code": "cancelled"})
        self.assertNotIn("secret path", json.dumps(cancelled))

    def test_integrity_tampering_is_detected(self):
        life = AdapterLifecycle(self.db, FakeRegistry())
        record = life.plan("fake-safe", self.request)
        with closing(sqlite3.connect(self.db)) as connection:
            raw = connection.execute(
                "SELECT content FROM adapter_lifecycle WHERE id = ?", (record["id"],)
            ).fetchone()[0]
            obj = json.loads(raw)
            obj["status"] = "completed"
            connection.execute(
                "UPDATE adapter_lifecycle SET status = ?, content = ? WHERE id = ?",
                ("completed", json.dumps(obj), record["id"]),
            )
            connection.commit()
        with self.assertRaises(ValueError):
            life.get(record["id"])

    def test_recent_is_minimized(self):
        life = AdapterLifecycle(self.db, FakeRegistry())
        record = life.plan("fake-safe", self.request)
        row = life.recent()[0]
        self.assertEqual(row["id"], record["id"])
        self.assertNotIn("request_sha256", row)
        self.assertNotIn("declaration", row)
        self.assertNotIn("receipt", row)

    def test_recovery_marks_executing_as_interrupted(self):
        life = AdapterLifecycle(self.db, FakeRegistry())
        record = life.plan("fake-safe", self.request)
        approved = life.approve(record["id"], record["plan_sha256"])
        executing = dict(approved)
        executing["status"] = "executing"
        executing["outcome"] = {"code": "execution_started"}
        life.store.replace(record["id"], "approved", executing)
        reopened = AdapterLifecycle(self.db, FakeRegistry())
        self.assertEqual(reopened.recovered_interruptions, 1)
        recovered = reopened.get(record["id"])
        self.assertEqual(recovered["status"], "interrupted")
        self.assertEqual(recovered["outcome"], {"code": "interrupted_after_restart"})

    def test_concurrent_execute_reaches_registry_once(self):
        registry = BlockingRegistry()
        life = AdapterLifecycle(self.db, registry)
        record = life.plan("fake-safe", self.request)
        life.approve(record["id"], record["plan_sha256"])
        result = []
        errors = []

        def first():
            try:
                result.append(life.execute(record["id"], "fake-safe", self.request))
            except Exception as exc:  # pragma: no cover - assertion below reports it
                errors.append(exc)

        worker = threading.Thread(target=first)
        worker.start()
        self.assertTrue(registry.started.wait(1))
        with self.assertRaises(ValueError):
            life.execute(record["id"], "fake-safe", self.request)
        self.assertEqual(registry.executions, 1)
        registry.release.set()
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(result[0]["status"], "completed")
        self.assertEqual(life.get(record["id"])["status"], "completed")

    def test_successful_execution_storage_fault_is_interrupted_not_failed(self):
        registry = FakeRegistry()
        life = AdapterLifecycle(self.db, registry)
        record = life.plan("fake-safe", self.request)
        life.approve(record["id"], record["plan_sha256"])
        original = life.store.replace
        failed_once = False

        def fail_completed_once(lifecycle_id, expected_status, candidate):
            nonlocal failed_once
            if (
                expected_status == "executing"
                and candidate.get("status") == "completed"
                and not failed_once
            ):
                failed_once = True
                raise OSError("synthetic terminal persistence failure")
            return original(lifecycle_id, expected_status, candidate)

        life.store.replace = fail_completed_once
        with self.assertRaises(AdapterLifecyclePersistenceError):
            life.execute(record["id"], "fake-safe", self.request)
        stored = life.get(record["id"])
        self.assertEqual(registry.executions, 1)
        self.assertEqual(stored["status"], "interrupted")
        self.assertEqual(stored["outcome"], {"code": "terminal_persistence_failed"})
        self.assertIsNone(stored["receipt"])

    def test_failed_execution_with_terminal_storage_fault_stays_non_successful(self):
        registry = FakeRegistry(error=PermissionError("synthetic policy denial"))
        life = AdapterLifecycle(self.db, registry)
        record = life.plan("fake-safe", self.request)
        life.approve(record["id"], record["plan_sha256"])
        original = life.store.replace
        failed_once = False

        def fail_failed_once(lifecycle_id, expected_status, candidate):
            nonlocal failed_once
            if (
                expected_status == "executing"
                and candidate.get("status") == "failed"
                and not failed_once
            ):
                failed_once = True
                raise OSError("synthetic failure-state persistence error")
            return original(lifecycle_id, expected_status, candidate)

        life.store.replace = fail_failed_once
        with self.assertRaises(AdapterLifecyclePersistenceError):
            life.execute(record["id"], "fake-safe", self.request)
        stored = life.get(record["id"])
        self.assertEqual(stored["status"], "interrupted")
        self.assertEqual(
            stored["outcome"],
            {
                "code": "terminal_persistence_failed",
                "prior_outcome_code": "policy_denied",
            },
        )
        self.assertIsNone(stored["receipt"])

    def test_request_digest_accepts_path_and_rejects_opaque_objects(self):
        first = request_digest({"root": Path("/tmp/project"), "asset_key": "a"})
        second = request_digest({"root": "/tmp/project", "asset_key": "a"})
        self.assertEqual(first, second)
        with self.assertRaises(ValueError):
            request_digest({"root": object()})


if __name__ == "__main__":
    unittest.main()
