# Product Requirements Document (PRD)

## Project: AgentPay Nexus — Autonomous Agentic Commerce & Settlement Engine
**Challenge**: Razorpay Buildathon 2026 — Track 01: AI Growth & Agentic Commerce  
**Tagline**: *Grow the merchant’s revenue, and make them sellable to AI buyers with bounded, gated, and explainable money actions.*  
**Version**: 1.1.0  
**Status**: Approved for Implementation  

---

## 1. Executive Summary & Problem Definition

### 1.1 The Market Shift
E-commerce is transitioning from manual human browsing (scrolling catalogs, filling forms, approving every OTP) to **Autonomous Agent-to-Merchant (A2M) and Agent-to-Agent (A2A) Commerce**. Enabled by protocols like **NPCI's UAP (Unified Autonomous Payments)**, **ACP (Agentic Commerce Protocol)**, and **x402 (HTTP 402 AI micropayments)**, consumer and enterprise AI agents are now making autonomous purchasing decisions.

### 1.2 The Core Problem
1. **Merchants are Invisible to AI Buyers**: Legacy e-commerce websites are built with HTML/CSS meant for human eyes, making them difficult and error-prone for AI agents to query without scraping.
2. **Merchants Leave Revenue on the Table**: Static pricing and dumb ad banners cannot dynamically negotiate with buyer agents to maximize cart value or prevent bounce.
3. **The "Blank Cheque" Fear & The "HITL Fatigue" Trap**: 
   - Giving AI unlimited financial autonomy leads to accidental overspending or hallucinated purchases.
   - Conversely, forcing **Simple HITL (Human-in-the-Loop for every single step)** defeats the entire purpose of autonomous AI agents.

### 1.3 The Solution: AgentPay Nexus
An end-to-end platform bridging **Autonomous AI Buyers** and **AI-Driven Merchants** over **Razorpay Test-Mode APIs**, powered by:
- **Agent-Readable MCP & JSON-LD Catalog Protocols**.
- **4 AI Merchant Revenue Growth Models** that increase Average Order Value (AOV) and conversion without spamming buyers.
- **Adaptive Bounded & Gated HITL Safety Framework** that executes autonomously when safe and gates execution when risk is detected.
- **An Immutable, Explainable Cryptographic Audit Ledger**.

---

## 2. Core Personas & User Journeys

| Persona | Role | Primary Goal | Key Interaction |
| :--- | :--- | :--- | :--- |
| **Aarav (The Buyer)** | End-User / Shopper | Delegate shopping tasks with natural language goals and strict spending limits. | Inputs: *"Buy me a 4K monitor & ergonomic keyboard under ₹25,000"*. |
| **Buyer AI Agent** | Autonomous Agent | Parse intent, query catalogs via MCP, negotiate quotes, validate safety rules, and execute checkout. | Runs tool-calling loop, rejects unneeded upsells, triggers Razorpay order. |
| **TechGear India (Merchant)** | Seller on Razorpay | Expose inventory to global AI buyers, maximize revenue and profit margins dynamically. | Configures MCP catalog, margin limits, and growth strategies in Merchant Dashboard. |
| **Merchant Growth Agent** | Seller AI Engine | Analyze incoming buyer carts and deploy the optimal Revenue Growth Model in real-time. | Evaluates buyer budget room, margin limits, and returns dynamic quotes. |
| **Safety & Audit Guard** | Financial Gatekeeper | Enforce bounded spending policies, escalate to HITL when needed, and record cryptographic audit trails. | Computes policy rules, verifies HMAC-SHA256 signatures on Razorpay webhooks. |

---

## 3. The 4 AI Merchant Revenue Growth Models

The Merchant AI does not simply push random accessories that waste the buyer's money. It dynamically selects from **4 specialized revenue growth strategies** depending on the buyer's intent, budget headroom, and inventory availability:

