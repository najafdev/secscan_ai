# SecScan AI Evidence Workbench

**Local-first assessment studio · version 0.1.0 · experimental bounded review release**

An isolated contribution in **HostX0/SecScan AI**. It does not replace or import the legacy application. Contribution initiated by **HostX0 (Abdulazeez)** with AI-assisted implementation and review. Original SecScan AI attribution and the existing [LICENSE](../LICENSE) are preserved; this contribution does not assert that the repository is MIT-licensed.

PR #1 was merged into this fork, not accepted upstream. The first bounded milestone has historical passing evidence; the owner-authorized **review-readiness hardening** continuation remains in progress. Read [PROGRESS.md](PROGRESS.md) for exact revisions/results and [ROADMAP.md](ROADMAP.md) for cumulative acceptance criteria. A passing historical run is not evidence for an untested newer commit.

## Run without an AI account or legacy installer

Python **3.11 or newer** is required. Native checks and the owned synthetic fixture need no pip packages, root privileges, model download, external scanner installation or cloud account.

```bash
git clone --branch main https://github.com/HostX0/secscan_ai.git
cd SecScan AI
python -m workbench
```

For a proposed follow-up PR, check out its exact reviewed head before testing its changes. Use `python3` where that is the Python command. `python workbench/start.py --check-install --json` provides machine-readable prerequisite diagnostics without opening report storage or contacting a model/scanner; failures use stable check/code fields instead of raw local exception text. Workspace preparation failures report `workspace_lock` / `workspace_unavailable`; an unsafe non-regular or symbolic-link lock reports `workspace_lock_unsafe`, while ordinary live-lock contention remains `workspace_busy`. Open the **private launch URL printed in the terminal**; its fragment contains a session token which the frontend removes after reading. Never share the launch URL. The service binds only to `127.0.0.1:8765`; do not expose it publicly or through a tunnel.

```bash
python -m workbench --port 8766 --data-dir ./local-workbench-data
```

**Do not run the legacy installer, root Dockerfile or enterprise compose stack for this workbench.** They have separate dependencies and behavior. The portable source package also starts with `python -m workbench` from its extracted root; it is not a native installer.

## Implemented capabilities and their limits

| Capability | Implemented | Boundary |
|---|---|---|
| Analyst assessment | One HTTP HEAD metadata response, optional validated Ollama commentary, integrity-checked report | Missing headers are observations, not exploit proof. |
| Controlled verification | Disposable owned lab, independent denied control, fresh synthetic canary | Applies only to that lab; no external exploit verification. |
| Read-only project checks | Metadata-only native adapter and reviewed Semgrep CE 1.177.0 container runner | Semgrep uses one repository-authored offline ruleset and an exact image digest; no broad language/rule coverage claim. |
| Bounded web adapter | One explicitly scoped HEAD request through DNS-pinned sockets | No redirects, bodies, authentication, arbitrary ports or broad dynamic scanning. |
| Execution review | Typed plan, exact digest approval, durable adapter lifecycle and candidate-only receipt through API/GUI | Model output cannot change authorization, scope, commands or budgets. Adapter receipts remain a separate audit trail, not automatically merged into assessment findings. |
| Retesting | API/GUI comparison and evidence-linked remediation recheck | `still_present`, `new`, `not_reproduced`, `not_retested`; absence never means fixed. |
| Reviewer export | JSON/Markdown and unsigned checksummed review ZIP | Internal assessment exports are sensitive, not a universally sanitized customer handover or signed report. |
| Release validation | Real Chromium E2E, three-OS checkout/package smoke, one real local-model compatibility probe | See exact historical runs below; not universal compatibility or security certification. |

Trivy and Nuclei are **parser-only**. ZAP and Nmap execution adapters are **not implemented**. Semgrep is **not bundled** and the runtime never pulls an image automatically. Its reviewed pin, source checksum, license and sandbox are documented in [ADAPTERS.md](ADAPTERS.md) and `tooling/semgrep-1.177.0.json`.

Public-web scope rejects non-global addresses, multicast, deprecated IPv6 site-local addresses, zone identifiers and explicitly excluded transition/special-purpose ranges. Some special-purpose anycast addresses are globally reachable but intentionally unsupported by this conservative policy; this is not a general routability classifier. A mixed DNS answer containing a denied address fails before any connection. No hostname grants permission to assess unrelated CDN/shared infrastructure.

### Owned synthetic walkthrough

Select **Built-in synthetic lab**, then **Controlled verification**. Enter a non-secret authorization reference and confirm both authorization and verification approval. With AI disabled, the approved proof runs deterministically. With AI enabled, only the single approved action or stop is available; skipping remains inconclusive.

The ephemeral loopback fixture has a denied control and a deliberately vulnerable route with designated synthetic records. The proof retains row count, schema/types, content digests and a fresh `SECSCAN_AI-SYNTHETIC-*` canary rather than ordinary record values. The corrected fixture denies the read. Neither outcome describes an outside website or proves access to a real customer database. Maximum native assessment budget is three HTTP requests, with one assessment/adapter execution lane at a time.

## AI is optional, local-first and provider-agnostic

Ollama is the **only implemented AI adapter**, our reference for private local operation, not a mandatory gateway for future providers. Model-neutral evidence/action/report interfaces permit reviewed self-hosted or third-party adapters without changing tool authority. There are no automatic downloads, sign-ins, provider/model substitutions or fallback. Deterministic no-AI operation remains available.

