import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(64), nullable=False, index=True)
    description = Column(Text, nullable=False)
    specifications = Column(Text, nullable=False, default="{}")  # JSON string
    cost_price = Column(Float, nullable=False)
    retail_price = Column(Float, nullable=False)
    stock_quantity = Column(Integer, nullable=False, default=10)
    upgrade_to_sku = Column(String(64), nullable=True)
    upgrade_bundle_discount = Column(Float, nullable=True, default=0.0)
    warranty_price = Column(Float, nullable=True, default=0.0)
    json_ld_schema = Column(Text, nullable=False, default="{}")  # JSON string
    is_subscription = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    margin_floor_pct = Column(Float, nullable=False, default=0.20)
    active_growth_models = Column(Text, nullable=False, default='["quality_upgrade", "conversion_closer", "bulk_subscription", "value_services"]')
    api_key = Column(String(128), nullable=False, default="sec_live_merchant_991823")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Policy(Base):
    __tablename__ = "policies"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    max_tx_amount = Column(Float, nullable=False, default=25000.0)
    daily_velocity_cap = Column(Float, nullable=False, default=50000.0)
    category_whitelist = Column(Text, nullable=False, default='["monitors", "keyboards", "mice", "electronics", "accessories", "furniture", "subscriptions", "services"]')
    allow_autonomous_upsell = Column(Boolean, default=False)
    price_drift_tolerance_pct = Column(Float, default=3.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class Order(Base):
    __tablename__ = "orders"

    id = Column(String(64), primary_key=True)
    razorpay_order_id = Column(String(64), nullable=False, index=True)
    razorpay_payment_id = Column(String(64), nullable=True)
    buyer_agent_id = Column(String(64), nullable=False)
    merchant_id = Column(String(64), nullable=False, default="merchant_techgear_01")
    status = Column(String(32), nullable=False, default="CREATED")  # CREATED, PENDING_HITL, AUTHORIZED, PAID, FAILED, ROLLED_BACK
    base_amount = Column(Float, nullable=False)
    discount_amount = Column(Float, nullable=False, default=0.0)
    warranty_amount = Column(Float, nullable=False, default=0.0)
    total_amount = Column(Float, nullable=False)
    currency = Column(String(8), default="INR")
    growth_model_applied = Column(String(64), nullable=True)
    items_json = Column(Text, nullable=False, default="[]")
    explainability_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AuditEntry(Base):
    __tablename__ = "audit_ledger"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence_number = Column(Integer, unique=True, nullable=False, index=True)
    timestamp = Column(String(64), nullable=False)
    actor = Column(String(64), nullable=False)
    action = Column(String(64), nullable=False)
    payload_json = Column(Text, nullable=False)
    prev_hash = Column(String(64), nullable=False)
    entry_hash = Column(String(64), nullable=False, index=True)
    verified = Column(Boolean, default=True)

class HITLApprovalQueue(Base):
    __tablename__ = "hitl_approval_queue"

    id = Column(String(64), primary_key=True)
    order_id = Column(String(64), nullable=True)
    buyer_agent_id = Column(String(64), nullable=False)
    trigger_reason = Column(String(64), nullable=False)  # BUDGET_CAP_BREACH, UNREQUESTED_UPSELL, HARD_GATE_LIMIT, PRICE_DRIFT
    details_json = Column(Text, nullable=False, default="{}")
    status = Column(String(32), nullable=False, default="PENDING")  # PENDING, APPROVED, REJECTED, ADJUSTED
    explainability_card_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
