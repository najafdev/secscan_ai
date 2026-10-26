<!-- SecScan AI document -->
# Repository Guidelines

## Project Structure & Module Organization
SecScan AI is primarily a Python security assessment platform. Core entry points live at `advance_secscan_ai.py` (with backward-compatible `advance_secscan_ai.py` and `secscan_ai.py`), and `demo.py`. Feature modules are grouped by domain: `ai_engine/` (multi-provider AI with model registry and provider clients), `cloud/`, `database/`, `exploitation/`, `performance/`, `reporting/`, and `security/`. Tests live under `tests/`, with current unit tests in `tests/unit/`; shared pytest setup is in both root `conftest.py` and `tests/conftest.py`. Infrastructure and runtime assets are in `Dockerfile`, `docker-compose.yml`, `nginx/`, `redis/`, `monitoring/`, `database/init.sql`, and `public/`. The `alpha/` directory contains prototype Node stubs and should be treated separately from the Python application.

## Build, Test, and Development Commands
Create an isolated Python environment, then install dependencies:

```bash
pip install -r requirements-dev.txt
```

Run the main application locally:

```bash
python advance_secscan_ai.py
python advance_secscan_ai.py --api
python advance_secscan_ai.py --web
```

Run tests and installation checks:

```bash
pytest tests/ -v --tb=short
pytest tests/ -v --cov=. --cov-report=xml --tb=short
python test_installation.py
```

Build or run the containerized stack:

```bash
docker build -t secscan_ai:test .
docker-compose up -d
```

## Coding Style & Naming Conventions
Use Python 3.8+ compatible code and follow PEP 8. CI checks Black formatting, Flake8 errors, and optional MyPy/Pylint reports, so keep imports clean, prefer typed function signatures for new code, and avoid broad exception handling unless justified. Use `snake_case` for functions, modules, variables, and test files; use `PascalCase` for classes. Keep configuration examples in `.env.example`; never hard-code secrets.

## Testing Guidelines
Use pytest for all Python tests. Place focused unit tests in `tests/unit/` and name files `test_*.py`. Add regression tests for bug fixes and tests for new security, database, or orchestration behavior. Run `pytest tests/ -v --tb=short` before opening a PR; run coverage when touching shared modules or public entry points.

## Commit & Pull Request Guidelines
Recent history uses short imperative subjects, including Conventional-style prefixes such as `feat:` and `fix:`. Prefer `feat: add scanner option` or `fix: validate config fallback`. Pull requests should follow `.github/pull_request_template.md`: include a clear description, linked issues, test results, security considerations, documentation updates, and screenshots when UI or report output changes.

## Security & Configuration Tips
This project is for authorized security testing only. Do not commit `.env`, logs, reports with sensitive targets, API keys, scan results, or customer data. Document new environment variables in `.env.example` and consider Bandit/Semgrep findings before merging security-sensitive changes.
