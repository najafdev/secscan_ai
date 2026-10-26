"""Cloud-policy tests use only owned loopback protocol fixtures, never a cloud API."""

import copy
import json
import http.client
import os
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

import workbench.tests.test_ollama_runtime as protocol
import workbench.tests.test_server as server_fixture
from workbench.engine import Assessment, Scope, verify_integrity
from workbench.ollama import Ollama
from workbench.ollama_runtime import OllamaError

CLOUD = "fixture:cloud"
SUMMARY = {
    "summary": "Observed checks only",
    "next_steps": [],
    "limitations": ["Fixture data"],
}


class CloudProtocolTests(unittest.TestCase):
    setUpClass = classmethod(protocol.ProtocolTests.setUpClass.__func__)
    tearDownClass = classmethod(protocol.ProtocolTests.tearDownClass.__func__)
    assert_code = protocol.ProtocolTests.assert_code

    def setUp(self):
        protocol.ProtocolTests.setUp(self)
        self.client = Ollama(CLOUD, self.server.server_port, allow_cloud=True)
        self.server.responses["/api/tags"] = (
            200,
            {"models": [{"name": CLOUD}, {"name": protocol.MODEL}]},
        )
        self.server.responses["/api/show"] = (
            200,
            {
                "remote_host": "https://cloud.example.invalid",
                "remote_model": "fixture",
                "capabilities": ["completion", "tools"],
            },
        )
        self.server.responses["/api/chat"] = (
            200,
            {
                "done": True,
                "remote_host": "https://cloud.example.invalid",
                "message": {"role": "assistant", "content": json.dumps(SUMMARY)},
            },
        )

    def test_opt_in_catalog_exposes_both_kinds_without_substitution(self):
        result = self.client.catalog()
        self.assertEqual(result["models"], sorted([CLOUD, protocol.MODEL]))
        self.assertEqual(result["blocked_models"], 0)
        self.assertEqual(result["cloud_models"], [CLOUD])
        self.assertEqual(result["processing_policy"], "cloud_allowed")
        self.assertEqual(self.client.model, CLOUD)
        self.assertEqual([x[0] for x in self.server.requests], ["/api/tags"])

    def test_cloud_inspection_needs_no_inference(self):
        result = self.client.inspect_model(require_tools=True)
        self.assertEqual(result["execution_location"], "cloud_reported")
        self.assertTrue(result["cloud_processing_approved"])
        self.assertFalse(result["inference_tested"])
        self.assertNotIn("/api/chat", [x[0] for x in self.server.requests])

    def test_cloud_summary_uses_prompted_contract_with_same_validation(self):
        self.assertEqual(self.client.summarize(protocol.REPORT), SUMMARY)
        payload = self.server.requests[-1][1]
        self.assertNotIn("format", payload)
        self.assertIn(
            '"additionalProperties": false', payload["messages"][0]["content"]
        )
        self.assertEqual(
            self.client.telemetry()["calls"][0]["schema_strategy"],
            "prompt_then_validate",
        )

    def test_prompted_contract_does_not_mutate_caller_messages_or_schema(self):
        messages = copy.deepcopy(protocol.MESSAGES)
        schema = {"type": "object", "properties": {}}
        self.client.chat(messages, format=schema)
        self.assertEqual(messages, protocol.MESSAGES)
        self.assertEqual(schema, {"type": "object", "properties": {}})

    def test_invalid_cloud_json_is_not_accepted_as_summary(self):
        self.server.responses["/api/chat"] = (
            200,
            {"done": True, "message": {"content": "```json\n{}\n```"}},
        )
        with self.assertRaises(ValueError):
            self.client.summarize(protocol.REPORT)

    def test_extra_summary_fields_are_rejected(self):
        self.server.responses["/api/chat"] = (
            200,
            {
                "done": True,
                "message": {"content": json.dumps({**SUMMARY, "verified": True})},
            },
        )
        with self.assertRaises(ValueError):
            self.client.summarize(protocol.REPORT)

    def test_cloud_metadata_does_not_grant_missing_tool_capability(self):
        self.server.responses["/api/show"] = (
            200,
            {"remote_host": "remote", "capabilities": ["completion"]},
        )
        self.assert_code(
            "tools_unsupported",
            lambda: self.client.chat(protocol.MESSAGES, tools=[protocol.TOOL]),
        )
        self.assertNotIn("/api/chat", [x[0] for x in self.server.requests])

    def test_metadata_alias_without_cloud_in_its_name_can_be_approved(self):
        self.client.model = protocol.MODEL
        self.assertEqual(
            self.client.inspect_model()["execution_location"], "cloud_reported"
        )
        self.assertEqual(self.client.summarize(protocol.REPORT), SUMMARY)

    def test_catalog_remote_alias_is_not_misclassified_when_show_omits_remote_fields(
        self,
    ):
        self.client.model = protocol.MODEL
        self.server.responses["/api/tags"] = (
            200,
            {"models": [{"name": protocol.MODEL, "remote_model": "remote"}]},
        )
        self.server.responses["/api/show"] = (200, {"capabilities": ["completion"]})
        self.assertEqual(
            self.client.inspect_model()["execution_location"], "cloud_reported"
        )
        self.client.summarize(protocol.REPORT)
        self.assertNotIn("format", self.server.requests[-1][1])

    def test_opt_in_does_not_force_local_model_into_cloud(self):
        self.client.model = protocol.MODEL
        self.server.responses["/api/show"] = (200, {"capabilities": ["completion"]})
        self.server.responses["/api/chat"] = (
            200,
            {"done": True, "message": {"content": json.dumps(SUMMARY)}},
        )
        self.client.summarize(protocol.REPORT)
        self.assertIn("format", self.server.requests[-1][1])
        self.assertEqual(
            self.client.telemetry()["execution_location"], "local_reported"
        )

    def test_cloud_output_has_same_truncation_gate(self):
        self.server.responses["/api/chat"] = (
            200,
            {"done": True, "done_reason": "length", "message": {"content": "partial"}},
        )
        self.assert_code(
            "output_truncated", lambda: self.client.chat(protocol.MESSAGES)
        )

    def test_cloud_tools_still_accept_at_most_one_call(self):
        self.server.responses["/api/chat"] = (
            200,
            {
                "done": True,
                "message": {
                    "content": "",
                    "tool_calls": [{"function": {}}, {"function": {}}],
                },
            },
        )
        self.assert_code(
            "invalid_tool_call",
            lambda: self.client.chat(protocol.MESSAGES, tools=[protocol.TOOL]),
        )

    def test_cloud_quota_error_does_not_retry_or_fallback(self):
        self.server.responses["/api/chat"] = (429, {"error": "not-logged"})
        self.assert_code("busy", lambda: self.client.chat(protocol.MESSAGES))
        self.assertEqual(
            len([r for r in self.server.requests if r[0] == "/api/chat"]), 1
        )
        self.assertEqual(self.client.model, CLOUD)
        self.assertEqual(self.client.telemetry()["inference_attempts"], 1)
        self.assertIsNone(self.client.telemetry()["prompt_tokens_reported"])

    def test_usage_is_reported_not_invented_or_billed(self):
        self.server.responses["/api/chat"] = (
            200,
            {
                "done": True,
                "prompt_eval_count": 41,
                "eval_count": 8,
                "message": {"content": "{}"},
            },
        )
        self.client.chat(protocol.MESSAGES)
        self.client.chat(protocol.MESSAGES)
        usage = self.client.telemetry()
        self.assertEqual(usage["prompt_tokens_reported"], 82)
        self.assertEqual(usage["output_tokens_reported"], 16)
        self.assertEqual(usage["inference_attempts"], 2)
        self.assertIsNone(usage["billing_cost"])
        self.assertNotIn("content", json.dumps(usage))

    def test_missing_or_invalid_usage_is_unknown_not_zero(self):
        for value in (None, True, -1, "100", 1.5, 10**15):
            with self.subTest(value=value):
                client = Ollama(CLOUD, self.server.server_port, allow_cloud=True)
                self.server.responses["/api/chat"] = (
                    200,
                    {
                        "done": True,
                        "prompt_eval_count": value,
                        "eval_count": value,
                        "message": {"content": "{}"},
                    },
                )
                client.chat(protocol.MESSAGES)
                self.assertIsNone(client.telemetry()["prompt_tokens_reported"])
                self.assertIsNone(client.telemetry()["output_tokens_reported"])

    def test_partial_usage_coverage_is_not_reported_as_a_complete_total(self):
        self.server.responses["/api/chat"] = (
            200,
            {"done": True, "prompt_eval_count": 8, "message": {"content": "{}"}},
        )
        self.client.chat(protocol.MESSAGES)
        self.server.responses["/api/chat"] = (
            200,
            {"done": True, "message": {"content": "{}"}},
        )
        self.client.chat(protocol.MESSAGES)
        self.assertIsNone(self.client.telemetry()["prompt_tokens_reported"])

    def test_oversized_cloud_prompt_is_blocked_before_dispatch(self):
        self.assert_code(
            "request_too_large",
            lambda: self.client.chat(
                [{"role": "user", "content": "x" * 70000}], format={"type": "object"}
            ),
        )
        self.assertEqual(self.client.telemetry()["inference_attempts"], 0)
        self.assertNotIn("/api/chat", [x[0] for x in self.server.requests])

    def test_cloud_self_test_does_not_receive_assessment_data(self):
        self.server.responses["/api/chat"] = (
            200,
            {
                "done": True,
                "message": {
                    "content": '{"status":"ready","scope":"synthetic_self_test"}'
                },
            },
        )
        result = self.client.self_test()
        self.assertTrue(result["inference_tested"])
        self.assertFalse(result["assessment_data_sent"])
        self.assertEqual(result["execution_location"], "cloud_reported")

    def test_complete_http_api_gateway_and_sealed_report_without_live_inference(self):
        """Both servers use real loopback HTTP; model content is a fixture."""
        from workbench.server import LocalServer, State

        self.server.responses["/api/chat"] = (
            200,
            {
                "done": True,
                "prompt_eval_count": 73,
                "eval_count": 11,
                "remote_model": "synthetic-cloud",
                "message": {"content": json.dumps(SUMMARY)},
            },
        )
        with tempfile.TemporaryDirectory() as directory:
            state = State(directory)
            web = LocalServer(("127.0.0.1", 0), state, "fixture-token")
            thread = threading.Thread(target=web.serve_forever, daemon=True)
            thread.start()

            def request(path, body=None):
                connection = http.client.HTTPConnection(
                    "127.0.0.1", web.server_port, timeout=3
                )
                try:
                    connection.request(
                        "GET" if body is None else "POST",
                        path,
                        body=json.dumps(body) if body is not None else None,
                        headers={
                            "Authorization": "Bearer fixture-token",
                            "Content-Type": "application/json",
                        },
                    )
                    response = connection.getresponse()
                    return response.status, json.loads(response.read())
                finally:
                    connection.close()

            try:
                with patch.dict(
                    os.environ, {"SECSCAN_AI_OLLAMA_PORT": str(self.server.server_port)}
                ):
                    status, response = request(
                        "/api/runs",
                        {
                            "target": "lab",
                            "mode": "analyst",
                            "authorized": True,
                            "authorization": "AUTH-SECRET-NOT-FOR-MODEL",
                            "model": CLOUD,
                            "use_ai": True,
                            "allow_cloud": True,
                        },
                    )
                    self.assertEqual(status, 202)
                    state.worker.join(timeout=5)
                    self.assertFalse(state.worker.is_alive())
                    status, report = request(
                        "/api/runs/" + response["id"] + "/export.json"
                    )
                    self.assertEqual(status, 200)
                    self.assertTrue(verify_integrity(report))
                    self.assertTrue(report["ai"]["cloud_processing_approved"])
                    self.assertEqual(report["ai"]["status"], "completed")
                    self.assertEqual(
                        report["ai"]["usage"]["prompt_tokens_reported"], 73
                    )
                    self.assertEqual(
                        report["ai"]["usage"]["execution_location"], "cloud_reported"
                    )
                    self.assertEqual(report["ai"]["interpretation"], SUMMARY)
                    self.assertNotIn(
                        "AUTH-SECRET-NOT-FOR-MODEL", json.dumps(self.server.requests)
                    )
                    self.assertTrue(verify_integrity(state.store.get(response["id"])))
            finally:
                state.cancel.set()
                if state.worker:
                    state.worker.join(timeout=5)
                web.shutdown()
                web.server_close()
                thread.join(timeout=2)


