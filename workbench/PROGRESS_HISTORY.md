# Contribution and validation ledger

Historical entries describe the policy at their time. Contribution 04 supersedes the local-inference-only restriction: Ollama remains the implemented reference integration; cloud-backed selection is allowed with explicit assessment-level consent. Contribution 05 records the newer local-first, provider-agnostic product direction: evidence, action and report contracts must not require Ollama to remain the permanent gateway.

## 2026-09-21 — Contribution 01: Evidence-first local workbench

### Implemented

An isolated `workbench/` package with a responsive HTML/CSS/JavaScript interface, native HTTP metadata inspection, an ephemeral authorization-canary lab, two execution modes, optional bounded Ollama tool selection and interpretation, deterministic evidence states, finding fingerprints, per-evidence SHA-256, an ordered hash-linked audit log, finalized report checksums, local SQLite history and JSON/Markdown exports.

Security boundaries include loopback-only service binding, session-token API access, strict Host/Origin validation, no cross-origin allowance, no arbitrary shell execution, typed scope validation, private-address rejection, DNS-pinned native requests, no redirects/body capture on public targets, a three-request native budget, a single active assessment and cancellation checkpoints. The legacy entry points and license were not replaced.

### Validation actually performed

- **72 unit/integration tests passed** on Python 3.13.5 in the development environment. This includes real HTTP requests to owned ephemeral loopback fixtures and the local workbench API; no external target was scanned.
- A deliberately vulnerable synthetic record returned a fresh marker without authorization while the control denied access. The verifier recorded one `verified_in_lab` finding. A corrected fixture did not produce that proof.
- API tests exercised authentication, Host/Origin rejection, content/body limits, protected paths, assessment lifecycle, report persistence, export integrity and history.
- Evidence/report tampering, failed scanners, skipped external verification, absent AI, rejected model actions, duplicate actions and budget enforcement were tested.
- Frontend JavaScript syntax checked with Node 22.16.0.
- Offline Chromium UI contract/layout checks passed at **1440, 768 and 390 pixels**: session unlock, approved form submission, rendering actual synthetic-lab result data, findings/history, no horizontal overflow and no JavaScript exceptions.

### Limits of the validation

- Browser-to-server E2E was **not run successfully**: browser administrator policy blocked localhost navigation (`ERR_BLOCKED_BY_ADMINISTRATOR`). Offline UI tests use a mocked fetch transport; native API tests separately use real loopback HTTP. These must not be presented as the same test.
- Live Ollama inference, GPU performance and compatibility with an actual installed model were **not tested**. Model-response contracts were tested with controlled fixtures.
- External websites and third-party scanner binaries were **not tested**. Those adapters are not integrated in this milestone.
- GitHub Actions workflow configuration is supplied; inspect actual hosted run status before claiming hosted CI success.
- Windows/macOS runtime behavior and Python versions other than 3.13 were not locally validated in this first session.

### Problems found and corrected during development

Four initial regression tests failed and were corrected before publishing the test-backed revision: explicit port `0` being treated as a default port, acceptance of an ASCII DEL control character, failure to independently check each finding's evidence digest after an outer reseal, and raw HTML in a target displayed in Markdown export. The interface also disables history switching while its active run is being observed.

### Next highest-priority work

Read ROADMAP.md item 1: hard total deadlines, special-range coverage across Python versions, atomic finalization/persistence and cancellation/restart recovery. Then define a stable adapter contract with offline scanner-output fixtures before increasing execution capability.

### Product claims deliberately not made

This is a working experimental foundation, not a complete production pentest suite. A local-lab proof is not a compromise of a customer's application. No findings does not establish security; inability to demonstrate exploitation does not establish impossibility. SHA-256 records are not signatures. No stars or community adoption are guaranteed.

## 2026-09-21 — Contribution 02: Ollama-only readiness and diagnostics

### Owner direction

At this point in the history, Ollama was the workbench's only intended AI provider. Later contributions supersede that product-level restriction while preserving the implemented Ollama path and its tests.

### Implemented

- Extracted a typed, standard-library-only local runtime with an explicit operation allowlist, strict port/model validation, bounded requests/responses and stable user-safe errors.
- Added model discovery diagnostics and authenticated metadata checking. Exact installed selection is required; `/api/show` gates completion/tool capabilities and rejects remote aliases before each inference under the policy active at that time.
- Added a fixed-provider GUI panel, model capability details, explicit Check model action, safe error guidance and preflight checks for AI-enabled submissions. Stale model-check results are invalidated; duplicate submissions and silent substitution are prevented.
- Kept local metadata checks separate from inference validation and daemon egress attestation. No prompt is sent during Check model, no model is pulled, no API key is requested, and no fallback provider is used.
- Added completed-response/truncation validation, controlled sampling/context/output settings and filtering of model thinking traces. Existing independent finding/evidence verdicts remain authoritative.
- Added [OLLAMA.md](OLLAMA.md) with the provider contract, supported operations, limits, diagnostics, threat boundary, references and validation caveats; updated the roadmap and isolated workflow.

### Validation actually performed before upload

