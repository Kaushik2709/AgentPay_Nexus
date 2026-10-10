const API_BASE = "/api/backend";

export interface Explanation {
  title?: string; status?: string; tier?: string; reasoning?: string; reason?: string;
  violations?: string[]; recommendation?: string; order_total?: number;
  budget_cap?: number; applied_growth_model?: string; discount_savings?: number;
}
export interface PolicyConfig {
  max_tx_amount: number; daily_velocity_cap: number; category_whitelist: string[];
  allow_autonomous_upsell: boolean;
}
export interface PendingGate {
  id: string; gate_id: string; order_id: string; workflow_id: string;
  trigger_reason: string; status: string; quote_data: Partial<DynamicQuote>;
  violations: string[]; explainability_card: Explanation;
}
export interface MerchantDashboard {
  margin_floor_pct: number; active_growth_models: string[];
  metrics: { total_revenue_inr: number; total_orders_completed: number; avg_order_value_inr: number; total_discounts_granted_inr: number; sku_count: number; total_units_in_stock: number };
}
export interface AuditVerification {
  is_valid: boolean; total_blocks_verified: number; latest_hash: string;
  genesis_hash: string; tampered_blocks: number[]; message: string;
}
export interface PaymentReceipt {
  order_id: string; payment_id: string; amount: number; currency: string; audit_hash: string;
}
export interface PaymentVerification {
  success: boolean; status: string; message: string; digital_receipt: PaymentReceipt;
}
export interface ApprovalResult {
  success: boolean; status: string; message: string;
  razorpay_order?: AgentWorkflowResponse["razorpay_order"];
}

async function apiFetch(input: string, init: RequestInit = {}) {
  let response: Response;
  try {
    response = await fetch(input, { ...init, signal: AbortSignal.timeout(input.includes("orchestrate") || input.includes("chaos") ? 120000 : 15000) });
  } catch {
    throw new Error("The API could not be reached or the request timed out. Check the backend connection. For purchase actions, check the audit trail before retrying.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : Array.isArray(body?.detail)
      ? body.detail.slice(0, 3).map((issue: { msg?: unknown }) => typeof issue.msg === "string" ? issue.msg : "Invalid request value.").join(" ")
      : `Request failed (${response.status}). Please try again.`;
    throw new Error(detail);
  }
  return response;
}

export interface CatalogProduct {
  id: number;
  sku: string;
  name: string;
  category: string;
  description: string;
  specifications: Record<string, unknown>;
  retail_price: number;
  cost_price: number;
  stock_quantity: number;
  upgrade_to_sku?: string;
  upgrade_bundle_discount?: number;
  warranty_price?: number;
  json_ld_schema: Record<string, unknown>;
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
  data_payload: Record<string, unknown>;
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
    explainability_card: Explanation;
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
    notes: Record<string, unknown>;
  };
  explainability_card?: Explanation;
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
  payload: Record<string, unknown>;
  prev_hash: string;
  entry_hash: string;
  verified: boolean;
}

export const api = {
  async getIdentity(): Promise<{ user_id: string; role: string }> {
    return (await apiFetch(`${API_BASE}/me`)).json();
  },
  async getOrders(): Promise<{ id: string; status: string; amount_inr: number; created_at: string; checkout?: AgentWorkflowResponse["razorpay_order"] }[]> {
    return (await apiFetch(`${API_BASE}/agent/orders`)).json();
  },
  async getHealth() {
    const res = await apiFetch(`${API_BASE}/health`, { cache: "no-store" });
    if (!res.ok) throw new Error("Backend unreachable");
    return res.json();
  },

  async getProducts(): Promise<CatalogProduct[]> {
    const res = await apiFetch(`${API_BASE}/catalog/products`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to load products");
    return res.json();
  },

  async updateProductInventory(sku: string, data: { stock_quantity?: number; retail_price?: number; cost_price?: number }) {
    const res = await apiFetch(`${API_BASE}/catalog/products/${sku}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to update inventory");
    return res.json();
  },

  async getMerchantDashboard(): Promise<MerchantDashboard> {
    const res = await apiFetch(`${API_BASE}/merchant/dashboard`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch merchant dashboard");
    return res.json();
  },

  async updateMerchantConfig(data: { margin_floor_pct?: number; active_growth_models?: string[] }) {
    const res = await apiFetch(`${API_BASE}/merchant/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to update merchant config");
    return res.json();
  },

  async getPolicyConfig(): Promise<PolicyConfig> {
    const res = await apiFetch(`${API_BASE}/policy/config`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to load policy config");
    return res.json();
  },

  async updatePolicyConfig(data: {
    max_tx_amount?: number;
    daily_velocity_cap?: number;
    category_whitelist?: string[];
    allow_autonomous_upsell?: boolean;
  }) {
    const res = await apiFetch(`${API_BASE}/policy/config`, {
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
    const payload = JSON.stringify(data);
    const previous = sessionStorage.getItem("pending-purchase");
    let key = crypto.randomUUID();
    if (previous) {
      try { const pending = JSON.parse(previous); if (pending.payload === payload) key = pending.key; } catch { /* Replace malformed local state. */ }
    }
    sessionStorage.setItem("pending-purchase", JSON.stringify({ payload, key }));
    const res = await apiFetch(`${API_BASE}/agent/orchestrate`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": key },
      body: payload,
    });
    if (!res.ok) throw new Error("Agent workflow orchestration failed");
    const result = await res.json();
    sessionStorage.removeItem("pending-purchase");
    return result;
  },

  async getPendingHITLGates(): Promise<PendingGate[]> {
    const res = await apiFetch(`${API_BASE}/agent/hitl/pending`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch pending HITL gates");
    return res.json();
  },

  async resumeHITLGatedWorkflow(gateId: string, action: string, adjustedBudget?: number): Promise<ApprovalResult> {
    const res = await apiFetch(`${API_BASE}/agent/hitl/resume`, {
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

  async verifyPayment(orderId: string, paymentId: string, signature: string): Promise<PaymentVerification> {
    const res = await apiFetch(`${API_BASE}/razorpay/verify-payment`, {
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
    const res = await apiFetch(`${API_BASE}/audit/trail?limit=${limit}`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch audit trail");
    return res.json();
  },

  async verifyAuditLedger(): Promise<AuditVerification> {
    const res = await apiFetch(`${API_BASE}/audit/verify`, { cache: "no-store" });
    if (!res.ok) throw new Error("Audit verification failed");
    return res.json();
  },

  async triggerChaosScenario(scenarioId: string): Promise<AgentWorkflowResponse> {
    const res = await apiFetch(`${API_BASE}/chaos/trigger`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario_id: scenarioId }),
    });
    if (!res.ok) throw new Error("Chaos scenario execution failed");
    return res.json();
  },
};