class CloudPolicyTests(unittest.TestCase):
    def data(self, **changes):
        return {
            "target": "lab",
            "authorized": True,
            "authorization": "Local fixture",
            "model": CLOUD,
            "use_ai": True,
            "allow_cloud": True,
            **changes,
        }

    def test_runtime_requires_explicit_boolean_consent(self):
        for invalid in ("true", "false", 1, 0, None, [], {}):
            with self.subTest(invalid=invalid), self.assertRaises(OllamaError):
                Ollama(CLOUD, allow_cloud=invalid)

    def test_scope_cloud_opt_in_and_default(self):
        self.assertTrue(Scope.parse(self.data()).allow_cloud)
        self.assertFalse(
            Scope.parse(self.data(model=protocol.MODEL, allow_cloud=False)).allow_cloud
        )
        with self.assertRaises(ValueError):
            Scope.parse(self.data(allow_cloud=False))

    def test_scope_rejects_ambiguous_consent_and_ai_disabled_contradiction(self):
        for invalid in ("true", 1, None):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                Scope.parse(self.data(allow_cloud=invalid))
        with self.assertRaises(ValueError):
            Scope.parse(self.data(use_ai=False))

    def test_cloud_opt_in_does_not_replace_authorization_or_verification_approval(self):
        with self.assertRaises(ValueError):
            Scope.parse(self.data(authorized=False))
        with self.assertRaises(ValueError):
            Scope.parse(self.data(mode="verify", approve_verification=False))

    def test_cloud_opt_in_does_not_permit_new_actions(self):
        assessment = Assessment(
            Scope.parse(self.data(mode="verify", approve_verification=True))
        )
        with self.assertRaises(ValueError):
            assessment.execute_action("run_shell", {}, None)
        self.assertEqual(assessment.requests_used, 0)

    def test_report_records_policy_and_keeps_missing_external_verification_visible(
        self,
    ):
        ai = Mock()
        ai.summarize.return_value = SUMMARY
        report = Assessment(
            Scope.parse(
                self.data(
                    target="https://example.invalid",
                    mode="verify",
                    approve_verification=True,
                )
            ),
            remote_reader=lambda _: {"status": 200, "headers": {}},
            ai_client=ai,
        ).run()
        self.assertTrue(report["ai"]["cloud_processing_approved"])
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["verdict"], "inconclusive")
        self.assertTrue(any(c["status"] == "skipped" for c in report["checks"]))
        self.assertTrue(verify_integrity(report))
        ai.plan.assert_not_called()

    def test_data_context_drops_target_authorization_evidence_and_raw_headers(self):
        report = {
            **protocol.REPORT,
            "target": "TARGET-SECRET",
            "authorization": "AUTH-SECRET",
            "findings": [
                {
                    "id": "x",
                    "rule": "header/csp",
                    "severity": "low",
                    "verification": "observed_only",
                    "remediation": "Review policy",
                    "evidence": {"body": "BODY-SECRET"},
                }
            ],
            "checks": [
                {
                    "tool": "http_baseline",
                    "status": "completed",
                    "evidence": {"headers": {"x-secret": "HEADER-SECRET"}},
                }
            ],
        }
        value = json.dumps(Ollama.context(report))
        for secret in ("TARGET-SECRET", "AUTH-SECRET", "BODY-SECRET", "HEADER-SECRET"):
            self.assertNotIn(secret, value)


