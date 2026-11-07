"""
Tests for HackBot HTTP Proxy / Traffic Capture module.
"""

import json
import time
import threading
from unittest.mock import patch, MagicMock

import pytest

from hackbot.core.proxy import (
    CapturedRequest,
    ProxyEngine,
    RequestMethod,
    TrafficFlag,
    _detect_flags,
    _FLAG_PATTERNS_COMPILED,
    get_proxy_engine,
    reset_proxy_engine,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_request(
    id: int = 1,
    method: str = "GET",
    url: str = "http://example.com/path",
    host: str = "example.com",
    path: str = "/path",
    request_headers: dict | None = None,
    request_body: str = "",
    status_code: int = 200,
    response_headers: dict | None = None,
    response_body: str = "",
    response_size: int = 0,
    duration_ms: float = 42.0,
    flags: list | None = None,
    is_https: bool = False,
    error: str = "",
) -> CapturedRequest:
    return CapturedRequest(
        id=id,
        timestamp=time.time(),
        method=method,
        url=url,
        host=host,
        path=path,
        request_headers=request_headers or {"Host": host, "Accept": "*/*"},
        request_body=request_body,
        status_code=status_code,
        response_headers=response_headers or {"Content-Type": "text/html"},
        response_body=response_body,
        response_size=response_size or len(response_body),
        duration_ms=duration_ms,
        flags=flags or [],
        is_https=is_https,
        error=error,
    )


# ── RequestMethod Enum ───────────────────────────────────────────────────────


class TestRequestMethod:
    def test_all_methods(self):
        methods = [m.value for m in RequestMethod]
        for expected in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD",
                         "OPTIONS", "CONNECT", "TRACE", "OTHER"):
            assert expected in methods

    def test_from_str_valid(self):
        assert RequestMethod.from_str("get") == RequestMethod.GET
        assert RequestMethod.from_str("POST") == RequestMethod.POST
        assert RequestMethod.from_str("Delete") == RequestMethod.DELETE

    def test_from_str_unknown(self):
        assert RequestMethod.from_str("FOO") == RequestMethod.OTHER
        assert RequestMethod.from_str("") == RequestMethod.OTHER


# ── TrafficFlag Enum ─────────────────────────────────────────────────────────


class TestTrafficFlag:
    def test_all_flags(self):
        flags = [f.value for f in TrafficFlag]
        for expected in ("auth_token", "cookie", "credentials", "error_response",
                         "redirect", "sensitive_data", "sql_pattern",
                         "file_upload", "api_key", "cors_header"):
            assert expected in flags

    def test_flag_string_values(self):
        assert TrafficFlag.AUTH_TOKEN == "auth_token"
        assert TrafficFlag.SQL_PATTERN == "sql_pattern"


# ── CapturedRequest ──────────────────────────────────────────────────────────


