# Evidence Workbench development roadmap

This is an ordered engineering backlog, not a claim that all features are implemented or that a fixed sprint can finish every item. Prefer complete, tested slices. Never create cosmetic commits merely to increase contribution counts or promise stars, investment, acceptance or universal capability.

## Development protocol

Read current `main`, the open workbench PR and `PROGRESS.md` before each contribution. Continue the reviewable `feat/evidence-workbench` branch unless a dependent branch is necessary. Preserve upstream attribution, the existing repository license and other contributors' changes. Do not force-push, deploy publicly, contact upstream maintainers or spend money without separate authorization.

Record actual files changed, tests run and explicit validation limits. A configured test is not a passing test. Missing adapters, model checks, E2E coverage or reliability guarantees remain real gaps, not optional polish.

**Current owner direction, 2026-09-21:** local-first and provider-agnostic. The workbench currently implements Ollama as its reference AI integration, including local and explicitly approved cloud-backed models, but product contracts must not depend on Ollama being the permanent gateway. Future reviewed adapters may support third-party APIs or self-hosted inference without changing evidence/tool authority. No silent provider/model fallback, paid development calls, automatic credential provisioning or mandatory cloud dependency. Deterministic no-AI operation remains supported.

## Measurable release-milestone gates

These gates determine whether a review milestone is genuinely complete. They are cumulative. A sprint may stop early only when all gates for the declared milestone pass and remaining work is explicitly outside that milestone.

### Gate A — evidence core
- Final reports are integrity-checked before persistence/export.
- Failed/skipped/inconclusive checks remain visible and cannot become successful coverage.
- Scanner imports cannot self-promote observations to independently verified findings.
- Synthetic proof has a denied control and fresh canary, and is never attributed to an external target.

### Gate B — reliability boundary
- One enforceable end-to-end deadline covers resolution, connect, TLS, response and model operations.
- Cancellation is tested in every phase and cannot publish an unsealed terminal report.
- Crash/restart recovery cannot expose a running job as completed.
- Terminal report publication and durable persistence are atomic or explicitly marked non-durable.

### Gate C — adapter and scope boundary
- Versioned adapter contracts reject malformed/truncated/oversized output and disclose exact coverage.
- Execution adapters use typed configuration, fixed binaries/images and independent scope/effect/request limits; no model-generated shell strings.
- At least one read-only project adapter and one bounded web adapter pass vulnerable/fixed synthetic fixtures before broader claims.

### Gate D — retest and reviewer evidence
- Cross-run comparison distinguishes still-present, new, not-reproduced and not-retested; absence alone never means fixed.
- Reviewer bundles contain checksummed report artifacts and safe proof metadata without reusable credentials or ordinary customer-row samples.
- Remediation evidence links to a comparable recheck and preserves changed-scope/failed-scanner states.

### Gate E — usable review release
- Real-model compatibility is tested separately from protocol doubles; processing location/usage remain honest.
- Browser-to-server E2E and keyboard/accessibility flows pass on documented browsers.
- Fresh-install smoke tests pass on the documented platforms with pinned dependencies/tool licenses and an SBOM.
- Threat model, sample reports, regression lab catalog and release notes clearly separate implemented, experimental and unsupported coverage.

**Current bounded milestone state: Gates A, B, C, D and E pass their declared criteria.** Gate C closed at feature head `c23414f3eb5fc34a0e66d2668ed0165a8d139b09` in Evidence Workbench run `35586469998`: the exact Semgrep CE 1.177.0 Linux/amd64 image digest was preloaded, then the runner executed with network disabled, read-only source/rules/root filesystem, dropped capabilities, no-new-privileges, host UID/GID mapping, bounded resources/output/deadline, disabled metrics/version checks and repository-authored offline rules. The owned vulnerable fixture produced the expected candidate rule and the corrected fixture did not. Trivy/Nuclei remain parser-only and ZAP/Nmap are not execution adapters; Gate C passing is not a claim of universal scanner coverage. Gate E closed after the real Chromium-to-loopback E2E/accessibility path, GitHub-hosted Ubuntu/macOS/Windows validation, a real assessment-data-free local Ollama model compatibility probe on an isolated internal network, and a deterministic portable source archive that is smoke-tested as the exact same bytes on Ubuntu/macOS/Windows before GitHub/Sigstore build-provenance and SBOM attestations are generated. The package remains a portable source archive rather than a native installer, and the milestone remains an experimental bounded review release rather than universal penetration-testing coverage. Work beyond these gates is expansion/hardening outside this declared milestone and should not be represented as a blocker to the bounded milestone.

