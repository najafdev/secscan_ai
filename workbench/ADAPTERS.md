# Scanner and execution adapter boundary

The workbench now has five separate implemented boundaries:

- an offline parse/review boundary for selected third-party scanner result formats;
- a typed native execution boundary with a metadata-only project adapter and a one-request web-header adapter;
- a reviewed third-party execution boundary with one pinned, offline Semgrep CE project runner;
- a versioned planning/receipt boundary that records sanitized scope previews, declared authority and bounded observed usage without granting verification authority; and
- a durable plan/approval/execution lifecycle that persists minimized authority records, binds approval to an exact request digest, and exposes the reviewed flow through the authenticated loopback API and GUI.

Only the Semgrep CE runner described below is executable as a third-party scanner in this milestone. Trivy and Nuclei remain parser-only, and ZAP/Nmap are not execution adapters. All normalized scanner observations remain `candidate` until a separate workbench-controlled verification step proves something in an approved test context.

## Why parsing comes before execution

Third-party output is untrusted input. The workbench therefore separates four authorities:

1. A scanner may produce a raw observation.
2. A format parser may extract a bounded, privacy-minimized subset.
3. `secscan_ai.adapter-result/v1` normalizes that subset and forces every imported finding to `candidate`.
4. Only a separate workbench-controlled verification step may later prove a finding in an approved test context.

A parser cannot widen target scope, execute a command, reuse a credential, mark itself independently verified, or turn missing coverage into a pass.

## Implemented offline parsers

| Parser | Input | Retained evidence | Deliberately omitted | Coverage interpretation |
|---|---|---|---|---|
| `semgrep-json` | Semgrep JSON result object | Rule, file path, start/end line, message, severity, stable external identifier when supplied | Source snippets, metavariable contents, arbitrary internal fields | Uses the explicit scanned-path list when present. Scanner errors make the result `partial`. |
| `trivy-json` | Trivy JSON report | Target, package/version/fix metadata, misconfiguration location metadata, secret rule and line range | Secret matches, embedded source/configuration code, advisory prose not required for evidence | Counts top-level result objects. Findings remain candidates. |
| `nuclei-jsonl` | One JSON finding per line | Template id/name, severity, matcher, protocol and URL path | Raw request/response, curl command, extracted values, URL query/host | Finding streams do not establish complete target/template coverage, so non-empty imports are deliberately `partial`; an empty stream keeps coverage unknown. |

All parser input is bounded to 2 MiB, must be UTF-8 text without NUL bytes, and is capped at the adapter contract's 500 normalized findings. Malformed/truncated content fails closed.

## Privacy properties

The parse layer intentionally does **not** act as an archive of raw scanner output. It keeps enough metadata for review and stable fingerprints while reducing the chance that a finding export becomes a second copy of customer secrets, response bodies or exploit material.

This is not a universal redaction guarantee. Future adapters may expose new sensitive fields and must receive adapter-specific review and regression tests before execution is enabled. Raw source files and raw scanner reports remain outside this normalized evidence contract unless a separately reviewed workflow explicitly handles them.

## Access-control matrix foundation

`access_matrix.py` adds an execution-neutral role/resource policy evaluator. It accepts only role/resource labels, an expected allow/deny state, a normalized observed state and whether an independent denied control was confirmed. It accepts no password, token, cookie, response body or customer record fields.

Unexpected allows become **candidate** access-control observations. A confirmed denied control raises confidence, but it still does not become independently verified until a separate workbench proof step validates impact. Missing, errored and skipped matrix cases remain incomplete coverage. Unexpected denials are reported as policy mismatches rather than being mislabeled as exploit findings.

This is groundwork for designated test-account matrices in owned synthetic fixtures. It is not an authenticated external scanner and does not store credentials.

## Implemented native execution declarations and adapters

