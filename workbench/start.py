"""Additive, dependency-free startup for the existing Evidence Workbench.

No legacy installer, model download or assessment is run by startup checks.
Workspace locking covers cooperating users of this launcher on a local filesystem;
the retained older entry points and third-party embedding do not take this lock.
"""

from __future__ import annotations

import argparse
import faulthandler
import json
import os
from pathlib import Path
import socket
import stat
import sys
import tempfile
import threading


class WorkspaceBusy(RuntimeError):
    """The selected local workspace cannot be exclusively acquired."""


class StartupCheckError(RuntimeError):
    """Stable, non-sensitive failure from one local startup prerequisite check."""

    def __init__(self, check, code):
        super().__init__(code)
        self.check = check
        self.code = code


class WorkspaceLock:
    """Process-scoped advisory OS lock, not a stale PID file or distributed lease."""

    def __init__(self, directory):
        self.fd = None
        try:
            self.directory = Path(directory).expanduser().resolve()
            self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        except (OSError, RuntimeError) as exc:
            raise StartupCheckError("workspace_lock", "workspace_unavailable") from exc
        path = self.directory / ".starter.lock"
        if path.is_symlink():
            raise StartupCheckError("workspace_lock", "workspace_lock_unsafe")
        flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
        flags |= getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_CLOEXEC", 0)
        try:
            fd = os.open(path, flags, 0o600)
        except OSError as exc:
            raise StartupCheckError("workspace_lock", "workspace_unavailable") from exc
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise StartupCheckError("workspace_lock", "workspace_lock_unsafe")
            os.set_inheritable(fd, False)
            os.lseek(fd, 0, os.SEEK_SET)
            try:
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise WorkspaceBusy("Workspace is busy or cannot be locked") from exc
            self.fd = fd
        except (WorkspaceBusy, StartupCheckError):
            os.close(fd)
            raise
        except OSError as exc:
            os.close(fd)
            raise StartupCheckError("workspace_lock", "workspace_unavailable") from exc
        except BaseException:
            os.close(fd)
            raise

    def close(self):
        if self.fd is not None:
            fd, self.fd = self.fd, None
            os.close(fd)
        # Never unlink: deleting a live lock can create two independent owners.


# Keep ownership until process exit, including while daemon handlers are stopping.
_PROCESS_LOCKS = []


def check_local_install(directory, port):
    """No model calls, remote connections, report reads or database recovery."""
    import sqlite3
    from contextlib import closing

    root = Path(__file__).resolve().parent
    for name in ("index.html", "app.js", "adapter.js", "style.css"):
        if not (root / "static" / name).is_file():
            raise StartupCheckError("application_files", "incomplete_application_files")
    try:
        with closing(sqlite3.connect(":memory:")) as database:
            if database.execute("SELECT 1").fetchone() != (1,):
                raise StartupCheckError("sqlite_memory", "sqlite_unavailable")
    except StartupCheckError:
        raise
    except Exception as exc:
        raise StartupCheckError("sqlite_memory", "sqlite_unavailable") from exc
    try:
        with tempfile.TemporaryFile(dir=directory, prefix=".starter-check-") as scratch:
            scratch.write(b"local startup check\n")
            scratch.flush()
            os.fsync(scratch.fileno())
    except Exception as exc:
        raise StartupCheckError("workspace_write", "workspace_not_writable") from exc
    # Availability at this instant, not a reservation against other applications.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", port))
    except Exception as exc:
        raise StartupCheckError("loopback_port", "loopback_port_unavailable") from exc
    return {
        "schema": "secscan_ai.startup-check/v1",
        "status": "passed",
        "python": sys.version.split()[0],
        "checks": [
            "application_files",
            "sqlite_memory",
            "workspace_write",
            "loopback_port",
        ],
        "assessment_database_opened": False,
        "inference_started": False,
        "scanner_started": False,
        "workspace_lock_scope": "this_launcher_only",
    }


