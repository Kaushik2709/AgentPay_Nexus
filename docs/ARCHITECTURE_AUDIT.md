# Architecture implementation audit

Review date: **2026-10-09**. Scope: local tracked source, dependency manifests, route contracts, ORM models, current coordinator, checkout UI, existing tests, and comparison with the PRD/blueprint. This is a source review plus the checks below, not certification of a deployed payment system.

## Verdict

**The architecture is partially implemented and is not production-ready.** The local prototype has a coherent purchase-request path, deterministic buyer selection, merchant pricing, policy gates, SQL persistence, browser checkout integration, and a hash-linked audit log. Durable orchestration, secure authorization, payment correctness under duplicate/concurrent events, and reproducible deployment remain incomplete.

The target architecture in the PRD and blueprint must not be presented as already delivered. The accurate implementation specification is [PROJECT_SPECIFICATION.md](PROJECT_SPECIFICATION.md).

## Architecture coverage

| Requirement | Status | Evidence |
| --- | --- | --- |
| Next.js workspace and typed HTTP helpers | Implemented | `client/src/components/`, `client/src/lib/api.ts` |
| Catalog-grounded buyer intent and bounded selection | Implemented within bounded vocabulary | `purchase_intent.py`; isolated regressions pass |
| Merchant pricing strategies | Partial | Four strategy branches exist; final margin/consent/config enforcement gaps remain |
| Spending policy and human gates | Partial | Evaluation and approval records exist; approval bypasses revalidation |
| Persistent orders/approval/audit data | Implemented for local demo | Six SQLite ORM tables; no full workflow persistence |
| Provider order and checkout signature integration | Partial | SDK and HMAC exist; fallback and settlement correctness gaps |
| Atomic reservations and idempotent settlement | Missing | No reservation table/business idempotency constraints; per-line commits |
| Durable LangGraph with restart/resume | Missing | Sequential methods; no LangGraph dependency/checkpointer |
| Separate worker, durable jobs, event replay/SSE | Missing | Workflow runs inside HTTP request |
| Authenticated sessions and scoped access | Missing | Fixed identities; unauthenticated mutation routes |
| Protocol-conformant MCP service | Missing | REST and in-process catalog access only |
| Audit tamper evidence | Partial | Recomputed SHA-256 chain; genesis/concurrency/anchoring limits |
| Real subscriptions/mandates and fulfillment | Missing | Pricing flags only |
| PostgreSQL, Alembic, containers, CI | Missing in inspected repository | SQLite/create_all; no checked-in orchestration/CI configuration found |
| Reproducible evaluation and reliability reports | Partial | Narrow unittest suite and prior UI records; no load/restart/concurrency suite |

## Findings requiring implementation work

P0 means a blocker for exposing payment/mutation APIs publicly. P1 means a correctness or architecture gap. P2 means a presentation, reproducibility, or operational gap. Findings below are source-confirmed; failures have not all been dynamically reproduced.

