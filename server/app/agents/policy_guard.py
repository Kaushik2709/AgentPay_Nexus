import json
import uuid
import datetime
from typing import Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models import Policy, Order, HITLApprovalQueue
from app.commerce import paise


def policy_snapshot(policy):
    """Exact financial authorization inputs; compared again on human approval."""
    return {
        "max_tx_paise": paise(policy.max_tx_amount if policy else 25000),
        "daily_cap_paise": paise(policy.daily_velocity_cap if policy else 50000),
        "categories": sorted(json.loads(policy.category_whitelist)) if policy else sorted([
            "monitors", "keyboards", "mice", "electronics", "accessories", "furniture", "subscriptions", "services"]),
        "upsell": bool(policy.allow_autonomous_upsell) if policy else False,
        "price_tolerance": policy.price_drift_tolerance_pct if policy else 3.0,
    }
from app.schemas.agent_schemas import (
    DynamicQuoteResponse,
    PolicyEvaluationResponse
)

class PolicyGuardAgent:
    """
    Financial Gatekeeper & Compliance Sentinel.
    Enforces the 3-Tier Adaptive Safety Architecture:
    - Tier 1: Autonomous (Instant zero-friction execution)
    - Tier 2: Gated HITL (Presents 1-Click Explainability Card for approval)
    - Tier 3: Hard Gate (High-value / Strict threshold requiring OTP/Biometric confirmation)
    """
    def __init__(self, agent_id: str = "policy_guard_sentinel"):
        self.agent_id = agent_id

    async def _get_24h_spent_velocity(self, db: AsyncSession, user_id: str) -> float:
        """Counts verified spend and outstanding checkout capacity, including uncertain attempts."""
        one_day_ago = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        query = select(func.sum(Order.amount_paise)).where(
            Order.buyer_agent_id == user_id,
            Order.status.in_(["PAID", "PAID_REQUIRES_REVIEW", "CREATED", "CREATING", "RECONCILIATION_REQUIRED"]),
            # Uncertain operations reserve spend even after 24h until reconciled.
            ((func.coalesce(Order.settled_at, Order.created_at) >= one_day_ago) |
             Order.status.in_(["CREATING", "RECONCILIATION_REQUIRED"]))
        )
        res = await db.execute(query)
        spent = res.scalar()
        return int(spent or 0) / 100

    async def evaluate_quote(
        self,
        db: AsyncSession,
        quote: DynamicQuoteResponse,
        user_id: str = "aarav_buyer_01",
        user_override_budget: float = None,
        create_gate: bool = True
    ) -> PolicyEvaluationResponse:
        # Load user policy
        pol_query = select(Policy).where(Policy.user_id == user_id)
        pol_res = await db.execute(pol_query)
        policy = pol_res.scalar_one_or_none()

        policy_cap = policy.max_tx_amount if policy else 25000.0
        max_tx = min(policy_cap, user_override_budget) if user_override_budget is not None else policy_cap
        daily_cap = policy.daily_velocity_cap if policy else 50000.0
        whitelist = json.loads(policy.category_whitelist) if (policy and policy.category_whitelist) else [
            "monitors", "keyboards", "mice", "electronics", "accessories", "furniture", "subscriptions", "services"
        ]
        allow_upsell = policy.allow_autonomous_upsell if policy else False

        spent_24h = await self._get_24h_spent_velocity(db, user_id)
        
        violations: List[str] = []
        is_tier_3_hard_gate = False
        is_tier_2_gated = False

        # Rule 1: Max Transaction Cap
        if paise(quote.final_total) > paise(max_tx):
            overage = quote.final_total - max_tx
            violations.append(f"TRANSACTION_CAP_EXCEEDED: Quote ₹{quote.final_total:,.2f} exceeds user cap of ₹{max_tx:,.2f} by ₹{overage:,.2f}.")
            is_tier_2_gated = True

        # Rule 2: Hard Gate threshold (> ₹25,000)
        if paise(quote.final_total) > 2500000:
            is_tier_3_hard_gate = True
            violations.append("HARD_GATE_LIMIT: Total order value exceeds Tier 3 hard limit (₹25,000).")

        # Rule 3: Daily Velocity Cap
        projected_daily = (paise(spent_24h) + paise(quote.final_total)) / 100
        if paise(projected_daily) > paise(daily_cap):
            violations.append(f"DAILY_VELOCITY_CAP_EXCEEDED: Rolling 24h spend (₹{spent_24h:,.2f} + ₹{quote.final_total:,.2f} = ₹{projected_daily:,.2f}) exceeds daily cap of ₹{daily_cap:,.2f}.")
            is_tier_2_gated = True

        # Rule 4: Category Whitelist
        for item in quote.items:
            cat = getattr(item, 'category', 'general')
            if cat not in whitelist:
                violations.append(f"UNAPPROVED_CATEGORY: Item '{item.name}' belongs to unapproved domain '{cat}'.")
                is_tier_2_gated = True

        # Rule 5: Unsolicited Upsell Gate
        for item in quote.items:
            if item.is_unrequested_upsell and not allow_upsell:
                violations.append(f"UNSOLICITED_UPSELL_DETECTED: Add-on '{item.name}' (₹{item.unit_price:,.2f}) was not in original intent.")
                is_tier_2_gated = True

        # Determine Tier
        if is_tier_3_hard_gate:
            tier = "TIER_3_HARD_GATE"
            hitl_required = True
            can_proceed = False
        elif is_tier_2_gated or len(violations) > 0:
            tier = "TIER_2_GATED_HITL"
            hitl_required = True
            can_proceed = False
        else:
            tier = "TIER_1_AUTONOMOUS"
            hitl_required = False
            can_proceed = True

        # Build Explainability Card
        explainability_card = {
            "title": "Autonomous Safety & Policy Guard Evaluation",
            "tier": tier,
            "status": "APPROVED_AUTONOMOUS" if can_proceed else "GATED_PENDING_APPROVAL",
            "order_total": quote.final_total,
            "budget_cap": max_tx,
            "spent_24h": spent_24h,
            "daily_cap": daily_cap,
            "applied_growth_model": quote.applied_growth_model,
            "discount_savings": quote.discount_total,
            "violations": violations,
            "reasoning": (
                "Purchase passed the spending rules. Checkout is approved; payment still requires verification."
                if can_proceed else
                f"Transaction requires human authorization due to {len(violations)} policy boundary trigger(s)."
            ),
            "recommendation": (
                "Proceed to checkout. A receipt appears after the payment is verified."
                if can_proceed else
                "Review the explainability breakdown and authorize 1-click escalation."
            )
        }

        # If HITL required, create entry in HITLApprovalQueue
        hitl_gate_id = None
        if hitl_required and create_gate:
            hitl_gate_id = f"gate_{uuid.uuid4().hex[:12]}"
            queue_entry = HITLApprovalQueue(
                id=hitl_gate_id,
                order_id=quote.quote_id,
                buyer_agent_id=quote.buyer_agent_id,
                trigger_reason=violations[0].split(":", 1)[0] if violations else "MANUAL_REVIEW",
                details_json=json.dumps({
                    "quote": quote.model_dump(),
                    "violations": violations,
                    "tier": tier,
                    "policy_snapshot": policy_snapshot(policy)
                }),
                status="PENDING",
                explainability_card_json=json.dumps(explainability_card)
            )
            db.add(queue_entry)
            await db.commit()

        return PolicyEvaluationResponse(
            is_compliant=can_proceed,
            tier=tier,
            violations=violations,
            explainability_card=explainability_card,
            can_proceed_autonomously=can_proceed,
            hitl_required=hitl_required,
            hitl_gate_id=hitl_gate_id
        )
