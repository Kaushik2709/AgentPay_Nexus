# AgentPay Nexus

A policy-controlled commerce prototype that turns a purchase request into catalog items, a merchant quote, human approval when required, and Razorpay test checkout—with a readable decision trail.

**Status:** local portfolio prototype; architecture partially implemented. Reviewed 2026-10-09. Frontend lint, type checking, production build, and all 14 isolated backend tests passed. Payment concurrency, idempotency, access control, and durable workflow recovery remain incomplete. See [the architecture audit](docs/ARCHITECTURE_AUDIT.md).

## Why this project exists

A buyer needs suitable products within a budget. A merchant wants profitable pricing. An operator needs to review exceptions and understand failures. AgentPay models these competing concerns in a single-merchant purchasing workflow, with computer equipment as the primary demonstration.

The engineering focus is separating product selection, pricing, policy, human decisions, checkout preparation, and payment verification. Local pricing savings and dashboard records are demo data; no real revenue, business uplift, or performance benchmark is claimed.

## What is implemented

- Five Next.js workspaces: buyer, merchant, policy/approvals, audit, and scenario lab.
- FastAPI and Pydantic APIs with SQLAlchemy and local SQLite persistence.
- Deterministic catalog-grounded intent parsing, exclusions, supported specs, one item per requested family, and conservative INR budget handling.
- Four merchant pricing strategies, tiered policy evaluation, and persisted human approval records.
- Razorpay order SDK integration, provider browser checkout, and server HMAC signature verification.
- SHA-256 hash-linked audit entries and a chain verification endpoint.

The coordinator uses sequential Python calls inside an HTTP request. LangGraph, durable checkpoints, a worker queue, event streaming, PostgreSQL, and a protocol-conformant MCP server are **planned**. Optional Hugging Face helpers exist but are not invoked by the current buyer request path. Order creation prepares checkout; it does not complete payment. The audit log offers limited tamper evidence, not blockchain immutability. Subscription strategies illustrate pricing; mandates and fulfillment are absent.

## Orchestration at a glance

~~~mermaid
flowchart TD
    UI[Next.js buyer workspace] --> API[FastAPI purchase request]
    API --> S[Sequential commerce supervisor]
    S --> B[Buyer intent and grounded selection]
    B --> C{Selection valid?}
    C -->|No| CL[Clarify or report unavailable inventory]
    C -->|Yes| M[Merchant quote]
    M --> SH[Buyer shield and optional quote revision]
    SH --> P[Policy evaluation]
    P --> G{Approval required?}
    G -->|Yes| H[Persist human gate and return]
    H --> D{Human decision via resume API}
    D -->|Reject| R[Persist rejection]
    D -->|Approve or adjust| O[Prepare payment order]
    G -->|No| O
    O --> A[Persist order and audit; return checkout payload]
    A --> RP[Razorpay test checkout]
    RP --> V[Server signature verification and local settlement]
    V --> DB[(SQLite orders, inventory and audit)]
~~~

