# Five-minute recruiter walkthrough

Use actual implementation and [current limitations](docs/REVIEW_FINDINGS.md); planned phases are not shipped capabilities.

## 0:00–0:45 — Business problem

“A buyer wants suitable equipment within a budget. A merchant wants a profitable order. An operator needs understandable exceptions. AgentPay coordinates those constraints and exposes its decisions.”

Identify the portfolio/test environment.

## 0:45–1:45 — Purchase workflow

Choose monitor/keyboard. Show input constraints, quote lines, pricing, and policy reasoning. Explain model-assisted proposals versus deterministic authorization. Current coordinator is sequential; present LangGraph as the target until implemented.

## 1:45–2:45 — Exception review

Inspect a pending approval and approve/reject. Show separate approval and payment states. Use correctly configured provider test checkout only; explain placeholder rejection if unavailable.

## 2:45–3:45 — Investigation

Inspect audit payloads and chain verification. Explain tamper evidence limits. Run a scripted scenario and distinguish it from actual concurrency/failure testing.

## 3:45–4:30 — Architecture tradeoffs

Show architecture_overview.md. Discuss application transactions, reservations, checkpoints, idempotent effects, and provider reconciliation. Explain why one backend plus worker fits this scope.

## 4:30–5:00 — Evidence

Show checks, limitations, and measured reports when available. Include sample sizes/runtime. Describe one concrete failure and its fix.

## Resume wording

Current summary: “Built a FastAPI and Next.js commerce-orchestration prototype coordinating model-assisted catalog discovery, merchant pricing, policy approvals, and an auditable Razorpay test-checkout flow.”

After completing backend/evaluation phases, add durable resume, idempotent payment effects, and evaluation results. Use numbers from this project's saved reports; do not reuse the old orchestration project's metrics.