## 1. Complete the reliability boundary

Implemented foundations include a shared monotonic deadline for native resolver/connect/TLS/response and Ollama runtime calls, cancellable bounded DNS waiting, no terminal unsealed publication from `Assessment`, active SQLite checkpoints, restart recovery to explicit `interrupted`, and atomic durable terminal publication with explicit `not_durable` memory-only fallback.

The production passive-web path uses a cancellation-aware nonblocking TCP connector. Owned adversarial fixtures exercise pending-connect cancellation/deadline, TLS-handshake cancellation/deadline, slow-response cancellation/deadline and slow model cancellation/deadline; bounded DNS cancellation/deadline and durable publication/recovery are also covered. The first timing-sensitive CI assertion was corrected because a successful cancellation may legitimately occur before the owned HTTP fixture parses a HEAD request; the corrected test asserts bounded cancellation and no unintended GET/body path instead.

Next work beyond the bounded Gate B criteria:
- Normalize rejection of special/multicast/tunnel IP ranges across supported Python versions; retain DNS pinning and no redirects.
- Test concurrent API activity and additional SQLite/storage failure modes, including checkpoint gaps followed by restart.
- Decide and document how test-only injected readers participate in deadline enforcement without weakening production boundaries.
- Add structured validation errors and richer coverage accounting that distinguish failed, unsupported, excluded and executed tests.
- Keep project-filesystem cancellation explicitly cooperative at metadata boundaries; do not describe blocking filesystem syscalls as instantly interruptible.

Acceptance: **Gate B passes** at feature head `4e71682a0a44c6cbd650c8aa1cf921d50e0766fa` in Evidence Workbench run `35568876285` on Python 3.11, 3.12 and 3.13. Later feature heads preserve that boundary in the same dedicated test matrix.

## 2. Stable adapter and finding contracts

Implemented foundations: `secscan_ai.adapter-result/v1`, deterministic fingerprints, candidate-only import authority, privacy-minimizing offline parsers for Semgrep JSON, Trivy JSON and Nuclei JSONL, malformed/truncated/oversized input tests, explicit coverage caveats, the closed `secscan_ai.execution-declaration/v1` authority contract, a finite `ExecutionRegistry` with operator-owned filesystem/network/effect ceilings, `secscan_ai.execution-receipt/v1`, and the durable `secscan_ai.adapter-lifecycle/v1` plan/approval/execution state machine.

The registry validates a typed adapter request without I/O, exposes a minimized review preview and binds a normalized candidate-only result to declared authority plus observed object/request/elapsed-time accounting. Lifecycle storage persists the minimized declaration/summary and an exact request digest rather than the raw request, makes approved plan fields immutable, revalidates the resubmitted request before I/O, records stable failure states without raw exception text and recovers stale `executing` records as `interrupted`. Receipt validation rejects nested sensitive/execution fields, identity mismatches and usage above declared object/request budgets. See [ADAPTERS.md](ADAPTERS.md).

The first reviewed third-party runner is now `semgrep-project-local/1.177.0-r1`. Its exact Linux/amd64 image digest, upstream release/source references, source checksum and LGPL-2.1-or-later license are recorded in `tooling/semgrep-1.177.0.json`. It launches only a fixed typed Docker invocation with `--pull never`, container network `none`, a read-only root filesystem, dropped Linux capabilities, `no-new-privileges`, PID/memory/CPU limits, host UID/GID mapping, read-only source/rules mounts and an ephemeral tmpfs for the scanner's mutable cache/log state. Metrics and version checks are disabled, rules are repository-authored/offline, output is bounded, and parser minimization keeps findings candidate-only.

