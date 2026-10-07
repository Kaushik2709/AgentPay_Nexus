import json
import uuid
import datetime
from typing import Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models import Policy, Order, HITLApprovalQueue
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
        """Calculates total spend by user in the rolling past 24 hours from confirmed orders."""
        one_day_ago = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        query = select(func.sum(Order.total_amount)).where(
            Order.buyer_agent_id.like(f"%{user_id}%") | (Order.buyer_agent_id == "agent_aarav_99"),
            Order.status == "PAID",
            Order.created_at >= one_day_ago
        )
        res = await db.execute(query)
        spent = res.scalar()
        return float(spent or 0.0)

    async def evaluate_quote(
        self,
        db: AsyncSession,
        quote: DynamicQuoteResponse,
        user_id: str = "aarav_buyer_01",
        user_override_budget: float = None
    ) -> PolicyEvaluationResponse:
        # Load user policy
        pol_query = select(Policy).where(Policy.user_id == user_id)
        pol_res = await db.execute(pol_query)
        policy = pol_res.scalar_one_or_none()

        max_tx = user_override_budget or (policy.max_tx_amount if policy else 25000.0)
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
        if quote.final_total > max_tx:
            overage = quote.final_total - max_tx
            violations.append(f"TRANSACTION_CAP_EXCEEDED: Quote ₹{quote.final_total:,.2f} exceeds user cap of ₹{max_tx:,.2f} by ₹{overage:,.2f}.")
            is_tier_2_gated = True

        # Rule 2: Hard Gate threshold (> ₹25,000)
        if quote.final_total > 25000.0:
            is_tier_3_hard_gate = True
            violations.append("HARD_GATE_LIMIT: Total order value exceeds Tier 3 hard limit (₹25,000).")

        # Rule 3: Daily Velocity Cap
        projected_daily = spent_24h + quote.final_total
        if projected_daily > daily_cap:
            violations.append(f"DAILY_VELOCITY_CAP_EXCEEDED: Rolling 24h spend (₹{spent_24h:,.2f} + ₹{quote.final_total:,.2f} = ₹{projected_daily:,.2f}) exceeds daily cap of ₹{daily_cap:,.2f}.")
            is_tier_2_gated = True

        # Rule 4: Category Whitelist
        for item in quote.items:
            cat = getattr(item, 'category', 'general')
            if cat not in whitelist and cat != "services" and cat != "general":
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
                "Transaction passed all bounded safety rules. Autonomous zero-friction settlement granted."
                if can_proceed else
                f"Transaction requires human authorization due to {len(violations)} policy boundary trigger(s)."
            ),
            "recommendation": (
                "Ready for instant settlement."
                if can_proceed else
                "Review the explainability breakdown and authorize 1-click escalation."
            )
        }

        # If HITL required, create entry in HITLApprovalQueue
        hitl_gate_id = None
        if hitl_required:
            hitl_gate_id = f"gate_{uuid.uuid4().hex[:12]}"
            queue_entry = HITLApprovalQueue(
                id=hitl_gate_id,
                order_id=quote.quote_id,
                buyer_agent_id=quote.buyer_agent_id,
                trigger_reason=violations[0] if violations else "MANUAL_REVIEW",
                details_json=json.dumps({
                    "quote": quote.model_dump(),
                    "violations": violations,
                    "tier": tier
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