The adapter connects only to the operator-managed daemon at `127.0.0.1:11434`, with an optional `SECSCAN_AI_OLLAMA_PORT` override. **Localhost transport is not proof of local inference.** Local-only is the default processing policy, not a mandatory product-wide deployment policy. Cloud-backed models require explicit **Allow cloud processing for this assessment** approval. Consent resets on model/scope changes and after submission; it never expands assessment scope. Dispatched requests cannot be unsent.

The current minimized AI context may include environment/mode, rule/finding IDs, severities, proof states, remediation, check outcomes and limitations. It omits target URLs, authorization notes, raw evidence, HTTP body/header values and credentials. This is a restricted projection, not universal secret detection. Any future provider needs engagement-specific destination/field disclosure, redaction review and isolated credentials. Metadata reports location; strong no-egress claims require enforcement and measurement. For a stronger local-only deployment, configure the running Ollama daemon with `OLLAMA_NO_CLOUD=1`, restart it and apply independent egress controls.

**Detect** and **Check model** do not infer. **Test response** explicitly sends fixed synthetic prompts and may consume usage, but executes no tool and sends no assessment data. Missing token usage is unknown, not zero; billing cost is not invented. One small real local model has historical compatibility evidence, not an assessment-quality/GPU benchmark. Cloud inference has not established this milestone. See [OLLAMA.md](OLLAMA.md) for endpoint schemas, response validation and exact limitations.

## Evidence, reliability and storage

Reports have finding/evidence hashes, ordered hash-linked events and a final integrity checksum. Integrity is checked before persistence/export. Running checkpoints and durable final publication distinguish interruption and storage failure; a memory-only fallback is explicitly `not_durable`, not a successful durable export. Adapter execution also fails closed at the terminal persistence boundary: if a bounded adapter returns but its durable terminal receipt cannot be published, the lifecycle is marked `interrupted` when storage recovers, no successful receipt is exposed, and callers are told to check status rather than automatically re-execute. Concurrent attempts against one approved lifecycle cannot both reach the registry. The shared monotonic deadline/cancellation path covers native DNS, TCP connect, TLS, response and the current Ollama transport. DNS cancellation bounds the caller's wait; it cannot kill an OS resolver already running. Filesystem cancellation remains cooperative at metadata boundaries.

`candidate` is imported output, `observed_only` is a native observation, and `verified_in_lab` is only an owned synthetic proof. Completion means selected checks finished, not that a target is safe. Failed/skipped/inconclusive coverage stays visible. Reports default to `~/.secscan_ai-workbench` and are **not encrypted at rest**; protect device storage and retention. Never put secrets in authorization references.

Checksums are unsigned integrity aids, not authorship proof: a writer with complete access can recompute them. Package provenance/SBOM attestations are separate from assessment-report signing.

**No findings is not a security guarantee. A failed or skipped verification does not prove that exploitation is impossible.**

## Reproduce validation

```bash
python -m unittest discover -s workbench/tests -v
python -m compileall -q workbench
node --check workbench/static/app.js
node --check workbench/static/adapter.js
node --test workbench/tests/*.cjs
python -m workbench.tests.fresh_install_smoke
```

Node is test-only, not an application runtime dependency. Protocol mocks and DOM/fetch tests are not live-model inference or browser E2E. Optional pinned Semgrep integration is explicitly skipped when its reviewed Docker image/runtime is unavailable; do not count that as passing execution.

Historical source head `328bfda14c1e2ea458391e491c575a8ee5303b9e` used PR checkout `87100841867832c72e26073bfc71ad664fe34481`:
- [Evidence Workbench run 35589788372](https://github.com/HostX0/secscan_ai/actions/runs/35589788372): native Python 3.11/3.12/3.13, real local model, pinned Semgrep, Chromium-to-loopback E2E and Ubuntu/macOS/Windows checkout smoke.
- [Package run 35589788385](https://github.com/HostX0/secscan_ai/actions/runs/35589788385): the same portable archive bytes tested on Ubuntu/macOS/Windows before GitHub/Sigstore provenance and SBOM attestations. Not Windows/macOS platform signing or a native installer.

Those runs do not certify newer changes or the legacy application. Legacy CI has independent failures and inherited advisory checks that suppress exit codes; its green jobs are not security/compliance certification. See the current ledger instead of assuming repository-wide success.

## Reviewer navigation

Start with [PROGRESS.md](PROGRESS.md), then [ROADMAP.md](ROADMAP.md). Review `engine.py`/`network_transport.py` for scope and deadlines, `registry.py`/`adapter_lifecycle.py` for finite execution and exact approval, and `contracts.py`/`retest.py` for observation authority and conservative comparisons. [ADAPTERS.md](ADAPTERS.md), [THREAT_MODEL.md](THREAT_MODEL.md), [REGRESSION_LABS.md](REGRESSION_LABS.md) and [RELEASE_NOTES.md](RELEASE_NOTES.md) document coverage. [PRODUCT_DIRECTION.md](PRODUCT_DIRECTION.md) describes direction rather than shipped claims.

Not implemented: authenticated real-role execution, external exploit verification, private-network target scopes, broad business-logic tests, multi-user/public hosting, application encryption at rest, signed assessment reports, PDF handover, native installers and broader provider/model quality evaluation. These are real future capabilities, not universal-completeness claims or guaranteed upstream acceptance.
