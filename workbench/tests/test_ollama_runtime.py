"""Real loopback HTTP against a fake Ollama protocol server, NOT live inference."""

import copy
import http.client
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import Mock, patch

from workbench.ollama import Ollama
from workbench.ollama_runtime import (
    MAX_MODELS,
    MAX_RESPONSE_BYTES,
    OllamaError,
    valid_model_name,
)

MODEL = "local:test"
MESSAGES = [{"role": "user", "content": "Synthetic fixture only"}]
TOOL = {
    "type": "function",
    "function": {
        "name": "verify_lab_canary",
        "parameters": {"type": "object", "properties": {}},
    },
}
REPORT = {
    "environment": "synthetic_lab",
    "mode": "analyst",
    "findings": [],
    "checks": [],
    "limitations": [],
}


class ProtocolServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                self.respond(None)

            def do_POST(self):
                data = json.loads(
                    self.rfile.read(int(self.headers.get("Content-Length", "0")))
                )
                self.respond(data)

            def respond(self, data):
                self.server.requests.append((self.path, data))
                status, value = self.server.responses.get(self.path, (404, {}))
                raw = value if isinstance(value, bytes) else json.dumps(value).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                if status == 302:
                    self.send_header("Location", "https://example.invalid/never-follow")
                self.end_headers()
                try:
                    self.wfile.write(raw)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        cls.server = ProtocolServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        self.server.requests = []
        self.server.responses = {
            "/api/tags": (200, {"models": [{"name": MODEL}]}),
            "/api/show": (
                200,
                {
                    "capabilities": ["completion", "tools"],
                    "details": {"parameter_size": "3B", "quantization_level": "Q4_K_M"},
                },
            ),
            "/api/chat": (
                200,
                {
                    "done": True,
                    "message": {
                        "role": "assistant",
                        "content": "Observed only",
                        "thinking": "not-retained",
                    },
                },
            ),
        }
        self.client = Ollama(MODEL, self.server.server_port)

    def assert_code(self, code, call):
        with self.assertRaises(OllamaError) as context:
            call()
        self.assertEqual(context.exception.code, code)
        return context.exception

    def test_catalog_and_empty_states(self):
        value = self.client.diagnostics()
        self.assertEqual(value["provider"], "ollama")
        self.assertEqual(value["models"], [MODEL])
        self.assertEqual(value["cloud_configuration"], "not_attested")
        self.server.responses["/api/tags"] = (200, {"models": []})
        self.assertEqual(self.client.diagnostics()["state"], "empty")

    def test_cloud_catalog_fields_and_names_are_filtered(self):
        self.server.responses["/api/tags"] = (
            200,
            {
                "models": [
                    {"name": MODEL},
                    {"name": "x:cloud"},
                    {"name": "alias:a", "remote_host": "remote"},
                    {"name": "alias:b", "remote_model": "remote"},
                ]
            },
        )
        value = self.client.catalog()
        self.assertEqual(value["models"], [MODEL])
        self.assertEqual(value["blocked_models"], 3)

    def test_only_remote_models_have_separate_status(self):
        self.server.responses["/api/tags"] = (200, {"models": [{"name": "x:cloud"}]})
        self.assertEqual(self.client.catalog()["state"], "no_local_models")

    def test_catalog_is_sorted_and_deduplicated(self):
        self.server.responses["/api/tags"] = (
            200,
            {"models": [{"name": "z:1"}, {"name": "a:1"}, {"name": "z:1"}]},
        )
        self.assertEqual(self.client.local_models(), ["a:1", "z:1"])

    def test_invalid_catalog_fails_closed(self):
        for data in (
            {},
            {"models": {}},
            {"models": [None]},
            {"models": [{"name": "bad name"}]},
            {"models": [{"name": MODEL}] * (MAX_MODELS + 1)},
        ):
            with self.subTest(data=str(data)[:80]):
                self.server.responses["/api/tags"] = (200, data)
                self.assert_code("invalid_catalog", self.client.catalog)

    def test_inspection_checks_capabilities_without_inference(self):
        value = self.client.inspect_model(require_tools=True)
        self.assertTrue(value["tool_calling"])
        self.assertFalse(value["inference_tested"])
        self.assertEqual(value["quantization"], "Q4_K_M")
        self.assertEqual(
            [x[0] for x in self.server.requests], ["/api/tags", "/api/show"]
        )

    def test_alias_remote_metadata_rejected_before_chat(self):
        for field in ("remote_host", "remote_model"):
            with self.subTest(field=field):
                self.server.requests.clear()
                self.server.responses["/api/show"] = (
                    200,
                    {"capabilities": ["completion", "tools"], field: "remote"},
                )
                self.assert_code(
                    "cloud_model_blocked", lambda: self.client.chat(MESSAGES)
                )
                self.assertNotIn("/api/chat", [x[0] for x in self.server.requests])

    def test_missing_model_does_not_pull_or_chat(self):
        self.client.model = "missing:latest"
        self.assert_code("model_not_installed", lambda: self.client.chat(MESSAGES))
        self.assertEqual([x[0] for x in self.server.requests], ["/api/tags"])

    def test_embedding_model_not_accepted_as_analyst(self):
        self.server.responses["/api/show"] = (200, {"capabilities": ["embedding"]})
        self.assert_code("completion_unsupported", lambda: self.client.chat(MESSAGES))

    def test_missing_or_malformed_capabilities_are_not_guessed(self):
        for capabilities in (None, "completion", [1]):
            with self.subTest(capabilities=capabilities):
                self.server.responses["/api/show"] = (
                    200,
                    {"capabilities": capabilities},
                )
                self.assert_code("capabilities_unknown", self.client.inspect_model)

    def test_analysis_only_model_cannot_be_used_as_tool_agent(self):
        self.server.responses["/api/show"] = (200, {"capabilities": ["completion"]})
        self.assert_code(
            "tools_unsupported", lambda: self.client.chat(MESSAGES, tools=[TOOL])
        )
        self.assertNotIn("/api/chat", [x[0] for x in self.server.requests])
        self.assertEqual(self.client.chat(MESSAGES)["content"], "Observed only")

    def test_inference_revalidates_model_metadata_each_time(self):
        self.client.chat(MESSAGES)
        self.server.responses["/api/show"] = (200, {"remote_host": "changed"})
        self.assert_code("cloud_model_blocked", lambda: self.client.chat(MESSAGES))
        self.assertEqual(
            len([x for x in self.server.requests if x[0] == "/api/chat"]), 1
        )

    def test_runtime_controls_model_stream_and_resource_options(self):
        self.client.chat(MESSAGES)
        data = self.server.requests[-1][1]
        self.assertEqual(data["model"], MODEL)
        self.assertIs(data["stream"], False)
        self.assertEqual(
            data["options"], {"temperature": 0, "num_predict": 768, "num_ctx": 4096}
        )
        self.assertEqual(data["keep_alive"], "2m")

    def test_model_config_overrides_fail_before_network(self):
        for key in ("model", "stream", "options", "endpoint", "keep_alive"):
            with self.subTest(key=key):
                self.assert_code(
                    "override_blocked",
                    lambda: self.client.chat(MESSAGES, **{key: "override"}),
                )
        self.assertEqual(self.server.requests, [])

    def test_invalid_messages_fail_before_network(self):
        for messages in (
            [],
            MESSAGES * 17,
            [{"role": "user", "content": None}],
            [{"role": "user", "content": "x", "images": ["x"]}],
        ):
            with self.subTest(messages=str(messages)[:80]), self.assertRaises(
                ValueError
            ):
                self.client.chat(messages)
        self.assertEqual(self.server.requests, [])

    def test_tool_count_is_bounded(self):
        with self.assertRaises(ValueError):
            self.client.chat(MESSAGES, tools=[TOOL, TOOL])
        self.assertEqual(self.server.requests, [])

    def test_sensitive_request_is_not_sent_when_oversized(self):
        self.assert_code(
            "request_too_large",
            lambda: self.client.chat([{"role": "user", "content": "x" * 70000}]),
        )
        self.assertNotIn("/api/chat", [x[0] for x in self.server.requests])

    def test_thinking_and_images_not_retained(self):
        self.assertEqual(
            self.client.chat(MESSAGES),
            {"role": "assistant", "content": "Observed only"},
        )

    def test_incomplete_response_is_not_success(self):
        self.server.responses["/api/chat"] = (
            200,
            {"message": {"content": "partial"}, "done": False},
        )
        self.assert_code("incomplete_response", lambda: self.client.chat(MESSAGES))

    def test_length_truncation_is_explicit(self):
        self.server.responses["/api/chat"] = (
            200,
            {"message": {"content": "cut off"}, "done": True, "done_reason": "length"},
        )
        self.assert_code("output_truncated", lambda: self.client.chat(MESSAGES))

    def test_remote_execution_warning_cannot_claim_prevention(self):
        self.server.responses["/api/chat"] = (
            200,
            {"done": True, "remote_host": "remote", "message": {"content": "not used"}},
        )
        error = self.assert_code(
            "remote_execution_reported", lambda: self.client.chat(MESSAGES)
        )
        self.assertIn("cannot undo", error.next_step)

    def test_malformed_tool_response_rejected(self):
        for calls in (
            "text",
            [None],
            [{"function": "bad"}],
            [{"function": {}}, {"function": {}}],
        ):
            with self.subTest(calls=calls):
                self.server.responses["/api/chat"] = (
                    200,
                    {"done": True, "message": {"content": "", "tool_calls": calls}},
                )
                self.assert_code(
                    "invalid_tool_call",
                    lambda: self.client.chat(MESSAGES, tools=[TOOL]),
                )

    def test_http_error_categories_do_not_leak_raw_body(self):
        for status, code in (
            (302, "redirect_blocked"),
            (401, "authentication_unsupported"),
            (403, "authentication_unsupported"),
            (404, "not_found"),
            (429, "busy"),
            (503, "busy"),
            (500, "service_error"),
        ):
            with self.subTest(status=status):
                self.server.responses["/api/tags"] = (
                    status,
                    {"error": "SECRET-DO-NOT-REPEAT"},
                )
                error = self.assert_code(code, self.client.catalog)
                self.assertNotIn("SECRET", json.dumps(error.public()))

    def test_redirect_is_not_followed(self):
        self.server.responses["/api/tags"] = (302, {})
        self.assert_code("redirect_blocked", self.client.catalog)
        self.assertEqual(len(self.server.requests), 1)

    def test_invalid_and_oversized_json_rejected(self):
        for value, code in (
            (b"not-json", "invalid_response"),
            (b"[]", "invalid_response"),
            ({"error": "SECRET"}, "invalid_response"),
            (b" " * (MAX_RESPONSE_BYTES + 1), "response_too_large"),
        ):
            with self.subTest(code=code):
                self.server.responses["/api/tags"] = (200, value)
                self.assert_code(code, self.client.catalog)

    def test_diagnostics_return_recoverable_machine_readable_state(self):
        self.server.responses["/api/tags"] = (503, {})
        value = self.client.diagnostics()
        self.assertIs(value["available"], False)
        self.assertIs(value["retryable"], True)
        self.assertEqual(value["state"], "busy")
        self.assertEqual(value["models"], [])

    def test_no_pull_or_mutating_routes(self):
        for route in (
            "/api/pull",
            "/api/create",
            "/api/push",
            "/api/delete",
            "/api/web_search",
            "https://example.invalid/api/chat",
        ):
            with self.subTest(route=route):
                self.assert_code(
                    "route_blocked", lambda: self.client.request(route, {})
                )
        self.assertEqual(self.server.requests, [])

    def test_http_method_contract_is_closed(self):
        self.assert_code("route_blocked", lambda: self.client.request("/api/tags", {}))
        self.assert_code("route_blocked", lambda: self.client.request("/api/show"))

    def test_complete_summary_round_trip_through_protocol_fixture(self):
        expected = {
            "summary": "Observed only",
            "next_steps": [],
            "limitations": ["Synthetic fixture"],
        }
        self.server.responses["/api/chat"] = (
            200,
            {"done": True, "message": {"content": json.dumps(expected)}},
        )
        self.assertEqual(self.client.summarize(REPORT), expected)
        self.assertEqual(self.server.requests[-1][1]["format"]["type"], "object")


