"""
port_check — Example HackBot Plugin
=====================================
Checks whether a TCP port is open on a given host.

Place this file in ~/.config/hackbot/plugins/ to auto-discover it,
or use it as a template for your own plugins.

Usage (agent mode):
    {"action": "execute", "tool": "hackbot-plugin",
     "command": "hackbot-plugin port_check --host 192.168.1.1 --port 22",
     "explanation": "Check if SSH port is open"}

Usage (CLI):
    /plugins              # list installed plugins
    /plugins reload       # reload after adding new plugins
"""

from hackbot.core.plugins import hackbot_plugin


@hackbot_plugin(
    name="port_check",
    description="Check if a TCP port is open on a target host",
    args={"host": "Target hostname or IP address", "port": "TCP port number to check"},
    category="recon",
    author="HackBot Team",
    version="1.0.0",
)
def run(host: str, port: str = "80") -> str:
    """Check if a TCP port is open using a socket connection."""
    import socket

    port_num = int(port)
    if port_num < 1 or port_num > 65535:
        return f"Invalid port number: {port}"

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        result = sock.connect_ex((host, port_num))
        if result == 0:
            # Try to grab banner
            try:
                sock.send(b"\r\n")
                banner = sock.recv(1024).decode("utf-8", errors="replace").strip()
            except Exception:
                banner = ""
            status = f"OPEN (banner: {banner})" if banner else "OPEN"
        else:
            status = "CLOSED"
    except socket.gaierror:
        return f"Error: Could not resolve hostname '{host}'"
    except socket.timeout:
        status = "FILTERED (timeout)"
    finally:
        sock.close()

    return f"Port {port}/{('tcp')} on {host}: {status}"