- **38 new Python tests passed locally on Python 3.13.5**, including real loopback HTTP against a synthetic Ollama protocol server. Tests cover installed-model and alias gates, capability compatibility, budgets, strict configuration, malformed/failed/redirected responses and bounded planning contracts.
- **10 new JavaScript behavior tests passed** with Node 22.16.0 using DOM/fetch doubles. Tests cover model discovery, no substitution, stale metadata, tool support, preflight failure, native-only submissions and duplicate-submit prevention.
- Compilation of the locally reconstructed workbench files and JavaScript syntax validation passed.
- The 72 existing Python tests were not rerun in this local working copy because the full repository was not materialized. The workflow was configured to run the complete repository test suite plus the new JavaScript tests on Python 3.11, 3.12 and 3.13; hosted results were checked in later contributions.

### Not validated / still pending

No live Ollama inference, GPU/model performance, cloud-egress attestation, new browser layout/E2E run, external target or third-party scanner execution was performed. Protocol fixtures and DOM doubles are not replacements for those tests. Hard total deadlines, cancellation/restart behavior and atomic durable finalization remained priorities.

## 2026-09-21 — Contribution 03: Assessment-data-free Ollama inference self-test

### Implemented

- Added a bounded compatibility probe that uses only fixed synthetic prompts. It never receives an assessment target, authorization reference, finding, evidence, credential, scanner output or arbitrary user content.
- The first probe requires one exact structured JSON response. Optional tool compatibility uses a second fixed prompt and a single `workbench_self_test` function with empty arguments. The returned tool call is validated but **never executed**; the self-test has no execution callback.
- Added `Ollama.self_test()` and an authenticated loopback `POST /api/models/self-test` endpoint. Its body is closed to `model` and optional policy booleans; extra fields such as a target are rejected before model access.
- Passing output is explicitly labeled `inference_compatible`, records `assessment_data_sent: false`, and does not become assessment evidence or a security verdict. Mismatches fail closed with `self_test_failed`.
- Updated [OLLAMA.md](OLLAMA.md) to distinguish model metadata readiness, synthetic inference compatibility, real assessment inference, and daemon/network-egress attestation.

### Validation performed in this development run

- **9 focused Python unit tests passed locally on Python 3.13** for the self-test module/wrapper. They cover fixed structured output, no assessment fields in the prompt, strict boolean options, inert tool declaration, malformed/missing/wrong tool calls, model-metadata failure before any prompt, and the public `Ollama.self_test()` wrapper.
- `python -m compileall -q workbench` passed in the reconstructed local slice containing the new module/wrapper and test dependencies.
- Four additional loopback API tests were added for authentication, closed request fields, strict options, safe Ollama error propagation and ensuring the probe does not start an assessment. They were not separately executed in that partial local slice; later hosted CI covered the full workbench.

### Deliberate limits

This contribution did **not** claim successful inference against a real installed Ollama model or measure GPU capacity, speed, model quality or future reliability. A self-test pass is not evidence that a daemon is offline. No external targets were contacted and no exploit action was added.

## 2026-09-21 — Contribution 04: Choice of inference location, explicit consent and reviewability

### Implemented

- Preserved Ollama as the implemented gateway while adding strictly typed per-assessment `allow_cloud` support across runtime, scope, authenticated model endpoints and GUI. Local-only remains the default policy; cloud-backed catalog/show aliases become selectable when approved. Local/cloud selection does not change tool authority.
- Added explicit cloud disclosure, no automatic first-model selection, model/location metadata and consent invalidation on model/scope changes, after submission and during stale preflight races. Added an explicit GUI Test response action for fixed synthetic compatibility probes.
- Adapted cloud JSON responses to a prompted contract because current Ollama Cloud documentation does not support server-constrained structured outputs. Both paths retain strict application validation and cannot invent proof states.
- Recorded daemon-reported token counts, attempts and processing metadata in assessment reports, including failed-response coverage and unknown counters. No billing values or hardware performance were fabricated.
- Added a combined loopback integration test covering the real workbench HTTP API, fake cloud-backed Ollama protocol, assessment completion, sealed export and SQLite persistence. No real cloud inference was used.
- Added a revision-bound CI source review artifact with the tracked workbench, workflow, original LICENSE, checksum and real test logs. Excludes root .env, untracked runtime data and reports; it is not a binary release, signed attestation or security certification.
- Updated the current Ollama guide, roadmap and product direction: professional engagement workflow, coverage-aware retest, permission preview, evidence review, customer isolation and provenance-aware retrieval are explicit development targets, not false implemented features.

### Validation actually performed before the main feature commit

- **155 Python unit/integration tests passed locally** on Python 3.13, including **32 new cloud-policy/usage/API tests**; full suite completed in 19.238 seconds in that environment.
- **20 JavaScript behavior tests passed locally**, including **10 new cloud-consent/self-test/stale-response tests**. These use DOM/fetch doubles, not browser E2E.
- `python -m compileall -q workbench` and `node --check workbench/static/app.js` passed.
- Hosted Evidence Workbench CI for feature head `5ad825c10ff3ddcd4377e5e5a2c8a0bda1dbd667` succeeded on Python 3.11, 3.12 and 3.13 in run `35552510665`. The independent legacy Enterprise CI/CD was separate and failed; workbench success was never presented as repository-wide success.

### Limits and next work

No live local/cloud model inference, account sign-in, paid API, GPU test, external target, real third-party scanner or new browser E2E/layout check was performed. Prompted JSON is not constrained decoding; model metadata is not egress attestation; reported counters are not a bill. Checkpoint cancellation and per-operation timeouts were still not hard end-to-end deadlines.

