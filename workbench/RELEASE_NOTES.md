# Evidence Workbench review-preview release notes

## Post-merge review-readiness hardening (in progress)

PR #1 and PR #2 are merged into the HostX0 fork; this is not upstream acceptance. Development remains active while substantial in-purpose reliability, release, reviewer and validation gaps remain. Historical implementation and hosted validation below are distinct from current unpassed acceptance criteria in ROADMAP.md.

- Repair the shared public-web resolver boundary: reject multicast, IPv6 site-local/zone identifiers and explicit special/transition prefixes, including mixed DNS answers before connection.
- Pre-cancelled/expired resolution dispatches no fresh resolver work; cancellation remains bounded even when a caller omits an explicit deadline. An OS resolver already running is not forcibly killed.
- Align current capability/release/model documentation; retain the first-milestone ledger and roadmap byte-for-byte as linked historical files.
- Repair legacy artifact-action setup and LDAP/PortAudio build prerequisites without dropping test/lint commands. Fork Docker CI is build-only, not publication. Other legacy defects remain separately tracked; setup fixes are not an all-green claim.
- Add offline scope/cancellation, candidate-lifecycle and documentation/workflow regression coverage. See PROGRESS.md for exact observed results and unavailable integrations.
- Harden adapter terminal publication: one approved lifecycle cannot execute concurrently twice; a terminal SQLite failure can no longer be mislabeled as an adapter execution failure or durable success. The recoverable state is `interrupted`, no receipt is exposed, and the API directs the operator to check status rather than automatically retry.
- Make dependency-free startup diagnostics actionable without leaking local exception details: `--check-install --json` reports stable failure stages/codes for application files, SQLite, workspace preparation/write access, unsafe lock objects and loopback-port availability while preserving the no-report/no-model/no-scanner preflight boundary.
- Repair trusted portable-release attestation verification after post-merge main exposed an output-name mismatch: package build, three-OS exact-byte smoke and both GitHub/Sigstore signatures succeeded, but the verifier received `_release/.tar.gz`. The release workflow now uses one `package_basename` output consistently and verifies the exact preserved provenance and CycloneDX SBOM bundles against the package, repository and source revision before evidence upload. Pull requests still receive no OIDC/attestation write authority. This verifies supply-chain claims for package bytes; it is not native code signing, assessment-report signing or security certification.

### Release failure propagation and pre-sign integrity

The concurrent release-verification repair is retained. Add a check of the exact revision-bound package name and downloaded SHA-256 before signing, and require both verification commands to match the expected signer workflow. Offline shell replay covers missing/tampered artifacts and either verifier's nonzero status, without claiming a fake verifier proves cryptographic integrity. The release tests and original product features remain. See PROGRESS.md for source reconciliation, exact validation and the current owner-authorized ongoing development scope.

## 0.1.0 review preview

This is an isolated contribution under `workbench/`; it does not replace the legacy SecScan AI entry points and is not a claim of complete penetration-testing coverage.

### Implemented

- Loopback single-operator assessment UI and token-authenticated local API.
- Explicit authorization/scope capture with Analyst and Controlled verification modes.
- Evidence-first report model with finding/evidence digests, hash-linked events and report integrity checks.
- Owned disposable authorization/data proof using a denied control and fresh synthetic canary.
- Shared assessment deadline/cancellation across native DNS, TCP connect, TLS, HTTP response and current Ollama transport.
- SQLite running checkpoints, atomic terminal publication, non-durable failure state and interruption recovery.
- Candidate-only scanner-result parsers for Semgrep JSON, Trivy JSON and Nuclei JSONL. Parser support by itself is not runner support.
- Finite execution registry with typed declarations, operator authority ceiling, a metadata-only project adapter and one bounded HEAD-only web adapter.
- Reviewed `semgrep-project-local/1.177.0-r1` execution adapter using an exact digest-pinned Semgrep CE Linux/amd64 image, repository-authored offline rules, disabled scanner networking/version checks/metrics, read-only source/rules/root filesystem, dropped capabilities, no-new-privileges, host UID/GID mapping, bounded CPU/memory/PIDs/output/deadline and no automatic image pull. The normalized parser removes source snippets/metavariable values and findings remain `candidate`.
- Durable adapter plan/approval/execution lifecycle with exact request-digest binding, minimized stored summaries, authenticated API/GUI controls and versioned execution receipts.
- Coverage-aware retesting and checksummed reviewer evidence bundles.
- Current Ollama adapter with explicit local/cloud processing policy and synthetic protocol self-tests.
- Machine-readable review manifest, CycloneDX SBOM for the isolated shipped component and a revision-generated synthetic sample report.
- Real Chromium browser-to-loopback E2E in CI using the actual token-authenticated server/UI, responsive widths 1440/768/390, accessibility-tree naming checks, keyboard traversal, owned synthetic controlled-verification flow, history rendering and runtime-exception monitoring.
- Fresh-checkout smoke jobs on GitHub-hosted Ubuntu, macOS and Windows runners using only the isolated standard-library workbench path. The smoke starts the real loopback server, exercises authenticated health/adapter discovery, completes the owned synthetic verification, checks durable persistence/integrity and exports the saved report.
- Dedicated scanner-validation CI that pulls the exact reviewed Semgrep image digest before assessment execution and then runs the offline adapter on owned vulnerable and corrected Python fixtures. Evidence Workbench run `35586469998` passed that scanner job and the full native/browser/platform matrix at feature head `c23414f3eb5fc34a0e66d2668ed0165a8d139b09`.

### Experimental or incomplete

- Trivy and Nuclei remain parser-only; ZAP and Nmap execution adapters are not implemented. The Semgrep runner validates one reviewed ruleset/boundary and is not universal language/rule coverage.
- Authenticated external application test accounts/role runners are not implemented.
- Historical run `35589788372` passed one real local Ollama `0.34.2` / `smollm2:135m-instruct-q5_K_M` compatibility probe separately from protocol doubles. Quality/GPU/cloud-provider benchmarking remains unestablished.
- The current real browser E2E is Chromium on GitHub-hosted Ubuntu; it is not a multi-browser compatibility claim and does not replace manual assistive-technology review.
- Historical package run `35589788385` tested the exact same portable source archive on Ubuntu/macOS/Windows before provenance/SBOM attestations. No native installer or bundled scanner/container image is produced.
- GitHub/Sigstore build-provenance and SBOM attestations exist for historical packages and are generated only in trusted repository contexts. Verification evidence is retained separately from the portable archive. These are not signed assessment reports, platform code-signing certificates or a security certification; report checksums remain unsigned.
- Any future executable third-party runner needs its own pinned version/image, checksum, license, sandbox boundary, owned integration fixtures and SBOM/release evidence before it can be described as shipped.
- Application-level encryption at rest and multi-user/public hosting are unsupported.

### Safety and interpretation

`candidate` and `observed_only` are not equivalent to demonstrated exploitation. `verified_in_lab` applies only to the owned synthetic fixture. `not_reproduced` is not renamed fixed. No findings in executed checks is not a security guarantee. Hashes are unsigned and do not prove authorship.

No external target, customer database, reusable credential, paid AI request, persistence or lateral movement is part of the review-preview validation path. The real Semgrep validation scans only repository-owned synthetic fixtures inside an offline least-privilege container.
