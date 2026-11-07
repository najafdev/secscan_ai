# 14. Plugin Creation Guide

This guide explains exactly how HackBot custom plugins work and how to build your own.

## How the Plugin System Works

1. HackBot loads plugin files from the user config plugins directory.
2. The directory is based on the platform config path and resolves to:
   1. Linux: `~/.config/hackbot/plugins/`
   2. macOS: `~/Library/Application Support/hackbot/plugins/`
   3. Windows: `%APPDATA%\\hackbot\\plugins\\`
3. Each plugin is a Python file (`.py`).
4. A plugin must register using one of two supported methods:
   1. `@hackbot_plugin(...)` decorator on a callable.
   2. `register()` function that returns `PluginDefinition`.
5. The plugin callable is executed with keyword args parsed from:

```text
hackbot-plugin <plugin_name> --arg1 value1 --arg2 value2
```

## Quick Start

1. Open HackBot.
2. Run `/plugins dir` to print your exact plugin directory.
3. Create a new file there, for example `my_port_check.py`.
4. Add plugin code (examples below).
5. Run `/plugins reload`.
6. Run `/plugins` to confirm it is registered.

## Method 1: Decorator (Recommended)

```python
from hackbot.core.plugins import hackbot_plugin


@hackbot_plugin(
    name="my_port_check",
    description="Check whether a TCP port is reachable",
    args={
        "host": "Target hostname or IP",
        "port": "TCP port number (default: 443)",
    },
    author="Your Name",
    version="1.0.0",
    category="recon",
)
def run(host: str, port: str = "443") -> str:
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        result = sock.connect_ex((host, int(port)))
        state = "OPEN" if result == 0 else "CLOSED"
        return f"Port {port} on {host}: {state}"
    finally:
        sock.close()
```

## Method 2: register() Function

```python
from hackbot.core.plugins import PluginDefinition


def register() -> PluginDefinition:
    return PluginDefinition(
        name="my_headers",
        description="Check important HTTP security headers",
        args={"url": "Target URL"},
        author="Your Name",
        version="1.0.0",
        category="recon",
        run=run,
    )


def run(url: str) -> str:
    import urllib.request

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=10) as resp:
        headers = dict(resp.headers)

    required = [
        "Strict-Transport-Security",
        "Content-Security-Policy",
        "X-Content-Type-Options",
    ]
    missing = [h for h in required if h not in headers]
    if missing:
        return "Missing headers: " + ", ".join(missing)
    return "All key headers are present"
```

## Running a Plugin

### From Agent JSON action

```json
{"action":"execute","tool":"hackbot-plugin","command":"hackbot-plugin my_port_check --host example.com --port 443","explanation":"Check HTTPS port"}
```

### From command runner in REPL

```text
/run hackbot-plugin my_port_check --host example.com --port 443
```

## Required Rules and Limits

1. Plugin names must be unique.
2. Return a string output. Non-string output is converted to string.
3. Keep execution bounded; long-running plugins degrade agent flow.
4. Use explicit timeouts for network operations.
5. Avoid destructive behavior and keep tests authorized.
6. Arguments are parsed as `--key value` pairs.
7. Keep argument values space-safe (for example, use domains, IPs, short tokens). Complex quoted values may not parse as expected.

## Troubleshooting

1. Plugin not listed:
   1. Check file extension is `.py`.
   2. Ensure it defines `register()` or a `@hackbot_plugin` callable.
   3. Run `/plugins reload` and review load errors.
2. "Plugin not found":
   1. Verify the name in command matches the plugin `name` field.
3. Import errors:
   1. Install missing dependencies in the same Python environment where HackBot runs.
4. Empty arguments received:
   1. Use `--key value` format for every argument.

## Security Best Practices

1. Validate all plugin inputs.
2. Prefer safe libraries over shell calls.
3. If shell calls are required, avoid unsanitized input.
4. Never hardcode credentials or API keys in plugin files.

## Useful Commands

```text
/plugins
/plugins dir
/plugins reload
```

Next: [Troubleshooting ->](10-troubleshooting.md)