## 2026-09-21 — Contribution 05: Adapter trust boundary, coverage-aware retest and privacy-preserving proof

### Implemented

This contribution spans feature commits `fa95c429a1d9dd6c47eafde7e0d2bb8381b869bd`, `d5ac514b7b829750f4913c0fc34ce8a9a1068d53` and `e2268b88ddaf027db819ab04437d2bd91fb7039e`.

- Added `contracts.py` with versioned `secscan_ai.adapter-result/v1` validation, bounded evidence/coverage, deterministic fingerprints and a verification firewall: imported scanner findings are always `candidate`; an adapter cannot label its own output independently verified.
- Added `retest.py` with conservative cross-run states `still_present`, `new`, `not_reproduced` and `not_retested`. Missing findings are never labeled fixed solely by absence; comparable target/environment and successful relevant coverage are required even for `not_reproduced`.
- Added `bundle.py` and authenticated `export.bundle.zip`: finalized intact reports can be packaged with JSON/Markdown and an unsigned manifest containing SHA-256/size metadata. This improves reviewer portability without pretending checksums are signatures.
- Added authenticated `/api/runs/<previous>/compare/<current>` to expose retest comparison through the real loopback API. Unknown or non-intact runs fail explicitly.
- Added `evidence_safety.py` for data-layer proof metadata. Ordinary record values are omitted; row count, column/type metadata and a content digest are retained, while only explicit `SECSCAN_AI-SYNTHETIC-*` canaries may be shown as sample proof.
- Upgraded the owned synthetic authorization fixture so successful verification demonstrates unauthenticated read of designated synthetic records, records a denied control and fresh canary, and explicitly states `customer_data_sampled: false`. The corrected fixture does not export a data summary.
- Rewrote `ROADMAP.md` with measurable cumulative Gates A–E covering evidence, reliability, adapter/scope boundaries, retest/reviewer evidence and usable review release. Current gates explicitly remain incomplete; this sprint must not stop early merely because optional polish remains.
- Reconciled `PRODUCT_DIRECTION.md` to local-first, provider-agnostic architecture: Ollama is the only AI adapter implemented today, not a permanent architectural requirement. Future reviewed provider/self-hosted adapters must reuse the same independent evidence/action authority.

### Validation actually observed

- **21 focused new pure-module unit tests passed locally** before the first commit. They cover adapter candidate-state enforcement, malformed coverage/evidence, stable fingerprints, retest states, unsigned bundle manifests and record-value minimization.
- The review API integration changes were syntax-compiled locally; the container used for this automation could not clone GitHub because external DNS was unavailable, so a second local full-suite run was not fabricated.
- Hosted **Evidence Workbench** run `35554625980` completed successfully for current head `e2268b88ddaf027db819ab04437d2bd91fb7039e` on Python **3.11, 3.12 and 3.13**. Each job passed isolated compilation, full Python unit/real-loopback integration discovery, JavaScript syntax and frontend DOM/fetch contract tests. The Python 3.13 job also produced the revision-bound review artifact.
- Real-loopback API tests added in this contribution exercise evidence-bundle export, conservative comparison and missing-run handling. Synthetic data-proof tests verify the evidence contains the canary/schema/hash but not ordinary fixture account values.
- No external assessment target, real database, live customer row, credential, third-party scanner, paid model or public service was touched.

### Remaining blockers to the measurable release gates

- Gate B remains incomplete: no true end-to-end deadline spanning DNS/network/model operations, no interruption-safe atomic terminal persistence and no complete restart recovery.
- Gate C remains incomplete: the adapter contract exists, but Semgrep/Trivy-style read-only execution and bounded ZAP/Nuclei-style web adapters are not implemented/tested.
- Gate D has substantial foundations, but retest/bundle controls are not yet surfaced in the GUI and evidence replay is not a signed attestation.
- Gate E remains incomplete: no live model benchmark, browser-to-server E2E/accessibility pass, cross-platform fresh-install smoke test, signed release or full packaging/SBOM evidence.
- The legacy Enterprise workflows remain separate from Evidence Workbench CI and must not be implied successful by this run.

### Safety/product interpretation

The stronger synthetic data proof is intentionally **not** a database dump. It demonstrates the product pattern the owner requested—concrete evidence that a data boundary can be crossed—using designated synthetic records and a denied control, while avoiding reusable credentials or customer data in the report. Real external exploitation, persistence, credential theft, customer-row sampling and lateral movement remain outside this workbench contribution.

## 2026-09-21 — Contribution 06: Privacy-minimizing scanner parsers and bounded access matrix

### Implemented

This contribution adds implementation commits `b436437bfee52478823e10587b72e5171466aa74`, `a6df41fa32dd71fb3094ada6530f9a6afa35890c`, `8c49a8a6cbab21de861e32cfa4a08940a2e3cbf0`, `83f67297e7825e96c8f7b9d0e1c3d6b53200d4f6` and documentation commit `932abb6101f3ddd69b13d804e27868a71e9f082a`.