class ConfigurationTests(unittest.TestCase):
    def test_invalid_names(self):
        for name in (
            None,
            3,
            " space",
            "a b",
            "../model",
            "x//y",
            "x/",
            "x:bad:tag",
            "https://remote/model",
            "x\n",
            "x" * 201,
        ):
            with self.subTest(name=name), self.assertRaises(ValueError):
                Ollama(name)

    def test_valid_installed_name_forms(self):
        for name in ("llama3.2:latest", "team/model:Q4_K_M", "model", "my-model:v1"):
            with self.subTest(name=name):
                self.assertTrue(valid_model_name(name))
                self.assertEqual(Ollama(name).model, name)

    def test_empty_name_is_for_discovery_only(self):
        self.assertEqual(Ollama("").model, "")

    def test_cloud_names_rejected(self):
        for name in ("x:cloud", "x:CLOUD", "x-cloud:latest"):
            with self.subTest(name=name), self.assertRaises(OllamaError):
                Ollama(name)

    def test_invalid_port_does_not_silently_use_default(self):
        for port in (0, -1, 65536, True, 1.2, "abc", "١١٤٣٤", "80 "):
            with self.subTest(port=port), self.assertRaises(OllamaError):
                Ollama(MODEL, port)

    def test_endpoint_environment_cannot_change_loopback_host(self):
        with patch.dict(
            os.environ,
            {
                "SECSCAN_AI_OLLAMA_PORT": "12345",
                "OLLAMA_HOST": "https://example.invalid",
                "HTTP_PROXY": "https://example.invalid",
            },
        ):
            self.assertEqual(Ollama(MODEL).endpoint, "http://127.0.0.1:12345")

    def test_socket_failures_are_categorized_and_connection_closed(self):
        for error, code in (
            (TimeoutError(), "timeout"),
            (ConnectionRefusedError(), "unreachable"),
            (http.client.BadStatusLine("bad"), "invalid_response"),
        ):
            with self.subTest(code=code):
                connection = Mock()
                connection.request.side_effect = error
                with patch(
                    "workbench.ollama_runtime.http.client.HTTPConnection",
                    return_value=connection,
                ) as factory:
                    result = Ollama(MODEL).diagnostics()
                self.assertEqual(result["state"], code)
                connection.close.assert_called_once()
                factory.assert_called_once_with("127.0.0.1", 11434, timeout=3)

    def test_legacy_mocked_planning_contract_still_works(self):
        client = Ollama(MODEL)
        client.local_models = Mock(return_value=[MODEL])
        client.chat = Mock(
            side_effect=[
                {
                    "tool_calls": [
                        {"function": {"name": "verify_lab_canary", "arguments": {}}}
                    ]
                },
                {"content": "done"},
            ]
        )
        execute = Mock(return_value={"demonstrated": True})
        self.assertEqual(
            len(client.plan(execute, copy.deepcopy(REPORT), lambda: None)), 1
        )
        execute.assert_called_once_with("verify_lab_canary", {})

    def test_malformed_planning_call_never_executes(self):
        client = Ollama(MODEL)
        client.local_models = Mock(return_value=[MODEL])
        client.chat = Mock(return_value={"tool_calls": [None]})
        execute = Mock()
        with self.assertRaises(ValueError):
            client.plan(execute, copy.deepcopy(REPORT), lambda: None)
        execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
