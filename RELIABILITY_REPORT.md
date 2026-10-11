# AgentPay Nexus reliability report

Verified October 11, 2026. Scope: existing single-merchant commerce prototype; deterministic purchase intent and Razorpay test checkout. No real or sandbox financial transactions were initiated during this work. Provider interactions in all new tests and benchmarks used mocks. Existing credentials, environment files, and configured commerce/auth data were not replaced.

## Results

| Check | Verified outcome |
| --- | --- |
| Baseline backend suite | 37/37 passed before changes |
| Final backend suite | **111/111 executions passed in 23.484 seconds**, no skips with PostgreSQL configured |
| SQLite/local tests | 70 executions, including API/auth/parser contracts, migration checks, and independent-process contention |
| Actual PostgreSQL | 41 executions against disposable PostgreSQL **17.11**, including 36 repeated commerce contracts, 3 process-contention cases, and 2 migration cases |
| Fixed intent dataset | 12/12 deterministic expected outputs; no LLM comparison performed |
| Frontend authentication | 1 integration test passed: registration, revocation, ownership/session identity, and TOTP |
| Frontend lint/build | ESLint and Next.js production build passed |
| CI | Added backend SQLite/PostgreSQL/security checks, parser regression, frontend tests/lint/build; hosted GitHub Actions run has not been observed |

The count includes shared commerce contracts exercised on both databases, not 111 unique business scenarios. Local runtime: Windows 11, Python 3.14.3, SQLAlchemy 2.0.52, SQLite 3.50.4, psycopg 3.3.6, Node/Next dependencies from the existing lockfile. PostgreSQL ran in a disposable Docker Desktop container bound to localhost. Tests create temporary SQLite files and unique PostgreSQL schemas, not tables in the configured application database.

## Phase 1 audit: safeguards already present

| Area | Existing correct behavior | Remaining issue found and disposition |
| --- | --- | --- |
| Authentication/roles | Better Auth session proxy signs method, path/query, identity, role, strong-auth flag, timestamp, and body digest; backend rejects invalid/stale signatures and restricts merchant/admin routes | Retained; added authenticated cross-user payment-verification assertion before any provider fetch |
| Ownership | User-scoped policies, approvals, orders; client-supplied buyer IDs do not grant ownership | Retained; persisted quote and approval ownership/state checked again |
| Intent and budgets | Catalog-grounded selection; exclusions, specifications, quantities, and minimum text/request budget prevent unrelated purchases | Retained deterministic parser; added fixed offline regression dataset |
| Policy/human gates | Transaction cap, rolling spend, category/upsell checks, high-value strong authentication, approval re-evaluation | Same violation code could hide a changed cap; category failures could be approved; fixed with complete snapshots and non-overridable category checks |
| Quotes | Server-owned quotes and stored amount/expiry; invalid amount or unapproved quote cannot create checkout | Added HMAC/content/line-total validation and final policy recheck; new quotes now match PRD's ten-minute lifetime |
| Reservations | Conditional stock decrements with one order per quote | Multi-line expiry released only the first line; fixed. Savepoint now rolls back partial carts even if caller later commits |
| Idempotency | Persisted workflow request hash/result; conflicting key reuse rejected; checkout reuses a quote's order | Retained and tested across actual processes; requests without a key remain independent purchases |
| Capture/settlement | Checkout HMAC plus authenticated provider fetch; raw-body webhook HMAC; matching captured order/payment/amount/currency; payment uniqueness | Settlement previously derived amount from mutable quote or float fallback; added canonical order paise and first-verification timestamp |
| Duplicate events | Shared settlement path and payment-ID uniqueness prevent repeated effects | Strengthened event-ID conflicts and complete-reservation checks; tested API/async/process replays |
| Provider uncertainty | Order/reservation committed before network submission; failures retain a reconciliation state | Unknown provider order ID previously stranded recovery; added exact receipt-based lookup without resubmission, cancellation handling, and bounded SDK transport waits |
| Late capture | Released stock produces `PAID_REQUIRES_REVIEW`, not automatic fulfillment | Retained; late capture now counts in the current rolling-spend window, and review payments also count |
| Database/audit | SQLite serialized tested writes; audit and settlement effects commit together | Writer acquisition after read autobegin was incomplete; global database writer mutex now covers guarded commerce writes and audit appends across processes |
| PostgreSQL | SQLAlchemy models were broadly portable but unverified | Added optional driver/migrations and real transaction/process tests; discovered and fixed PostgreSQL-only approval-reason length failure |

The historical `server/test_backend.py` smoke script used the configured provider/database. It now delegates to the isolated regression suite. Browser/sandbox success described in the previous README is historical evidence, not a payment repeated in this audit.