- Added `adapters.py`, an offline non-executing parser layer for Semgrep JSON, Trivy JSON and Nuclei JSONL. Input is UTF-8/NUL checked and bounded to 2 MiB; malformed/truncated output fails closed and normalized findings still pass through `secscan_ai.adapter-result/v1`, so imported scanner data remains `candidate` rather than independently verified.
- Semgrep parsing retains rule, path and line metadata but deliberately omits source snippets and metavariable contents. Scanner errors make coverage partial rather than successful.
- Trivy parsing handles vulnerability, misconfiguration and secret observations while omitting secret matches and embedded source/configuration code from normalized evidence.
- Nuclei JSONL parsing deliberately omits raw requests/responses, curl commands, extracted values and URL queries. A finding stream does not establish complete target/template coverage, so non-empty imports are marked partial; an empty stream keeps coverage unknown instead of implying the target is safe.
- Added `access_matrix.py`, an execution-neutral role/resource policy evaluator. It accepts no credentials, cookies, tokens, response bodies or customer records. Unexpected allows become candidate access-control observations; a confirmed denied control raises confidence but does not self-promote the finding to verified. Missing/error/skipped cases stay incomplete coverage, and unexpected denials remain policy mismatches rather than exploit findings.
- Added [ADAPTERS.md](ADAPTERS.md) documenting format assumptions, privacy omissions, execution boundaries and the still-unmet requirements for actual scanner runners.

### Validation actually performed

- **20 focused Python tests passed locally** on Python 3.13 in the reconstructed pure-module slice: 12 parser/redaction/fail-closed tests plus 8 access-matrix tests. They cover stable fingerprints, oversized/non-UTF-8 input, malformed/truncated formats, Semgrep partial errors, Trivy secret/code omission, Nuclei raw-material omission, fixed/vulnerable matrix semantics, denied-control confidence, missing coverage, out-of-scope/duplicate cases and rejection of credential/body fields.
- Hosted **Evidence Workbench** run `35557901717` completed successfully for branch head `932abb6101f3ddd69b13d804e27868a71e9f082a` on Python **3.11, 3.12 and 3.13**. The revision-bound Python 3.13 review artifact recorded **211 Python tests passed** and **23 JavaScript tests passed**. The artifact's `REVISION.txt` is the GitHub pull-request merge revision `29602520afa3ef33348ecb6339ac202985e78ab3`, while the workflow metadata records feature head `932abb6101f3ddd69b13d804e27868a71e9f082a`; this distinction is retained rather than presenting the synthetic merge SHA as the feature-branch commit.
- The hosted log explicitly includes all 20 new `test_adapters` / `test_access_matrix` cases. No real scanner binary, external target, customer data, credential, model download or paid service was used.
- Legacy Enterprise/SecScan AI workflows are separate and are not inferred successful from the dedicated workbench workflow.

### Release-gate impact and remaining blockers

- Gate A's adapter verification firewall is now exercised by concrete format parsers rather than only a generic envelope, but the gate status is not used to justify early sprint completion while B/C/E remain materially incomplete.
- Gate C advances on malformed/truncated/oversized parser handling and privacy-minimized normalization for three formats. **Gate C is still incomplete** because the workbench does not execute a read-only project scanner or bounded web scanner, has no pinned runner/license/SBOM packaging for them, and has not passed vulnerable/fixed execution fixtures.
- The access matrix advances the role-matrix data/evidence model, but it is not an authenticated external role runner and does not store or use credentials.
- Gate B remains incomplete because cancellation is checkpoint-based and the currently implemented deadline/recovery mechanisms do not yet prove every blocking phase is interruptible within a true total deadline under all supported paths.
- Gate D now has real GUI comparison/bundle controls on the live branch, correcting the older Contribution 05 note; remediation-to-recheck linkage and stronger reviewer attestation remain work.
- Gate E remains incomplete: no live model compatibility benchmark, browser-to-server E2E/accessibility pass, cross-platform fresh-install smoke test, signed release or complete packaging/SBOM evidence.

### Safety/product interpretation

This contribution deliberately increases **review quality**, not exploit authority. It makes scanner output safer to import and access-control test results harder to overstate. It does not launch scanners, harvest credentials, dump databases, replay raw exploit traffic or contact external targets.

## 2026-09-21 — Contribution 07: Reliability publication boundary and cancellable resolution

### Implemented

Feature commits in this slice: `640e7805ebe00facb878f744a37f826e2e7fceec`, `06a948885ffbea0f6beba5ea325c845e90939367`, and `0e65f26d25f10ef874987b6c07078524c0f30cef`.

- Bounded DNS resolution now checks the assessment cancellation event while waiting on the resolver worker. A cancellation request can therefore stop the assessment before a slow resolver returns and before a network connection is opened.
- `Assessment` no longer publishes its terminal `finished` event through the live callback before sealing. All callback snapshots emitted by the engine remain explicitly `running`; the returned terminal report contains the final event and passes integrity verification.
- The local server accepts only running progress snapshots for the active run. Terminal publication is controlled by `State.run` after the report has been resealed with durability metadata.
- SQLite finalization remains one `BEGIN IMMEDIATE` transaction that inserts the intact terminal report and retires the active checkpoint. The published terminal report now records `durability.status=durable`, `storage=sqlite` and `terminal_publication=after_atomic_commit` only after that transaction succeeds.
- If terminal persistence fails, the in-memory terminal report is resealed and explicitly marked `not_durable` / `memory_only`; JSON/Markdown/evidence-bundle export and cross-run comparison refuse that explicit non-durable result. Legacy finalized rows without the new field remain reviewable for backward compatibility.
- Running-checkpoint persistence failures are retained as `checkpoint_gap_observed=true` in a later successfully durable terminal report instead of being silently forgotten.
- Restart recovery now marks an abandoned checkpoint `interrupted` / `inconclusive` and records explicit durable recovery metadata. It is never exposed as a completed assessment.

