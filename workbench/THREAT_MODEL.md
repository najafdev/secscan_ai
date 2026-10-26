# Evidence Workbench threat model

Status: review-preview threat model for the isolated `workbench/` package. This is not a security certification of the legacy SecScan AI application.

## Security objectives

The workbench is designed to keep assessment authority outside AI/model output, preserve the distinction between observation and independently demonstrated proof, prevent accidental expansion of an approved scope, minimize sensitive data in evidence and model context, and make incomplete coverage visible rather than converting it into a clean verdict.

The current deployment model is a single operator on a trusted workstation. The HTTP service binds to loopback and is not designed for public or multi-user hosting. The operator is responsible for obtaining authorization, protecting the host, choosing retention, and deciding whether external model processing is permitted for an engagement.

## Assets

1. Scope and authorization metadata.
2. Test-account secrets when authenticated contexts are added in a later milestone; these are not implemented today.
3. Findings, evidence digests, coverage records, execution receipts and report history.
4. Local model prompts/responses and optional external-processing metadata.
5. SQLite report/checkpoint storage and exported evidence bundles.
6. Source projects inspected by read-only adapters.

## Trust boundaries

### Browser to loopback service

The browser UI is untrusted input. The server requires a per-launch bearer token for `/api/*`, validates Host and Origin, does not enable CORS, limits request bodies, returns no-store/CSP headers and binds only to `127.0.0.1`. A copied launch token grants the same local preview access, so it must be treated as a session secret.

### Scope to execution registry

User/model text does not become a command. Reviewed adapter IDs map to code-owned constructors. Typed execution declarations and an independent operator policy limit effect level, filesystem/network access, subprocess/write/symlink permissions and object/request/time budgets. Unknown adapter or request fields fail closed.

### Adapter output to evidence model

Tool output is untrusted data. Normalizers bound size/shape and force imported scanner observations to `candidate`. An adapter cannot mark its own finding independently verified. Coverage failures, partial results and unsupported checks remain explicit.

### Model boundary

Model output is commentary or a request for a finite allowlisted action; it is never execution authority or evidence by itself. The current Ollama adapter can represent local or explicitly approved cloud-backed processing. Localhost transport is not proof of local inference. External processing requires engagement-specific opt-in and minimized context; there is no silent provider/model fallback.

### Durable storage and exports

Terminal reports are sealed before durable publication. Running checkpoints are distinct from finalized reports. Restart recovery produces `interrupted`/`inconclusive`, not completed. Current SHA-256 chains and manifests detect inconsistent modification relative to a trusted digest but are unsigned and do not prove authorship. SQLite and exports are not encrypted by the application.

## Threats and controls

| Threat | Current control | Residual limitation |
|---|---|---|
| DNS rebinding/private-target pivot | URL validation, public-address validation, DNS-pinned native sockets, no redirects | Public routing/TLS validation still depends on the host OS/network; private-network assessment is unsupported. |
| Browser/API cross-origin abuse | Loopback bind, bearer token, strict Host/Origin, no CORS, CSP/no-store | Malware or another process with local-user privileges may still access local resources. |
| Prompt injection expands authority | Model receives minimized normalized context; action registry and scope checks are enforced outside model | Model text can still be misleading; human review remains required. |
| Scanner output claims exploitation | Candidate-only normalization and verification firewall | Third-party scanner execution is not yet bundled or pinned. |
| Secret leakage in reports | Native proof uses fresh synthetic canaries and digests; parser minimization removes selected sensitive raw fields | Future adapters require adapter-specific minimization tests; generic redaction is not a proof that every secret is removed. |
| Customer data sampled as proof | Current proof uses owned synthetic records only | Authenticated customer environments need designated test records before that feature can be enabled. |
| Run marked complete after crash | Active checkpoints, atomic finalization, restart recovery to interrupted/inconclusive | Device/filesystem failure can still make a run non-durable; that state blocks export/retest use. |
| Cancellation ignored during I/O | Shared deadline and cancellation-aware DNS/connect/TLS/HTTP/model paths | Filesystem cancellation is cooperative at metadata boundaries; an already-blocking OS syscall is not guaranteed instantly preemptible. |
| Cloud model receives data without consent | Cloud processing is engagement-specific opt-in; context omits target URL, authorization notes, raw evidence and credentials | Provider/runtime/network behavior is outside the workbench; stronger no-egress claims require deployment controls and measurement. |
| Evidence bundle represented as signed proof | UI/docs label hashes and ZIP manifest unsigned | Digital signing/key management is not implemented. |
| Local database theft | Restrictive file modes where supported | Application-level encryption at rest is not implemented. |
| Tool supply-chain compromise | No third-party scanner binaries are bundled in this milestone | Future runner packaging must pin versions/images, licenses, checksums and SBOM entries before execution support is claimed. |

## Explicitly out of scope for this milestone

- Public/multi-user service hosting.
- Unrestricted autonomous compromise.
- Credential harvesting, persistence, lateral movement or customer-database dumps.
- Private-network scanning and broad subnet discovery.
- Signed reports/releases or application-managed encrypted storage.
- Executable Semgrep, Trivy, Nuclei, ZAP or Nmap runners.
- Claims that a completed run means the target is secure.

## Security review triggers

A fresh threat-model review is required before adding: a new executable runner; authenticated external test accounts; private-network scope; arbitrary file-content access; a new AI provider adapter; public/multi-user hosting; evidence signing; or a data-retention/export format that carries more raw target material.
