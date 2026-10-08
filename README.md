# AgentPay Nexus

A business-focused AI engineering portfolio: turn a purchase request into a merchant quote, enforce spending policy, route exceptions to a human, and prepare an auditable test checkout.

**Status:** working prototype undergoing an architecture refactor. This is a recruiter demonstration, not a live payment service.

## Business problem

Buyers want suitable items within a budget. Merchants want profitable sales. Operators need to understand approvals, exceptions, and failures. The primary demo is computer-equipment purchasing from a single merchant.

## Current capabilities

- Next.js 16, React 19, TypeScript workspace: buyer, merchant, policy, audit, and scenario views.
- FastAPI, SQLAlchemy, local SQLite, and a sequential Python commerce coordinator.
- Catalog-grounded intent validation and bounded product selection. One requested product per family, explicit exclusions, conservative INR budgets, and clarification before unsafe or unsupported purchases. Hugging Face helper functions remain experimental; model output no longer authorizes cart contents.
- Merchant pricing strategies, policy checks, persistent approval records, and hash-linked audit entries.
- Razorpay order and signature-verification integration. The UI uses provider test checkout rather than fabricating signatures.

The backend does **not** currently instantiate a LangGraph graph or checkpointer. Functions named “MCP” are in-process catalog/database calls, not an MCP server. Traces arrive when a request completes. Creating an order is not completing payment. Hash chaining is tamper evidence, not an immutable blockchain. Subscription pricing is illustrative; recurring mandates and fulfillment are absent.

## Architecture and review

Read [the architecture](architecture_overview.md), [six-phase roadmap](PROJECT_BLUEPRINT.md), [business requirements](PRD.md), [review findings](docs/REVIEW_FINDINGS.md), and [UI verification record](docs/UI_REVIEW.md). Use [the recruiter walkthrough](script.md) to demonstrate actual capabilities.

## Local setup

Use Python 3.11+ and a Node version supported by installed Next.js (Node 20.9+ minimum).

Backend:
```powershell
cd server
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend in a second terminal:
```powershell
cd client
npm ci
npm run dev
```

Open http://localhost:3000; API docs: http://127.0.0.1:8000/docs. Startup seeds a local database. First model use may download weights. Python requirements are not yet pinned for reproducibility.

Frontend API base defaults to http://127.0.0.1:8000/api, configurable with `NEXT_PUBLIC_API_URL`. Payment secrets belong on the server; never use a `NEXT_PUBLIC_*` secret. The browser only receives the public test key ID.

## Payment limitations

Do not expose the current backend publicly. The review found hardcoded server credential defaults, unsigned-webhook acceptance, non-idempotent settlement, unauthenticated mutation endpoints, and non-atomic inventory handling. Phase 1 addresses these.

Any credentials previously committed or bundled for browsers must be rotated by their owner. Removing source references does not revoke credentials.

The backend can silently generate a placeholder order after provider failure. The updated UI rejects placeholders and live keys. Real provider test orders require valid server-side test credentials. Provider payment completion was not exercised during this review.

## Checks

From `client/`: `npm run lint`, `npx tsc --noEmit`, `npm run build`.

From `server/`: `venv\Scripts\python.exe -m unittest discover -s tests -v` runs isolated approval-response checks. The older `test_backend.py` uses configured database/model/provider integrations and is not an isolated CI suite.

Publish reproducible evaluation reports before claiming latency, reliability, or revenue improvements on the resume.
