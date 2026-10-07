# ⚡ AgentPay Nexus

> **Autonomous Multi-Agent Commerce & Settlement Engine on Razorpay Test Rails**  
> Built for the **Razorpay Buildathon 2026 — Track 01: AI Growth & Agentic Commerce**

[![Razorpay](https://img.shields.io/badge/Razorpay-Test_Mode_APIs-0284c7?style=for-the-badge&logo=razorpay)](https://razorpay.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi_Agent_StateGraph-7c3aed?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)
[![Next.js](https://img.shields.io/badge/Next.js-14+(App_Router)-000000?style=for-the-badge&logo=nextdotjs)](https://nextjs.org)

---

## 📖 Table of Contents
1. [Track 01 Overview & Problem Statement](#-track-01-overview--problem-statement)
2. [Key Architecture & The Supervisor Pattern](#-key-architecture--the-supervisor-pattern)
3. [4 AI Merchant Revenue Growth Models](#-4-ai-merchant-revenue-growth-models)
4. [Adaptive Bounded & Gated HITL Safety Framework](#-adaptive-bounded--gated-hitl-safety-framework)
5. [Immutable Cryptographic Audit Trail](#-immutable-cryptographic-audit-trail)
6. [Tech Stack](#-tech-stack)
7. [Quick Start & Running Locally](#-quick-start--running-locally)
8. [5-Minute Video Demo Script](#-5-minute-video-demo-script)
9. [Project Documentation](#-project-documentation)

---

## 🎯 Track 01 Overview & Problem Statement

E-commerce is transitioning from manual human browsing (scrolling catalogs, filling forms, approving OTPs) to **Autonomous Agent-to-Merchant (A2M) and Agent-to-Agent (A2A) Commerce** powered by protocols like **NPCI UAP (Unified Autonomous Payments)**, **ACP (Agentic Commerce Protocol)**, and **x402 (HTTP 402 AI micropayments)**.

### The Challenge
* **Merchants are invisible to AI buyers** unless they expose machine-readable protocols (MCP / JSON-LD).
* **Merchants lose revenue** without intelligent AI agents dynamically optimizing bundles and closing deals.
* **Consumers fear unconstrained AI spending** unless every financial action is bounded, gated, and explainable.

---

## 🏛️ Key Architecture & The Supervisor Pattern

AgentPay Nexus uses a **Supervisor Multi-Agent StateGraph** built in **LangGraph**:

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
   │  (Consumer Advocate) │   │    (Revenue Optimizer)   │   │  (Compliance & Sentinel) │   │   (Fintech & Webhooks)   │
   ├──────────────────────┤   ├──────────────────────────┤   ├──────────────────────────┤   ├──────────────────────────┤
   │• Intent Parsing      │   │• 4 Revenue Growth Models │   │• Bounded Spending Caps   │   │• Orders API (POST /v1)   │
   │• MCP Catalog Search  │   │• Margin Floor Validation │   │• Category Whitelisting   │   │• Payment Link Generation │
   │• Upsell Shield Rej.  │   │• Cryptographic Quotes    │   │• Tier 2/3 HITL Triggers  │   │• HMAC Webhook Signature  │
   └──────────────────────┘   └──────────────────────────┘   └──────────────────────────┘   └──────────────────────────┘
```

---

## 📈 4 AI Merchant Revenue Growth Models

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

1. **Model 1: Quality Upgrade (Vertical Upsell)**: Recommends upgraded 120Hz Creator 4K Monitor (+₹1,500) when budget headroom exists, delivering higher AOV without physical clutter.
2. **Model 2: Conversion Closer (Dynamic Anti-Abandonment)**: Applies an instant 2.5% autonomous checkout discount on strict-intent buyers to beat competitor agents and guarantee order closure.
3. **Model 3: Bulk / Subscription (Future Recurring LTV)**: 15% discount for scheduled recurring replenishment via Razorpay Subscriptions / UPI Autopay.
4. **Model 4: Value-Add Services & Care**: Subsidized 2-Year Express Replacement Warranty delivering 90% gross margins.

---

## 🛡️ Adaptive Bounded & Gated HITL Safety Framework

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

* **Buyer AI Shield**: Automatically rejects unrequested accessories (`USER_INTENT_STRICT_ITEMS_ONLY`) so user money is never wasted.
* **LangGraph `interrupt()`**: Halts state execution when a boundary is tested and presents a 1-click approval modal.

---

## 🔗 Immutable Cryptographic Audit Trail

Every money action is recorded with SHA-256 hash chaining:
$$\text{Entry\_Hash} = \text{SHA256}(\text{Action} + \text{Actor} + \text{Timestamp} + \text{Previous\_Hash})$$

* Demonstrates zero money leakage.
* Produces natural language **Explainability Cards** breaking down item choice, applied discounts, and policy validation.

---

## 💻 Tech Stack

| Layer | Framework / Library | Purpose |
| :--- | :--- | :--- |
| **Backend** | Python 3.11+ / FastAPI + Uvicorn | Async high-throughput REST backend & auto Swagger UI (`/docs`) |
| **AI Orchestration** | LangGraph + LangChain Core | Multi-Agent StateGraph with native HITL `interrupt()` checkpoints |
| **Fintech Rails** | Razorpay Python SDK (`razorpay`) | Test Orders API, Payment Links, HMAC-SHA256 signature verification |
| **Frontend** | Next.js 14+ (App Router) + TypeScript | Modern dark-mode glassmorphic showcase dashboard |
| **Protocols** | MCP & JSON-LD Schemas (Pydantic) | Standardized machine-readable catalog & quote exchange |

---

## 🚀 Quick Start & Running Locally

### Prerequisites
* Python 3.11+
* Node.js v18+ & npm

### 1. Start the FastAPI Backend
```bash
cd server
# Windows:
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
* Backend API: `http://127.0.0.1:8000`
* Interactive Swagger Docs: `http://127.0.0.1:8000/docs`

### 2. Start the Next.js Frontend
```bash
cd client
npm install
npm run dev
```
* Frontend Dashboard: `http://localhost:3000`

---

## 🎥 5-Minute Video Demo Script

1. **Minute 0:00 – 1:00 (The Problem & Protocol Shift)**: Explain the rise of AI buyers (NPCI UAP, ACP, x402) and why merchants need AgentPay Nexus.
2. **Minute 1:00 – 2:15 (Merchant Growth Engine)**: Open the **Merchant Growth Dashboard**, show MCP catalog, gross margin sliders, and 4 Growth Models.
3. **Minute 2:15 – 3:30 (Autonomous Bounded Checkout)**: Run natural language query in **AI Buyer Simulator**, show live multi-agent execution waterfall, explainability card, and complete Razorpay test payment modal.
4. **Minute 3:30 – 5:00 (The Bar: HITL Gating, Audit Trail & Failure Handling)**:
   * Switch to **Chaos Lab**, trigger **Budget Breach**, show the 1-click **Tier 2 HITL Gate Modal**.
   * Show the **Immutable Audit Trail** with verified SHA-256 hash chains.

---

## 📚 Project Documentation

* **[`PRD.md`](file:///d:/Razor_Pay_Track/PRD.md)** — Comprehensive Product Requirements Document.
* **[`PROJECT_BLUEPRINT.md`](file:///d:/Razor_Pay_Track/PROJECT_BLUEPRINT.md)** — Complete Technical Architecture & Video Pitch Blueprint.
* **[`docs/data_flow_viewer.html`](file:///d:/Razor_Pay_Track/docs/data_flow_viewer.html)** — Interactive Visual Sequence Flow Viewer.
* **[`docs/agentpay_data_flow.svg`](file:///d:/Razor_Pay_Track/docs/agentpay_data_flow.svg)** — High-precision vector architecture diagram.