def open_local_browser(url):
    """Best-effort OS browser launch; success is not a browser E2E assertion."""
    try:
        import webbrowser

        opened = webbrowser.open_new_tab(url)
    except Exception:
        opened = False
    if not opened:
        print(
            "Browser did not open. Use the private launch URL printed above.",
            flush=True,
        )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Start the existing local Evidence Workbench without the legacy installer."
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--data-dir", type=Path, default=Path.home() / ".secscan_ai-workbench"
    )
    parser.add_argument(
        "--check-install",
        action="store_true",
        help="Check local prerequisites without opening or recovering reports",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Machine-readable startup check result; requires --check-install",
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Open the private local UI; does not start AI or a scan",
    )
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        parser.error("Python 3.11 or newer is required")
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    if args.json and not args.check_install:
        parser.error("--json requires --check-install")
    if args.check_install and args.open_browser:
        parser.error("--check-install cannot be combined with --open-browser")
    previous_umask = os.umask(0o077)
    lock = state = server = None
    trace_startup = os.environ.get("SECSCAN_AI_STARTUP_TRACE") == "1"
    if trace_startup:
        # CI-only diagnostic: preserve the bounded readiness assertion while making
        # a genuinely stuck child explain where it is blocked. Production startup
        # is unchanged unless the explicit diagnostic environment flag is set.
        faulthandler.dump_traceback_later(10, repeat=True, file=sys.stderr)
    try:
        lock = WorkspaceLock(args.data_dir)
        result = check_local_install(lock.directory, args.port)
        if args.check_install:
            print(
                json.dumps(result, sort_keys=True)
                if args.json
                else "Local startup checks passed. No reports were opened, no AI/scanner was contacted. This is not full application or model validation."
            )
            return 0
        # Fixed repository imports: no target, command or provider code is loaded.
        if __package__ in (None, ""):
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from workbench import __version__
        from workbench.server import State
        from workbench.workspace_server import WorkbenchServer
        import secrets

        state = State(lock.directory)
        server = WorkbenchServer(
            ("127.0.0.1", args.port), state, secrets.token_urlsafe(32)
        )
        _PROCESS_LOCKS.append(lock)
        lock = None
        url = "http://127.0.0.1:" + str(args.port) + "/#token=" + server.token
        print("SecScan AI Evidence Workbench " + __version__, flush=True)
        print("Open locally: " + url, flush=True)
        print(
            "Keep this URL private. No tunnel/public binding. Stop with Ctrl+C.",
            flush=True,
        )
        print(
            "AI is optional: choose a model explicitly in the UI. No automatic downloads, inference or scans.",
            flush=True,
        )
        print(
            "Use this launcher for every process sharing this workspace; older entry points do not acquire its lock.",
            flush=True,
        )
        if args.open_browser:
            threading.Thread(
                target=open_local_browser, args=(url,), daemon=True
            ).start()
        server.serve_forever()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        if isinstance(exc, WorkspaceBusy):
            code, check = "workspace_busy", "workspace_lock"
        elif isinstance(exc, StartupCheckError):
            code, check = exc.code, exc.check
        else:
            code, check = "startup_failed", "startup"
        if args.json:
            print(
                json.dumps(
                    {
                        "schema": "secscan_ai.startup-check/v1",
                        "status": "failed",
                        "code": code,
                        "check": check,
                    }
                )
            )
        elif code == "workspace_busy":
            print(
                "Workspace is already in use or cannot be locked. Close its other process or choose another --data-dir. Do not delete the lock file.",
                file=sys.stderr,
            )
        elif isinstance(exc, StartupCheckError):
            hints = {
                "incomplete_application_files": "Extract the complete application archive and retry.",
                "sqlite_unavailable": "Use a Python build with working SQLite support.",
                "workspace_not_writable": "Choose a writable local --data-dir with available space.",
                "workspace_unavailable": (
                    "Choose a usable local --data-dir whose parent is writable and available."
                ),
                "workspace_lock_unsafe": (
                    "Use a local --data-dir with a regular non-symlink .starter.lock; do not replace a live lock."
                ),
                "loopback_port_unavailable": "Choose another unused --port on this machine.",
            }
            print(
                "Startup check failed at "
                + check
                + ". "
                + hints.get(code, "Review local prerequisites and retry.")
                + " No automatic repair was performed.",
                file=sys.stderr,
            )
        else:
            print(
                "Startup failed. Check Python/SQLite, extract all application files, verify workspace permissions/free space, and choose an unused --port. No automatic repair was performed.",
                file=sys.stderr,
            )
        return 1
    finally:
        if state is not None:
            state.cancel.set()
        if server is not None:
            with server.operation_gate:
                if server.adapter_cancel is not None:
                    server.adapter_cancel.set()
            server.server_close()
        if state is not None and state.worker is not None:
            state.worker.join(timeout=10)
        if lock is not None:
            lock.close()
        if trace_startup:
            faulthandler.cancel_dump_traceback_later()
        os.umask(previous_umask)


if __name__ == "__main__":
    raise SystemExit(main())