## Transaction boundaries and business rules

1. Persist a workflow idempotency claim. The sequential supervisor parses, prices, and evaluates a server-owned quote.
2. Under the database writer lock, recheck owner, expiry, quote state/signature/content, and policy. Human approval additionally compares the exact policy snapshot, current stock, price drift, and required strong authentication.
3. In the same local transaction, reserve the full cart, consume the quote, persist the provider receipt and `CREATING` order, and commit. Human approval and its audit event join this claim transaction.
4. Submit provider order creation outside the transaction, with bounded connection/read waits and SDK retries disabled. Bind a validated response in a fresh transaction. Timeout/cancellation becomes `RECONCILIATION_REQUIRED`; a crash or database failure can leave recoverable `CREATING`.
5. Reconciliation searches by persisted receipt and validates exact receipt, quote note, integer amount, and INR currency. It attaches only one exact match; no creation resubmission occurs.
6. Owned checkout verification, signed webhook, or authenticated reconciliation supplies capture evidence. Under the writer lock, verify IDs, canonical order paise, currency, and captured status; deduplicate payment/event IDs; consume complete expected holds; append the audit event; commit once.

The existing soft transaction-cap, daily-spend, and unsolicited-upsell exceptions retain explicit human-override semantics when the policy inputs and observed spend are unchanged. Category policy and signature integrity cannot be overridden. High-value approval still requires strong authentication. Automatic checkout cannot exceed its current policy or rolling-spend capacity. Existing pending approvals without a complete snapshot require a fresh decision. No LLM participates in these boundaries.

Money calculations use integer paise for line totals, prices during pricing, policy comparisons, reservations of spend capacity, and settlement; percentage arithmetic uses Decimal and explicit rounding. Canonical quote/order/payment-event amounts are persisted as integer paise. Legacy catalog, policy, reporting, and INR API float fields remain for compatibility and are converted at the boundary; this is not a full historical column conversion.

## Tested failure and concurrency scenarios

| Scenario | Evidence and result |
| --- | --- |
| Last inventory unit | Async and four separate process attempts on SQLite/PostgreSQL; exactly one provider submission, order, and reservation; stock stays zero |
| Same checkout repeated | One order/hold/provider submission; concurrent in-flight retries may receive 409 and later reuse checkout |
| Same workflow key | Replays stored result or stored failure; changed body rejected; concurrent claim executes workflow once |
| Duplicate settlement | Async and four-process captures produce one payment event/audit effect; no second stock decrement |
| Partial cart failure | Savepoint restores earlier decrements and creates no holds, even when caller catches failure and commits |
| Expired multi-item cart | All held lines released atomically, once; repeat sweeps do not inflate stock |
| Expired/conflicting approvals | Expired/consumed quotes cannot prepare checkout; category violations and changed policy snapshots stay closed |
| Forged/stale identity and ownership | Invalid/stale signatures, role violations, cross-user quote/approval/order/payment access rejected |
| Quote tampering/stale signing key | Modified signature or line price cannot reach provider creation |
| Invalid/unverified payment | Bad checkout HMAC, signed wrong-amount webhook, unsigned/forged webhook, uncaptured payment, wrong currency/order/amount, unknown order, and fetch timeout leave checkout unpaid |
| Replayed/conflicting payment event | Duplicate delivery produces no repeated effects; reuse of recorded event ID for another order rejected |
| Provider order timeout | Receipt recovery discovers existing order, then captured payment; repeated sweeps do not create another order |
| Crash/response persistence failure | Durable `CREATING` attempt recovered by receipt; existing checkout reused |
| Provider lookup uncertain | Zero/multiple/conflicting matches retain reconciliation state, stock, and spend capacity, even beyond 24 hours |
| Provider call versus local writers | Independent transaction completes while provider submission is blocked; no writer lock spans the network call |
| Recovery/capture versus slow creation response | Verified paid state survives the original response arriving later |
| Cancelled submission | Durable uncertain state retained; background SDK thread may finish, but creation is not resubmitted |
| Late capture | Released/missing reservation enters review; capture of an old order counts as current spend; replay preserves first capture-verification time |
| Audit writes/genesis | Concurrent appends preserve the chain; altered genesis link is rejected even if its entry hash is recomputed |
| Schema migration | Fresh and representative legacy schemas migrate repeatably on both databases; old amount retained and paise backfilled |