This is a simplified normal-path diagram. The [full orchestration specification](docs/PROJECT_SPECIFICATION.md#current-orchestration) also shows clarification, scripted failure, placeholder-order rejection, and payment-error branches. Writes commit independently; the diagram does not establish atomic transactions.

## Documentation for reviewers

| Document | Purpose |
| --- | --- |
| [Implementation specification](docs/PROJECT_SPECIFICATION.md) | Stack, roles/screens, detailed orchestration, business rules, data model, API inventory, status semantics, and repository guide |
| [Architecture audit](docs/ARCHITECTURE_AUDIT.md) | Implementation coverage, prioritized source-confirmed gaps, executed checks, and acceptance criteria |
| [Architecture overview](architecture_overview.md) | Current topology and explicitly planned durable architecture |
| [Product requirements](PRD.md) | Target business scope and acceptance rules |
| [Six-phase blueprint](PROJECT_BLUEPRINT.md) | Ordered implementation roadmap |
| [Recruiter walkthrough](script.md) | Demonstration narrative |
| [Query regression review](docs/QUERY_TEST_REVIEW.md) | Earlier custom-query evidence and parser limits |
| [UI review](docs/UI_REVIEW.md) | Earlier browser verification record |

## Local setup

Run commands from the repository root initially. Use Python 3.11+ and a Node release satisfying the installed Next.js package requirements (Node 20.9+ minimum). Python dependencies currently use unpinned lower bounds; an installation may differ from the reviewed environment.

Backend, in one PowerShell terminal:

~~~powershell
cd server
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit server/.env with your own Razorpay TEST credentials before provider checkout.
uvicorn app.main:app --host 127.0.0.1 --port 8000
~~~

Frontend, in a second terminal from the repository root:

~~~powershell
cd client
npm ci
npm run dev
~~~

Open http://localhost:3000. Backend API documentation: http://127.0.0.1:8000/docs; health metadata: http://127.0.0.1:8000/api/health. Backend startup creates/seeds the local database. Run backend commands from server/ so the relative database path is consistent. Keep an existing .env rather than copying over it.

Optional client configuration in client/.env.local:

~~~dotenv
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api
~~~

Server settings in server/.env:

| Variable | Purpose |
| --- | --- |
| RAZORPAY_KEY_ID | Your provider test key ID |
| RAZORPAY_KEY_SECRET | Server-only provider secret |
| RAZORPAY_WEBHOOK_SECRET | Server-only webhook signing secret |
| DATABASE_URL | Async SQLite connection; default sqlite+aiosqlite:///./agentpay.db |
| SYNC_DATABASE_URL | Synchronous connection to the same database; default sqlite:///./agentpay.db |
| DEFAULT_MERCHANT_MARGIN_FLOOR | Fallback pricing floor setting; seeded merchant configuration also applies |
| DEFAULT_MAX_TX_AMOUNT, DEFAULT_DAILY_VELOCITY_CAP | Declared configuration defaults; the current seed uses hardcoded caps instead |
| PRICE_DRIFT_TOLERANCE_PCT | Stored setting; current policy evaluation does not enforce it |

No browser secret is required. Checkout receives the public key ID from the backend order response. Existing start.bat/start.sh are convenience launchers; the manual steps above make configuration explicit.

## Five-minute local demonstration

1. Open the buyer workspace and submit “Buy a 4K monitor and ergonomic keyboard under ₹25,000” with conversion_closer if selecting a strategy. Inspect selected products, quote, and returned trace.
2. Submit “Buy two keyboards” to demonstrate clarification before quote/payment side effects.
3. Lower the request budget to ₹15,000 for the monitor/keyboard request. Inspect the policy gate and reject it from the approval view.
4. Inspect merchant inventory and the audit chain verification result.
5. With your own server test credentials configured, prepare a new eligible purchase and open provider test checkout. Provider completion was not exercised in this audit.

Scenario lab requests illustrate branches. They do not prove concurrent stock reservation or financial rollback. Historical approvals/orders remain in the local database and can affect daily-spend gates.

## Checks

From client/:

~~~powershell
npm run lint
npx tsc --noEmit
npm run build
~~~

From server/:

~~~powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
~~~

The 14 isolated backend tests cover buyer intent, request validation, budget propagation, policy-cap enforcement, and mocked approval responses. They do not test provider settlement or transaction concurrency. The older server/test_backend.py uses configured integration resources; it is not an isolated CI suite. See [the dated audit](docs/ARCHITECTURE_AUDIT.md#checks-executed-in-this-review) for results and limits.

## Known limitations and publishing readiness

The architecture is not perfectly implemented. Current blockers include server credential defaults, unsigned-webhook acceptance, repeatable settlement effects, non-atomic inventory updates, missing authentication/ownership, client-authoritative direct order amounts, and incomplete capture validation. Approval does not revalidate quote expiry or policy. Provider errors can generate placeholder orders; the browser rejects these, but the backend still persists them. Keep the current service local until these gaps are fixed.

Environment examples were sanitized during this review. Previously exposed credentials still require owner rotation and history cleanup before publication; deleting values from an example does not revoke them. Runtime credential defaults remain in server/app/config.py. Do not publish secrets, local .env files, or runtime databases. The root .gitignore excludes these runtime files, but ignores do not remove tracked content or earlier history.

The [audit](docs/ARCHITECTURE_AUDIT.md) records the findings; the [blueprint](PROJECT_BLUEPRINT.md) defines the remediation plan. This review made documentation/example changes only and did not push to GitHub, deploy a service, rotate credentials, or submit a payment.