`execution_contracts.py` adds `secscan_ai.execution-declaration/v1`. It is a closed declaration of required authority, not a permission grant. A declaration records the adapter/version, launcher class, effect level, filesystem/network authority, whether subprocesses/writes/symlinks are involved, hard object/request/time limits and a coverage unit. Unknown fields such as an arbitrary `command` are rejected. Native Python adapters cannot declare subprocess execution; read-only adapters cannot declare writes; network-none adapters must have a zero request budget.

Two native adapters currently implement this declaration:

| Adapter | Authority | What it does | What it deliberately does not do |
|---|---|---|---|
| `native-project-metadata/1` | read-only filesystem metadata, no network, no subprocess, no writes, no symlink following | Traverses bounded project filenames and reports candidate observations for filenames commonly associated with environment/credential/key material | Reads no file content or secret value, executes no scanner, follows no symlink |
| `native-web-headers/1` | passive scoped-target network, exactly one request, no filesystem/subprocess/write authority | Issues one scoped HEAD request through the existing DNS-pinned/no-redirect/body-free reader and reports candidate HTML hardening-header observations | Sends no payload/body, follows no redirect, reads no response body, stores no cookie/header outside the small allowlist |

Both adapters feed `secscan_ai.adapter-result/v1`, so their observations remain `candidate`. Filename presence or a missing header is not exploit proof. Tests use vulnerable/corrected synthetic fixtures and also exercise fail-closed input/authority boundaries.

## Reviewed third-party runner: Semgrep CE

`semgrep-project-local/1.177.0-r1` is the first reviewed third-party execution adapter. Its boundary is intentionally narrower than a generic process runner:

- Semgrep CE is pinned to version **1.177.0** and an exact Linux/amd64 container manifest digest recorded in `tooling/semgrep-1.177.0.json`.
- The engine license is recorded as `LGPL-2.1-or-later`; the upstream source/release references and source archive checksum are retained in the pin metadata.
- The runner **never pulls** an image. The exact image must already be present. CI pulls that exact reviewed digest before the owned integration fixture starts; assessment execution itself uses Docker `--pull never`.
- The container network is `none`; the container root filesystem is read-only; Linux capabilities are dropped; `no-new-privileges` is set; PID, memory and CPU limits are declared; project source and the repository-authored rules file are mounted read-only.
- The process runs with the calling Linux operator UID/GID rather than container root, so host file permissions remain authoritative.
- Semgrep metrics and version checks are disabled. Cache/log/home paths are confined to the bounded ephemeral `/tmp` tmpfs, so offline startup does not wait on a version service or require writes to the read-only root filesystem.
- The reviewed ruleset is repository-authored; no Semgrep registry/rule download is used during execution.
- A bounded preflight enforces project file/depth limits before launch. The runner has one overall deadline, cancellation cleanup, bounded stdout/stderr capture and no generic shell-string surface.
- The rules config is mounted at `/workbench.yml` so Semgrep's local-config path rewriting cannot make rule IDs depend on an internal mount-directory prefix. This keeps evidence/rule identifiers stable across deployments.
- The existing Semgrep parser strips source snippets and metavariable contents from normalized results and forces findings to `candidate`.

Hosted Evidence Workbench run `35586469998` on feature head `c23414f3eb5fc34a0e66d2668ed0165a8d139b09` passed the dedicated `semgrep-container` job against two **owned** fixtures: a deliberately vulnerable Python project containing the repository-authored `dynamic-eval` test case and a corrected project using `json.loads`. The vulnerable fixture produced the expected candidate rule, the corrected fixture produced no finding, and the same run also passed the native Python matrix, real browser E2E and cross-platform checkout validation. The scanner job contacts no assessment target and uses no customer source.

This pass is **not** a claim that Semgrep covers every language/rule or that an empty Semgrep result proves the project secure. It validates the pinned runner/parser/sandbox path for the reviewed ruleset and owned fixture only.

## Planning, durable approval and execution receipts

`ExecutionRegistry.plan()` validates one reviewed typed request against the operator-owned authority ceiling **without executing adapter I/O**. The preview is intentionally minimized:

