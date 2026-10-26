<!-- SecScan AI document -->
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

SecScan AI is an AI-powered penetration-testing automation platform (Python). It is **authorized-use security tooling**: it orchestrates real offensive tools (nmap, sqlmap, hydra, metasploit, etc.) driven by an LLM through a structured 6-phase pentest methodology. Treat changes here as security-sensitive.

## Two entry points — they are separate, not layered

There are **two independent CLI applications** that do not import each other:

- **`secscan_ai.py`** / **`secscan_ai.py`** (v1) — self-contained single file. Classes: `SecScan AI` / `SecScan AI`, `AIEngine`, `ToolManager`, `PentestingPhases`, `VoiceInterface`, `WebDashboard`. This is what the `ci.yml` workflow imports/tests and what `install.sh` symlinks to `/usr/local/bin/secscan_ai`.
- **`advance_secscan_ai.py`** / **`advance_secscan_ai.py`** (v2, "Enterprise") — the actively-developed version. Classes: `EnterpriseSecScanAI` / `EnterpriseSecScanAI`, `EnterpriseToolManager`, `EnterprisePentestingPhases`, etc. Unlike v1, it depends on the seven internal packages (below). `docker-compose`, the README deployment instructions, and `enterprise-ci.yml` target v2.

When fixing a bug, determine which entry point the user means — logic is often duplicated across both files (each is ~44 KB). A change in one does **not** propagate to the other.

## Architecture (v2)

`advance_secscan_ai.py` wires together seven internal packages, each exposing a factory getter via its `__init__.py`. Use the getters rather than constructing classes directly:

| Package | Getter / key exports | Responsibility |
|---|---|---|
| `database/` | `get_db_manager`, `PentestSession`, `Vulnerability`, `User`, `AuditLog` | SQLAlchemy models + PostgreSQL persistence |
| `ai_engine/` | `get_advanced_ai_engine`, `AdvancedAIEngine`, `PatternRecognizer`, `VulnerabilityCorrelator`, `ModelProvider`, `ModelInfo`, `MODEL_CATALOG`, `ProviderFactory` | Multi-provider AI (OpenAI, Anthropic, Google, DeepSeek, GLM, OpenRouter, Ollama) + ML analysis, zero-day correlation, runtime model switching |
| `security/` | `EnterpriseAuth`, `ComplianceFrameworkMapper` | RBAC/LDAP auth, OWASP/NIST/ISO27001/SOC2/PCI-DSS mapping |
| `exploitation/` | `AdvancedExploitationEngine`, `ZeroDayDetector` | Exploit orchestration, behavioral zero-day detection |
| `reporting/` | `DynamicReportGenerator`, `get_realtime_dashboard` | HTML/PDF/JSON reports, live WebSocket dashboard |
| `cloud/` | `DockerManager`, `KubernetesManager`, `ServiceRegistry` | Container/K8s orchestration, Consul service discovery |
| `performance/` | `get_cache_manager`, `get_parallel_processor`, `get_performance_monitor` | Redis/memory caching, Celery distributed tasks |

Two cross-cutting patterns to preserve when editing:

1. **Graceful degradation.** v2 imports optional deps through a `safe_import()` helper and wraps the internal-package imports in a try/except that sets `MODULES_AVAILABLE = False`. The app must still start when optional dependencies (openai, redis, psycopg2, docker, etc.) are absent — never make a top-level import hard-fail. Guard new optional-dependency use the same way.
2. **6-phase methodology** is the core domain model. `EnterprisePentestingPhases` defines `phase1_reconnaissance` … `phase6_retesting`; `run_full_enterprise_pentest()` drives them in order. New scanning/exploitation capabilities should slot into the relevant phase rather than creating a parallel flow.

The Celery app lives in `performance/parallel_processor.py` (referenced as `-A performance.parallel_processor` by the worker/scheduler/flower services).

## Running it

```bash
python3 advance_secscan_ai.py                       # interactive enterprise menu (default)
python3 advance_secscan_ai.py --api                 # REST API only, :8000
python3 advance_secscan_ai.py --web                 # web dashboard only, :8080
python3 advance_secscan_ai.py --realtime            # real-time dashboard only
python3 advance_secscan_ai.py --config myconfig.ini # override config file
# Direct (non-interactive) assessment — requires all three:
python3 advance_secscan_ai.py --target example.com --scope "Web app" --auth-key KEY \
  --assessment-type black-box --compliance OWASP
```

Configuration precedence: **environment variables (`.env`) override `config.ini`** (see the `Config` class in `advance_secscan_ai.py`). Copy `.env.example` → `.env` before running with external services.

## Build, test, lint

```bash
./install.sh                  # Debian/Ubuntu only: apt installs pentest tools + ollama, pip installs, symlinks v1
pip install -r requirements.txt            # core deps
pip install -r requirements_enterprise.txt # additional enterprise deps
python3 test_installation.py  # validates deps + tools are present (NOT a unit-test suite)
```

Linting / formatting (as enforced in CI — run from repo root):

```bash
black --check --diff .
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
mypy . --ignore-missing-imports
bandit -r .                   # security lint; v2 stack runs against the whole tree
```

### Testing reality vs. README

The README lists `pytest tests/unit/`, `tests/integration/`, `tests/e2e/` and `requirements-dev.txt` — **integration/e2e trees are not present yet.** Unit tests live under `tests/unit/`. The only other validation script is `python3 test_installation.py` (checks importable packages + installed system tools).

## Docker stack

```bash
docker-compose up -d   # full stack: app, celery worker/beat/flower, postgres, redis,
                       # prometheus, grafana, elasticsearch, kibana, consul, nginx
```

**Gotcha:** `docker-compose up` requires `POSTGRES_PASSWORD` and `REDIS_PASSWORD` in `.env` (compose uses `${VAR:?...}` and aborts if unset). App/worker/celery services build `DATABASE_URL`/`REDIS_URL` from those vars — they must match the postgres/redis service passwords.

## `alpha/` is a prototype stub

`alpha/` contains a separate Node.js "autonomous web editor" experiment (`server/index.js`, `worker/orchestrator.js`, `web/alpha.html`) with its own `alpha-ci.yml` workflow. The committed `.js` files are **single-line placeholder stubs**, not working code. It is unrelated to the Python platform — don't treat it as a dependency of the main app.

## Conventions

- Python 3.8+ (CI pins 3.9). Target line length 127 for flake8 complexity checks.
- This is offensive security tooling. The exploitation/scanning modules invoke real attack tools; keep the authorization gating (`--auth-key`, scope checks, safe-mode approval workflows) intact when modifying those paths.