class TestCapturedRequest:
    def test_create_basic(self):
        req = _make_request()
        assert req.id == 1
        assert req.method == "GET"
        assert req.url == "http://example.com/path"

    def test_to_dict(self):
        req = _make_request(flags=["auth_token", "cookie"])
        d = req.to_dict()
        assert d["id"] == 1
        assert d["method"] == "GET"
        assert d["flags"] == ["auth_token", "cookie"]
        assert isinstance(d["duration_ms"], float)
        assert isinstance(d["request_headers"], dict)

    def test_to_dict_truncates_response_body(self):
        long_body = "x" * 5000
        req = _make_request(response_body=long_body)
        d = req.to_dict()
        assert len(d["response_body"]) == 2000

    def test_from_dict(self):
        req = _make_request(flags=["cookie"])
        d = req.to_dict()
        restored = CapturedRequest.from_dict(d)
        assert restored.id == req.id
        assert restored.method == req.method
        assert restored.url == req.url
        assert restored.flags == ["cookie"]

    def test_from_dict_defaults(self):
        restored = CapturedRequest.from_dict({})
        assert restored.id == 0
        assert restored.method == "GET"
        assert restored.url == ""
        assert restored.flags == []

    def test_roundtrip(self):
        req = _make_request(
            id=42,
            method="POST",
            url="https://target.com/api",
            request_body='{"key":"value"}',
            status_code=201,
            flags=["auth_token"],
            is_https=True,
        )
        d = req.to_dict()
        restored = CapturedRequest.from_dict(d)
        assert restored.id == req.id
        assert restored.method == req.method
        assert restored.url == req.url
        assert restored.request_body == req.request_body
        assert restored.status_code == req.status_code
        assert restored.flags == req.flags
        assert restored.is_https == req.is_https

    def test_matches_filter_url(self):
        req = _make_request(url="http://target.com/api/v2/users")
        assert req.matches_filter("users")
        assert req.matches_filter("api/v2")
        assert not req.matches_filter("admin")

    def test_matches_filter_case_insensitive(self):
        req = _make_request(url="http://TARGET.COM/Admin")
        assert req.matches_filter("target")
        assert req.matches_filter("ADMIN")
        assert req.matches_filter("Target.Com")

    def test_matches_filter_header(self):
        req = _make_request(request_headers={"Authorization": "Bearer token123"})
        assert req.matches_filter("Bearer")
        assert req.matches_filter("Authorization")

    def test_matches_filter_body(self):
        req = _make_request(request_body="password=secret123")
        assert req.matches_filter("password")
        assert req.matches_filter("secret123")

    def test_matches_filter_response_body(self):
        req = _make_request(response_body="<html>Welcome admin</html>")
        assert req.matches_filter("Welcome admin")

    def test_get_summary(self):
        req = _make_request(id=5, method="POST", url="http://x.com/login",
                            status_code=401, duration_ms=123.4, response_size=512,
                            flags=["credentials"])
        s = req.get_summary()
        assert "#5" in s
        assert "POST" in s
        assert "http://x.com/login" in s
        assert "401" in s
        assert "512B" in s
        assert "credentials" in s

    def test_get_summary_no_flags(self):
        req = _make_request()
        s = req.get_summary()
        assert "[" not in s  # no flags bracket


# ── Flag Detection ───────────────────────────────────────────────────────────


class TestFlagDetection:
    def test_auth_token(self):
        req = _make_request(request_headers={"Authorization": "Bearer eyJhbGciOi..."})
        flags = _detect_flags(req)
        assert "auth_token" in flags

    def test_cookie(self):
        req = _make_request(response_headers={"Set-Cookie": "session=abc123; Path=/"})
        flags = _detect_flags(req)
        assert "cookie" in flags

    def test_credentials(self):
        req = _make_request(request_body="username=admin&password=secret")
        flags = _detect_flags(req)
        assert "credentials" in flags

    def test_api_key(self):
        req = _make_request(request_headers={"X-Api-Key": "key123"},
                            request_body="api_key=abcdef123456")
        flags = _detect_flags(req)
        assert "api_key" in flags

    def test_sql_pattern(self):
        req = _make_request(request_body="id=1 UNION SELECT * FROM users")
        flags = _detect_flags(req)
        assert "sql_pattern" in flags

    def test_sql_pattern_insert(self):
        req = _make_request(request_body="INSERT INTO accounts VALUES (1, 'admin')")
        flags = _detect_flags(req)
        assert "sql_pattern" in flags

    def test_file_upload(self):
        req = _make_request(
            request_headers={"Content-Type": "multipart/form-data; boundary=---xxx"})
        flags = _detect_flags(req)
        assert "file_upload" in flags

    def test_cors_header(self):
        req = _make_request(
            response_headers={"Access-Control-Allow-Origin": "*"})
        flags = _detect_flags(req)
        assert "cors_header" in flags

    def test_sensitive_data_ssn(self):
        req = _make_request(response_body="SSN: 123-45-6789")
        flags = _detect_flags(req)
        assert "sensitive_data" in flags

    def test_sensitive_data_credit_card(self):
        req = _make_request(response_body="card: 4111 1111 1111 1111")
        flags = _detect_flags(req)
        assert "sensitive_data" in flags

    def test_redirect_302(self):
        req = _make_request(status_code=302)
        flags = _detect_flags(req)
        assert "redirect" in flags

    def test_redirect_301(self):
        req = _make_request(status_code=301)
        flags = _detect_flags(req)
        assert "redirect" in flags

    def test_error_response_500(self):
        req = _make_request(status_code=500)
        flags = _detect_flags(req)
        assert "error_response" in flags

    def test_error_response_503(self):
        req = _make_request(status_code=503)
        flags = _detect_flags(req)
        assert "error_response" in flags

    def test_no_flags_clean_request(self):
        req = _make_request(
            request_headers={"Host": "example.com", "Accept": "text/html"},
            request_body="",
            response_headers={"Content-Type": "text/html"},
            response_body="<html>Hello</html>",
            status_code=200,
        )
        flags = _detect_flags(req)
        assert flags == []

    def test_multiple_flags(self):
        req = _make_request(
            request_headers={"Authorization": "Bearer xxx",
                             "Content-Type": "multipart/form-data; boundary=---"},
            request_body="password=secret",
            status_code=500,
        )
        flags = _detect_flags(req)
        assert "auth_token" in flags
        assert "credentials" in flags
        assert "file_upload" in flags
        assert "error_response" in flags

    def test_no_duplicate_flags(self):
        req = _make_request(
            request_headers={"Authorization": "Bearer token1"},
            request_body="token=abc Authorization: Bearer token2",
        )
        flags = _detect_flags(req)
        # Even if pattern matches multiple times, flag should appear only once
        assert flags.count("auth_token") == 1


