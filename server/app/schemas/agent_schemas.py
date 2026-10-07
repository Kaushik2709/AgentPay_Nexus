from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# ----------------- Catalog & MCP Schemas -----------------

class CatalogQueryRequest(BaseModel):
    category: Optional[str] = None
    query_text: Optional[str] = None
    specs: Optional[Dict[str, Any]] = None
    max_price_inr: Optional[float] = None
    in_stock_only: bool = True

class CatalogProductResponse(BaseModel):
    id: int
    sku: str
    name: str
    category: str
    description: str
    specifications: Dict[str, Any]
    retail_price: float
    cost_price: float
    stock_quantity: int
    upgrade_to_sku: Optional[str] = None
    upgrade_bundle_discount: Optional[float] = 0.0
    warranty_price: Optional[float] = 0.0
    json_ld_schema: Dict[str, Any]
    is_subscription: bool = False

# ----------------- Quote Schemas -----------------

class QuoteItem(BaseModel):
    sku: str
    name: str
    quantity: int = 1
    unit_price: float
    original_price: float
    is_upgraded: bool = False
    upgraded_from_sku: Optional[str] = None
    is_warranty: bool = False
    is_unrequested_upsell: bool = False
    category: str = "general"

class BuyerContext(BaseModel):
    budget_cap_inr: float = 25000.0
    strict_items_only: bool = False
    allow_autonomous_upsell: bool = False
    user_id: str = "aarav_buyer_01"

class DynamicQuoteRequest(BaseModel):
    buyer_agent_id: str = "agent_aarav_99"
    requested_skus: List[str]
    buyer_context: BuyerContext
    preferred_growth_model: Optional[str] = None  # None = dynamic auto-selection

class DynamicQuoteResponse(BaseModel):
    quote_id: str
    buyer_agent_id: str
    merchant_id: str = "merchant_techgear_01"
    items: List[QuoteItem]
    base_subtotal: float
    discount_total: float
    warranty_total: float
    final_total: float
    merchant_gross_margin_pct: float
    applied_growth_model: str  # quality_upgrade, conversion_closer, bulk_subscription, value_services, standard
    savings_breakdown: str
    merchant_signature: str
    explainability_note: str
    expires_at: str

# ----------------- Policy & Safety Schemas -----------------

class PolicyEvaluationRequest(BaseModel):
    buyer_agent_id: str
    quote: DynamicQuoteResponse
    user_id: str = "aarav_buyer_01"

class PolicyEvaluationResponse(BaseModel):
    is_compliant: bool
    tier: str  # TIER_1_AUTONOMOUS, TIER_2_GATED_HITL, TIER_3_HARD_GATE
    violations: List[str] = []
    explainability_card: Dict[str, Any]
    can_proceed_autonomously: bool
    hitl_required: bool
    hitl_gate_id: Optional[str] = None

class PolicyUpdateRequest(BaseModel):
    max_tx_amount: Optional[float] = None
    daily_velocity_cap: Optional[float] = None
    category_whitelist: Optional[List[str]] = None
    allow_autonomous_upsell: Optional[bool] = None
    price_drift_tolerance_pct: Optional[float] = None

# ----------------- Razorpay Schemas -----------------

class RazorpayCreateOrderRequest(BaseModel):
    quote_id: str
    amount_inr: float
    currency: str = "INR"
    buyer_agent_id: str
    receipt_prefix: str = "rcpt_nexus"
    notes: Optional[Dict[str, Any]] = None

class RazorpayOrderResponse(BaseModel):
    razorpay_order_id: str
    amount_in_paise: int
    amount_inr: float
    currency: str
    status: str
    receipt: str
    payment_link: str
    key_id: str
    notes: Dict[str, Any]

class PaymentVerificationRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    buyer_agent_id: str = "agent_aarav_99"

class PaymentVerificationResponse(BaseModel):
    success: bool
    status: str
    transaction_hash: str
    audit_sequence: int
    message: str
    digital_receipt: Dict[str, Any]

# ----------------- HITL Gate Schemas -----------------

class HITLActionRequest(BaseModel):
    gate_id: str
    action: str  # APPROVE, REJECT, ADJUST_BUDGET
    adjusted_budget: Optional[float] = None
    comment: Optional[str] = None

class HITLActionResponse(BaseModel):
    success: bool
    status: str
    message: str
    order_id: Optional[str] = None
    next_step: str

# ----------------- Full Multi-Agent Workflow Schemas -----------------

class AgentWorkflowRequest(BaseModel):
    user_goal: str  # e.g., "Buy me a 4K monitor and ergonomic keyboard under ₹25,000"
    budget_cap_inr: float = 25000.0
    strict_items_only: bool = False
    allow_autonomous_upsell: bool = False
    force_growth_model: Optional[str] = None  # None for auto, or "quality_upgrade", "conversion_closer", etc.
    simulate_stock_race: bool = False

class AgentStepTrace(BaseModel):
    step_number: int
    actor: str  # Supervisor, BuyerAgent, MerchantGrowthAgent, PolicyGuard, RazorpaySettlementAgent
    action: str
    status: str  # SUCCESS, GATED, FAILED, WARNING
    summary: str
    data_payload: Dict[str, Any] = {}
    timestamp: str

class AgentWorkflowResponse(BaseModel):
    workflow_id: str
    user_goal: str
    status: str  # COMPLETED_AUTONOMOUS, GATED_HITL, FAILED_ROLLED_BACK
    steps: List[AgentStepTrace]
    quote: Optional[DynamicQuoteResponse] = None
    policy_result: Optional[PolicyEvaluationResponse] = None
    razorpay_order: Optional[RazorpayOrderResponse] = None
    explainability_card: Optional[Dict[str, Any]] = None
    hitl_gate_id: Optional[str] = None
    audit_entry_hash: Optional[str] = None
    total_spent: float = 0.0
    total_saved: float = 0.0

# ----------------- Audit & Chaos Schemas -----------------

class AuditVerificationResponse(BaseModel):
    is_valid: bool
    total_blocks_verified: int
    latest_hash: str
    genesis_hash: str
    tampered_blocks: List[int] = []
    message: str

class ChaosScenarioRequest(BaseModel):
    scenario_id: str  # "budget_breach", "stock_race_condition", "strict_upsell_rejection"