### Validation actually performed in this run

- `py_compile` passed for the reconstructed modified reliability slice.
- **14 targeted Python tests passed locally** in a reduced reconstructed harness: the existing deadline and restart-recovery cases plus six new reliability-publication cases. The new cases cover no unsealed terminal callback, durable-before-publication semantics, explicit memory-only fallback on finalization failure, checkpoint-gap disclosure, durable interrupted restart recovery and cancellation during a deliberately slow DNS resolver.
- The local cancellation test sets the cancellation event while a synthetic resolver sleeps and verifies the call raises `Cancelled` in under 0.2 seconds; it does not open an external connection.
- Hosted Evidence Workbench runs for feature head `0e65f26d25f10ef874987b6c07078524c0f30cef` were **still pending** when this ledger entry was written. Their configuration is not counted as a pass. The dedicated push run is `35561466540`; the PR run is `35561470769`.
- The local harness used stubs for unrelated workbench modules and is **not** a full repository/workbench suite. No external assessment target, scanner binary, live model inference, credential or paid service was used.

### Release-gate impact and remaining blockers

- Gate B advances substantially: terminal unsealed publication is closed, terminal durability is atomic-or-explicitly-non-durable, restart recovery remains inconclusive, and DNS waiting now honors cancellation.
- **Gate B still does not pass.** Cancellation has not yet been exercised during connect, TLS, slow response and model operations across the supported paths. Test-only injected readers also remain outside the production socket deadline guarantee. Additional storage/concurrency failure modes and special-address regression coverage remain to be completed.
- Gates C, D and E retain their existing blockers; this reliability slice does not justify early sprint completion.

### Safety/product interpretation

These changes improve evidence trust and interruption behavior without increasing exploitation authority. They do not execute third-party scanners, contact an external target, collect credentials, extract customer records, deploy payloads, persist access or add lateral movement.

## 2026-09-21 — Contribution 08: Remediation-linked recheck evidence

### Implemented

Feature commits: `ffb7961ce19ed6003012cd5976b016116e8157e9` and `1c85853a1c4ad1a51ff91d4ab3e758de32f206b9`.

- The existing `secscan_ai.retest-diff/v1` output remains backward-compatible while each prior finding now receives an explicit `recheck` binding.
- The binding carries previous/current run IDs, prior finding ID when available, prior evidence SHA-256 when available, a SHA-256 reference to remediation guidance, exact mapped coverage status and scope comparability. It intentionally records `remediation_applied: unknown` rather than inferring that advice was implemented.
- Changed target or environment is preserved as non-comparable scope and therefore `not_retested`, even if a similarly named check completed.
- Failed, skipped, absent and unmapped check coverage remains visible in the recheck object. A failed mapped scanner cannot turn an absent finding into `not_reproduced`.
- New findings use an explicit `not_applicable` remediation-application state rather than pretending they came from a prior remediation cycle.

### Validation actually performed

- Focused local assertions exercised still-present/not-reproduced/not-retested behavior, remediation/evidence hash linkage, failed mapped coverage and changed-scope behavior. This was a small logic check, not a full local repository run.
- Hosted **Evidence Workbench** run `35561727602` completed successfully for feature head `1c85853a1c4ad1a51ff91d4ab3e758de32f206b9`. All matrix jobs succeeded on Python **3.11, 3.12 and 3.13**.
- The Python 3.13 job ran **221 Python tests in 22.456s** and passed all of them, including the six new reliability-publication tests and the expanded ten-case retest suite. The same job also passed JavaScript syntax and **23 JavaScript DOM/fetch contract tests**; these are not browser E2E.
- The Python 3.13 review artifact was produced from GitHub's pull-request merge revision `d8cb750a06a07da8c9c16a6070152b6a58719460`, while workflow metadata records feature head `1c85853a1c4ad1a51ff91d4ab3e758de32f206b9`. That distinction is intentional.
- No live model inference, external target, scanner binary, credential, customer row or paid service was used.

### Release-gate impact

- **Gate D now passes its declared bounded criteria**: four-state conservative comparison is implemented; safe checksummed reviewer bundles already exist; remediation guidance/evidence is linked to the exact recheck without claiming it was applied; and changed-scope/failed/unmapped coverage remains non-closing.
- Gate D passing does not mean reports are cryptographically signed or that a human remediation action was independently attested. Those stronger release/reviewer properties remain later work.
- Gate B remains incomplete, and Gates C/E remain incomplete, so the sprint is not eligible for early completion.

## 2026-09-21 — Contribution 09: Typed native execution boundary and bounded project/web adapters

### Implemented

Feature commit: `57dfcfede62e87b2485f5238533ca2c63e81ce2d`.