# ── ProxyEngine (unit tests, no actual server) ──────────────────────────────


class TestProxyEngine:
    def setup_method(self):
        reset_proxy_engine()
        self.engine = ProxyEngine()

    def test_initial_state(self):
        assert not self.engine.is_running
        assert self.engine.port == 8080
        assert self.engine.scope == []
        assert self.engine.get_traffic() == []

    def test_record_single(self):
        req = _make_request()
        self.engine._record(req)
        traffic = self.engine.get_traffic()
        assert len(traffic) == 1
        assert traffic[0].id == 1

    def test_record_multiple(self):
        for i in range(5):
            self.engine._record(_make_request(id=i + 1))
        assert len(self.engine.get_traffic()) == 5

    def test_get_traffic_most_recent_first(self):
        for i in range(3):
            self.engine._record(_make_request(id=i + 1, url=f"http://x.com/{i}"))
        traffic = self.engine.get_traffic()
        assert traffic[0].id == 3  # most recent first

    def test_get_traffic_limit(self):
        for i in range(10):
            self.engine._record(_make_request(id=i + 1))
        traffic = self.engine.get_traffic(limit=3)
        assert len(traffic) == 3
        assert traffic[0].id == 10  # most recent

    def test_get_traffic_filter(self):
        self.engine._record(_make_request(id=1, url="http://x.com/admin"))
        self.engine._record(_make_request(id=2, url="http://x.com/public"))
        self.engine._record(_make_request(id=3, url="http://x.com/admin/users"))
        traffic = self.engine.get_traffic(filter_term="admin")
        assert len(traffic) == 2
        assert all("admin" in r.url for r in traffic)

    def test_get_traffic_method_filter(self):
        self.engine._record(_make_request(id=1, method="GET"))
        self.engine._record(_make_request(id=2, method="POST"))
        self.engine._record(_make_request(id=3, method="GET"))
        traffic = self.engine.get_traffic(method="POST")
        assert len(traffic) == 1
        assert traffic[0].method == "POST"

    def test_get_traffic_combined_filters(self):
        self.engine._record(_make_request(id=1, method="GET", url="http://x.com/api"))
        self.engine._record(_make_request(id=2, method="POST", url="http://x.com/api"))
        self.engine._record(_make_request(id=3, method="GET", url="http://x.com/home"))
        traffic = self.engine.get_traffic(filter_term="api", method="GET")
        assert len(traffic) == 1
        assert traffic[0].id == 1

    def test_get_request_by_id(self):
        self.engine._record(_make_request(id=1))
        self.engine._record(_make_request(id=2))
        self.engine._record(_make_request(id=3))
        req = self.engine.get_request_by_id(2)
        assert req is not None
        assert req.id == 2

    def test_get_request_by_id_not_found(self):
        self.engine._record(_make_request(id=1))
        assert self.engine.get_request_by_id(99) is None

    def test_get_flagged_traffic(self):
        self.engine._record(_make_request(id=1, flags=["auth_token"]))
        self.engine._record(_make_request(id=2, flags=[]))
        self.engine._record(_make_request(id=3, flags=["cookie", "credentials"]))
        flagged = self.engine.get_flagged_traffic()
        assert len(flagged) == 2
        assert flagged[0].id == 1
        assert flagged[1].id == 3

    def test_get_flagged_traffic_empty(self):
        self.engine._record(_make_request(id=1, flags=[]))
        assert self.engine.get_flagged_traffic() == []

    def test_clear(self):
        for i in range(5):
            self.engine._record(_make_request(id=i + 1, response_size=100))
        count = self.engine.clear()
        assert count == 5
        assert self.engine.get_traffic() == []
        assert self.engine._total_bytes == 0

    def test_clear_resets_counter(self):
        self.engine._record(_make_request(id=1))
        self.engine.clear()
        assert self.engine._id_counter == 0

    def test_next_id_increments(self):
        assert self.engine._next_id() == 1
        assert self.engine._next_id() == 2
        assert self.engine._next_id() == 3

    def test_next_id_thread_safe(self):
        ids = []
        barrier = threading.Barrier(10)

        def get_id():
            barrier.wait()
            ids.append(self.engine._next_id())

        threads = [threading.Thread(target=get_id) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(set(ids)) == 10  # All unique

    # ── Scope ────────────────────────────────────────────────────────────

    def test_set_scope(self):
        self.engine.set_scope(["example.com", "target.org"])
        assert self.engine.scope == ["example.com", "target.org"]

    def test_set_scope_normalizes(self):
        self.engine.set_scope(["  Example.COM  ", "TARGET.org"])
        assert self.engine.scope == ["example.com", "target.org"]

    def test_set_scope_ignores_empty(self):
        self.engine.set_scope(["example.com", "", "  "])
        assert self.engine.scope == ["example.com"]

    def test_clear_scope(self):
        self.engine.set_scope(["example.com"])
        self.engine.clear_scope()
        assert self.engine.scope == []

    # ── Stats ────────────────────────────────────────────────────────────

    def test_get_stats_empty(self):
        stats = self.engine.get_stats()
        assert stats["total_requests"] == 0
        assert stats["total_bytes"] == 0
        assert stats["methods"] == {}
        assert stats["avg_duration_ms"] == 0
        assert stats["scope"] == []

    def test_get_stats_with_traffic(self):
        self.engine._record(_make_request(id=1, method="GET", status_code=200,
                                          duration_ms=10, response_size=100,
                                          host="a.com"))
        self.engine._record(_make_request(id=2, method="POST", status_code=201,
                                          duration_ms=20, response_size=200,
                                          host="a.com"))
        self.engine._record(_make_request(id=3, method="GET", status_code=404,
                                          duration_ms=30, response_size=50,
                                          host="b.com"))
        stats = self.engine.get_stats()
        assert stats["total_requests"] == 3
        assert stats["total_bytes"] == 350
        assert stats["methods"]["GET"] == 2
        assert stats["methods"]["POST"] == 1
        assert stats["status_codes"]["2xx"] == 2
        assert stats["status_codes"]["4xx"] == 1
        assert stats["avg_duration_ms"] == 20.0
        assert "a.com" in stats["top_hosts"]
        assert stats["top_hosts"]["a.com"] == 2

    def test_get_stats_with_flags(self):
        self.engine._record(_make_request(id=1, flags=["auth_token", "cookie"]))
        self.engine._record(_make_request(id=2, flags=["auth_token"]))
        stats = self.engine.get_stats()
        assert stats["flags"]["auth_token"] == 2
        assert stats["flags"]["cookie"] == 1

    def test_get_stats_with_scope(self):
        self.engine.set_scope(["example.com"])
        stats = self.engine.get_stats()
        assert stats["scope"] == ["example.com"]

    # ── Callbacks ────────────────────────────────────────────────────────

    def test_on_request_callback(self):
        captured_reqs = []
        self.engine.on_request(lambda r: captured_reqs.append(r))
        self.engine._record(_make_request(id=1))
        self.engine._record(_make_request(id=2))
        assert len(captured_reqs) == 2
        assert captured_reqs[0].id == 1

    def test_callback_error_ignored(self):
        def bad_callback(req):
            raise ValueError("oops")

        self.engine.on_request(bad_callback)
        # Should not raise
        self.engine._record(_make_request(id=1))
        assert len(self.engine.get_traffic()) == 1

    # ── Start/Stop ───────────────────────────────────────────────────────

    def test_stop_when_not_running(self):
        result = self.engine.stop()
        assert not result["ok"]
        assert "not running" in result["error"]

    def test_start_already_running(self):
        self.engine.is_running = True
        self.engine.port = 1234
        result = self.engine.start(port=9999)
        assert not result["ok"]
        assert "already running" in result["error"]

    @patch("hackbot.core.proxy._ProxyServer")
    def test_start_success(self, mock_server_cls):
        mock_server = MagicMock()
        mock_server_cls.return_value = mock_server

        result = self.engine.start(port=9090)
        assert result["ok"]
        assert result["port"] == 9090
        assert "9090" in result["message"]
        assert "curl" in result["curl_example"]
        assert "http_proxy" in result["env_hint"]
        assert self.engine.is_running

    @patch("hackbot.core.proxy._ProxyServer")
    def test_start_port_in_use(self, mock_server_cls):
        mock_server_cls.side_effect = OSError("Address already in use")
        result = self.engine.start(port=80)
        assert not result["ok"]
        assert "Cannot bind" in result["error"]
        assert not self.engine.is_running

    @patch("hackbot.core.proxy._ProxyServer")
    def test_stop_success(self, mock_server_cls):
        mock_server = MagicMock()
        mock_server_cls.return_value = mock_server

        self.engine.start(port=9090)
        self.engine._record(_make_request(id=1))

        result = self.engine.stop()
        assert result["ok"]
        assert "stopped" in result["message"].lower()
        assert result["total_requests"] == 1
        assert not self.engine.is_running
        mock_server.shutdown.assert_called_once()
        mock_server.server_close.assert_called_once()

    # ── Export JSON ──────────────────────────────────────────────────────

    def test_export_json_empty(self):
        data = json.loads(self.engine.export_traffic_json())
        assert data["traffic"] == []
        assert data["proxy_stats"]["total_requests"] == 0

    def test_export_json_with_traffic(self):
        self.engine._record(_make_request(id=1, method="GET"))
        self.engine._record(_make_request(id=2, method="POST"))
        data = json.loads(self.engine.export_traffic_json())
        assert len(data["traffic"]) == 2
        assert "exported_at" in data

    def test_export_json_with_filter(self):
        self.engine._record(_make_request(id=1, url="http://a.com/admin"))
        self.engine._record(_make_request(id=2, url="http://a.com/public"))
        data = json.loads(self.engine.export_traffic_json(filter_term="admin"))
        assert len(data["traffic"]) == 1

    def test_export_json_with_limit(self):
        for i in range(10):
            self.engine._record(_make_request(id=i + 1))
        data = json.loads(self.engine.export_traffic_json(limit=3))
        assert len(data["traffic"]) == 3

    # ── Export Markdown ──────────────────────────────────────────────────

    def test_export_markdown_empty(self):
        md = self.engine.export_traffic_markdown()
        assert "Traffic Capture Report" in md
        assert "Total Requests:** 0" in md

    def test_export_markdown_with_traffic(self):
        self.engine._record(_make_request(id=1, method="GET", status_code=200,
                                          flags=["cookie"]))
        self.engine._record(_make_request(id=2, method="POST", status_code=500,
                                          flags=["error_response"]))
        md = self.engine.export_traffic_markdown()
        assert "GET" in md
        assert "POST" in md
        assert "Flagged Requests" in md

    def test_export_markdown_includes_scope(self):
        self.engine.set_scope(["example.com"])
        md = self.engine.export_traffic_markdown()
        assert "example.com" in md

    def test_export_markdown_table(self):
        self.engine._record(_make_request(id=1))
        md = self.engine.export_traffic_markdown()
        assert "| #" in md
        assert "| Method |" in md

    # ── Detail Markdown ──────────────────────────────────────────────────

    def test_get_request_detail_markdown(self):
        req = _make_request(
            id=5,
            method="POST",
            url="http://target.com/login",
            host="target.com",
            request_headers={"Content-Type": "application/json"},
            request_body='{"user":"admin","pass":"secret"}',
            status_code=401,
            response_headers={"Content-Type": "application/json"},
            response_body='{"error":"unauthorized"}',
            flags=["credentials"],
            duration_ms=150.5,
        )
        md = ProxyEngine.get_request_detail_markdown(req)
        assert "#5" in md
        assert "POST" in md
        assert "target.com" in md
        assert "401" in md
        assert "credentials" in md
        assert "Request Headers" in md
        assert "Request Body" in md
        assert "Response Headers" in md
        assert "Response Body" in md
        assert "admin" in md

    def test_get_request_detail_markdown_no_body(self):
        req = _make_request(request_body="", response_body="")
        md = ProxyEngine.get_request_detail_markdown(req)
        assert "Request Headers" in md
        assert "Response Headers" in md
        # Body sections should not appear since bodies are empty
        # (The method checks if body is truthy before adding section)

    def test_get_request_detail_error(self):
        req = _make_request(error="Connection refused")
        md = ProxyEngine.get_request_detail_markdown(req)
        assert "Connection refused" in md
        assert "Error" in md

    # ── Replay ───────────────────────────────────────────────────────────

    def test_replay_not_found(self):
        result = self.engine.replay_request(999)
        assert result is None

    @patch("hackbot.core.proxy.urllib.request.urlopen")
    def test_replay_success(self, mock_urlopen):
        # Setup mock
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"replayed response"
        mock_resp.headers = {"Content-Type": "text/plain"}
        mock_resp.status = 200
        mock_urlopen.return_value = mock_resp

        # Record original
        self.engine._record(_make_request(
            id=1, method="GET", url="http://example.com/page",
            host="example.com", path="/page",
            request_headers={"Host": "example.com"},
        ))

        # Replay
        result = self.engine.replay_request(1)
        assert result is not None
        assert result.method == "GET"
        assert result.url == "http://example.com/page"
        assert result.status_code == 200
        assert "replayed response" in result.response_body

    @patch("hackbot.core.proxy.urllib.request.urlopen")
    def test_replay_records_new_traffic(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"ok"
        mock_resp.headers = {}
        mock_resp.status = 200
        mock_urlopen.return_value = mock_resp

        self.engine._record(_make_request(id=1))
        self.engine.replay_request(1)
        # Should have original + replayed
        assert len(self.engine.get_traffic()) == 2

    @patch("hackbot.core.proxy.urllib.request.urlopen")
    def test_replay_network_error(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Connection refused")

        self.engine._record(_make_request(id=1))
        result = self.engine.replay_request(1)
        assert result is not None
        assert "Connection refused" in result.error

    @patch("hackbot.core.proxy.urllib.request.urlopen")
    def test_replay_http_error(self, mock_urlopen):
        import urllib.error
        mock_error = urllib.error.HTTPError(
            url="http://example.com",
            code=403,
            msg="Forbidden",
            hdrs=MagicMock(),
            fp=MagicMock(),
        )
        mock_error.read = MagicMock(return_value=b"forbidden")
        mock_error.headers = {"X-Error": "denied"}
        mock_urlopen.side_effect = mock_error

        self.engine._record(_make_request(id=1))
        result = self.engine.replay_request(1)
        assert result is not None
        assert result.status_code == 403


# ── Singleton ────────────────────────────────────────────────────────────────


class TestSingleton:
    def setup_method(self):
        reset_proxy_engine()

    def teardown_method(self):
        reset_proxy_engine()

    def test_get_proxy_engine(self):
        engine = get_proxy_engine()
        assert isinstance(engine, ProxyEngine)

    def test_get_proxy_engine_returns_same(self):
        e1 = get_proxy_engine()
        e2 = get_proxy_engine()
        assert e1 is e2

    def test_reset_proxy_engine(self):
        e1 = get_proxy_engine()
        reset_proxy_engine()
        e2 = get_proxy_engine()
        assert e1 is not e2

    @patch("hackbot.core.proxy._ProxyServer")
    def test_reset_stops_running_proxy(self, mock_server_cls):
        mock_server = MagicMock()
        mock_server_cls.return_value = mock_server

        engine = get_proxy_engine()
        engine.start(port=9090)
        assert engine.is_running
        reset_proxy_engine()
        mock_server.shutdown.assert_called()


# ── Thread Safety ────────────────────────────────────────────────────────────


class TestThreadSafety:
    def test_concurrent_record(self):
        engine = ProxyEngine()
        barrier = threading.Barrier(20)

        def record(i):
            barrier.wait()
            engine._record(_make_request(id=i, response_size=10))

        threads = [threading.Thread(target=record, args=(i,)) for i in range(1, 21)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(engine.get_traffic()) == 20
        assert engine._total_bytes == 200

    def test_concurrent_read_write(self):
        engine = ProxyEngine()
        barrier = threading.Barrier(20)

        def writer(i):
            barrier.wait()
            engine._record(_make_request(id=i))

        def reader():
            barrier.wait()
            engine.get_traffic()
            engine.get_stats()

        threads = []
        for i in range(1, 11):
            threads.append(threading.Thread(target=writer, args=(i,)))
        for _ in range(10):
            threads.append(threading.Thread(target=reader))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(engine.get_traffic()) == 10


# ── Integration-level edge cases ─────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_request_body(self):
        req = _make_request(request_body="")
        d = req.to_dict()
        assert d["request_body"] == ""

    def test_empty_response_body(self):
        req = _make_request(response_body="")
        d = req.to_dict()
        assert d["response_body"] == ""

    def test_large_traffic_export(self):
        engine = ProxyEngine()
        for i in range(100):
            engine._record(_make_request(id=i + 1, response_size=1024))
        data = json.loads(engine.export_traffic_json())
        assert len(data["traffic"]) == 100

    def test_filter_no_match(self):
        engine = ProxyEngine()
        engine._record(_make_request(id=1, url="http://a.com"))
        assert engine.get_traffic(filter_term="nonexistent") == []

    def test_method_filter_case_insensitive(self):
        engine = ProxyEngine()
        engine._record(_make_request(id=1, method="GET"))
        assert len(engine.get_traffic(method="get")) == 1
        assert len(engine.get_traffic(method="GET")) == 1

    def test_stats_avg_duration_no_requests(self):
        engine = ProxyEngine()
        stats = engine.get_stats()
        assert stats["avg_duration_ms"] == 0

    def test_scope_empty_domains(self):
        engine = ProxyEngine()
        engine.set_scope(["", "  ", "example.com", ""])
        assert len(engine.scope) == 1
        assert engine.scope[0] == "example.com"

    def test_detail_markdown_truncates_large_bodies(self):
        req = _make_request(
            request_body="x" * 5000,
            response_body="y" * 5000,
        )
        md = ProxyEngine.get_request_detail_markdown(req)
        assert "x" * 2000 in md
        assert "y" * 2000 in md
        # Bodies in detail are truncated to 2000 chars
        assert "x" * 2001 not in md
        assert "y" * 2001 not in md

    def test_compiled_flag_patterns_count(self):
        # Ensure all patterns are compiled
        assert len(_FLAG_PATTERNS_COMPILED) == 8

    def test_request_method_covers_standard(self):
        for m in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "CONNECT", "TRACE"):
            assert RequestMethod.from_str(m).value == m
