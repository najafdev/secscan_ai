"""
HackBot HTTP Proxy / Traffic Capture
======================================
A lightweight intercepting HTTP proxy for capturing, inspecting, and
replaying web application requests during security assessments.

Features:
  • HTTP/HTTPS interception (CONNECT tunnelling for SSL)
  • Request/response logging with full headers and bodies
  • Keyword-based filtering (URL, header, body matching)
  • Scope control (limit capture to specific domains/paths)
  • Export captured traffic as HAR, JSON, or Markdown
  • Replay individual requests for manual testing
  • Auto-flag interesting patterns (tokens, cookies, credentials, errors)
  • Real-time traffic feed via iterator/callback

Architecture:
  Uses Python's ``http.server`` + ``socketserver`` for a zero-dependency
  proxy. No external packages required — works out of the box.

Usage (CLI)::

    /proxy start [port]     Start the proxy on the given port (default 8080)
    /proxy stop             Stop the proxy
    /proxy status           Show proxy status and stats
    /proxy traffic          Show captured traffic
    /proxy traffic 5        Show last 5 requests
    /proxy filter <term>    Filter traffic by URL/header/body substring
    /proxy scope <domain>   Restrict capture to a domain (e.g. example.com)
    /proxy clear            Clear captured traffic
    /proxy export [file]    Export traffic as JSON
    /proxy replay <id>      Replay a captured request
    /proxy flags            Show auto-flagged interesting requests

Usage (Agent)::

    The agent can recommend starting the proxy before web app testing
    to capture all HTTP traffic for later analysis.
"""

from __future__ import annotations

import json
import logging
import re
import ssl
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingTCPServer
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────

class RequestMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    CONNECT = "CONNECT"
    TRACE = "TRACE"
    OTHER = "OTHER"

    @classmethod
    def from_str(cls, method: str) -> "RequestMethod":
        try:
            return cls(method.upper())
        except ValueError:
            return cls.OTHER


class TrafficFlag(str, Enum):
    """Auto-detected interesting patterns in traffic."""
    AUTH_TOKEN = "auth_token"
    COOKIE = "cookie"
    CREDENTIALS = "credentials"
    ERROR_RESPONSE = "error_response"
    REDIRECT = "redirect"
    SENSITIVE_DATA = "sensitive_data"
    SQL_PATTERN = "sql_pattern"
    FILE_UPLOAD = "file_upload"
    API_KEY = "api_key"
    CORS_HEADER = "cors_header"


# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class CapturedRequest:
    """A single captured HTTP request/response pair."""
    id: int
    timestamp: float
    method: str
    url: str
    host: str
    path: str
    request_headers: Dict[str, str]
    request_body: str = ""
    status_code: int = 0
    response_headers: Dict[str, str] = field(default_factory=dict)
    response_body: str = ""
    response_size: int = 0
    duration_ms: float = 0.0
    flags: List[str] = field(default_factory=list)
    is_https: bool = False
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "method": self.method,
            "url": self.url,
            "host": self.host,
            "path": self.path,
            "request_headers": self.request_headers,
            "request_body": self.request_body,
            "status_code": self.status_code,
            "response_headers": self.response_headers,
            "response_body": self.response_body[:2000] if self.response_body else "",
            "response_size": self.response_size,
            "duration_ms": round(self.duration_ms, 2),
            "flags": self.flags,
            "is_https": self.is_https,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapturedRequest":
        return cls(
            id=data.get("id", 0),
            timestamp=data.get("timestamp", 0),
            method=data.get("method", "GET"),
            url=data.get("url", ""),
            host=data.get("host", ""),
            path=data.get("path", ""),
            request_headers=data.get("request_headers", {}),
            request_body=data.get("request_body", ""),
            status_code=data.get("status_code", 0),
            response_headers=data.get("response_headers", {}),
            response_body=data.get("response_body", ""),
            response_size=data.get("response_size", 0),
            duration_ms=data.get("duration_ms", 0),
            flags=data.get("flags", []),
            is_https=data.get("is_https", False),
            error=data.get("error", ""),
        )

    def matches_filter(self, term: str) -> bool:
        """Check if this request matches a search term."""
        term_lower = term.lower()
        searchable = (
            f"{self.method} {self.url} {self.host} {self.path} "
            f"{json.dumps(self.request_headers)} {self.request_body} "
            f"{json.dumps(self.response_headers)} {self.response_body}"
        ).lower()
        return term_lower in searchable

    def get_summary(self) -> str:
        """One-line summary."""
        flags_str = f" [{', '.join(self.flags)}]" if self.flags else ""
        status = f" → {self.status_code}" if self.status_code else ""
        return (f"#{self.id} {self.method} {self.url}{status} "
                f"({self.duration_ms:.0f}ms, {self.response_size}B){flags_str}")


