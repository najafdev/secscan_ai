"""
http_headers — Example HackBot Plugin (register pattern)
==========================================================
Fetches and analyzes HTTP response headers for security issues.

This example demonstrates the **register() function** pattern,
which gives you full control over the PluginDefinition.

Place this file in ~/.config/hackbot/plugins/ to auto-discover it.
"""

from hackbot.core.plugins import PluginDefinition


def register() -> PluginDefinition:
    """Return plugin definition — called by PluginManager during discovery."""
    return PluginDefinition(
        name="http_headers",
        description="Fetch HTTP headers and check for security misconfigurations",
        args={
            "url": "Target URL (e.g. https://example.com)",
            "follow_redirects": "Follow redirects (true/false, default: true)",
        },
        author="HackBot Team",
        version="1.0.0",
        category="recon",
        run=check_headers,
    )


# Security headers to check for
SECURITY_HEADERS = {
    "Strict-Transport-Security": "HSTS — forces HTTPS",
    "Content-Security-Policy": "CSP — prevents XSS/injection",
    "X-Content-Type-Options": "Prevents MIME-type sniffing",
    "X-Frame-Options": "Prevents clickjacking",
    "X-XSS-Protection": "Legacy XSS filter",
    "Referrer-Policy": "Controls referrer leakage",
    "Permissions-Policy": "Controls browser feature access",
}

DANGEROUS_HEADERS = {
    "Server": "Reveals server software",
    "X-Powered-By": "Reveals technology stack",
    "X-AspNet-Version": "Reveals ASP.NET version",
}


def check_headers(url: str, follow_redirects: str = "true") -> str:
    """Fetch HTTP headers and analyse security posture."""
    import urllib.request
    import urllib.error
    import ssl

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    follow = follow_redirects.lower() in ("true", "1", "yes")

    # Create a context that doesn't verify SSL (for pentesting)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "HackBot-HeaderCheck/1.0")

        if not follow:
            # Disable redirect following
            class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *_args, **_kwargs):
                    return None
            opener = urllib.request.build_opener(
                NoRedirectHandler,
                urllib.request.HTTPSHandler(context=ctx),
            )
            resp = opener.open(req, timeout=10)
        else:
            opener = urllib.request.build_opener(
                urllib.request.HTTPSHandler(context=ctx),
            )
            resp = opener.open(req, timeout=10)

    except urllib.error.HTTPError as e:
        resp = e  # Still has headers
    except Exception as e:
        return f"Error fetching {url}: {e}"

    headers = dict(resp.headers)
    status = getattr(resp, "status", getattr(resp, "code", "?"))

    lines = [f"URL: {url}", f"Status: {status}", ""]

    # Check security headers
    present = []
    missing = []
    for hdr, desc in SECURITY_HEADERS.items():
        val = headers.get(hdr)
        if val:
            present.append(f"  ✅ {hdr}: {val}")
        else:
            missing.append(f"  ❌ {hdr} — {desc}")

    lines.append(f"Security Headers ({len(present)}/{len(SECURITY_HEADERS)}):")
    lines.extend(present)
    if missing:
        lines.append(f"\nMissing ({len(missing)}):")
        lines.extend(missing)

    # Check dangerous headers
    leaked = []
    for hdr, desc in DANGEROUS_HEADERS.items():
        val = headers.get(hdr)
        if val:
            leaked.append(f"  ⚠️  {hdr}: {val} — {desc}")
    if leaked:
        lines.append(f"\nInformation Leakage ({len(leaked)}):")
        lines.extend(leaked)

    return "\n".join(lines)