- Added `secscan_ai.execution-declaration/v1`, a closed execution-authority declaration independent of model output. It records adapter identity, launcher class, effect level, filesystem/network authority, subprocess/write/symlink flags, object/request/time limits and coverage unit. Unknown fields such as arbitrary command strings fail closed.
- Added `native-project-metadata/1`, a read-only native project adapter. It inventories bounded filenames only: no file-content reads, no network, no subprocesses, no writes and no symlink following. Candidate observations identify filenames commonly associated with environment/credential/key material without reading or exporting the underlying values.
- Added `native-web-headers/1`, a passive one-request web adapter. Its production path reuses the existing explicit-URL, DNS-pinned, HEAD-only, no-redirect/body-free reader; normalized evidence retains only a small hardening-header observation and cannot self-promote past `candidate`.
- Both adapters keep execution authority separate from `secscan_ai.adapter-result/v1`, preserving the existing parser/result API rather than embedding new execution fields into it.
- Added explicit policies and coverage accounting for configured bounds. Reaching a file/depth/deadline bound becomes partial coverage rather than a successful complete scan. Non-2xx web responses likewise remain partial/inconclusive for the intended HTML representation.

### Validation actually performed

- Downloaded the prior successful hosted review artifact for branch head `7ef166f70c96df78d01b74f49ebd314544fdaad4` and reconstructed its exact tracked workbench source locally; this avoids attributing tests to the older blocked/unpublished draft.
- After layering only this contribution's six new source/test files onto that source, `python -m compileall -q workbench` passed.
- The complete local workbench Python suite passed **251 tests** in 21.945 seconds on the available Python 3.13 environment. JavaScript syntax and all **23** existing DOM/fetch contract tests passed as well; these are not browser-to-server E2E.
- Hosted **Evidence Workbench** run `35564908833` completed successfully for feature head `57dfcfede62e87b2485f5238533ca2c63e81ce2d` on Python **3.11, 3.12 and 3.13**. The Python 3.13 revision-bound review artifact records **251 Python tests passed** in 26.203 seconds and **23 JavaScript tests passed**. The artifact's `REVISION.txt` is the exact feature head for this push.
- The new slice includes 8 execution-declaration tests, 11 project-adapter tests and 11 web-adapter tests. Project tests cover no secret-content reads, symlink/exclusion/file-cap bounds and stable asset-scoped fingerprints. Web tests cover vulnerable/corrected synthetic HTML responses, non-2xx/non-HTML coverage, no query-bearing target, no response-body/raw field, approved-header allowlisting and strict HEAD/no-redirect semantics.
- The web logic fixtures use an injected owned reader; they do not yet prove the production socket path against a loopback web fixture.
- No external target, third-party scanner binary, real credential, customer data, live model or paid service was used.

### Release-gate impact and remaining blockers

- Gate C advances from parse-only foundations to two real bounded native execution adapters plus a versioned execution-authority declaration. The declared vulnerable/corrected logic fixtures now exist for both a read-only project adapter and a bounded web adapter.
- **Gate C is not declared passed yet.** The adapters are not yet wired through a common workbench execution registry/UI lifecycle; the web adapter still needs production-path owned network fixture coverage; external scanners still need pinned versions/licenses/packaging and parser/runner integration before they can be advertised as executable.
- Gate B remains incomplete for connect/TLS/slow-response/model cancellation and additional concurrency/failure paths. Gate E remains incomplete for live-model testing, browser-to-server E2E/accessibility, fresh-install/package/SBOM and release-quality evidence.
- Gates A and D remain passing within their existing bounded definitions; this contribution does not weaken their evidence/retest rules.

### Safety/product interpretation

This slice increases execution structure without adding exploit authority. The project adapter cannot read secrets; the web adapter sends one HEAD request and cannot read bodies or follow redirects. Neither adapter accepts model-generated shell commands or marks its own findings verified.

## 2026-09-21 — Contribution 10: Closed execution registry and operator authority ceiling

### Implemented

Feature commit: `3fe6e73fe071edb5886fcb74b6db477a5c7c7eb9`.

- Added `ExecutionRegistry`, a finite in-process registry for reviewed native adapters. Adapter IDs map to code-owned constructors; there is no dynamic import/module path, arbitrary command, executable name or generic keyword forwarding surface.
- Added `RegistryPolicy`, an operator-owned authority ceiling independent of model output. It can deny filesystem or network authority and cap the maximum effect level before adapter I/O starts.
- Requests are adapter-specific closed objects. Unknown fields such as `command` are rejected rather than forwarded to a runner. Project execution accepts only root/asset and bounded scan limits; web execution accepts only target/asset and a bounded timeout.
- A pre-set cancellation event prevents adapter I/O. Result authority remains unchanged: registry-executed observations still pass through the candidate-only adapter result contract.
- `describe()` exposes only declarations currently permitted by the operator policy, giving later UI/API layers a safe capability preview without granting execution.

### Validation actually performed

- Layered the two new registry files onto the exact source used for the preceding native-adapter validation. `python -m compileall -q workbench` passed.
- The complete local workbench suite passed **259 Python tests** in 21.966 seconds on the available Python 3.13 environment after adding 8 registry tests. JavaScript syntax passed and the existing **23 DOM/fetch contract tests** passed; these are not browser E2E.
- Hosted **Evidence Workbench** run `35565442843` ran against feature head `3fe6e73fe071edb5886fcb74b6db477a5c7c7eb9`; all Python **3.11, 3.12 and 3.13** matrix jobs completed successfully. The Python 3.13 job ran **259 Python tests in 27.568s** and all **23 JavaScript tests** passed. Its checkout was GitHub's pull-request merge revision `e518069a031d4ad74b1948e22639096d882a41eb`, while workflow metadata records the feature head; both identities are retained explicitly.
- Registry tests cover unknown adapter/command rejection, network/filesystem policy denial before I/O, pre-cancel behavior, candidate-only project/web results and secret-value non-retention.
- No external target, third-party scanner binary, live model, credential, customer data or paid service was used.