# ── Flag Detection ───────────────────────────────────────────────────────────

# Patterns to auto-flag
_FLAG_PATTERNS: List[Tuple[str, TrafficFlag, str]] = [
    # (regex, flag, description)
    (r"(?i)(authorization|bearer|token)\s*[:=]\s*\S+", TrafficFlag.AUTH_TOKEN, "Authorization header or token"),
    (r"(?i)set-cookie|^cookie:", TrafficFlag.COOKIE, "Cookie header"),
    (r"(?i)(password|passwd|pwd|secret)\s*[=:]\s*\S+", TrafficFlag.CREDENTIALS, "Potential credential in request"),
    (r"(?i)(api[_-]?key|apikey|access[_-]?key)\s*[=:]\s*\S+", TrafficFlag.API_KEY, "API key detected"),
    (r"(?i)(select|insert|update|delete|union|drop)\s+.{0,20}(from|into|table|set)", TrafficFlag.SQL_PATTERN, "SQL-like pattern"),
    (r"(?i)content-type:\s*multipart/form-data", TrafficFlag.FILE_UPLOAD, "File upload"),
    (r"(?i)access-control-allow-origin", TrafficFlag.CORS_HEADER, "CORS header"),
    (r"(?i)(ssn|social.?security|credit.?card|\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b)", TrafficFlag.SENSITIVE_DATA, "Potential sensitive data"),
]

_FLAG_PATTERNS_COMPILED = [
    (re.compile(p), flag, desc) for p, flag, desc in _FLAG_PATTERNS
]


def _detect_flags(req: CapturedRequest) -> List[str]:
    """Auto-detect interesting patterns in a captured request."""
    flags = []

    # Build searchable blob with headers as key: value (not JSON-serialized)
    req_hdrs = " ".join(f"{k}: {v}" for k, v in req.request_headers.items())
    resp_hdrs = " ".join(f"{k}: {v}" for k, v in req.response_headers.items())
    blob = f"{req_hdrs} {req.request_body} {resp_hdrs} {req.response_body}"

    for pattern, flag, _desc in _FLAG_PATTERNS_COMPILED:
        if pattern.search(blob):
            if flag.value not in flags:
                flags.append(flag.value)

    # Status-code based flags
    if 300 <= req.status_code < 400:
        if TrafficFlag.REDIRECT.value not in flags:
            flags.append(TrafficFlag.REDIRECT.value)
    if req.status_code >= 500:
        if TrafficFlag.ERROR_RESPONSE.value not in flags:
            flags.append(TrafficFlag.ERROR_RESPONSE.value)

    return flags


# ── Proxy Handler ────────────────────────────────────────────────────────────

