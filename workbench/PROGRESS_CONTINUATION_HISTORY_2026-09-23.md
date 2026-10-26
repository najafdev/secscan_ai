# Evidence Workbench current development ledger

## Active milestone: review-readiness hardening (in progress)

Owner-authorized continuation on 2026-09-21. The existing hourly automation was re-enabled without changing its original DTSTART, hourly cadence or COUNT=48 maximum end time. No new task, reset or extension. PR #1 merged into **HostX0/SecScan AI**, not upstream. No owner installation/testing/action is required during this sprint.

The complete first-milestone ledger is preserved byte-for-byte in [PROGRESS_HISTORY.md](PROGRESS_HISTORY.md), Git blob `1e3f288fa2666feac06a87558f6e01e74e8d8d9d`. Its Contributions 01-12 are dated historical checkpoints: the last entry's incomplete C/E state and 288 Python/23 JS totals are not current status. The corresponding old roadmap is preserved in [ROADMAP_BASELINE.md](ROADMAP_BASELINE.md), Git blob `113fdd48b9d4ea10c901c6a60fd0874831014edd`. The active cumulative criteria are in [ROADMAP.md](ROADMAP.md).

## Verified historical baseline (not validation of future changes)

- Source head: `328bfda14c1e2ea458391e491c575a8ee5303b9e`.
- Hosted PR checkout: `87100841867832c72e26073bfc71ad664fe34481`.
- Merged fork main: `2048e59143b568fa80c1736a3d02921491252eef`.
- Published Workbench subtree: `87d20c356c44d1a1c7fa35f6241c0a8b58316919`.
- [Evidence Workbench 35589788372](https://github.com/HostX0/secscan_ai/actions/runs/35589788372) passed its native Python 3.11/3.12/3.13, pinned Semgrep, real local-model, real Chromium browser and platform smoke jobs. This is separate from the failing legacy workflows.
- [Release Package 35589788385](https://github.com/HostX0/secscan_ai/actions/runs/35589788385) passed the exact-byte Ubuntu/macOS/Windows source-package smoke and provenance/SBOM attestation path. GitHub artifact ID `10633947927`; outer ZIP SHA-256 `cb873f5247f7cde6dafa7c02fb008f06297054296fba76cca94c29b2f7a2de31`; enclosed source archive SHA-256 `9bc6b79f79aab63f14b30193d5edc8704855f35c8d57375ded0918a75a84296e`.
- The first milestone added durable adapter API/GUI execution, pinned Semgrep, real-model and browser/platform/package validation after historical Contribution 12; they were not entered into that old ledger. Their source and hosted runs, not an invented backdated narrative, establish the baseline.

The immediate continuation used that downloaded **published** package, verified both SHA-256 values and computed the local original Workbench Git subtree hash: it exactly matched the live hosted `87d20c...` subtree. It did not use the blocked unpublished draft. Local direct `git clone` could not resolve github.com; the connected GitHub reads and the already downloaded published artifact remained available. This was a local network limitation, not a permission or safety denial.

## Contribution 13: public scope/DNS repair and review/CI reconciliation

### Implemented in the candidate working tree

- Shared public-web address validation rejects multicast, deprecated IPv6 site-local addresses, zone identifiers and explicit special/transition prefixes. A mixed DNS answer fails before a transport connection; public unicast order/deduplication remain compatible. Special-purpose globally reachable anycast assignments inside the excluded prefixes are deliberately outside this conservative policy, not mislabeled universally unroutable.
- Pre-cancelled or expired DNS work is rejected before resolver dispatch. Omitting an explicit deadline no longer removes cancellation or permits an indefinite caller wait. An already-running OS resolver remains cooperative/daemon work, not forcibly killed.
- A regression traverses the real finite registry and durable adapter lifecycle using only injected DNS answers: rejection creates a sealed `failed` record with no successful receipt and no connection. It does not scan an outside target.
- README, OLLAMA, PRODUCT_DIRECTION, RELEASE_NOTES and the live roadmap/ledger now distinguish implemented Semgrep, historical live-model/E2E/package evidence, source-package attestations and unsigned sensitive assessment exports. The native `python -m workbench` entry point remains independent of legacy installation. No provider exclusivity or universal-completeness claim was added.
- All three inherited `actions/upload-artifact@v3` uses in the two legacy workflows move to v4. Their dependency-install jobs receive `libldap2-dev`, `libsasl2-dev`, `portaudio19-dev` and `python3-dev`. Original test/lint commands are retained; no additional exit-code suppression or continue-on-error is introduced.
- Fork Docker CI is explicitly build-only: no DockerHub login, credentials or image push. Its success text no longer declares production deployment readiness. Existing test/lint/security deficiencies remain visible and must be evaluated separately.
- New offline scope/cancellation/lifecycle and documentation/workflow regression tests. Historical documents are checksum-tested, not rewritten or passed off as fresh validation.

### Validation for this candidate

Local candidate based on main `2048e59143b568fa80c1736a3d02921491252eef`, validated on 2026-09-21 with Linux x86_64, Python 3.13.5 and Node 22.16.0:

- `python -m unittest discover -s workbench/tests -v`: **342 discovered, 341 passed, 1 skipped, 0 failures/errors**, in 29.830 seconds. The skipped test is the existing opt-in real Semgrep-container integration; Docker is unavailable locally. It is not counted as a pass.
- The added tests include **9** offline scope/DNS/cancellation/durable-lifecycle regressions and **8** documentation/workflow consistency regressions. Adversarial cases were first reproduced against the unchanged source; the repaired candidate passes them. No external assessment connections are made by these fixtures.
- `node --test workbench/tests/*.cjs`: **28 passed, 0 failed/skipped**. These are DOM/fetch behavior contracts, not browser E2E.
- Workbench Python compilation, both frontend JavaScript syntax checks and structural YAML parsing of both modified legacy workflows passed. YAML parsing is not GitHub runner execution.
- `python -m workbench.tests.fresh_install_smoke` passed: real loopback server, owned synthetic assessment, durable SQLite export and history. No live model or external target was used.
- Local browser E2E and live model inference were not rerun in this contribution. The prior development browser policy denied loopback navigation; no alternate route was used to bypass that restriction. Historical hosted Chromium/model evidence above does not validate a new revision.
- No legacy dependency installation or native LDAP/PortAudio build was run locally; network/Docker availability limits remain explicit. Current hosted workflows must establish the actual result after publication.

These are candidate-working-tree results, not a claim of an uploaded feature commit or new hosted success. Record the published code commit and subsequent hosted results in the next checkpoint; preserve the distinction between PR source SHA and GitHub checkout merge SHA.

### Confirmed legacy failures and unresolved follow-through

Historical [SecScan AI CI/CD 35589788333](https://github.com/HostX0/secscan_ai/actions/runs/35589788333) failed dependency installation before lint/test/import: python-ldap lacked `lber.h`, and PyAudio lacked `portaudio.h`. The security job failed setup because upload-artifact v3 is deprecated. Historical [Enterprise CI/CD 35589788387](https://github.com/HostX0/secscan_ai/actions/runs/35589788387) also had setup/dependency failures. Fixing these first errors is not evidence that later legacy tests passed.

The main repository tree lacks the `tests/unit/` and `tests/integration/` directories referenced by the enterprise workflow. Broad formatter/type/dependency/runtime compatibility has not been established. Existing advisory `|| true` commands and placeholder performance/compliance echo jobs are not real passing security/performance/compliance evaluations. Do not remove assertions, replace missing legacy tests with irrelevant Workbench tests, disable workflows or conceal failures to get green status. Reproduce remaining errors against the unchanged baseline, then repair coherently within authorized scope.

### Gate impact and remaining work

Continuation A/C/D have concrete implemented progress; B still needs an additional meaningful concurrency/storage-fault slice; E needs current candidate aggregate/package runs and explicit baseline diagnosis or repair of the remaining legacy failures. The continuation is **not complete**, and historical Gates A-E passing is not an early-stop condition for this resumed work.

No external assessment target, real customer data/credentials, paid model/API calls, account provisioning, payloads, persistence, lateral movement, public deployment or upstream submission. The blocked unpublished handover draft in PR comment `5754686659` remains excluded; no replay, repackaging or alternate write route was used.

### Primary repair references

Reviewed 2026-09-21:
- https://github.com/actions/upload-artifact (v4 migration and immutable artifact names)
- https://www.python-ldap.org/en/latest/installing.html (OpenLDAP/SASL build prerequisites)
- https://people.csail.mit.edu/hubert/pyaudio/ (PortAudio/Python development prerequisites)
- https://docs.python.org/3/library/ipaddress.html and the IANA registries linked in ROADMAP.md (special-purpose classification versus the narrower public-web policy)

## 2026-09-21: additive easy startup and cooperating-process protection

Owner narrowed this delivery to compatibility, easy installation/GUI/AI/tool/report usage, large coherent PR batches and preservation of the original contribution. The existing hourly DTSTART/COUNT=48 were retained; no new task or extension. This batch changes no existing runtime, GUI, adapter or test implementation: it adds `start.py`, Windows/macOS/Linux helpers, an operator walkthrough and fourteen startup regressions. The added START_HERE walkthrough clarifies startup and the current AI/tool/report journey; the existing roadmap gates and original feature modules are retained.

### Published baseline and actual candidate tests

- Read current PR #2 head `773714ea81e4818abe5a1116cd1e3ee1f3d6ecf8`, main `2048e59143b568fa80c1736a3d02921491252eef`, source/docs and PR checkpoint `5762849195`.
- Downloaded the **published** package artifact `10646231412` from [35615042484](https://github.com/HostX0/secscan_ai/actions/runs/35615042484), source head `773714ea` / checkout `cc3d96011352a282d93e7bbbb0a100d9101d1143`. Verified outer ZIP SHA-256 `cbd11e2e49477f9a4eb2e3f90e1877ce1d5d353a9a7ec01ed78a7dd030cdabb4`, inner archive SHA-256 `87681f0704c610100d1fae7c20025c7d1ecb6b24bfe6c7e91dfe87fc5d3177c6`, and Workbench Git subtree `27112756bbdd372575e8da6172a5ca3100aa29b5` before edits. The old blocked handover draft was not read or reused.
- Baseline Workbench [35615042424](https://github.com/HostX0/secscan_ai/actions/runs/35615042424) and package run above passed for that source head. They do not validate this new candidate.
- Linux x86_64, Python 3.13.5, Node 22.16.0: baseline package suite **342 discovered / 339 passed / 3 skipped / 0 failures**, 30.228s. Candidate suite **356 discovered / 353 passed / 3 skipped / 0 failures**, 42.161s. The three skips are the opt-in real Semgrep integration and two repository-workflow checks omitted from the portable package; none is counted as a pass.
- All **14 new startup tests** passed. The final focused rerun took 15.766s. They cover unsupported Python/options, invalid/busy ports, no inference/remote connection in preflight, existing database byte preservation, injected storage failure, lock/symlink handling, separate workspaces, helper execution from another directory, real loopback assessment/export/history and duplicate-process denial before an injected valid running checkpoint can be incorrectly recovered.
- All **28 JavaScript DOM/fetch tests** passed; Python compilation, both frontend syntax checks and the existing real loopback no-AI fresh-install smoke passed. DOM tests are not browser E2E.
- Two synchronous full-suite invocations were interrupted by the execution tool timeout before a summary; neither is claimed as a completed run. The subsequent in-turn test process finished with exit 0 and the exact 356/353/3 totals above. No test was removed or weakened.
- Added a focused three-OS startup workflow without changing existing workflows/checks. Only its YAML structure was checked locally; Windows/macOS execution and fresh hosted Workbench/browser/model/package validation are pending publication. No live inference, external scanner/container, legacy dependency install or browser E2E was rerun locally.

### Scope and limitations

Startup checks do not open or recover reports and do not download packages/models, activate the legacy installer or invoke scanners. They may create the selected workspace, an advisory lock file and a temporary scratch file. Browser opening is explicit/best-effort. The lock covers **only cooperating uses of this new launcher on local storage**; original entry points/embedding remain unchanged and do not acquire it. A busy port is a point-in-time preflight, not a reserved port. This is not a native signed installer, all-process/distributed protection or an all-scanner AI agent.

At source head `773714ea`, legacy CI still failed after setup: installation had mismatched dependency imports and missing `aiohttp`/tools/model/reports assumptions; enterprise unit tests collected zero because `tests/unit/` was absent; Black failed. During the immediate run, concurrent published commit `ccb00e2507700475a6538bf3ef203599ca76140b` added deterministic legacy readiness checks, dependencies and real unit/integration test paths, and updated legacy workflows. The compare changed only seven root/legacy files and left the Workbench subtree unchanged. This additive batch preserves that newer commit as its parent; its local Workbench results do not claim to validate the concurrent legacy changes. Recheck the newer hosted CI rather than repeating historical errors as current facts. No legacy check is removed by this batch. The resumed milestone remains in progress: current hosted validation, legacy compatibility repairs and the easier combined GUI/AI/tool/report journey still need follow-through. Source/feature/merge SHA and subsequent hosted results belong to the PR checkpoint and next substantive ledger update, not an invented backdated success.


## 2026-09-22: coherent UI transaction and report-review batch

The owner clarified that the entire practical product is our delivery responsibility: historical origin explains a defect but does not excuse an unresolved shipping path. The existing hourly schedule remains unchanged; no extra task, reset or extension. This is an additive/narrow repair on the published application, not replacement of the first contribution.

### Source and implemented changes

- Read live fork main `2048e59143b568fa80c1736a3d02921491252eef`, all open PRs (PR #2), source head `dad3f020243cc0e1b7e0bd298fca993a6caf9833`, required docs and latest PR comments. Before edits, the complete local Workbench Git subtree matched hosted `b46020fe0fb6a0d6d45f7f3d69266f61450b7f68`. Source came from the published review artifact, not the blocked unpublished draft. Local git clone failed DNS; connected GitHub reads remained available.
- Freeze adapter inputs before the planning request leaves the UI. Prevent duplicate planning, reset during approval/report linking, and execution before confirmed exact-plan approval. Reject malformed or mismatched returned plan identities.
- Separate HTTP completion, durable receipt completion and the adapter result's actual coverage. Failed, cancelled, interrupted, executing, partial and unknown results no longer receive the same success message or export controls.
- Add **Check run status** as an explicit read-only reconnect action. Lost transport does not prove a job stopped and never automatically retries execution. Late Stop responses cannot overwrite a confirmed terminal outcome.
- Add **View linked report**, connecting the existing idempotent receipt-to-report endpoint to the existing evidence/history/export interface. It does not rerun a tool/model, expand authority or mark candidate observations verified. The report bridge validates IDs, refuses to interrupt active work, and focuses the conclusion.
- Bind poll/comparison callbacks and export filenames to their initiating selection. Switching reports disables stale exports immediately. Delayed errors/results from a previous selection cannot unlock an active run or overwrite the next report. An unconfirmed assessment stays locked until explicit Refresh confirms its state.
- Extend the existing hosted browser scenario with an owned temporary project, exact approval, metadata execution, candidate report linking and focused review. Existing synthetic-proof, responsive-layout, keyboard, token and runtime-exception checks remain. This scenario is configured, not claimed locally executed.
- Update START_HERE and the live roadmap without changing the historical ledger, original feature modules, adapter/AI contracts, LICENSE or entry points. No scanner or provider was added.

### Exact local validation

Environment: Linux x86_64, Python **3.13.5**, Node **22.16.0**. Tested candidate is based on the source/subtree above plus only the files in this batch; the feature commit and its hosted results are identified in PR #2 after publication.

- Before repair, the first focused delayed-response regression run had **23 tests: 10 passed, 13 failed**. The new failures reproduced stale UI scope/status/selection behavior rather than relying on visual guesses.
- Final `node --test workbench/tests/*.cjs`: **50 passed, 0 failed/cancelled/skipped** (1.695s); published baseline had 29. The 21 additions are deterministic DOM/fetch/response-order contracts, not browser E2E or live inference.
- Complete candidate Python suite: **360 discovered, 358 passed, 2 skipped, 0 errors/failures** (52.766s). Skips are opt-in real Semgrep container integration and the macOS-only startup trace diagnostic. No assertion was removed or suppressed.
- An initial synchronous suite call hit the tool timeout without a final summary. A subsequent baseline run completed with two local missing-workflow fixture errors: the source-review artifact contains workbench-ci.yml but not both root CI files. Fetched the exact hosted CI files locally, verified blobs `23ef8fade5f08dd88bdb666bc52260fa435482f1` and `dfae20de62e8241960985f9bce0cc36d7743fb2d`, and reran all eight documentation tests successfully before the complete 360-test candidate run. Neither workflow is modified by this batch.
- Workbench Python compilation, both frontend syntax checks, extended browser-script syntax, `git diff --check` and real loopback fresh-install smoke passed. Smoke exercised owned no-AI assessment, durable export/integrity and history.
- Local browser E2E was not attempted through an alternate route after the prior browser-policy denial. No live inference, external target, real scanner/container or root dependency installation was run locally. Current hosted CI must validate the published bytes; historical results are not new-head passes.

### Whole-repository follow-through and gates

At source `dad3f020`, Workbench run `35645389701`, startup `35645389577` and release package `35645389548` report success. Basic CI `35645389567` and Enterprise `35645389609` still report failure. Enterprise jobs report successful Python 3.9/3.10/3.11 unit/integration paths, a cancelled 3.8 dependency job, and failed Black/build stages. These distinctions locate remaining work; they are not excuses or repository-wide green status.

The inspected Docker job `106486054811` reports missing `nikto`/`theharvester` packages on a Debian Python-slim build, while the fetched Dockerfile at the stated source starts from Kali. Reconcile actual workflow checkout/build inputs before changing distributions or declaring the root cause repaired; do not silently remove tools, activate legacy installers, or claim those inconsistent inputs establish a tested Docker fix. Formatter/runtime and full build follow-through remain open. No CI check was disabled, weakened or bypassed in this UI batch.

Continuation A/D/E progress is measurable, but the combined milestone is **not passed** and this batch is not grounds for early disable. New hosted UI/browser/package results and whole-project fixes still gate delivery. Preserve head checks and expected-SHA merging; no unverified main merge, upstream submission, public deployment, paid call, customer data or blocked payload was used.

UI references reviewed: https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/disabled and https://www.w3.org/WAI/WCAG21/Understanding/status-messages.html . DOM contract evidence is not assistive-technology certification.