### Release-gate impact and remaining blockers

- Gate C advances again: execution declarations now flow through a common finite registry with an independent operator authority ceiling instead of being constructed ad hoc.
- **Gate C remains incomplete.** The registry is not yet connected to a durable assessment execution lifecycle/API/GUI with per-adapter progress and budgets; the bounded web adapter still lacks owned production-socket-path fixture coverage; external scanner runners still require pinned versions, licenses, least-privilege packaging and parser/runner integration.
- Gate B remains incomplete for cancellation during every connect/TLS/slow-response/model phase and additional failure/concurrency paths. Gate E remains incomplete for live-model, browser E2E/accessibility, fresh-install/package/SBOM and release-quality evidence.
- Gates A and D remain passing within their declared bounded definitions. The sprint is not eligible for early completion.

### Safety/product interpretation

This registry narrows execution authority; it does not add exploit behavior. It cannot accept a model-generated shell command, dynamically load a scanner, expand target scope, read project secret contents or turn a candidate observation into verified proof.

## 2026-09-21 — Contribution 11: End-to-end reliability gate and cooperative adapter cancellation

### Implemented

Feature commits in this slice include `0af2bf2b7a2a506fb9ce51ba2d5b631e90178c98`, `86719d1f4cb7d0ebe636e1e9e78b1583612545a9`, `216df34f0e1f061878673d3a09347ce2849d616a`, the corrective test commit `4e71682a0a44c6cbd650c8aa1cf921d50e0766fa`, and the project-cancellation commits `459446e9a7c3f926e290eaa5100fe3c1288c7d06`, `c2744c8b54007194607e1756bbc51defdf986240`, `fd3fd581e4dd04a037ed1be5e426f0106e159f76` and `62fd8fa0f43b2652b8263cca7a8dc8fa9807919f`.

- Added a dedicated cancellation-aware, DNS-pinned passive HTTP transport. TCP connect uses nonblocking `connect_ex` plus bounded readiness polling so a pending connect can be cancelled or expire on the same assessment deadline instead of waiting for a separate socket timeout.
- Routed the bounded native web-header adapter through that transport without changing its one-HEAD/no-redirect/no-body contract or candidate-only finding authority.
- Extended owned adversarial fixtures across pending TCP connect, TLS handshake, slow HTTP response and model transport. Deadline and cancellation behavior are now exercised in each of those phases in addition to the existing DNS tests.
- Kept cancellation outcomes honest: cancellation may occur before the owned server parses a HEAD request, so the regression test no longer requires request arrival. It still requires prompt cancellation and verifies no GET/body path occurs.
- Propagated the registry cancellation object into the native project metadata adapter. The adapter now checks cancellation before root inspection, before directory batches and at each metadata object boundary. This is cooperative filesystem cancellation; it does not claim to interrupt an already-blocking OS filesystem call.
- Preserved the existing evidence/retest boundaries: these reliability changes do not expand scope, add exploit authority, read project secret contents or allow model-generated execution.

### Validation actually observed

- Before upload, four focused synthetic TCP-connect tests were run in a reconstructed local slice: pending-connect cancellation, pending-connect deadline, immediate successful connect and connect-error socket closure all passed. This was a narrow local test, not the full repository suite.
- The first hosted Evidence Workbench run for feature head `216df34f0e1f061878673d3a09347ce2849d616a` exposed one timing-sensitive Python 3.13 test assumption: cancellation completed before the owned HTTP fixture had parsed the HEAD request, so the expected request list was empty. Python 3.11 and 3.12 passed. The test was corrected rather than weakening cancellation.
- Hosted **Evidence Workbench** run `35568876285` then passed on Python **3.11, 3.12 and 3.13** for corrective head `4e71682a0a44c6cbd650c8aa1cf921d50e0766fa`. The Python 3.13 job ran **276 Python tests in 26.697s** and all **23 JavaScript DOM/fetch contract tests** passed. These JavaScript tests are not browser-to-server E2E.
- The 3.13 run also produced a revision-bound source review artifact. No live Ollama inference, cloud inference request, external assessment target, third-party scanner binary, credential, customer row or paid service was used.
- Hosted **Evidence Workbench** run `35569076171` for feature head `62fd8fa0f43b2652b8263cca7a8dc8fa9807919f` also passed on Python **3.11, 3.12 and 3.13**. The Python 3.13 job ran **279 Python tests in 28.653s** and all **23 JavaScript tests** passed; this includes pre-cancel, mid-walk and registry-propagation coverage for project-adapter cancellation.

### Release-gate impact