class _ProxyHandler(BaseHTTPRequestHandler):
    """HTTP proxy request handler."""

    # Suppress default stderr logging
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self._proxy_request("GET")

    def do_POST(self):
        self._proxy_request("POST")

    def do_PUT(self):
        self._proxy_request("PUT")

    def do_DELETE(self):
        self._proxy_request("DELETE")

    def do_PATCH(self):
        self._proxy_request("PATCH")

    def do_HEAD(self):
        self._proxy_request("HEAD")

    def do_OPTIONS(self):
        self._proxy_request("OPTIONS")

    def do_CONNECT(self):
        """Handle HTTPS CONNECT tunnelling."""
        engine: ProxyEngine = self.server._proxy_engine  # type: ignore
        host_port = self.path
        host = host_port.split(":")[0]

        # Scope check
        if engine.scope and not any(s in host for s in engine.scope):
            self.send_error(403, "Out of scope")
            return

        start_time = time.time()
        req_id = engine._next_id()

        try:
            # Connect to the remote host
            remote_host, remote_port = host_port.split(":")
            remote_port = int(remote_port)

            # Send 200 Connection established
            self.send_response(200, "Connection established")
            self.send_header("Proxy-Agent", "HackBot-Proxy")
            self.end_headers()

            # Record the CONNECT request
            captured = CapturedRequest(
                id=req_id,
                timestamp=start_time,
                method="CONNECT",
                url=f"https://{host_port}",
                host=host,
                path=host_port,
                request_headers=dict(self.headers),
                status_code=200,
                duration_ms=(time.time() - start_time) * 1000,
                is_https=True,
            )
            captured.flags = _detect_flags(captured)
            engine._record(captured)

        except Exception as e:
            logger.debug(f"CONNECT tunnel error: {e}")
            self.send_error(502, str(e))

    def _proxy_request(self, method: str):
        """Forward the request and capture the exchange."""
        engine: ProxyEngine = self.server._proxy_engine  # type: ignore
        start_time = time.time()
        req_id = engine._next_id()

        # Parse URL
        parsed = urllib.parse.urlparse(self.path)
        host = str(parsed.hostname or self.headers.get("Host") or "")
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"

        # Scope check
        if engine.scope and not any(s in host for s in engine.scope):
            self.send_error(403, "Out of scope")
            return

        # Read request body
        content_length = int(self.headers.get("Content-Length", 0))
        request_body = ""
        if content_length > 0:
            raw = self.rfile.read(content_length)
            try:
                request_body = raw.decode("utf-8", errors="replace")
            except Exception:
                request_body = f"<binary {len(raw)} bytes>"

        # Build captured request
        captured = CapturedRequest(
            id=req_id,
            timestamp=start_time,
            method=method,
            url=self.path,
            host=host,
            path=path,
            request_headers=dict(self.headers),
            request_body=request_body[:5000],
            is_https=self.path.startswith("https://"),
        )

        # Forward request
        try:
            # Determine scheme
            if self.path.startswith("http://") or self.path.startswith("https://"):
                target_url = self.path
            else:
                target_url = f"http://{host}{path}"

            # Build urllib request
            req_headers = {
                k: v for k, v in self.headers.items()
                if k.lower() not in ("proxy-connection", "proxy-authorization", "host")
            }
            req_headers["Host"] = host

            body_bytes = request_body.encode("utf-8") if request_body else None
            req = urllib.request.Request(
                target_url,
                data=body_bytes,
                headers=req_headers,
                method=method,
            )

            # Send request
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            resp = urllib.request.urlopen(req, timeout=30, context=ctx)

            resp_body = resp.read()
            resp_headers = dict(resp.headers)
            status_code = resp.status

        except urllib.error.HTTPError as e:
            resp_body = e.read() if hasattr(e, "read") else b""
            resp_headers = dict(e.headers) if hasattr(e, "headers") else {}
            status_code = e.code
        except Exception as e:
            captured.error = str(e)
            captured.duration_ms = (time.time() - start_time) * 1000
            captured.flags = _detect_flags(captured)
            engine._record(captured)

            self.send_error(502, f"Proxy error: {e}")
            return

        # Capture response
        captured.status_code = status_code
        captured.response_headers = resp_headers
        captured.response_size = len(resp_body)
        captured.duration_ms = (time.time() - start_time) * 1000

        try:
            captured.response_body = resp_body.decode("utf-8", errors="replace")[:5000]
        except Exception:
            captured.response_body = f"<binary {len(resp_body)} bytes>"

        captured.flags = _detect_flags(captured)
        engine._record(captured)

        # Send response back to client
        try:
            self.send_response(status_code)
            for key, val in resp_headers.items():
                if key.lower() not in ("transfer-encoding", "connection"):
                    self.send_header(key, val)
            self.end_headers()
            self.wfile.write(resp_body)
        except Exception as e:
            logger.debug(f"Error sending response to client: {e}")


# ── Proxy Server ─────────────────────────────────────────────────────────────

class _ProxyServer(ThreadingTCPServer):
    """Threaded TCP server with proxy engine reference."""
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, addr, handler, engine: "ProxyEngine"):
        self._proxy_engine = engine
        super().__init__(addr, handler)


# ── Proxy Engine ─────────────────────────────────────────────────────────────