Next work beyond Gate C:
- Add new third-party runners only after each tool receives the same pin/license/checksum/sandbox/fixture review; parser availability alone does not qualify.
- Keep severity separate from confidence, proof state, exploitability assumptions and business impact.
- Preserve adapter-specific minimization and lifecycle-tamper tests as richer outputs are added.
- Add richer per-tool progress without weakening exact request-digest approval or the independent audit trail.

Acceptance: **Gate C passes** at feature head `c23414f3eb5fc34a0e66d2668ed0165a8d139b09` in Evidence Workbench run `35586469998`. Malformed/truncated fixtures cannot invent verified findings; native project/web execution stays independently bounded; the reviewed Semgrep runner passes owned vulnerable/corrected integration fixtures in its least-privilege offline container boundary. This acceptance does not imply executable Trivy/Nuclei/ZAP/Nmap support.

## 3. Project-code checks first

The first native project execution adapter is implemented as a metadata-only boundary: it inventories bounded filenames without reading content, following symlinks, using subprocesses/network, or writing to the project. Vulnerable/corrected filename fixtures pass. Cancellation is propagated by the finite registry into cooperative checkpoints before and during the metadata walk. Its plan/approval/execution receipt can be reviewed and persisted through the same authenticated lifecycle API/GUI without storing the full local root path.

A reviewed Semgrep CE project runner is also implemented for a narrow repository-authored ruleset. It reads project content only through the explicitly approved read-only source mount, has no scanner network, no dynamic rule source, no target writes, no model-selected argv and no automatic image pull. Hosted CI validates the exact pinned image against owned vulnerable/corrected Python fixtures and confirms normalized output remains candidate-only with source snippets/metavariable values removed.

Next work: broaden code/dependency/secret checks only through similarly reviewed runners and never expose raw secret values in normalized evidence. A Trivy implementation, if added, requires its own pinned release/image, license, offline database/update policy, sandbox and secret-redaction tests; current Trivy support is parser-only. Do not send source, credentials or raw secrets to inference by default. Any external processing needs adapter-specific minimization and disclosure rather than a generic cloud checkbox.

Acceptance: Gate C's read-only project-execution criterion is now met by the native metadata adapter plus the bounded Semgrep runner. Broader project-security coverage remains future work rather than part of the Gate C claim.

## 4. Controlled web assessment adapters

A first bounded native web execution adapter exists: one explicit URL, one HEAD request, no redirects, no response body, no filesystem/subprocess/write authority, and candidate-only hardening-header observations. Its vulnerable/corrected logic fixtures pass and its production HTTP-reader path has an owned loopback fixture. The same exact URL/limits pass through durable plan approval and execution receipt controls. This does not constitute ZAP/Nuclei execution or broad application coverage.

Next work: add reviewed ZAP/Nuclei-style integrations only with target/path allowlists, request budgets, safe profiles, pinned versions/licenses and isolated fixtures. Do not equate a hostname with permission for a CDN/shared IP. Disable uncontrolled callbacks/out-of-band behavior by default. Process runners consume typed configs, never model-generated shell strings.

Acceptance: Gate C's bounded web-adapter criterion is met by the native one-HEAD adapter and owned production-path fixture. Broader dynamic web scanning remains future capability and requires separate tool-specific review.

## 5. Authenticated test contexts

The execution-neutral `access_matrix.py` foundation compares explicit role/resource expectations against normalized allowed/denied/error/skipped outcomes, rejects credential/body fields, keeps missing cases incomplete and forces unexpected allows through the candidate-only adapter boundary. It does **not** authenticate or send requests.

Next work: support operator-provided designated test accounts/roles with secure local storage, redaction, expiry and a scoped runner that feeds this matrix. Use customer-designated synthetic/test records and inert canaries for proof. Never use unrelated live customer rows as report samples.

Acceptance: role/isolation vulnerable/fixed fixtures pass, denied controls are independently demonstrated and secrets are absent from logs, prompts and exports.

## 6. Bounded model-independent orchestration

The current `ExecutionRegistry` is finite and policy-gated: reviewed adapter IDs map to code-owned constructors, unknown command/dynamic fields fail closed, and operator filesystem/network/effect ceilings are checked before adapter I/O. `plan()` is I/O-free and `execute_with_receipt()` produces versioned candidate-only receipts.