```
                              ┌──────────────────────────────────────────────┐
                              │     4 AI Merchant Revenue Growth Models      │
                              └──────────────────────┬───────────────────────┘
                                                     │
         ┌───────────────────┬───────────────────────┴───────────────────────┬───────────────────┐
         ▼                   ▼                                               ▼                   ▼
  1. Quality Upgrade   2. Conversion Closer                            3. Bulk/Subscription  4. Value Services
  (Vertical Upsell)    (Dynamic Discount)                              (Future Revenue)      (Warranty/Care)
  Better item instead   Save the deal from                              Discount for 6-month  Extended support
  of extra item         bouncing to competitor                          refill commitment     or express shipping
```

### Model 1: Quality Upgrade (Vertical Upsell — Better Product, Not More Products)
* **When Triggered**: Buyer has remaining budget room, but strict item constraints (e.g., *"Only monitor and keyboard, no extra junk"*).
* **Mechanism**: Upgrades a requested item to a higher-tier specification (e.g., 60Hz 4K Monitor -> 120Hz Creator 4K Monitor) at an exclusive bundle upgrade rate.
* **Economic Impact**: Merchant increases revenue by +₹1,500 with zero physical clutter for the buyer.

### Model 2: Conversion Closer (Dynamic Anti-Abandonment Discount)
* **When Triggered**: Buyer agent is multi-homing (comparing quotes from multiple stores) or close to abandoning the session.
* **Mechanism**: Evaluates merchant gross margin floor (e.g., min 20% margin) and offers an instant 2–5% **Autonomous Instant-Settlement Discount** via Razorpay.
* **Economic Impact**: Captures an immediate ₹22,500 order that would have otherwise bounced to a rival store (100% conversion recovery).

### Model 3: Bulk / Subscription / Replenishment (Future LTV Lock-In)
* **When Triggered**: Consumable or recurring products (e.g., specialty coffee beans, printer toner, API credits, protein supplements).
* **Mechanism**: Proposes a pre-authorized recurring mandate (e.g., 15% discount for a 3-month scheduled Razorpay recurring payment mandate).
* **Economic Impact**: Transforms a single ₹1,000 transaction into a predictable ₹3,000+ Customer Lifetime Value (LTV).

### Model 4: Value-Add Services & Protection (Zero-Clutter Peace of Mind)
* **When Triggered**: High-value electronics or critical productivity gear where accidental damage or downtime is costly.
* **Mechanism**: Adds 2-Year Express Replacement Warranty or Same-Day Guaranteed Courier Delivery at marginal cost.
* **Economic Impact**: Near 90% gross margin on digital warranty services for merchant; maximum peace of mind for buyer.

---

## 4. Adaptive Bounded & Gated HITL Safety Framework

To solve both **uncontrolled AI spending** and **HITL notification fatigue**, AgentPay Nexus implements a 3-Tier Adaptive Safety Architecture:

```
                                  INCOMING TRANSACTION
                                           │
                        ┌──────────────────┴──────────────────┐
                        ▼                                     ▼
             [ WITHIN USER BOUNDS ]               [ OUTSIDE BOUNDS / AMBIGUOUS ]
          • Below pre-set limit (e.g. <₹5,000)   • Exceeds budget or new category
          • Whitelisted merchant                 • Unrequested upsell items
          • Strict intent matched                • Price drift > 5%
                        │                                     │
                        ▼                                     ▼
              ⚡ TIER 1: AUTONOMOUS                🛡️ TIER 2: GATED HITL
             (Zero friction, instant)             (Presents 1-Click Explainability Card)
                                                              │
                                                              ▼
                                                   🔐 TIER 3: HARD GATE
                                                  (Biometric / OTP for > ₹25,000)
```