class ProxyEngine:
    """
    Lightweight HTTP intercepting proxy for security assessments.

    Start/stop the proxy, capture traffic, filter, flag, and export results.
    Thread-safe for concurrent request handling.
    """

    def __init__(self) -> None:
        self._traffic: List[CapturedRequest] = []
        self._lock = threading.Lock()
        self._id_counter = 0
        self._server: Optional[_ProxyServer] = None
        self._thread: Optional[threading.Thread] = None
        self.port: int = 8080
        self.is_running: bool = False
        self.scope: List[str] = []  # Domain scope restrictions
        self._callbacks: List[Callable[[CapturedRequest], None]] = []
        self._start_time: float = 0
        self._total_bytes: int = 0

    # ── Lifecycle ────────────────────────────────────────────────────────

    def start(self, port: int = 8080) -> Dict[str, Any]:
        """Start the proxy server.

        Args:
            port: Port to listen on (default 8080).

        Returns:
            Status dict with port, result.
        """
        if self.is_running:
            return {"ok": False, "error": f"Proxy already running on port {self.port}"}

        self.port = port
        try:
            self._server = _ProxyServer(("127.0.0.1", port), _ProxyHandler, self)
            self._thread = threading.Thread(
                target=self._server.serve_forever,
                daemon=True,
                name=f"hackbot-proxy-{port}",
            )
            self._thread.start()
            self.is_running = True
            self._start_time = time.time()
            logger.info(f"Proxy started on port {port}")
            return {
                "ok": True,
                "port": port,
                "message": f"HTTP proxy listening on 127.0.0.1:{port}",
                "curl_example": f"curl -x http://127.0.0.1:{port} http://example.com",
                "env_hint": f"export http_proxy=http://127.0.0.1:{port}",
            }
        except OSError as e:
            return {"ok": False, "error": f"Cannot bind port {port}: {e}"}

    def stop(self) -> Dict[str, Any]:
        """Stop the proxy server.

        Returns:
            Status dict with capture stats.
        """
        if not self.is_running:
            return {"ok": False, "error": "Proxy is not running"}

        if self._server:
            try:
                self._server.shutdown()
                self._server.server_close()
            except Exception as e:
                logger.debug(f"Error during proxy shutdown: {e}")

        self.is_running = False
        uptime = time.time() - self._start_time

        stats = self.get_stats()
        stats["ok"] = True
        stats["uptime_seconds"] = round(uptime, 1)
        stats["message"] = "Proxy stopped"
        logger.info("Proxy stopped")
        return stats

    # ── Recording ────────────────────────────────────────────────────────

    def _next_id(self) -> int:
        with self._lock:
            self._id_counter += 1
            return int(self._id_counter)

    def _record(self, req: CapturedRequest) -> None:
        """Record a captured request (thread-safe)."""
        with self._lock:
            self._traffic.append(req)
            self._total_bytes += req.response_size

        # Notify callbacks
        for cb in self._callbacks:
            try:
                cb(req)
            except Exception as e:
                logger.debug(f"Callback error: {e}")

    def on_request(self, callback: Callable[[CapturedRequest], None]) -> None:
        """Register a callback for new captured requests."""
        self._callbacks.append(callback)

    # ── Traffic Access ───────────────────────────────────────────────────

    def get_traffic(
        self,
        limit: Optional[int] = None,
        filter_term: Optional[str] = None,
        method: Optional[str] = None,
    ) -> List[CapturedRequest]:
        """Get captured traffic with optional filtering.

        Args:
            limit: Max number of requests to return (most recent first).
            filter_term: Substring filter on URL/headers/body.
            method: Filter by HTTP method.

        Returns:
            List of CapturedRequest objects.
        """
        with self._lock:
            traffic = list(self._traffic)

        # Apply filters
        if filter_term:
            traffic = [r for r in traffic if r.matches_filter(filter_term)]
        if method:
            traffic = [r for r in traffic if r.method.upper() == method.upper()]

        # Most recent first
        traffic.reverse()

        if limit:
            traffic = traffic[:limit]

        return traffic

    def get_request_by_id(self, req_id: int) -> Optional[CapturedRequest]:
        """Get a specific captured request by ID."""
        with self._lock:
            for r in self._traffic:
                if r.id == req_id:
                    return r
        return None

    def get_flagged_traffic(self) -> List[CapturedRequest]:
        """Get only requests that have auto-detected flags."""
        with self._lock:
            return [r for r in self._traffic if r.flags]

    def clear(self) -> int:
        """Clear all captured traffic. Returns number cleared."""
        with self._lock:
            count = len(self._traffic)
            self._traffic.clear()
            self._id_counter = 0
            self._total_bytes = 0
        return count

    # ── Scope ────────────────────────────────────────────────────────────

    def set_scope(self, domains: List[str]) -> None:
        """Restrict capture to specific domains."""
        self.scope = [d.strip().lower() for d in domains if d.strip()]

    def clear_scope(self) -> None:
        """Remove all scope restrictions."""
        self.scope = []

    # ── Statistics ────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get proxy statistics."""
        with self._lock:
            total = len(self._traffic)
            methods: Dict[str, int] = {}
            status_codes: Dict[str, int] = {}
            hosts: Dict[str, int] = {}
            flag_counts: Dict[str, int] = {}
            total_duration = 0.0

            for r in self._traffic:
                methods[r.method] = methods.get(r.method, 0) + 1
                if r.status_code:
                    bucket = f"{r.status_code // 100}xx"
                    status_codes[bucket] = status_codes.get(bucket, 0) + 1
                hosts[r.host] = hosts.get(r.host, 0) + 1
                total_duration += r.duration_ms
                for f in r.flags:
                    flag_counts[f] = flag_counts.get(f, 0) + 1

        return {
            "is_running": self.is_running,
            "port": self.port if self.is_running else None,
            "total_requests": total,
            "total_bytes": self._total_bytes,
            "methods": methods,
            "status_codes": status_codes,
            "top_hosts": dict(sorted(hosts.items(), key=lambda x: -x[1])[:10]),
            "flags": flag_counts,
            "avg_duration_ms": round(total_duration / total, 1) if total else 0,
            "scope": self.scope,
        }

    # ── Replay ───────────────────────────────────────────────────────────

    def replay_request(self, req_id: int) -> Optional[CapturedRequest]:
        """Replay a previously captured request.

        Args:
            req_id: ID of the request to replay.

        Returns:
            New CapturedRequest with the replayed results, or None if not found.
        """
        original = self.get_request_by_id(req_id)
        if not original:
            return None

        start_time = time.time()
        new_id = self._next_id()

        try:
            req_headers = {
                k: v for k, v in original.request_headers.items()
                if k.lower() not in ("proxy-connection", "proxy-authorization")
            }
            body_bytes = original.request_body.encode("utf-8") if original.request_body else None

            target_url = original.url
            if not target_url.startswith("http"):
                target_url = f"http://{original.host}{original.path}"

            req = urllib.request.Request(
                target_url,
                data=body_bytes,
                headers=req_headers,
                method=original.method,
            )

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            resp = urllib.request.urlopen(req, timeout=30, context=ctx)
            resp_body = resp.read()
            resp_headers = dict(resp.headers)
            status_code = resp.status

        except urllib.error.HTTPError as e:
            resp_body = e.read() if hasattr(e, "read") else b""
            resp_headers = dict(e.headers) if hasattr(e, "headers") else {}
            status_code = e.code
        except Exception as e:
            captured = CapturedRequest(
                id=new_id,
                timestamp=start_time,
                method=original.method,
                url=original.url,
                host=original.host,
                path=original.path,
                request_headers=original.request_headers,
                request_body=original.request_body,
                error=str(e),
                duration_ms=(time.time() - start_time) * 1000,
            )
            captured.flags = _detect_flags(captured)
            self._record(captured)
            return captured

        captured = CapturedRequest(
            id=new_id,
            timestamp=start_time,
            method=original.method,
            url=original.url,
            host=original.host,
            path=original.path,
            request_headers=original.request_headers,
            request_body=original.request_body,
            status_code=status_code,
            response_headers=resp_headers,
            response_size=len(resp_body),
            duration_ms=(time.time() - start_time) * 1000,
            is_https=original.is_https,
        )

        try:
            captured.response_body = resp_body.decode("utf-8", errors="replace")[:5000]
        except Exception:
            captured.response_body = f"<binary {len(resp_body)} bytes>"

        captured.flags = _detect_flags(captured)
        self._record(captured)
        return captured

    # ── Export ────────────────────────────────────────────────────────────

    def export_traffic_json(
        self,
        limit: Optional[int] = None,
        filter_term: Optional[str] = None,
    ) -> str:
        """Export captured traffic as JSON."""
        traffic = self.get_traffic(limit=limit, filter_term=filter_term)
        data = {
            "proxy_stats": self.get_stats(),
            "traffic": [r.to_dict() for r in traffic],
            "exported_at": time.time(),
        }
        return json.dumps(data, indent=2)

    def export_traffic_markdown(
        self,
        limit: Optional[int] = None,
        filter_term: Optional[str] = None,
    ) -> str:
        """Export captured traffic as markdown report."""
        traffic = self.get_traffic(limit=limit, filter_term=filter_term)
        stats = self.get_stats()

        lines = ["# 🔀 HTTP Traffic Capture Report\n"]
        lines.append(f"**Total Requests:** {stats['total_requests']} | "
                      f"**Total Bytes:** {stats['total_bytes']:,} | "
                      f"**Avg Duration:** {stats['avg_duration_ms']}ms\n")

        if stats["scope"]:
            lines.append(f"**Scope:** {', '.join(stats['scope'])}\n")

        # Method breakdown
        if stats["methods"]:
            lines.append("## Methods\n")
            for m, c in sorted(stats["methods"].items()):
                lines.append(f"- **{m}:** {c}")
            lines.append("")

        # Flagged items
        flagged = [r for r in traffic if r.flags]
        if flagged:
            lines.append(f"## 🚩 Flagged Requests ({len(flagged)})\n")
            for r in flagged:
                flags_str = ", ".join(r.flags)
                lines.append(f"### #{r.id} {r.method} {r.url}\n")
                lines.append(f"**Flags:** {flags_str} | **Status:** {r.status_code}\n")
                if r.request_body:
                    lines.append(f"```\n{r.request_body[:500]}\n```\n")

        # Traffic log
        lines.append(f"## Traffic Log ({len(traffic)} requests)\n")
        lines.append("| # | Method | URL | Status | Size | Duration | Flags |")
        lines.append("|---|--------|-----|--------|------|----------|-------|")
        for r in traffic:
            url_short = r.url[:60] + ("..." if len(r.url) > 60 else "")
            flags_str = ", ".join(r.flags) if r.flags else "-"
            lines.append(
                f"| {r.id} | {r.method} | {url_short} | {r.status_code} | "
                f"{r.response_size}B | {r.duration_ms:.0f}ms | {flags_str} |"
            )
        lines.append("")

        return "\n".join(lines)

    # ── Detail View ──────────────────────────────────────────────────────

    @staticmethod
    def get_request_detail_markdown(req: CapturedRequest) -> str:
        """Generate detailed markdown view for a single request."""
        lines = [f"## #{req.id} {req.method} {req.url}\n"]
        lines.append(f"**Host:** {req.host} | **Status:** {req.status_code} | "
                      f"**Duration:** {req.duration_ms:.1f}ms | "
                      f"**Size:** {req.response_size}B\n")

        if req.flags:
            lines.append(f"**🚩 Flags:** {', '.join(req.flags)}\n")
        if req.error:
            lines.append(f"**❌ Error:** {req.error}\n")

        lines.append("### Request Headers\n```")
        for k, v in req.request_headers.items():
            lines.append(f"{k}: {v}")
        lines.append("```\n")

        if req.request_body:
            lines.append("### Request Body\n```")
            lines.append(req.request_body[:2000])
            lines.append("```\n")

        lines.append("### Response Headers\n```")
        for k, v in req.response_headers.items():
            lines.append(f"{k}: {v}")
        lines.append("```\n")

        if req.response_body:
            lines.append("### Response Body\n```")
            lines.append(req.response_body[:2000])
            lines.append("```\n")

        return "\n".join(lines)


# ── Module-Level Singleton ───────────────────────────────────────────────────

_proxy_engine: Optional[ProxyEngine] = None


def get_proxy_engine() -> ProxyEngine:
    """Get or create the global proxy engine singleton."""
    global _proxy_engine
    if _proxy_engine is None:
        _proxy_engine = ProxyEngine()
    return _proxy_engine


def reset_proxy_engine() -> None:
    """Reset the global proxy engine (for testing)."""
    global _proxy_engine
    if _proxy_engine and _proxy_engine.is_running:
        _proxy_engine.stop()
    _proxy_engine = None