`AdapterLifecycle` now persists `planned -> approved -> executing -> completed|failed|cancelled|interrupted`, binds approval to the exact plan/request digest and revalidates the same request before execution. `workspace_server.py` exposes authenticated plan/approve/execute/cancel/read routes and serializes the adapter lane against ordinary assessment starts. The GUI freezes inputs after planning and keeps execution disabled until the exact digest is approved. No model output participates in these approval decisions.

Next work: expand the registry only after each third-party adapter has deterministic validation, pinned packaging/licensing and independent sandbox/scope enforcement. Add per-tool progress events and integrate resulting candidate observations into the main assessment report only with explicit provenance and without collapsing the independent lifecycle audit trail. Renew approval whenever target/effect/scope changes.

Acceptance: adversarial responses cannot change target, permissions, shell commands, budgets or evidence state. Local/cloud/provider routing never changes tool authority.

## 7. Retesting and change-aware reports

Implemented Gate D foundations distinguish `still_present`, `new`, `not_reproduced` and `not_retested`; comparison is exposed through the local API/GUI; reviewer bundles carry checksums and safe minimized proof; and each prior finding gets a recheck binding with previous/current run IDs, previous finding/evidence references, a remediation-guidance digest, exact mapped coverage status and explicit scope comparability. Failed/unmapped checks and changed target/environment remain `not_retested`; `not_reproduced` is never renamed fixed; whether remediation was actually applied remains `unknown` absent separate evidence.

Next work beyond the bounded Gate D criteria: add optional operator-authored remediation activity records with provenance and reviewer signatures/attestation only after a threat model and key-management design. Do not weaken the existing conservative state machine to make dashboards look greener.

Acceptance: Gate D passes at `1c85853a`; failed scanner or changed scope cannot falsely close a finding.

## 8. Interface and accessibility

Retest comparison, evidence-bundle download and reviewed adapter plan/approval/receipt controls are surfaced in the current GUI. The adapter UI performs no automatic discovery or execution, freezes exact typed inputs after planning, and labels receipts as candidate review metadata rather than proof. DOM/fetch contract tests cover plan, approval, execution and web/project request shapes.

A real browser-to-server job launches the actual loopback workbench and system Chromium through the DevTools protocol without Playwright/Selenium. It verifies private launch-token removal, no token rendering, responsive widths at 1440/768/390, no horizontal overflow, accessible names on focusable controls, keyboard reachability across enabled assessment/review controls, actual owned synthetic controlled verification, history rendering and zero observed runtime exceptions. Hosted validation remains Chromium/Ubuntu, not a multi-browser/manual assistive-technology certification.

Next work: continue typography/touch targets, focus management under long-running/cancellation states, localization-ready strings, filters, per-tool progress and evidence drill-down. Broaden real-browser coverage only where it produces meaningful compatibility evidence; manual assistive-technology review remains separate from the automated accessibility-tree checks.

Acceptance: the bounded Chromium/Ubuntu browser-to-loopback and keyboard/accessibility criterion is test-backed by the current aggregate Evidence Workbench workflow.

## 9. Reproducible packaging

The isolated workbench remains standard-library-first and separate from legacy dependencies. A fresh-checkout smoke module starts the real `WorkbenchServer`, exercises token-authenticated health and adapter discovery, completes the owned synthetic verification, verifies report integrity/durable SQLite persistence, exports the saved report and checks history. The aggregate Evidence Workbench workflow passes this checkout smoke on GitHub-hosted Ubuntu, macOS and Windows with Python 3.13.

The optional Semgrep execution boundary has explicit supply-chain metadata: exact tool/image version and digest, upstream release/source references, source checksum, license, offline rules source and non-bundled/automatic-pull-false state are included in review metadata/SBOM surfaces. CI fetches the exact reviewed image for its owned scanner fixture; the runtime runner itself never performs a pull.