### Safety Rules Engine
1. `max_transaction_amount`: Absolute upper cap per single purchase (e.g. ₹15,000).
2. `daily_velocity_cap`: Maximum total spend allowed in a rolling 24-hour window.
3. `category_whitelist`: Approved purchase domains (`electronics`, `office_supplies`, `cloud_services`).
4. `unsolicited_upsell_gate`: If an extra item is recommended that was not in the original prompt, **it must trigger a Tier 2 Gated HITL modal** unless the user set `allow_autonomous_upsell: true`.
5. `price_drift_tolerance`: Rejects checkout if quote changes by > 3% between discovery and settlement.

---

## 5. Technology Stack Specification

| Layer / Tier | Technology / Framework | Key Packages & Libraries | Purpose & Justification |
| :--- | :--- | :--- | :--- |
| **Backend Framework** | **Python 3.11+ / FastAPI** | `fastapi`, `uvicorn`, `pydantic-v2`, `httpx` | High-performance asynchronous API runtime with automatic OpenAPI/Swagger docs and strict schema validation. |
| **Agent Orchestration** | **LangGraph + LangChain Core** | `langgraph`, `langchain-core`, `langchain-google-genai` / `langchain-openai` | Multi-agent state-graph workflow with **native HITL `interrupt()` checkpoints**, cyclic negotiation, and deterministic rollback branching. |
| **Payment Gateway** | **Razorpay Python SDK** | `razorpay` (Official Python SDK), `hmac`, `hashlib` | Real Orders API (`POST /v1/orders`), Payment Links, Standard Checkout modal, Webhook HMAC-SHA256 non-repudiation. |
| **Agent Protocols** | **MCP / JSON-LD & REST** | `pydantic`, Schema.org Product Schemas | Standardized machine-readable catalog discovery and multi-turn agent quote negotiation. |
| **Safety & Audit Ledger** | **LangGraph Checkpointer & Audit Engine** | `langgraph.checkpoint.memory` / SQLite, `hashlib` | State checkpointing for zero-leakage financial rollbacks, explainability cards, and cryptographic audit ledger. |
| **Frontend Framework** | **Next.js 14+ (App Router) + TypeScript** | `next`, `react`, `react-dom`, `lucide-react`, `canvas-confetti` | Full-stack production-grade dashboard with Server/Client Components, fast rendering, and API proxying to FastAPI. |
| **Styling & Design** | **Vanilla CSS Design System / Modern Glassmorphism** | Custom CSS Variables & Glassmorphism Tokens | Pixel-perfect responsiveness, smooth animations, zero Tailwind version bloat. |

---

## 6. Supervisor Multi-Agent Architecture & Specifications

The system implements the **Supervisor Multi-Agent Pattern** in LangGraph. The `CommerceSupervisorAgent` serves as the central state coordinator, delegating tasks to 4 specialized worker agents, enforcing state transitions, and managing HITL interrupts:

```
                               ┌────────────────────────────────────────────────────────┐
                               │           COMMERCE SUPERVISOR AGENT (ORCHESTRATOR)      │
                               │  - Controls LangGraph State & Route Decisions          │
                               │  - Manages HITL Interrupts & Atomic Rollbacks          │
                               │  - Enforces Protocol Standards (MCP, ACP, x402)        │
                               └───────────────────────────┬────────────────────────────┘
                                                           │
              ┌────────────────────────────┬───────────────┴───────────────┬────────────────────────────┐
              ▼                            ▼                               ▼                            ▼
   ┌──────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────────┐
   │     BUYER AGENT      │   │  MERCHANT GROWTH AGENT   │   │    POLICY GUARD AGENT    │   │ RAZORPAY SETTLEMENT AGENT│
   │ (Consumer Advocate)  │   │   (Revenue Optimizer)    │   │  (Compliance & Sentinel) │   │   (Fintech & Webhooks)   │
   ├──────────────────────┤   ├──────────────────────────┤   ├──────────────────────────┤   ├──────────────────────────┤
   │• Intent Parsing      │   │• 4 Revenue Growth Models │   │• Bounded Spending Caps   │   │• Orders API (POST /v1)   │
   │• MCP Catalog Search  │   │• Margin Floor Validation │   │• Category Whitelisting   │   │• Payment Link Generation │
   │• Upsell Shield Rej.  │   │• Cryptographic Quotes    │   │• Tier 2/3 HITL Triggers  │   │• HMAC Webhook Signature  │
   └──────────────────────┘   └──────────────────────────┘   └──────────────────────────┘   └──────────────────────────┘
```

