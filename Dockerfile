# ═══════════════════════════════════════════════════════════════════════════════
# HackBot — Docker Image
# Full cybersecurity testing environment with AI assistant
# ═══════════════════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS base

LABEL maintainer="HackBot Team"
LABEL description="HackBot AI Cybersecurity Assistant"
LABEL version="1.0.1"

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PATH="/root/.local/bin:/root/go/bin:${PATH}"

# ── System Dependencies ──────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Networking tools
    nmap \
    netcat-openbsd \
    dnsutils \
    whois \
    traceroute \
    curl \
    wget \
    # SSL/TLS tools
    openssl \
    sslscan \
    # Web testing
    nikto \
    dirb \
    # Password tools
    hydra \
    john \
    # Build tools
    git \
    build-essential \
    golang \
    # Misc
    jq \
    && rm -rf /var/lib/apt/lists/*

# ── Go-based Security Tools ─────────────────────────────────────────────────
RUN go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest 2>/dev/null || true \
    && go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest 2>/dev/null || true \
    && go install github.com/projectdiscovery/httpx/cmd/httpx@latest 2>/dev/null || true \
    && go install github.com/ffuf/ffuf/v2@latest 2>/dev/null || true \
    && go install github.com/tomnomnom/waybackurls@latest 2>/dev/null || true

# ── Python tools ─────────────────────────────────────────────────────────────
RUN pip install --no-cache-dir setuptools sqlmap wfuzz

# ── HackBot Installation ────────────────────────────────────────────────────
WORKDIR /app
COPY pyproject.toml .
COPY hackbot/ hackbot/
COPY README.md .

RUN pip install --no-cache-dir ".[all]"

# ── Entrypoint ───────────────────────────────────────────────────────────────
ENTRYPOINT ["hackbot"]
CMD []
