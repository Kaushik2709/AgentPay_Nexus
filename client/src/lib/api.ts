const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

export interface CatalogProduct {
  id: number;
  sku: string;
  name: string;
  category: string;
  description: string;
  specifications: Record<string, any>;
  retail_price: number;
  cost_price: number;
  stock_quantity: number;
  upgrade_to_sku?: string;
  upgrade_bundle_discount?: number;
  warranty_price?: number;
  json_ld_schema: Record<string, any>;
  is_subscription: boolean;
}

export interface QuoteItem {
  sku: string;
  name: string;
  quantity: number;
  unit_price: number;
  original_price: number;
  is_upgraded: boolean;
  upgraded_from_sku?: string;
  is_warranty: boolean;
  is_unrequested_upsell: boolean;
  category: string;
}

export interface DynamicQuote {
  quote_id: string;
  buyer_agent_id: string;
  merchant_id: string;
  items: QuoteItem[];
  base_subtotal: number;
  discount_total: number;
  warranty_total: number;
  final_total: number;
  merchant_gross_margin_pct: number;
  applied_growth_model: string;
  savings_breakdown: string;
  merchant_signature: string;
  explainability_note: string;
  expires_at: string;
}

export interface AgentStepTrace {
  step_number: number;
  actor: string;
  action: string;
  status: string;
  summary: string;
  data_payload: Record<string, any>;
  timestamp: string;
}

export interface AgentWorkflowResponse {
  workflow_id: string;
  user_goal: string;
  status: string;
  steps: AgentStepTrace[];
  quote?: DynamicQuote;
  policy_result?: {
    is_compliant: boolean;
    tier: string;
    violations: string[];
    explainability_card: Record<string, any>;
    can_proceed_autonomously: boolean;
    hitl_required: boolean;
    hitl_gate_id?: string;
  };
  razorpay_order?: {
    razorpay_order_id: string;
    amount_in_paise: number;
    amount_inr: number;
    currency: string;
    status: string;
    receipt: string;
    payment_link: string;
    key_id: string;
    notes: Record<string, any>;
  };
  explainability_card?: Record<string, any>;
  hitl_gate_id?: string;
  audit_entry_hash?: string;
  total_spent: number;
  total_saved: number;
}

export interface AuditEntry {
  id: number;
  sequence_number: number;
  timestamp: string;
  actor: string;
  action: string;
  payload: Record<string, any>;
  prev_hash: string;
  entry_hash: string;
  verified: boolean;
}

export const api = {
  async getHealth() {
    const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
    if (!res.ok) throw new Error("Backend unreachable");
    return res.json();
  },

  async getProducts(): Promise<CatalogProduct[]> {
    const res = await fetch(`${API_BASE}/catalog/products`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to load products");
    return res.json();
  },

  async updateProductInventory(sku: string, data: { stock_quantity?: number; retail_price?: number; cost_price?: number }) {
    const res = await fetch(`${API_BASE}/catalog/products/${sku}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to update inventory");
    return res.json();
  },

  async getMerchantDashboard() {
    const res = await fetch(`${API_BASE}/merchant/dashboard`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch merchant dashboard");
    return res.json();
  },

  async updateMerchantConfig(data: { margin_floor_pct?: number; active_growth_models?: string[] }) {
    const res = await fetch(`${API_BASE}/merchant/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to update merchant config");
    return res.json();
  },

  async getPolicyConfig() {
    const res = await fetch(`${API_BASE}/policy/config`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to load policy config");
    return res.json();
  },

  async updatePolicyConfig(data: {
    max_tx_amount?: number;
    daily_velocity_cap?: number;
    category_whitelist?: string[];
    allow_autonomous_upsell?: boolean;
  }) {
    const res = await fetch(`${API_BASE}/policy/config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to update policy");
    return res.json();
  },

  async orchestrateWorkflow(data: {
    user_goal: string;
    budget_cap_inr: number;
    strict_items_only: boolean;
    allow_autonomous_upsell: boolean;
    force_growth_model?: string;
  }): Promise<AgentWorkflowResponse> {
    const res = await fetch(`${API_BASE}/agent/orchestrate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Agent workflow orchestration failed");
    return res.json();
  },

  async getPendingHITLGates() {
    const res = await fetch(`${API_BASE}/agent/hitl/pending`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch pending HITL gates");
    return res.json();
  },

  async resumeHITLGatedWorkflow(gateId: string, action: string, adjustedBudget?: number) {
    const res = await fetch(`${API_BASE}/agent/hitl/resume`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        gate_id: gateId,
        action,
        adjusted_budget: adjustedBudget,
      }),
    });
    if (!res.ok) throw new Error("Failed to resolve HITL gate");
    return res.json();
  },

  async verifyPayment(orderId: string, paymentId: string, signature: string) {
    const res = await fetch(`${API_BASE}/razorpay/verify-payment`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        razorpay_order_id: orderId,
        razorpay_payment_id: paymentId,
        razorpay_signature: signature,
      }),
    });
    if (!res.ok) throw new Error("Payment verification failed");
    return res.json();
  },

  async getAuditTrail(limit = 50): Promise<AuditEntry[]> {
    const res = await fetch(`${API_BASE}/audit/trail?limit=${limit}`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch audit trail");
    return res.json();
  },

  async verifyAuditLedger() {
    const res = await fetch(`${API_BASE}/audit/verify`, { cache: "no-store" });
    if (!res.ok) throw new Error("Audit verification failed");
    return res.json();
  },

  async triggerChaosScenario(scenarioId: string): Promise<AgentWorkflowResponse> {
    const res = await fetch(`${API_BASE}/chaos/trigger`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario_id: scenarioId }),
    });
    if (!res.ok) throw new Error("Chaos scenario execution failed");
    return res.json();
  },
};
