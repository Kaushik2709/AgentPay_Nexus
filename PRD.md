# AgentPay Nexus product requirements

Updated 2026-10-08. This specifies the portfolio target; delivery status belongs in [the blueprint](PROJECT_BLUEPRINT.md).

## Purpose

Demonstrate business modeling, AI/backend architecture, reliable transaction workflows, and a usable operator interface to recruiters. This is a candidate portfolio project, not the owner's commercial business.

Scenario: controlled computer-equipment purchasing for a single merchant.

| Role | Business need | Evidence |
| --- | --- | --- |
| Buyer | Suitable requested items within a budget | Correct item/quantity selection, clarification for ambiguity |
| Merchant | Profitable pricing | Quote costs, discounts, and enforced margin floor |
| Approver | Understand exceptions | Decisions bound to a quote and durable across restart |
| Operator | Investigate and recover failures | Connected workflow, approval, stock, and payment timeline |
| Recruiter | Assess engineering quickly | Repeatable demo, tests, tradeoffs, measured results |

## Purchase journey

1. Start an isolated demo session; enter a goal or choose a scenario.
2. Parse requested lines, quantities, exclusions, budget, and upgrade permission.
3. Retrieve candidates and select a bounded cart; retrieval candidates are not automatically purchases.
4. Generate a quote, then check intent, margin, stock, spending policy, signature, and expiry.
5. Reject, clarify, request human approval, or reserve stock and prepare a payment order.
6. Complete explicitly labeled test checkout. Only verified captured payment completes the purchase.
7. Inspect the durable event timeline and any recovery-required outcome.

## Rules

- Models propose; deterministic services authorize money and inventory effects.
- Effective budget is the lower of the slider and an explicit prompt budget. A human adjustment creates a new authorized revision.
- Category/signature violations cannot be overridden by soft-budget approval.
- INR amounts use integer paise. Quotes derive prices and costs from the server catalog.
- Quotes expire after 10 minutes. Changed/expired quotes require a new decision.
- Reserve all stock and rolling-spend capacity atomically before order creation.
- Approval, order creation, authorization, capture, and recovery are separate states.
- Explicit modes are `demo` and `razorpay_test`; live money is outside this release.

## Business model and scope

The modeled product is a merchant-facing commerce control layer; managed workflows and operational/audit tooling are a possible commercial offering. Pricing and conversion improvement are hypotheses. No customers, real revenue, validated ROI, or product-market fit are claimed.

Initial scope: one merchant, isolated buyer sessions, buyer/operator/viewer permissions, computer equipment. Multi-merchant routing, real subscriptions, mandate lifecycle, fulfillment, automated refunds, cross-border payments, and external audit anchoring are deferred.

## Measures and acceptance

Measure requested-line coverage, irrelevant-item rate, policy violations, below-floor quotes, repeated payment effects, negative stock, restart/resume, stage latency, approval rate, and provider-recovery backlog.

Business metrics derive from captured demo orders. Compare fixed-price and strategy variants on identical scenarios and label results synthetic. Simulated orders do not establish real conversion uplift.

Acceptance requires reproducible evals, zero forbidden actions in the tested invariant cases, successful duplicate/concurrency/restart tests, and all five UI views verified at 360/768/1440 px with keyboard use, errors, empty states, long content, and preserved drafts.