| ID | Priority | Finding and concrete consequence | Source | Required behavior |
| --- | --- | --- | --- | --- |
| A01 | P0 | Server credential defaults and tracked server environment example contain credential values. Browser example also contained a public-prefixed secret variable. Environment examples were sanitized in this review; server defaults/history remain. | `server/app/config.py`, environment examples | Owner rotates exposed credentials; remove server defaults and verify tracked files/history. Never publish browser secrets. |
| A02 | P0 | Webhook signature check is conditional on header presence; missing signature is accepted. Event is only audited, not settled. | `api/razorpay_router.py:razorpay_webhook` | Reject missing/invalid signatures; deduplicate event IDs and converge capture on validated settlement. |
| A03 | P0 | Every repeated `settle_order` call decrements inventory again; provider payment IDs are not unique. | `razorpay/settlement_agent.py:settle_order`, `db/models.py:Order` | One guarded financial/stock effect per payment/order under callback and webhook replay. |
| A04 | P0 | Stock uses read/modify/write and commits each line independently. Settlement ignores a `False` result and can leave a paid order with missing stock or partial updates. | `catalog/catalog_service.py:reserve_and_decrement_stock`, `settle_order` | Atomic all-line stock/spend reservation with conditional updates and transactional settlement. |
| A05 | P0 | Mutation/approval routes lack identity and ownership checks; direct create-order accepts client-authoritative amount and bypasses coordinator policy. CORS permits all origins. | `api/`, `main.py`, `RazorpayCreateOrderRequest` | Authenticated, scoped commands; persisted authoritative quote; explicit frontend origins. |
| A06 | P0 | Valid HMAC leads directly to local `PAID` without verifying provider capture, expected amount/currency, or known order. Unknown order can still return successful payment verification. | `api/razorpay_router.py:verify_razorpay_payment` | Known owned order, guarded transition, provider state reconciliation, capture/amount/currency validation. |
| A07 | P1 | Provider exception is converted into a placeholder order and reported as created. Test-mode restriction exists in browser only. | `settlement_agent.py:create_order`, `RazorpayModal.tsx` | Explicit demo/test mode, fail closed on provider errors, reconcile ambiguous outcomes. |
| A08 | P1 | Approval commits before audit/provider creation. Crash or error strands an approved gate; concurrent decisions lack version/lock protection. | `supervisor.py:resume_hitl_workflow` | Durable decision/job transaction, guarded version, independently idempotent provider effect. |
| A09 | P1 | Resume does not check signature/expiry, stock, policy, or adjusted budget. All policy violations can be approved through the same path; Tier 3 has no additional verification. | `resume_hitl_workflow`, `policy_guard.py` | Reevaluate authorized quote revision and preserve hard constraints before side effects. |
| A10 | P1 | Strict buyer shield only checks the add-on flag; merchant quality upgrade can replace an exact requested SKU. `requested_skus` is not used to validate offered lines in the shield. | `buyer_agent.py:evaluate_upsell_shield`, `merchant_agent.py` | Validate final cart against intent/specs/SKUs and explicit upgrade permission. |
| A11 | P1 | Final margin is calculated but not universally enforced. Minimum discount can exceed available margin slack; subscription discount has no final floor rejection. Enabled strategy list is stored but not consulted by quote generation. | `merchant_agent.py`, `merchant_router.py` | Enforce enabled strategies and final whole-quote margin after every pricing branch. |
| A12 | P1 | No durable graph/run state, job queue, replay, or checkpoint. Fixed identities and pending-gate `workflow_id` mapped to quote ID prevent accurate durable correlation. | `supervisor.py`, `agent_router.py`, `db/models.py` | Persist workflow identity/state/events and resume the same run after restart. |
| A13 | P1 | Payment, approval, inventory, and audit writes commit independently. Synchronous SDK blocks async request handling. Float money is converted to paise only at provider boundary. | `settlement_agent.py`, `catalog_service.py`, `ledger.py`, models | Application-owned transactions, integer money, off-event-loop provider work. |
| A14 | P1 | Audit append reads latest head without serialization. Verifier omits genesis-parent and sequence-contiguity validation. Entire chain can be rewritten by DB writer. | `audit/ledger.py` | Serialize stream head, verify genesis/sequence/link/payload; describe tamper evidence accurately. |
| A15 | P2 | `COMPLETED_AUTONOMOUS`, `total_spent`, and checkout-confirmed audit action precede payment. Static health metadata claims protocols/mode that are not verified. | `supervisor.py`, `main.py` | Separate order-prepared and captured states; report actual configured mode/readiness. |
| A16 | P2 | Empty merchant dataset returns ₹23,500 average order value. Drift tolerance is stored but unused in evaluation. | `merchant_router.py`, `policy_guard.py` | Zero/unavailable metric when no paid orders; implement or explicitly mark unsupported settings. |
| A17 | P2 | Stock scenario is a boolean branch with asserted rollback text; it does not race two transactions or release an actual provider hold. Python requirements are lower bounds, not a lockfile; CI/deployment manifests absent. | `chaos_service.py`, `supervisor.py`, `requirements.txt` | Real failure/concurrency tests, pinned reproducible environment and automated checks. |

Quotes currently advertise **15-minute** expiry; the target PRD specifies **10 minutes**. Neither expiry duration is enforced by the current downstream approval/payment path.

## Checks executed in this review

| Check | Result | Interpretation |
| --- | --- | --- |
| `server/venv/Scripts/python.exe -m unittest discover -s tests -v` from `server/` | **14 tests passed** | Intent/parser/selection, request validation, budget propagation, policy-cap rule, and mocked approval-response contracts |
| `npm run lint` equivalent: local ESLint CLI from `client/` | **Passed** | Frontend static lint |
| `npx tsc --noEmit` equivalent: local TypeScript CLI | **Passed** | Frontend type checking |
| `npm run build` equivalent: local Next.js build CLI | **Passed** | Optimized frontend build; compiled and prerendered successfully |
| Initial `git status --short` | Clean | Existing checkout had no pending user edits |

The isolated tests use mocks/doubles and do not establish database transactions or provider behavior. Warnings observed: Starlette/httpx test-client deprecation and naive UTC datetime deprecation. Commands were run using the local executables directly without installing/upgrading dependencies.

Not exercised here: live/test provider payment completion, webhooks against Razorpay, database concurrency, duplicate settlement, process restart recovery, complete browser acceptance, performance, credentials rotation, deployment, or GitHub push. Prior screenshot/query evidence is linked from the README and remains dated to its original review.

## Publication and acceptance

The README/specification can present this as a local prototype with tested deterministic selection and typed integration boundaries. They must not claim LangGraph/MCP implementation, atomic rollback, exactly-once payments, immutable blockchain, real subscription mandates, or measured revenue/latency improvements.

Before a public service, close A01–A06 and add tests demonstrating unsigned/tampered event rejection, unknown-order rejection, duplicate callback/webhook convergence, amount/currency/capture validation, last-unit contention, all-line rollback, and unauthorized/cross-owner mutation rejection. Then implement recovery/checkpoints and verify restart during approval/provider submission without duplicate effects. Use the [blueprint](../PROJECT_BLUEPRINT.md) for the full phased acceptance criteria.

Sanitizing example files does not revoke credentials or remove earlier Git history. Runtime code was intentionally left unchanged by this documentation audit; the defects above remain implementation work.
