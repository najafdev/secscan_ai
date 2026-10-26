# Product direction: evidence-led security assessment operations

**Owner direction recorded 2026-09-21. This is an engineering direction, not an implemented-feature list, novelty claim, release commitment or investor forecast.** Current functionality is in README.md; measured progress is in PROGRESS.md.

## The product, not the model, owns the workflow

Aim to help an authorized assessment team manage the journey from engagement/scope through observations, controlled verification, remediation, retesting and handover. The public architecture is **local-first and provider-agnostic**. Ollama is the only AI integration implemented in the current workbench and is our reference path for private local operation, but evidence schemas, action authority, reports and test outcomes must not depend on a permanent Ollama gateway. Reviewed future adapters may use self-hosted inference or third-party APIs when an operator explicitly chooses them.

Local execution is preferred when an engagement requires operator control or data sovereignty. External inference requires engagement-specific disclosure/approval and minimized fields. No provider/model/location changes target authorization or tool authority. Deterministic no-AI operation remains a first-class path.

The product should reduce operator effort while making every conclusion auditable. It must not claim to replace all expertise, legal judgment or customer review. Global reputation or investment is an external outcome, not a code feature.

## Target end-to-end engagement journey

1. Record customer, approved assets, exclusions, designated test accounts/data, time window, effect/request budgets, data handling and stop contact. Preview exactly what a proposed run may do.
2. Inspect project code/configuration/dependencies and scoped web/API surfaces through reviewed adapters. Keep failed, excluded, unsupported and executed coverage distinct.
3. Triage observations by evidence, confidence, technical severity, assumptions and business context rather than an invented single safety score.
4. Demonstrate relevant impact with the **smallest approved non-destructive proof**. Prefer synthetic records/canaries or customer-designated test data. Stop after sufficient evidence; deeper access is not an objective by itself.
5. Supply evidence-linked remediation and independently recheck it under comparable coverage. Separate still-present, new, not-reproduced and not-retested; do not equate absence with fixed.
6. Produce reviewed executive and technical reports with scope, method/tool versions, evidence, demonstrated impact, limitations, remediation and residual work.

Authorization is not unrestricted access. No autonomous persistence, credential theft, real-customer data extraction, lateral movement or open-ended compromise agent is part of this direction. A report may demonstrate synthetic/test-data impact without exporting reusable secrets.

## Evidence without leaking customer data

For database/API impact, the preferred proof pattern is a denied control plus an inert fresh canary. Ordinary customer row values are not needed in the report. Store schema/type information, row counts when appropriate, response/content digests and designated synthetic canaries. This gives a reviewer concrete evidence while reducing the chance that a security report becomes a secondary data breach.

The new evidence-safety helper follows this rule: ordinary record values are omitted; only explicit `SECSCAN_AI-SYNTHETIC-*` canaries may appear as sample values. This helper is a foundation, not a claim that all future adapters are automatically safe.

## High-value differentiators to validate

| Candidate | User value | Acceptance evidence | Current state |
|---|---|---|---|
| Coverage-aware retest | Prevents a broken/missing scanner from falsely marking a vulnerability fixed. | Comparable fixtures distinguish still-present, new, not-reproduced and not-retested. | Comparison and remediation-bound rechecks implemented in API/GUI; further reviewer validation remains ongoing. |
| Evidence replay/review bundle | Lets another reviewer inspect evidence without repeating risky actions. | Checksummed JSON/Markdown/manifest with optional retest diff; no claim of signature/authorship. | Unsigned JSON/Markdown bundle implemented through API/GUI; not a universally sanitized client handover. |
| Adapter verification firewall | Prevents third-party scanner output from declaring itself independently verified. | Versioned parser forces imported findings to candidate state and rejects unsupported fields. | Candidate-only parsers and one pinned offline Semgrep runner implemented; other runners remain future work. |
| Privacy-preserving database proof | Demonstrates data-layer impact without copying customer rows into reports. | Ordinary values omitted; only designated synthetic canaries may be shown. | Helper/tests added; live adapter integration pending. |
| Permission/effect preview | Shows requests, roles and excluded assets before execution. | Planner output cannot exceed independently enforced scope/action registry. | Finite registry, typed previews and exact digest approval implemented in durable API/GUI lifecycle. |
| Role-difference matrix | Makes access-control failures understandable across designated test roles. | Owned vulnerable/fixed fixtures with independent denied controls and no real records. | Execution-neutral role/resource matrix implemented; real authentication/request runner remains unimplemented. |
| Knowledge provenance/freshness | Shows which dated source supports advice, including uncertainty. | Source revisions/licenses/conflict tests/evaluation/rollback. | Planned; no updater/training runs. |
| Comparable model budget view | Helps choose local/remote models using measured usefulness/resource usage. | Fixed eval cases plus labeled known/unknown usage/latency/memory. | Protocol usage and one real local-model compatibility case exist; quality/GPU/provider benchmarking remains unimplemented. |

## Knowledge updates are not model self-training

A first implementation should refresh approved documentation/advisory records into a retrieval index with source URLs, licenses, versions and dates. Retrieve relevant passages for an assessment; do not ingest the internet indiscriminately or let retrieved instructions control tools. Keep each customer's private evidence isolated from shared knowledge.

Embeddings/RAG and weight changes are different mechanisms. Fine-tuning or swapping a model/adapter requires a reviewed training source, held-out tests, deployment approval and rollback. The application must never rewrite executable code, permissions or model weights merely because it retrieved new material.

## Wider-review readiness

Use the measurable gates in ROADMAP.md. Favor a small reproducible release over a long feature list: vulnerable/fixed fixtures, honest failure paths, hard cancellation/deadline guarantees, crash recovery, reviewed adapter licensing, cross-platform install checks, real-model compatibility, accessible browser E2E, privacy review and independently reviewable sanitized reports. Upstream submission and maintainer acceptance remain separate events.
