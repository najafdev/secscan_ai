"""Cancellation-aware, DNS-pinned HTTP metadata transport for bounded web checks."""

from __future__ import annotations

import errno
import http.client
import ipaddress
import select
import socket
import threading
import time
from typing import Any

from . import engine

_PENDING_CONNECT = {
    value
    for value in (
        getattr(errno, "EINPROGRESS", None),
        getattr(errno, "EWOULDBLOCK", None),
        getattr(errno, "EALREADY", None),
        getattr(errno, "EINTR", None),
        10035,
        10036,
        10037,
    )
    if value is not None
}
_CONNECTED = {
    value for value in (0, getattr(errno, "EISCONN", None), 10056) if value is not None
}


def _connect_bounded(address: str, port: int, deadline: engine.Deadline, cancel=None):
    """Establish one TCP connection while honoring cancellation and the shared deadline."""
    ip = ipaddress.ip_address(address)
    family = socket.AF_INET6 if ip.version == 6 else socket.AF_INET
    endpoint = (address, port, 0, 0) if family == socket.AF_INET6 else (address, port)
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        sock.setblocking(False)
        result = sock.connect_ex(endpoint)
        if result not in _CONNECTED and result not in _PENDING_CONNECT:
            raise OSError(result, "TCP connect failed")
        while result not in _CONNECTED:
            if cancel is not None and cancel.is_set():
                raise engine.Cancelled()
            wait = min(0.05, deadline.remaining())
            _readable, writable, exceptional = select.select([], [sock], [sock], wait)
            if not writable and not exceptional:
                continue
            result = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if result not in _CONNECTED:
                raise OSError(result, "TCP connect failed")
        if cancel is not None and cancel.is_set():
            raise engine.Cancelled()
        sock.setblocking(True)
        sock.settimeout(deadline.remaining(8))
        return sock
    except BaseException:
        try:
            sock.close()
        except OSError:
            pass
        raise


def inspect_remote(
    url: str, deadline: engine.Deadline | None = None, cancel=None
) -> dict[str, Any]:
    """Inspect one HEAD response using one deadline across DNS, connect, TLS and response."""
    deadline = deadline or engine.Deadline(8)
    parsed = engine.validate_url(url)
    host = parsed.hostname.encode("idna").decode("ascii")
    port = (
        parsed.port
        if parsed.port is not None
        else (443 if parsed.scheme == "https" else 80)
    )
    address = engine.public_addresses(host, port, deadline=deadline, cancel=cancel)[0]
    if cancel is not None and cancel.is_set():
        raise engine.Cancelled()
    sock = _connect_bounded(address, port, deadline, cancel)
    holder = {"socket": sock}
    watcher_stop = threading.Event()

    def cancel_watcher():
        while not watcher_stop.wait(0.025):
            if cancel is not None and cancel.is_set():
                current = holder.get("socket")
                if current is not None:
                    try:
                        current.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    try:
                        current.close()
                    except OSError:
                        pass
                return

    watcher = None
    if cancel is not None:
        watcher = threading.Thread(
            target=cancel_watcher, name="secscan_ai-http-cancel", daemon=True
        )
        watcher.start()
    connection = http.client.HTTPConnection(host, port, timeout=deadline.remaining(8))
    try:
        if parsed.scheme == "https":
            sock.settimeout(deadline.remaining(8))
            sock = engine.ssl.create_default_context().wrap_socket(
                sock, server_hostname=host
            )
            holder["socket"] = sock
        sock.settimeout(deadline.remaining(8))
        if cancel is not None and cancel.is_set():
            raise engine.Cancelled()
        connection.sock = sock
        connection.request(
            "HEAD",
            parsed.path or "/",
            headers={
                "User-Agent": "SecScanAI-Workbench/" + engine.__version__,
                "Connection": "close",
            },
        )
        sock.settimeout(deadline.remaining(8))
        response = connection.getresponse()
        if cancel is not None and cancel.is_set():
            raise engine.Cancelled()
        headers = {}
        allowed = {
            "content-type",
            "content-security-policy",
            "x-frame-options",
            "strict-transport-security",
            "x-content-type-options",
            "referrer-policy",
        }
        for name, value in response.getheaders():
            if name.lower() in allowed:
                headers[name.lower()] = value[:2048]
        return {
            "status": response.status,
            "headers": headers,
            "resolved_ip": address,
            "method": "HEAD",
            "redirect_followed": False,
        }
    except (OSError, engine.ssl.SSLError, http.client.HTTPException) as exc:
        if cancel is not None and cancel.is_set():
            raise engine.Cancelled() from exc
        if time.monotonic() >= deadline.expires_at:
            raise engine.DeadlineExceeded(
                "Assessment wall-clock deadline exceeded"
            ) from exc
        raise
    finally:
        watcher_stop.set()
        connection.close()
        try:
            sock.close()
        except OSError:
            pass
        if watcher is not None:
            watcher.join(timeout=0.2)
