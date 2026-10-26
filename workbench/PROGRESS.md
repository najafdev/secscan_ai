# Evidence Workbench current development ledger

## Active milestone: reviewer evidence and product-readiness hardening

This is the live continuation ledger for the owner's **HostX0/SecScan AI** fork. Historical detail remains preserved in Git history and in [PROGRESS_HISTORY.md](PROGRESS_HISTORY.md), [PROGRESS_CONTINUATION_HISTORY_2026-09-23.md](PROGRESS_CONTINUATION_HISTORY_2026-09-23.md), and [ROADMAP_BASELINE.md](ROADMAP_BASELINE.md). This file records current shipping state and current-source evidence; it does not replace those historical records.

The fork itself is the product target. Upstream acceptance is not a release gate. Preserve the retained application and Evidence Workbench, deterministic no-AI operation, finite independently approved tools, local-first/provider-neutral model contracts, evidence integrity, cancellation and truthful limitations. No owner-side installation or testing is required.

## Merged shipping state through PR #10

PRs #2-#10 remain in fork `main`. They preserve the original Workbench while adding reviewed startup/install and package paths, scoped execution lifecycle, report/retest integrity, evidence/coverage/AI review, explicit resource ownership, adapter lifecycle authority, terminal history/durability review and complete frontend-contract discovery.

PR #10 source `d0f81ccf6157d0788fb561ceb227fdbe437bfd4b` passed Basic `36007613152`, Workbench Frontend Contracts `36007613252`, PR Release Package `36007613448`, Evidence Workbench `36007613269`, Enterprise `36007613240`, and Workbench Startup `36007613151`, then merged with expected-head protection and no force update into main **`aa61ff910268419c2c17256b9f711588c7d651d7`**.

Merged main `aa61ff9...` was rechecked before this continuation started: Evidence Workbench `36012222422`, Basic `36012222482`, Workbench Startup `36012222449`, Enterprise `36012222458`, trusted Release Package `36012222400`, and Workbench Frontend Contracts `36012222385` all completed **SUCCESS**. The trusted package run is a push/main context and is separate from PR package smoke. Historical duplicate runs cancelled by concurrency are superseded runs, not product-failure evidence.

The retained boundaries remain unchanged: portable source packaging is not native installer signing; package provenance/SBOM attestations are not assessment-report signing; advisory security/type/compliance jobs are not security or compliance certification.

## PR #11: truthful assessment stop-request state

PR #11 is open at https://github.com/HostX0/secscan_ai/pull/11 on branch `fix/cancel-request-state`, based on main `aa61ff910268419c2c17256b9f711588c7d651d7`.

### Product defect and behavior

The assessment UI previously disabled **Stop run** immediately after `POST /cancel`, but the next poll of a still-running report called `render()` and re-enabled the control. That made an accepted stop request visually disappear and allowed duplicate cancel requests even though the server had not yet confirmed a terminal state.

The repair adds a bounded client-side stop-request state keyed to the exact selected run:

- an accepted cancel request keeps **Stop run** disabled while that exact run remains `running`;
- duplicate cancel POSTs are suppressed;
- the existing `#notice` polite status region reports **`Stop requested; waiting for terminal confirmation.`** without moving focus;
- a poll failure after an accepted stop keeps the request non-repeatable and says terminal state is unconfirmed;
- a terminal report clears the pending request and announces the actual recorded terminal status rather than inventing `cancelled`;
- a failed cancel POST clears only that pending request, restores **Stop run** for the same still-running run, and says Stop is not confirmed;
- stale cancel responses remain bound by run identity and `selectionEpoch`, so they cannot overwrite the next selected run's UI;
- selection/loading also disables Stop until the selected report has been read.

This changes no server cancellation semantics, report schema, model policy, adapter/scanner, target scope, filesystem/network authority or automatic retry. A Stop click remains a request until the service reports a terminal outcome.

### Regression and hosted evidence

Tests were added before the implementation in `workbench/tests/test_workflow_transactions.cjs`. They bind accepted-stop persistence across running renders, duplicate suppression, terminal resolution without fabricated cancellation, cancel-request failure recovery, unconfirmed polling after an accepted stop and stale-response selection isolation.

Implementation source **`e078b0bdea06b0fe302e6d95c843d4fac068cae0`** has generated PR checkout **`c7083cb23f6870cf69c9ca8cfd6e74456ad72ca3`**.

Exact hosted evidence observed on that implementation source:

- Workbench Frontend Contracts `36020037533`: **SUCCESS** on Ubuntu 24.04.5 / Node 22.23.2. It discovered all six `workbench/tests/*.cjs` files and ran **77 tests: 77 passed, 0 failed, 0 skipped, 0 cancelled**. The new stop-request contracts are included in that total.
- Evidence Workbench `36020037549`: **SUCCESS**. CPython 3.13.15 ran **415 Python tests: 413 passed, 2 explicit skips, 0 failed**; the established Workbench subset ran **44 JavaScript tests: 44 passed, 0 failed**. Native Python 3.11/3.12/3.13, real Chromium browser-to-loopback E2E/accessibility, pinned Semgrep owned fixtures, assessment-data-free live local Ollama compatibility, fresh-install Ubuntu/macOS/Windows and aggregate validation all succeeded.
- Workbench Startup `36020037720`: **SUCCESS**.
- PR Release Package `36020037482`: **SUCCESS** for deterministic package build and exact-package platform smoke; privileged trusted signing is intentionally not established by PR context.
- Basic `36020037611` and Enterprise `36020037477` were still **IN PROGRESS** at this ledger checkpoint. Enterprise Python 3.8 legacy-core and fail-closed Black/Flake8 had already succeeded; remaining full-runtime/dependency lanes were still executing. These pending aggregates are not counted as passes.

This ledger update is a documentation successor to implementation source `e078b0b...`; all required merge gates must therefore complete again on the exact resulting source before PR #11 can merge. A historical green implementation head does not certify the successor.

## Research applied this round

No external code or dependency was copied.

- **W3C WCAG 2.1 SC 4.1.3 Status Messages** — https://www.w3.org/WAI/WCAG21/Understanding/status-messages : waiting, progress, results and errors should be programmatically available to assistive technology without moving focus. Applied: reuse the existing `role="status"` / `aria-live="polite"` notice for request acknowledgement, pending terminal confirmation and resolution, while avoiding repeated identical announcements on every poll.
- **OWASP ZAP Automation Framework** — https://www.zaproxy.org/docs/desktop/addons/automation-framework/ : `stopPlan(planId)` is distinct from `planProgress(planId)` and some jobs may not stop immediately. Applied: the UI does not equate a successful stop request with a terminal cancellation result.
- **OWASP ZAP Automation Framework changelog** — https://www.zaproxy.org/docs/addons/automation/changelog/ : recent releases add long-running progress visibility and soft-stop semantics. Applied only as a workflow-state design reference; SecScan AI's existing server semantics are unchanged.

## Required merge gate for PR #11

The exact latest source must pass:

1. Evidence Workbench, including real Chromium browser E2E/accessibility, native Python matrix, owned-fixture Semgrep, assessment-data-free local Ollama compatibility and three-OS fresh-install;
2. Workbench Frontend Contracts discovering and executing every CJS contract;
3. Workbench Startup on Ubuntu/macOS/Windows;
4. PR Release Package deterministic build + exact-package Ubuntu/macOS/Windows smoke; PR signing remains intentionally unavailable and is not successful signing;
5. Basic CI including its required build/test path;
6. Enterprise CI including Python 3.8 legacy-core, Python 3.9/3.10/3.11 full unit/integration, fail-closed Black/Flake8 and required Docker build;
7. final live main/head/diff review immediately before an expected-head, non-force merge;
8. merged main verified separately, including trusted package signing/attestation rather than inference from PR smoke.

If any required current-head workflow fails, use its exact completed job logs and repair the defect; do not weaken checks, hide failures or merge based on predecessor evidence.

## Preserved boundaries and next work

The retained application continues to use exact scoped authorization, finite typed adapter declarations, exact-plan approval, bounded effects/requests/time/output, candidate-only imported observations, cancellation/deadline paths, durable receipts, integrity-checked reports, conservative retesting, structured reviewer evidence, explicit AI-processing provenance and trusted package-attestation verification. Ollama remains the implemented reference model adapter rather than a mandatory gateway; deterministic no-AI remains available. Model output never expands scope or tool authority.

Autonomous tests remain limited to owned synthetic fixtures, denied controls and redacted canaries. No external-target exploitation, credential/customer-row collection, payload deployment, persistence, lateral movement, paid inference, public deployment or upstream outreach is part of this work.

After PR #11 is safely resolved, continue Gate B/D/E work based on live code and current evidence. Prefer reliable cancellation/recovery, actionable reviewer flows, explicit model/tool state and dependable install/startup over cosmetic additions or platform sprawl.

## Verification discipline

Distinguish source head from GitHub's generated PR checkout, DOM contracts from real browser E2E, protocol doubles from live model compatibility, individual jobs from aggregate workflows, PR package smoke from trusted-main signing, and portable-source packaging from native installers. A historical green run never certifies a later commit. No findings is not a security guarantee; failed reproduction is not proof of impossibility; `not_reproduced` is explicitly not a fixed verdict.

See [ROADMAP.md](ROADMAP.md), [README.md](README.md), [START_HERE.md](START_HERE.md), [OLLAMA.md](OLLAMA.md), and [PRODUCT_DIRECTION.md](PRODUCT_DIRECTION.md) for the retained product contract and cumulative Gates A-E.