- project scans retain an asset key and a short project label but not the full local root path;
- web scans retain the exact approved URL plus the fixed `HEAD` / no-redirect / no-body behavior;
- arbitrary commands, argv, environment fields and dynamic adapter identifiers are not part of the planning surface.

`execution_receipts.py` adds `secscan_ai.execution-receipt/v1`. `ExecutionRegistry.execute_with_receipt()` combines the reviewed declaration, minimized request summary, normalized candidate-only result and bounded observed usage. Receipt validation rejects object/request usage above the declaration's hard limits, adapter identity mismatches, self-verified findings and sensitive/execution fields such as passwords, tokens, cookies, authorization values, commands or argv at **any nesting depth** in the request summary.

`adapter_lifecycle.py` adds `secscan_ai.adapter-lifecycle/v1` and persists the reviewed sequence:

`planned -> approved -> executing -> completed | failed | cancelled | interrupted`

The lifecycle stores the minimized plan plus SHA-256 of the exact typed request, **not the raw request itself**. Approval is bound to the exact plan digest. Execution re-plans and re-hashes the resubmitted request before any adapter I/O; a changed root, URL, asset key or bound is rejected before execution. Plan fields become immutable after creation. Records are hash-sealed, terminal failures retain stable error codes rather than raw exception strings, and startup recovery converts stale `executing` records into explicit `interrupted` state rather than successful completion.

The loopback-only `workspace_server.py` exposes authenticated plan/approve/execute/cancel/read routes and serializes the reviewed-adapter execution lane against ordinary assessment starts. The GUI exposes the same exact authority preview. Inputs are frozen after planning; execution stays disabled until the exact plan digest is approved. Completed receipts show usage, coverage and candidate findings without changing verification authority.

Current native adapter accounting includes:

- eligible filesystem objects tested;
- scoped network requests (zero for the project adapter, exactly one for a completed/partial native web-header run); and
- elapsed adapter execution time in milliseconds.

A receipt is review metadata, not a security verdict. It does not prove that every possible object was covered, it does not attest OS-level egress, and it does not upgrade candidate findings.

## Gate C status

**Gate C passes the declared bounded milestone at `c23414f3eb5fc34a0e66d2668ed0165a8d139b09` in Evidence Workbench run `35586469998`.** The gate now has versioned fail-closed adapter contracts, two bounded native execution adapters, a finite operator-controlled registry, exact request-digest approval, durable lifecycle/receipts, and one reviewed pinned/licensed third-party Semgrep runner with an independently enforced least-privilege container boundary and vulnerable/corrected owned integration fixtures.

Gate C passing does **not** mean every scanner in the parser layer is executable. Trivy and Nuclei remain parser-only; ZAP and Nmap execution are not implemented. Each future runner still requires its own pinned version/license/checksum, typed fixed arguments, independent filesystem/network/target/effect limits, cancellation/deadline behavior, owned vulnerable/corrected fixtures, coverage/error accounting, secret-safe logs/exports, release/SBOM metadata and parser/runner regression tests before it can be advertised as executable.

The model may later select from approved adapter actions, but model output never becomes execution authority.

## Format references and compatibility notes

Checked 2026-09-21:

- Semgrep has documented JSON output as an integration surface, while later releases also removed some internal/private JSON fields. The parser therefore consumes only a small common subset and tests its own contract rather than depending on private fields: https://semgrep.dev/blog/2022/semgrep-release-v1-announcement/ and https://semgrep.dev/blog/2024/important-updates-to-semgrep-oss/
- Trivy currently documents JSON as a supported report format for its scanners and supports writing JSON reports to a file: https://trivy.dev/docs/dev/guide/configuration/reporting/
- Nuclei's current public documentation evolves independently of this parser. The JSONL parser is fixture-driven and deliberately does not claim complete scan coverage from a finding stream. Its assumptions must be revalidated against the pinned Nuclei version before an execution runner is added: https://docs.projectdiscovery.io/tools/nuclei/input-formats

Exact observed validation for each contribution is recorded in [PROGRESS.md](PROGRESS.md) and the PR validation checkpoints.
