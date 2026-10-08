# AgentPay Nexus refurbishment plan

Updated 2026-10-08. Target: a recruiter-ready AI/backend portfolio with a clear business scenario and reproducible engineering evidence.

## Summary and defaults

Refurbish in **six phases**. Keep Next.js, FastAPI, Python, and a single repository. Evolve to PostgreSQL, LangGraph, and a separate worker inside one backend codebase. Demonstrate controlled computer-equipment purchasing for one merchant with isolated demo sessions. Support explicit demo and Razorpay test modes.

The UI repair and documentation review are underway. The durable backend below is **planned, not implemented**. Visual browser acceptance remains pending.

## Phase 1 — Domain and payment correctness

- Remove hardcoded credential defaults and require server-only test configuration. Owner rotates previously exposed credentials separately. Add secret scanning, explicit mode reporting, and no silent fake fallback.
- Add authenticated session identity, buyer/operator/viewer permissions, ownership checks, rate limits, validation, and explicit CORS before public deployment.
- Introduce typed money/quote/policy/order domain models, integer paise, persisted authoritative quotes, signature/expiry checks, guarded state transitions, and application-owned transactions.
- Use PostgreSQL and Alembic. Seed a new demo database; preserve/export the local SQLite file instead of treating its unverifiable paid history as production data.
- Reserve stock and rolling-spend capacity atomically. Guard approval decisions and payment attempts by business idempotency keys.
- Require signed webhook deliveries, persist/deduplicate event IDs, and converge callbacks/webhooks on one settlement service. Unknown provider outcomes enter reconciliation.
- Record order preparation separately from captured payment.

**Exit:** unsigned/tampered events fail; two buyers cannot reserve the last unit; repeated approval/payment has one effect; timeout never creates fictitious success.

## Phase 2 — Durable orchestration

- Build a real typed LangGraph: intent, retrieval, cart selection, merchant proposal, buyer review, policy, human interrupt, reservation, payment-order creation, and payment wait.
- Persist checkpoints by workflow/thread ID, plus ordered workflow events and durable jobs.
- Run API and worker separately. Claim PostgreSQL jobs with leases, attempt counts, and bounded retries; do not hold DB transactions across provider/model calls.
- Retry transient read/model operations up to three attempts with backoff. Never automatically repeat an ambiguous payment submission. Guard each side effect independently of graph checkpoints.
- Approval/rejection/revision resumes the same run; expected-version checks reject competing decisions. Persist clarification, expiry, failure, and recovery states.
- Add versioned workflow APIs and SSE replay/reconnect; use persisted-status polling as fallback.

**Exit:** restart during approval/provider submission preserves the run without duplicate effects; reconnect resumes the event cursor.

## Phase 3 — Business-relevant AI and evaluation

- Parse Pydantic-validated requested lines, quantities, specs, exclusions, budget, and upgrade permission. Use the lower prompt/slider budget and clarify ambiguity.
- Separate retrieval from selection: choose one suitable product per requested line unless requested quantity differs; check whole-cart budget.
- Retain a local model adapter and add an explicit scripted adapter for deterministic demos/tests. Report mode. Hosted models are optional behind the same interface.
- Cache embeddings by catalog version. Move blocking inference/SDK work off the API event loop.
- Use a typed, per-node tool allowlist. Treat model/catalog content as untrusted; agents cannot mutate money or waive policy.
- Create at least 60 labeled eval cases covering multi-item requests, irrelevant candidates, exclusions, budget disagreement, malformed model output, and injected product text.
- Compare with a deterministic baseline; report actual intent coverage, irrelevant-item rate, policy violations, latency, and cost.

**Exit:** malformed plans cannot create orders; policy invariants pass; versioned reports show measured results without invented uplift.

## Phase 4 — Operator UX and browser acceptance

- Finish the repaired light workspace with responsive layout, readable controls, preserved drafts, and state-specific feedback.
- Bind statuses to persisted workflow/payment state; handle expiry, approval conflicts, duplicate clicks, reconnect, and recovery guidance.
- Add workflow detail routes and an approval inbox; keep technical payloads in disclosure views.
- Use captured-order metrics; show unknown data as unavailable and empty datasets as empty/zero.
- Browser-test all five views at 360/768/1440 px using empty, slow, disconnected, failed, and successful fixtures. Check long content, keyboard, dialogs, 200% zoom, contrast, reduced motion, and screenshots.

**Exit:** no horizontal document overflow, unsaved-draft reset, false success, or inaccessible critical controls. This exit remains pending.

## Phase 5 — Reliability and observability evidence

- Add isolated pytest suites, Postgres fixtures, provider doubles, concurrency/restart tests, and deterministic fault injection.
- Add structured logs/OpenTelemetry spans with workflow/node/provider IDs, stage latency, retries, policy outcomes, and model/token cost when available. Redact secrets.
- CI checks lint/type/build, backend tests, migrations, secrets, and deterministic evals. Live-model evaluation is an explicit budgeted job.
- Turn scenario lab into replay of actual fault-test outcomes: competing reservation, stale approval, duplicate/out-of-order webhook, timeout, audit corruption, worker restart.
- Implement a small read-only MCP catalog adapter only after correctness, with protocol conformance tests. Until then describe catalog as REST/JSON-LD.

**Exit:** reports include sample size, runtime/hardware, p50/p95, invariant results, and limits. Demonstrate effectively-once business effects under at-least-once delivery; do not claim exactly-once delivery.

## Phase 6 — Portfolio packaging

- Docker Compose: frontend, API, worker, PostgreSQL; migrations/seed, liveness/readiness, pinned dependencies.
- Default hosted recruiter sessions to isolated, expiring scripted demos; never require personal payment data.
- Provide one-command demo setup and a five-minute purchase/approval/failure/trace walkthrough.
- Publish screenshots, architecture decisions, tests/evals, and a business/engineering scorecard.
- Write resume bullets linked to implemented capabilities and reports. Defer live billing, multi-merchant scale, mandates, automated refunds, and external immutable anchoring.

**Exit:** another engineer reproduces the demo from README; every claim has evidence.

## Interfaces, migration, and folders

POST /api/v1/workflows returns 202 and workflow ID, requires an idempotency key. GET workflow and SSE event endpoints expose durable progress; decisions carry typed action/expected version. Generate frontend types from versioned OpenAPI. Keep old /api endpoints until client migration.

Extract domain behavior before moving files. Introduce PostgreSQL before relying on concurrency guarantees; gate new orchestration until parity tests pass. Use additive migrations and compatible rollback versions; never destructively downgrade financial records.

Keep client/ and server/. Backend ownership becomes api/application/domain/orchestration/infrastructure; frontend becomes buyer/merchant/approvals/audit/scenarios features. Move behavior, tests, imports, and docs together. Refresh graphify output after each phase; generated graph data is evidence, not hand-maintained architecture.

## Required tests

| Area | Cases |
| --- | --- |
| Intent/cart | Multi-line, quantities, missing specs, unavailable catalog, budget conflicts, invalid model output |
| Pricing/policy | Margin floor, upsell consent, disallowed category, exact cap, rolling limit, concurrent spend |
| Approval | Approve/reject, repeated request, competing decisions, expiry, adjusted budget, restart |
| Payment/stock | Duplicate callback/webhook, missing/bad signature, unknown order, amount/currency mismatch, last-unit race, timeout after provider success |
| Recovery/audit | Job retry, late capture, out-of-order event, concurrent append, genesis/link/payload tamper |
| UI | Outage, empty/search-none, verification false, saving, draft preservation, long content, dialog focus/Escape, reconnect |