Suite organization: `test_purchase_intent.py` and `test_approval_contract.py` cover pure/parser/API contract cases; `test_api_endpoints.py` covers authenticated HTTP integration; `test_reliability.py` covers file-backed database/provider doubles; `test_process_contention.py` uses independent processes; `test_postgresql.py` repeats the commerce contract on real PostgreSQL; migration/configuration tests cover deployment invariants. Provider entities injected by tests are explicit test doubles, not actual sandbox evidence.

## Controlled benchmark

Raw results and assertions: [local benchmark JSON](docs/benchmarks/local-2026-10-11.json). Reproduction: `python -m benchmarks.local_reliability --output ../docs/benchmarks/local.json` from `server/`; set `TEST_POSTGRES_URL` to add actual PostgreSQL process measurements.

| Local scenario | Samples | Median | p95 | Maximum |
| --- | ---: | ---: | ---: | ---: |
| New checkout, sequential, SQLite | 50 | 36.969 ms | 44.899 ms | 172.695 ms |
| Idempotent workflow replay, SQLite | 100 | 3.247 ms | 4.813 ms | 8.694 ms |
| New checkout, eight concurrent requests, SQLite | 32 | 55.268 ms | 1,497.258 ms | 1,607.168 ms |
| Four-process last unit, SQLite | 4 | 59.332 ms | 103.756 ms | 103.756 ms |
| Four-process last unit, PostgreSQL | 4 | 114.168 ms | 150.505 ms | 150.505 ms |

API timing uses signed HTTP requests through httpx's in-process ASGI transport and SQLite on local disk, after one warm-up. It includes parsing, quote/policy work, database transactions, and immediate mocked provider responses; it excludes browser, TCP/TLS, and real Razorpay latency. The eight-request limit excludes time waiting outside the semaphore. Process timing starts after a barrier, includes connection establishment, and excludes interpreter/process startup; four samples do not establish meaningful tail-latency estimates.

The API run created 83 unpaid orders with 83 mocked provider submissions, leaving 17 of 100 units and **zero payment events**. Each independent-process last-unit run left one reservation/order and zero stock. The eight-request p95 documents significant lock contention; no production throughput, improvement percentage, or scale claim follows from these single-machine measurements.

## Known limitations and deployment requirements

- Hosted CI has been configured but not run remotely in this work. Frontend build passed locally; fresh browser walkthroughs and provider-to-localhost webhook delivery were not performed.
- Actual Razorpay receipt lookup, capture configuration, delivery retries, and secret rotation still need controlled **test-mode** verification. Automated tests use provider doubles, so actual sandbox behavior is not inferred from them.
- Global write serialization limits throughput, including PostgreSQL. Independent-process contention tests do not prove multi-host behavior, network-partition recovery, or production availability.
- There is no durable general workflow engine, queue, automatic resume for pre-order `RUNNING` workflows, or outbox. Failed workflow responses do not automatically become successful after order recovery; order history exposes recovered checkout.
- Unknown creation attempts retain stock/spend indefinitely if receipt lookup remains absent/ambiguous. Operator-confirmed resolution is required; automatic cancellation/refund tooling is not implemented.
- Known-order holds can expire after a failed provider lookup. Later capture is explicit review, not fulfillment. Refunds, fulfillment, multiple captured-payment remediation, and live-money operations are outside scope.
- Legacy INR columns remain floats; migrated SQLite tables are not rebuilt to retrofit every new check constraint. Direct database writers must respect application invariants.
- Better Auth remains SQLite-backed. Provisioning and migrations must run once with workers stopped; concurrent empty-database seed startup is not verified.
- Audit hashes provide local tamper evidence, not externally anchored immutability or non-repudiation. Demo merchant signing secrets must be replaced for hosting.
- Dependency warnings remain for naive UTC timestamps and the Starlette/httpx test bridge; tests pass, but a later dependency/timezone migration should address them separately.

See [deployment and recovery procedures](docs/DEPLOYMENT_AND_RECOVERY.md), [actual architecture](architecture_overview.md), and [separate intent-model evaluation boundary](docs/INTENT_PARSER_EVALUATION.md).

## Resume bullets supported by this work

- Hardened a FastAPI/SQLAlchemy commerce prototype with atomic cart reservations, idempotent order creation, verified-capture settlement, and receipt-based recovery for uncertain Razorpay test-order outcomes.
- Added a 111-execution regression suite across SQLite and real PostgreSQL, including independent four-process tests for last-unit contention, duplicate checkout, and duplicate settlement.
- Implemented policy-snapshot approval revalidation, canonical integer-paise settlement/spend accounting, additive database migrations, and CI checks for payment/security invariants and frontend build.
- Measured local mocked checkout and replay latency with reproducible benchmarks; documented contention costs, recovery states, and test-mode limitations without production-scale claims.