- **Gate B now passes its declared bounded criteria** at `4e71682a...`: one wall-clock deadline reaches DNS/connect/TLS/response/model operations; cancellation is exercised in those phases; terminal unsealed publication is blocked; terminal storage is atomic or explicitly non-durable; and restart recovery cannot turn a running checkpoint into a completed report.
- Gate B passing does not mean every possible OS syscall is asynchronously preemptible, nor does it replace future concurrency/storage-fault regression work. Test-only injected readers remain a separate seam from the production socket transport.
- Gate C advances because the finite registry now propagates cancellation into the read-only project adapter, but Gate C remains incomplete until the native/external adapters are integrated into the durable assessment lifecycle/API/GUI with explicit per-adapter budgets/progress and third-party scanners have reviewed pinned runner/package boundaries.
- Gates A and D remain passing; Gate E remains materially incomplete. Early sprint completion is therefore not justified.

### Safety/product interpretation

This slice closes reliability gaps without adding destructive security behavior. It does not execute external scanners, attack an outside target, deploy a payload, harvest credentials, dump a database, sample ordinary customer rows, persist access or enable lateral movement.

## 2026-09-21 — Contribution 12: Adapter planning and budget-accounted execution receipts

### Implemented

Feature commits in this slice: `56c3ba166ec2141bfcd20c317ee680d7232c87f4`, `efb3d57a986ba0eb4fef41d140b4bb13f348f4cf`, `c390380a24df9da58e72dfaa691ad09c26f695f3`, hardening commit `f78cd11046502a20f71ba379bae8a2aa4dd352d5`, documentation commit `1aaf81304de483027ee7c7c33ba15298519f5fb4`, and roadmap status commit `31444b34515f0be91eef56efcb0b965a2990047b`.

- Added `secscan_ai.execution-receipt/v1`, a versioned review contract that binds the already reviewed execution declaration to a minimized request summary, observed object/request/elapsed-time usage and the normalized candidate-only adapter result.
- Added `ExecutionRegistry.plan()` as an I/O-free preflight. It validates the same typed adapter request and operator authority ceiling used by execution. Project plans retain only an asset key and sanitized root basename rather than the full local path; web plans preserve the exact approved URL plus fixed `HEAD`, no-redirect and no-response-body behavior.
- Added `ExecutionRegistry.execute_with_receipt()` without removing or changing the existing `execute()` API. The project adapter accounts eligible filesystem objects and zero network requests. The native web adapter accounts exactly one request for completed/partial executions. Elapsed time is observational metadata rather than a fabricated performance guarantee.
- Receipt validation rejects object/request usage above the execution declaration, adapter identity/version mismatches, self-verified findings and sensitive/execution fields such as password, token, cookie, authorization, secret, command, argv or environment in the request summary.
- Hardened planning validation so web URLs and asset keys are validated before reader I/O, and project asset keys are bounded text. Non-printable project basename characters are normalized in the preview rather than retained raw.
- Updated [ADAPTERS.md](ADAPTERS.md) and [ROADMAP.md](ROADMAP.md) to describe the new planning/receipt boundary and keep Gate C explicitly incomplete until these receipts are persisted/surfaced through the durable assessment/API/GUI lifecycle and third-party runners are pinned/licensed/tested.

### Validation actually observed

- Added **9 new Python tests** covering I/O-free project planning, full-path minimization, project object accounting without retaining a real fixture secret value, exact single-request web accounting, operator policy denial before I/O, rejection of self-verified findings, rejection of over-budget usage, rejection of sensitive/execution summary fields, pre-cancel behavior and nonnegative elapsed-time recording.
- Hosted **Evidence Workbench** run `35573191621` completed successfully for feature head `1aaf81304de483027ee7c7c33ba15298519f5fb4` on Python **3.11, 3.12 and 3.13**. The Python 3.13 job ran **288 Python tests in 26.356s** and all passed; JavaScript syntax and all **23 JavaScript DOM/fetch contract tests** also passed. The 3.13 job produced the revision-bound source review artifact.
- The Python 3.13 log contains one non-fatal `ResourceWarning` associated with an existing synthetic Ollama self-test socket fixture. The test passed, but the warning remains a cleanup issue rather than being hidden or reclassified as success evidence.
- The hosted checkout used GitHub's PR merge revision `740dc8cc91b29fc2e9b6c112d934af99173c3b25`, while workflow metadata records feature head `1aaf81304de483027ee7c7c33ba15298519f5fb4`; both identities are retained explicitly.
- No external assessment target, third-party scanner binary, live model inference, real credential, customer row, paid model/API or public service was used.

### Release-gate impact and remaining blockers

- Gates A, B and D remain passing within their declared bounded criteria.
- Gate C advances materially because authority preview and observed budget accounting are now versioned, test-backed and independent of model output. **Gate C still does not pass**: execution receipts are not yet persisted inside the durable assessment record or exposed through authenticated API/GUI review controls, and reviewed third-party scanner runners still need pinned versions, licenses, least-privilege packaging and parser/runner integration fixtures.
- Gate E remains materially incomplete for real-model compatibility, browser-to-server E2E/accessibility, fresh-install/cross-platform packaging, SBOM/licensing evidence, threat-model/sample-report/regression-lab release material and signing.
- The sprint is therefore not eligible for early completion.

### Safety/product interpretation

This contribution adds observability and accountability around already bounded native adapters; it does not add broader exploitation authority. It does not execute Semgrep/Trivy/Nuclei/ZAP/Nmap, expose reusable secrets, broaden target scope, read project secret contents, harvest credentials or turn candidate observations into verified findings.