---

## 7. Functional & API Requirements

### 7.1 Agent-Readable Catalog Endpoint
* **Endpoint**: `POST /api/catalog/agent-query`
* **Request**:
  ```json
  {
    "category": "monitors",
    "specs": { "resolution": "4K", "refresh_rate": ">=60Hz" },
    "max_price_inr": 20000
  }
  ```
* **Response**: Returns JSON-LD structured products with stock, pricing, and margin-safe upgrade options.

### 7.2 Merchant Dynamic Quote Endpoint
* **Endpoint**: `POST /api/agent/quote`
* **Request**:
  ```json
  {
    "buyer_agent_id": "agent_aarav_99",
    "requested_items": ["item_monitor_4k", "item_keyboard_ergo"],
    "buyer_context": {
      "budget_cap_inr": 25000,
      "strict_items_only": false
    }
  }
  ```
* **Response**: Returns optimized quote, applied growth model, savings breakdown, and merchant signed quote token.

### 7.3 Razorpay Order Creation & Webhook Verification
* **Endpoint**: `POST /api/razorpay/create-order`
  * Calls Razorpay Test Orders API with `amount` (in paise), `currency: "INR"`, `receipt`, and metadata `notes`.
* **Endpoint**: `POST /api/razorpay/webhook`
  * Intercepts `payment.captured`.
  * Verifies `X-Razorpay-Signature` using `crypto.createHmac('sha256', secret)` (or Python `hmac.new`).
  * Commits transaction to immutable audit ledger.

---

## 8. Failure Handling & Resilience (The Evaluation Bar)

| Failure Case | Root Cause | System Recovery & Graceful Handling |
| :--- | :--- | :--- |
| **Case 1: Budget Cap Breach** | Buyer requests items totaling ₹18,000 with a ₹15,000 policy limit. | Policy Guard halts automated debit; Agent does not crash; generates explainability card showing ₹3,000 breach; provides Tier 2 HITL 1-click budget escalation or suggests lower-tier in-budget items. |
| **Case 2: Inventory Race Condition** | An item sells out between quote generation and payment capture. | Agent catches stock lock failure, invalidates quote, releases held funds, and presents immediate compatible in-stock substitute without creating orphaned Razorpay charges. |
| **Case 3: Unwanted Upsell Rejection** | Buyer AI rejects merchant's add-on accessory because user selected strict items only. | Merchant agent catches `REJECTION_REASON_STRICT_ITEMS`, automatically drops accessory, shifts to Growth Model 2 (Dynamic 2% Checkout Closer), and completes base order smoothly. |

---

## 9. Verification & Demo Criteria

1. **Working GitHub Repository**: Fully typed Python FastAPI backend + Next.js (TypeScript) frontend.
2. **Interactive Multi-View Dashboard**:
   - Tab 1: AI Buyer Simulator (Interactive chat with live MCP tool call execution waterfall).
   - Tab 2: Merchant Revenue Dashboard (Catalog manager, margin sliders, active growth models, AOV metrics).
   - Tab 3: Live Audit Trail & Explainability Inspector (Step-by-step reasoning cards and cryptographic hashes).
   - Tab 4: Failure & Security Testbed (1-click trigger for budget breach, unrequested upsell rejection, and inventory race condition).
3. **5-Minute Pitch Video Script**: Structured to showcase problem, live agentic checkout, dynamic bundling uplift, HITL safety gating, and handled failure recovery.
