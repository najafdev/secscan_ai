<!-- SecScan AI document -->
# Alpha — Autonomous Web Editor (EARLY PROTOTYPE / NOT IMPLEMENTED)

> Status: **EARLY PROTOTYPE — NOT IMPLEMENTED.** This directory is an
> experimental sketch, not a working subsystem. Nothing here runs yet.

This `alpha/` directory is a separate experiment from the main SecScan AI
Python platform. It explores the idea of an "autonomous web editor": a
small Node.js service plus a browser UI that would let an LLM read and
edit code/content through a web interface. It shares no runtime, build, or
dependencies with the main Python platform and should be treated as a
throwaway design stub until it is actually built.

## Current reality

- All `.js` files are **single-line placeholder stubs**, not real code.
  They contain only a comment describing what the file is *intended* to do.
- There is no functional server, worker, or UI logic — only scaffolding.
- The CI workflow (`.github/workflows/alpha-ci.yml`) only validates that
  the stub package metadata installs cleanly and that the HTML file exists.
  It does **not** prove any functionality.

## Intended pieces (not yet implemented)

- **Express server** (`server/index.js`) — HTTP API endpoints, OpenAI
  integration, and logging. Currently a stub.
- **Worker / orchestrator** (`worker/orchestrator.js`) — coordination of
  OpenAI and Ollama interactions for the editing loop. Currently a stub.
- **Web UI** (`web/alpha.html`) — browser front end (e.g. a Monaco-based
  editor). Currently a placeholder HTML comment.

## Do not

- Do not treat a green Alpha CI run as evidence that the editor works.
- Do not depend on anything in `alpha/` from the main platform.

If/when this experiment is built out, replace this README with real setup,
usage, and environment-configuration documentation.