The release-package workflow now builds one deterministic portable source archive from the reviewed revision, records its SHA-256 and machine-readable package manifest, includes the scoped CycloneDX SBOM/release evidence, and then downloads and smoke-tests the exact same archive bytes on GitHub-hosted Ubuntu, macOS and Windows. Only after all three package-smoke jobs pass does the workflow generate GitHub/Sigstore build-provenance and SBOM attestations for that archive and verify the attestation through GitHub CLI. The package explicitly remains a portable source archive, not a native installer or platform code-signing claim.

Next work beyond Gate E: native installers and platform-specific code signing may be added only if they create material user value; additional reviewed scanner runtimes require the same pin/license/SBOM/sandbox treatment. Offline/update bundles and measured storage/performance remain future release-expansion work, not blockers to this bounded source-package milestone.

Acceptance: **Gate E's packaging criterion passes** at feature head `569e387177ac73f1d620cf0421fc3549986d2d83` in Evidence Workbench Release Package run `35589361575`: the exact package candidate passed compile + real loopback fresh-install smoke on Ubuntu, macOS and Windows before provenance/SBOM attestations were created. This acceptance is provenance for a bounded portable source package, not a native-installer security certification.

## 10. Release-quality evidence

Implemented review-evidence foundations include [THREAT_MODEL.md](THREAT_MODEL.md), [REGRESSION_LABS.md](REGRESSION_LABS.md), [RELEASE_NOTES.md](RELEASE_NOTES.md) and `release_evidence.py`. The Python 3.13 CI job generates a revision-bound machine-readable review manifest, a CycloneDX SBOM scoped to the isolated workbench plus explicitly described optional scanner component, a JSON/Markdown sample report produced by the owned synthetic authorization fixture, checksums and the source/test-log review bundle. Separate jobs generate real Chromium loopback E2E evidence, scanner-validation evidence, real local-model compatibility evidence and source/package smoke results.

The real-model job preloads `smollm2:135m-instruct-q5_K_M`, then restarts Ollama with `OLLAMA_NO_CLOUD=1` on a Docker internal-only network. A test-only loopback relay has one validated private-container destination so the production workbench client remains loopback-only. The fixed structured-output compatibility probe sends no assessment target, evidence, authorization, credentials or customer data, executes no tool and records one inference request/response. Evidence Workbench run `35588796848` first demonstrated the corrected isolated live-model path; later aggregate runs preserve it.

The revision-bound validation-summary job fails closed unless native Python matrix, pinned Semgrep fixture, live local model, browser E2E and cross-platform checkout jobs all pass. Evidence Workbench run `35589361607` passed the complete bounded validation workflow at the packaging feature head. Release Package run `35589361575` separately demonstrated exact-archive cross-platform smoke and signed GitHub/Sigstore provenance/SBOM attestations after those smokes.

Next work beyond the bounded Gate E criteria: benchmark additional real models/providers only when a concrete compatibility/quality question requires it; broaden browser/manual assistive-technology coverage where useful; and add native-install/package channels only with explicit signing/key-management designs. These are expansions, not evidence that the bounded review milestone is incomplete.

Acceptance: **Gate E passes its declared bounded criteria.** The release remains experimental and scoped: one real small local model/runtime combination is validated rather than all models/providers; Chromium/Ubuntu is the hosted browser path rather than multi-browser certification; the signed artifact is a portable source archive rather than a native installer; Trivy/Nuclei remain parser-only and ZAP/Nmap are not executable adapters; no external assessment target, real credential, ordinary customer row, live cloud inference or paid service was used to establish the milestone.

## 11. Professional engagement workflow and trusted knowledge

Build customer-isolated workspaces, machine-readable rules of engagement, scope/effect previews, designated role matrices, reviewed proof plans, remediation ownership and executive/technical handover. Legal authorization is necessary but not a substitute for precise technical scope/data handling.

Knowledge refresh begins with a licensed, source-linked, versioned retrieval corpus. Preserve publication/ingestion dates, source revisions, licenses, conflict/staleness state, evaluation and rollback. Never ingest customer secrets into shared knowledge. Runtime/model downloads, RAG refresh and actual fine-tuning are distinct. Fine-tuning requires a separately approved dataset/evaluation/release pipeline; no autonomous self-modification.

Acceptance: one customer cannot cross into another workspace, retrieved text cannot authorize an action and a report cannot claim deeper impact than independent evidence demonstrates.
