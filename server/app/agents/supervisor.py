import datetime
import uuid
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.buyer_agent import BuyerAgent
from app.agents.merchant_agent import MerchantGrowthAgent
from app.agents.policy_guard import PolicyGuardAgent
from app.razorpay.settlement_agent import RazorpaySettlementAgent
from app.audit.ledger import AuditLedgerEngine
from app.catalog.catalog_service import CatalogService
from app.db.models import HITLApprovalQueue, Order, Product
from app.schemas.agent_schemas import (
    AgentWorkflowRequest,
    AgentWorkflowResponse,
    AgentStepTrace,
    DynamicQuoteRequest,
    DynamicQuoteResponse,
    BuyerContext,
    RazorpayCreateOrderRequest,
    RazorpayOrderResponse,
    PolicyEvaluationResponse
)

class CommerceSupervisorAgent:
    """
    Central Multi-Agent State Coordinator & Orchestrator.
    Controls the state transitions, worker routing, HITL interrupt gates, and atomic rollbacks.
    """
    def __init__(self):
        self.buyer_agent = BuyerAgent(agent_id="agent_aarav_99")
        self.merchant_agent = MerchantGrowthAgent(merchant_id="merchant_techgear_01")
        self.policy_guard = PolicyGuardAgent(agent_id="policy_guard_sentinel")
        self.settlement_agent = RazorpaySettlementAgent()

    async def execute_workflow(
        self,
        db: AsyncSession,
        request: AgentWorkflowRequest
    ) -> AgentWorkflowResponse:
        workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
        steps: List[AgentStepTrace] = []
        step_idx = 1

        def add_trace(actor: str, action: str, status: str, summary: str, payload: Dict[str, Any] = None):
            nonlocal step_idx
            steps.append(AgentStepTrace(
                step_number=step_idx,
                actor=actor,
                action=action,
                status=status,
                summary=summary,
                data_payload=payload or {},
                timestamp=datetime.datetime.utcnow().isoformat()
            ))
            step_idx += 1

        # ----------------------------------------------------
        # STEP 1: Intent & Goal Parsing (Buyer Agent)
        # ----------------------------------------------------
        parsed_intent = self.buyer_agent.parse_intent(request.user_goal, request.budget_cap_inr)
        effective_budget = parsed_intent["effective_budget"]
        strict_items = request.strict_items_only or parsed_intent.get("strict_items_only", False)
        add_trace(
            actor="BuyerAgent",
            action="PARSE_INTENT",
            status="SUCCESS",
            summary=f"Parsed intent: Target categories: {parsed_intent['target_categories']}, Target SKUs: {parsed_intent['target_skus']}, Effective budget: ₹{parsed_intent['effective_budget']:,.2f}",
            payload=parsed_intent
        )

        # ----------------------------------------------------
        # STEP 2: MCP Catalog Discovery (Buyer Agent)
        # ----------------------------------------------------
        if parsed_intent.get("quantity_unsupported") or parsed_intent.get("unresolved_clauses") or set(parsed_intent.get("requested_families", [])) & set(parsed_intent.get("excluded_families", [])):
            add_trace("BuyerAgent", "VALIDATE_PURCHASE_INTENT", "GATED", "Clarify the request before pricing or checkout.", parsed_intent)
            return AgentWorkflowResponse(workflow_id=workflow_id, user_goal=request.user_goal, status="NEEDS_CLARIFICATION", steps=steps, explainability_card={"title": "Purchase request needs clarification", "status": "NEEDS_CLARIFICATION", "reasoning": "Specify supported catalog products without conflicting exclusions. This workflow currently supports one unit per requested product family; multiple-unit requests cannot be fulfilled safely.", "recommendation": "Request one item per family, or use an exact catalog SKU. No quote or payment order was created."})
        discovered_products = await self.buyer_agent.execute_catalog_discovery(db, parsed_intent)
        if not discovered_products:
            add_trace(
                actor="BuyerAgent",
                action="MCP_CATALOG_QUERY",
                status="FAILED",
                summary=f"No matching in-stock inventory found in MCP catalog for '{request.user_goal}'.",
                payload={"parsed_intent": parsed_intent}
            )
            return AgentWorkflowResponse(
                workflow_id=workflow_id,
                user_goal=request.user_goal,
                status="FAILED_ROLLED_BACK",
                steps=steps,
                explainability_card={
                    "title": "Item Not Available in Merchant Catalog",
                    "reasoning": f"No matching SKU or in-stock item was found in the connected merchant's MCP catalog for '{request.user_goal}'.",
                    "status": "UNAVAILABLE_INVENTORY",
                    "recommendation": "This merchant specializes in Computer Displays, Ergonomic Keyboards & Mice, GIGABYTE Motherboards, ANC Audio, USB-C Hubs, Desk Mats, Coffee Subscriptions, and GPU Compute Packs.",
                    "violations": [f"UNMATCHED_INVENTORY: The requested item is not sold by this merchant or is currently out of stock."]
                }
            )

        found_skus = [p.sku for p in discovered_products]
        add_trace(
            actor="BuyerAgent",
            action="MCP_CATALOG_QUERY",
            status="SUCCESS",
            summary=f"Discovered {len(discovered_products)} candidate item(s) in catalog: {', '.join(p.name for p in discovered_products)}",
            payload={"discovered_skus": found_skus, "product_count": len(discovered_products)}
        )

        # ----------------------------------------------------
        # STEP 3: Dynamic Quote Generation (Merchant Growth Agent)
        # ----------------------------------------------------
        buyer_ctx = BuyerContext(
            budget_cap_inr=effective_budget,
            strict_items_only=strict_items,
            allow_autonomous_upsell=request.allow_autonomous_upsell
        )
        quote_req = DynamicQuoteRequest(
            buyer_agent_id="agent_aarav_99",
            requested_skus=found_skus,
            buyer_context=buyer_ctx,
            preferred_growth_model=request.force_growth_model
        )

        quote = await self.merchant_agent.generate_dynamic_quote(db, quote_req)
        add_trace(
            actor="MerchantGrowthAgent",
            action="GENERATE_DYNAMIC_QUOTE",
            status="SUCCESS",
            summary=f"Generated quote #{quote.quote_id} deploying Growth Model: '{quote.applied_growth_model}'. Total: ₹{quote.final_total:,.2f} (Savings: ₹{quote.discount_total:,.2f}, Merchant Margin: {quote.merchant_gross_margin_pct * 100:.1f}%)",
            payload=quote.model_dump()
        )

        # ----------------------------------------------------
        # STEP 4: Buyer AI Shield (Upsell & Strict Filter Evaluation)
        # ----------------------------------------------------
        has_rejections, rejected_skus, shield_reason = self.buyer_agent.evaluate_upsell_shield(
            offered_items=[i.model_dump() for i in quote.items],
            strict_items_only=strict_items,
            requested_skus=found_skus
        )

        if has_rejections:
            add_trace(
                actor="BuyerAgent",
                action="UPSELL_SHIELD_EVALUATION",
                status="WARNING",
                summary=f"Shield Activated: Rejected unrequested add-ons {rejected_skus}. Reason: {shield_reason}",
                payload={"rejected_skus": rejected_skus, "reason": shield_reason}
            )
            # Re-negotiate quote without rejected add-on, falling back to Model 2 (Conversion Closer)
            filtered_skus = [s for s in found_skus if s not in rejected_skus]
            quote_req.requested_skus = filtered_skus
            quote_req.preferred_growth_model = "conversion_closer"
            quote = await self.merchant_agent.generate_dynamic_quote(db, quote_req)
            add_trace(
                actor="MerchantGrowthAgent",
                action="GRACEFUL_QUOTE_RENEGOTIATION",
                status="SUCCESS",
                summary=f"Re-negotiated quote #{quote.quote_id} without accessories. Applied Model 2 (Conversion Closer 2.5% discount). Final Total: ₹{quote.final_total:,.2f}",
                payload=quote.model_dump()
            )
        else:
            add_trace(
                actor="BuyerAgent",
                action="UPSELL_SHIELD_EVALUATION",
                status="SUCCESS",
                summary="Upsell Shield check passed. All items match buyer intent.",
                payload={"items": [i.model_dump() for i in quote.items]}
            )

        # ----------------------------------------------------
        # STEP 5: Policy Guard & HITL Gating
        # ----------------------------------------------------
        policy_result = await self.policy_guard.evaluate_quote(
            db=db,
            quote=quote,
            user_override_budget=effective_budget
        )

        add_trace(
            actor="PolicyGuard",
            action="POLICY_EVALUATION",
            status="SUCCESS" if policy_result.can_proceed_autonomously else "GATED",
            summary=f"Policy Tier: {policy_result.tier}. Compliance: {'APPROVED' if policy_result.can_proceed_autonomously else 'GATED (HITL Required)'}. Violations: {len(policy_result.violations)}",
            payload=policy_result.model_dump()
        )

        # ----------------------------------------------------
        # BRANCH: GATED (Tier 2 / 3 HITL Interrupt)
        # ----------------------------------------------------
        if policy_result.hitl_required:
            add_trace(
                actor="Supervisor",
                action="HITL_INTERRUPT_TRIGGERED",
                status="GATED",
                summary=f"Multi-Agent Execution Halted. Created HITL Gate #{policy_result.hitl_gate_id}. Waiting for human 1-click authorization.",
                payload={"gate_id": policy_result.hitl_gate_id, "violations": policy_result.violations}
            )

            # Log audit trail for gate
            await AuditLedgerEngine.append_entry(
                db=db,
                actor="PolicyGuard",
                action="HITL_GATE_TRIGGERED",
                payload={
                    "workflow_id": workflow_id,
                    "gate_id": policy_result.hitl_gate_id,
                    "quote_id": quote.quote_id,
                    "total_amount": quote.final_total,
                    "tier": policy_result.tier,
                    "violations": policy_result.violations
                }
            )

            return AgentWorkflowResponse(
                workflow_id=workflow_id,
                user_goal=request.user_goal,
                status="GATED_HITL",
                steps=steps,
                quote=quote,
                policy_result=policy_result,
                explainability_card=policy_result.explainability_card,
                hitl_gate_id=policy_result.hitl_gate_id,
                total_spent=quote.final_total,
                total_saved=quote.discount_total
            )

        # ----------------------------------------------------
        # SIMULATE STOCK RACE CONDITION (Chaos Scenario 2)
        # ----------------------------------------------------
        if request.simulate_stock_race:
            add_trace(
                actor="Supervisor",
                action="STOCK_RACE_CONDITION_DETECTED",
                status="FAILED",
                summary="Atomic Stock Lock Failed: Item was reserved or depleted by a competing buyer agent before checkout confirmation.",
                payload={"error": "INSUFFICIENT_STOCK_RACE_CONDITION"}
            )
            # Log rollback in audit ledger
            await AuditLedgerEngine.append_entry(
                db=db,
                actor="Supervisor",
                action="TRANSACTION_ROLLED_BACK",
                payload={
                    "workflow_id": workflow_id,
                    "reason": "STOCK_RACE_CONDITION_DETECTED",
                    "quote_id": quote.quote_id,
                    "rollback_status": "FUNDS_HELD_RELEASED_CLEANLY"
                }
            )
            return AgentWorkflowResponse(
                workflow_id=workflow_id,
                user_goal=request.user_goal,
                status="FAILED_ROLLED_BACK",
                steps=steps,
                quote=quote,
                policy_result=policy_result,
                explainability_card={
                    "title": "Inventory Race Condition Handled Gracefully",
                    "status": "ROLLED_BACK",
                    "reason": "Selected product inventory reached 0 right before checkout settlement. No funds were debited, orphaned Razorpay charge prevented.",
                    "recovery": "Agent released quote and recommended available in-stock alternatives."
                },
                total_spent=0.0,
                total_saved=0.0
            )

        # ----------------------------------------------------
        # STEP 6: Razorpay Order Creation (Tier 1 Autonomous)
        # ----------------------------------------------------
        rzp_order_req = RazorpayCreateOrderRequest(
            quote_id=quote.quote_id,
            amount_inr=quote.final_total,
            currency="INR",
            buyer_agent_id="agent_aarav_99",
            notes={
                "workflow_id": workflow_id,
                "growth_model": quote.applied_growth_model,
                "merchant_margin": f"{quote.merchant_gross_margin_pct * 100:.1f}%"
            }
        )

        rzp_order = await self.settlement_agent.create_order(
            db=db,
            request=rzp_order_req,
            items_payload=[i.model_dump() for i in quote.items],
            growth_model=quote.applied_growth_model,
            discount_amount=quote.discount_total,
            warranty_amount=quote.warranty_total,
            explainability=quote.explainability_note
        )

        add_trace(
            actor="RazorpaySettlementAgent",
            action="CREATE_RAZORPAY_ORDER",
            status="SUCCESS",
            summary=f"Created Razorpay Order {rzp_order.razorpay_order_id} (₹{quote.final_total:,.2f} / {rzp_order.amount_in_paise} paise). Payment link ready.",
            payload=rzp_order.model_dump()
        )

        # ----------------------------------------------------
        # STEP 7: Audit Ledger Commit (SHA-256 Hash Chain)
        # ----------------------------------------------------
        audit_entry = await AuditLedgerEngine.append_entry(
            db=db,
            actor="CommerceSupervisor",
            action="AUTONOMOUS_CHECKOUT_CONFIRMED",
            payload={
                "workflow_id": workflow_id,
                "quote_id": quote.quote_id,
                "razorpay_order_id": rzp_order.razorpay_order_id,
                "amount": quote.final_total,
                "growth_model": quote.applied_growth_model,
                "discount": quote.discount_total,
                "policy_tier": policy_result.tier
            }
        )

        add_trace(
            actor="CommerceSupervisor",
            action="AUDIT_LEDGER_COMMIT",
            status="SUCCESS",
            summary=f"Committed block #{audit_entry.sequence_number} to Cryptographic Audit Ledger. Entry Hash: {audit_entry.entry_hash[:16]}...",
            payload={
                "sequence_number": audit_entry.sequence_number,
                "entry_hash": audit_entry.entry_hash,
                "prev_hash": audit_entry.prev_hash
            }
        )

        return AgentWorkflowResponse(
            workflow_id=workflow_id,
            user_goal=request.user_goal,
            status="COMPLETED_AUTONOMOUS",
            steps=steps,
            quote=quote,
            policy_result=policy_result,
            razorpay_order=rzp_order,
            explainability_card=policy_result.explainability_card,
            audit_entry_hash=audit_entry.entry_hash,
            total_spent=quote.final_total,
            total_saved=quote.discount_total
        )

    async def resume_hitl_workflow(
        self,
        db: AsyncSession,
        gate_id: str,
        action: str,  # "APPROVE", "REJECT", "ADJUST_BUDGET"
        adjusted_budget: Optional[float] = None
    ) -> Dict[str, Any]:
        """Resumes execution of a halted HITL checkpoint."""
        gate_query = select(HITLApprovalQueue).where(HITLApprovalQueue.id == gate_id)
        res = await db.execute(gate_query)
        gate = res.scalar_one_or_none()

        if not gate:
            return {"success": False, "message": f"HITL Gate {gate_id} not found."}

        if gate.status != "PENDING":
            return {"success": False, "message": f"Gate {gate_id} already resolved as {gate.status}."}

        gate_details = json.loads(gate.details_json or "{}")
        quote_dict = gate_details.get("quote", {})

        if action == "REJECT":
            gate.status = "REJECTED"
            gate.resolved_at = datetime.datetime.utcnow()
            await db.commit()
            
            await AuditLedgerEngine.append_entry(
                db=db,
                actor="HumanUser",
                action="HITL_GATE_REJECTED",
                payload={"gate_id": gate_id, "reason": "User rejected over-budget or unrequested item escalation."}
            )
            return {
                "success": True,
                "status": "REJECTED",
                "message": "Transaction was rejected by human operator. State safely cancelled without charges."
            }

        # APPROVE or ADJUST_BUDGET
        gate.status = "APPROVED"
        gate.resolved_at = datetime.datetime.utcnow()
        await db.commit()

        # Log Human Approval to Audit Ledger
        await AuditLedgerEngine.append_entry(
            db=db,
            actor="HumanUser",
            action="HITL_GATE_APPROVED",
            payload={
                "gate_id": gate_id,
                "action": action,
                "adjusted_budget": adjusted_budget,
                "amount": quote_dict.get("final_total", 0.0)
            }
        )

        # Create Razorpay Order
        rzp_order_req = RazorpayCreateOrderRequest(
            quote_id=quote_dict.get("quote_id", f"q_{uuid.uuid4().hex[:8]}"),
            amount_inr=quote_dict.get("final_total", 0.0),
            currency="INR",
            buyer_agent_id=gate.buyer_agent_id,
            notes={
                "hitl_gate_id": gate_id,
                "resolution": "HUMAN_OVERRIDE_APPROVED"
            }
        )

        rzp_order = await self.settlement_agent.create_order(
            db=db,
            request=rzp_order_req,
            items_payload=quote_dict.get("items", []),
            growth_model=quote_dict.get("applied_growth_model", "hitl_approved"),
            discount_amount=quote_dict.get("discount_total", 0.0),
            warranty_amount=quote_dict.get("warranty_total", 0.0),
            explainability=f"Authorized via Human 1-Click HITL Gate #{gate_id}"
        )

        return {
            "success": True,
            "status": "APPROVED",
            "message": "Human approval confirmed. Razorpay order created successfully.",
            "razorpay_order": rzp_order.model_dump(),
            "next_step": "TRIGGER_CHECKOUT_MODAL"
        }