class CloudApiTests(unittest.TestCase):
    setUp = server_fixture.ServerTests.setUp
    tearDown = server_fixture.ServerTests.tearDown
    call = server_fixture.ServerTests.call

    @patch("workbench.server.Ollama")
    def test_metadata_forwards_policy_without_starting_run(self, factory):
        factory.return_value.inspect_model.return_value = {"state": "metadata_checked"}
        self.assertEqual(
            self.call(
                "/api/models/check",
                {"model": CLOUD, "allow_cloud": True, "require_tools": True},
            )[0],
            200,
        )
        factory.assert_called_once_with(CLOUD, allow_cloud=True)
        factory.return_value.inspect_model.assert_called_once_with(require_tools=True)
        self.assertIsNone(self.state.active)

    @patch("workbench.server.Ollama")
    def test_discovery_accepts_only_boolean_policy(self, factory):
        factory.return_value.diagnostics.return_value = {"models": [CLOUD]}
        self.assertEqual(
            self.call("/api/models/discover", {"allow_cloud": True})[0], 200
        )
        factory.assert_called_once_with("", allow_cloud=True)
        factory.reset_mock()
        for body in (
            {"allow_cloud": "true"},
            {"allow_cloud": True, "target": "https://example.invalid"},
            [],
        ):
            self.assertEqual(self.call("/api/models/discover", body)[0], 400)
        factory.assert_not_called()

    @patch("workbench.server.Ollama")
    def test_cloud_diagnostics_and_selftest_still_require_api_authentication(
        self, factory
    ):
        for route in (
            "/api/models/discover",
            "/api/models/check",
            "/api/models/self-test",
        ):
            self.assertEqual(
                self.call(route, {"allow_cloud": True, "model": CLOUD}, auth=False)[0],
                401,
            )
        factory.assert_not_called()

    @patch("workbench.server.Ollama")
    def test_selftest_uses_opt_in_without_assessment_fields(self, factory):
        factory.return_value.self_test.return_value = {"assessment_data_sent": False}
        status, _, raw = self.call(
            "/api/models/self-test", {"model": CLOUD, "allow_cloud": True}
        )
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(raw)["assessment_data_sent"])
        factory.assert_called_once_with(CLOUD, allow_cloud=True)
        factory.return_value.self_test.assert_called_once_with(require_tools=False)

    @patch("workbench.server.Ollama")
    def test_invalid_cloud_flags_are_rejected_before_gateway_access(self, factory):
        for route in ("/api/models/check", "/api/models/self-test"):
            self.assertEqual(
                self.call(route, {"model": CLOUD, "allow_cloud": "yes"})[0], 400
            )
        factory.assert_not_called()

    def test_health_distinguishes_local_ui_from_inference_policy(self):
        health = json.loads(self.call("/api/health")[2])
        self.assertTrue(health["local_only"])
        self.assertEqual(health["local_only_scope"], "server_binding")
        self.assertEqual(
            health["ai_processing_policies"], ["local_only", "cloud_allowed"]
        )


if __name__ == "__main__":
    unittest.main()
