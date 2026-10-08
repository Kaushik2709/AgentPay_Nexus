# Architecture review evidence

Historical review from 2026-10-08. For current source-confirmed status and executed checks, see [the 2026-10-09 architecture audit](ARCHITECTURE_AUDIT.md). In particular, the candidate-set and budget-propagation findings below were subsequently addressed by the deterministic intent path; final quote validation still has gaps.

Reviewed 2026-10-08 against the local AgentPay_Nexus checkout. The resume was read locally to position this project; its claims were not independently verified.

## Portfolio story

Existing resume projects cover retrieval quality, model guardrails, and computer use. AgentPay adds business transactions: buyer/merchant incentives, authorization, durable state, and failure recovery.

Suggested title after the backend phases ship: **AgentPay Nexus — Policy-Controlled Agentic Commerce & Durable Payment Workflows**. Do not copy reliability/latency metrics from the old orchestration project.

## Findings

| Priority | Finding | Evidence and consequence |
| --- | --- | --- |
| P0 | Browser secret/signature fabrication | Previous RazorpayModal generated payment IDs/signatures. Removed from UI; owner rotation and server-default cleanup remain. |
| P0 | Unsigned webhook accepted | razorpay_router validates only inside an if-signature branch. |
| P0 | Duplicate settlement | settle_order unconditionally marks paid and decrements inventory again. |
| P0 | Non-atomic stock mutation | CatalogService reads then decrements/commits; settlement ignores the failure boolean. |
| P0 | Missing authorization boundary | Mutation endpoints lack identity/ownership; create-order trusts client amount. |
| P1 | LangGraph claim unsupported | Supervisor is sequential method calls; LangGraph is absent from requirements. |
| P1 | Approval can strand state | Approval commits before provider creation, without durable recovery. |
| P1 | Approval response lost checkout | Router discarded returned order; optional order field added in this repair. |
| P1 | Candidate set becomes cart | All similarity matches are passed as requested SKUs. |
| P1 | Budget mismatch | Discovery uses parsed budget, later quote/policy uses slider budget. |
| P1 | Blocking inference/SDK calls | Synchronous work happens within async HTTP workflow. |
| P1 | Audit append races | Latest sequence is read then independently committed. |
| P1 | Audit claims overstated | No external anchoring/immutability; incomplete genesis-parent check. |
| P2 | UI contract mismatch | Merchant fields nested under metrics were read at top level. Fixed. |
| P2 | False success displays | Audit always green, order creation treated settled, chaos asserted guarantees. Fixed displays. |
| P2 | Integration-only test script | Configured DB seeded/mutated; provider/model paths not isolated. |

## Relational graph

graphify-out/graph.json contains 321 nodes and 699 edges. The report is dated 2026-09-03 and mixes extracted/inferred connections, so current source is authoritative.

Most-connected business nodes in the report: CommerceSupervisorAgent (25 edges), CatalogService (23), Product (21), RazorpaySettlementAgent (21), MerchantGrowthAgent (18), AuditLedgerEngine (17). These identify coupled responsibilities, not required microservices.

Verified source paths connect buyer discovery to catalog, supervisor to buyer/merchant/policy/payment services, and settlement to inventory mutation. The refactor assigns transaction ownership to application services and isolates provider effects. No import cycles were detected by the report.

## Capability labels

| Old label | Accurate current description |
| --- | --- |
| LangGraph StateGraph | Sequential coordinator; graph migration planned |
| MCP catalog | In-process access and REST/JSON-LD |
| Autonomous settlement | Policy-approved order preparation; payment separate |
| Immutable blockchain | Database hash chain |
| Stock-race proof | Scripted branch, not concurrent transaction test |
| Subscription/UPI Autopay | Illustrative pricing; mandates absent |
| Revenue growth | Pricing strategies; real uplift unmeasured |

Complete Phase 1 before public deployment. UI corrections do not harden backend financial state. No credentials were rotated, provider settings changed, payment submitted, repo pushed, or service deployed in this review.
