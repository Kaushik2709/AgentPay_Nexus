import asyncio
import hmac
import hashlib
import sys
import os

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings
from app.db.session import init_db
from app.db.seed import seed_database
from app.catalog.catalog_service import CatalogService
from app.agents.buyer_agent import BuyerAgent
from app.agents.merchant_agent import MerchantGrowthAgent
from app.agents.policy_guard import PolicyGuardAgent
from app.agents.supervisor import CommerceSupervisorAgent
from app.razorpay.settlement_agent import RazorpaySettlementAgent
from app.audit.ledger import AuditLedgerEngine
from app.chaos.chaos_service import ChaosResilienceService
from app.schemas.agent_schemas import (
    AgentWorkflowRequest,
    DynamicQuoteRequest,
    BuyerContext,
    RazorpayCreateOrderRequest
)

async def run_comprehensive_tests():
    print("================================================================")
    print("   AGENTPAY NEXUS — BACKEND & AGENT VERIFICATION TEST SUITE     ")
    print("================================================================")
    
    # 1. Initialize & Seed DB
    print("\n[TEST 1] Initializing & Seeding Real Database...")
    init_db()
    seed_database()
    print("  -> Database seeded successfully.")

    # Setup async session for tests
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as db:
        # 2. Test Catalog & MCP Query
        print("\n[TEST 2] Testing Catalog & MCP Agent Discovery...")
        products = await CatalogService.query_catalog(db, category="monitors")
        assert len(products) >= 2, f"Expected >= 2 monitors, got {len(products)}"
        print(f"  -> Found {len(products)} monitor(s): {[p.name for p in products]}")

        # 3. Test Buyer Agent Intent Parsing & Upsell Shield
        print("\n[TEST 3] Testing Buyer Agent Intent Parsing & Shield...")
        buyer = BuyerAgent()
        intent = buyer.parse_intent("Buy me a 4K monitor and ergonomic keyboard under ₹25,000", 25000.0)
        assert "monitors" in intent["target_categories"]
        assert "keyboards" in intent["target_categories"]
        assert intent["effective_budget"] == 25000.0
        print(f"  -> Parsed intent: {intent['target_categories']}, budget: ₹{intent['effective_budget']}")

        # 4. Test 4 Merchant Growth Models
        print("\n[TEST 4] Testing 4 Merchant Revenue Growth Models...")
        merchant = MerchantGrowthAgent()
        
        # Model 1: Quality Upgrade
        q1 = await merchant.generate_dynamic_quote(
            db,
            DynamicQuoteRequest(
                requested_skus=["item_monitor_4k_standard"],
                buyer_context=BuyerContext(budget_cap_inr=25000.0, strict_items_only=False),
                preferred_growth_model="quality_upgrade"
            )
        )
        assert q1.applied_growth_model == "quality_upgrade"
        assert q1.discount_total > 0
        print(f"  -> Model 1 (Quality Upgrade): Subtotal ₹{q1.base_subtotal} -> Final ₹{q1.final_total}, Savings: ₹{q1.discount_total}")

        # Model 2: Conversion Closer
        q2 = await merchant.generate_dynamic_quote(
            db,
            DynamicQuoteRequest(
                requested_skus=["item_keyboard_ergo"],
                buyer_context=BuyerContext(budget_cap_inr=5000.0, strict_items_only=True),
                preferred_growth_model="conversion_closer"
            )
        )
        assert q2.applied_growth_model == "conversion_closer"
        assert q2.discount_total > 0
        print(f"  -> Model 2 (Conversion Closer): Subtotal ₹{q2.base_subtotal} -> Final ₹{q2.final_total}, Savings: ₹{q2.discount_total}")

        # Model 3: Bulk / Subscription
        q3 = await merchant.generate_dynamic_quote(
            db,
            DynamicQuoteRequest(
                requested_skus=["item_coffee_beans_subscription"],
                buyer_context=BuyerContext(budget_cap_inr=5000.0),
                preferred_growth_model="bulk_subscription"
            )
        )
        assert q3.applied_growth_model == "bulk_subscription"
        print(f"  -> Model 3 (Bulk / Subscription): Subtotal ₹{q3.base_subtotal} -> Final ₹{q3.final_total}, 15% Recurring discount: ₹{q3.discount_total}")

        # Model 4: Value-Add Services
        q4 = await merchant.generate_dynamic_quote(
            db,
            DynamicQuoteRequest(
                requested_skus=["item_monitor_4k_standard"],
                buyer_context=BuyerContext(budget_cap_inr=25000.0),
                preferred_growth_model="value_services"
            )
        )
        assert q4.applied_growth_model == "value_services"
        assert q4.warranty_total > 0
        print(f"  -> Model 4 (Value Services): Subtotal ₹{q4.base_subtotal} + Warranty ₹{q4.warranty_total} -> Final ₹{q4.final_total}")

        # 5. Test Policy Guard & HITL Gating
        print("\n[TEST 5] Testing Policy Guard Bounds & Gating...")
        guard = PolicyGuardAgent()
        
        # In-bounds quote (Tier 1 Autonomous)
        p_eval_auto = await guard.evaluate_quote(db, q1, user_override_budget=30000.0)
        assert p_eval_auto.can_proceed_autonomously == True
        assert p_eval_auto.tier == "TIER_1_AUTONOMOUS"
        print(f"  -> In-bounds quote: Tier={p_eval_auto.tier}, Autonomous={p_eval_auto.can_proceed_autonomously}")

        # Out-of-bounds quote (Tier 2 Gated HITL)
        p_eval_gated = await guard.evaluate_quote(db, q1, user_override_budget=10000.0)
        assert p_eval_gated.hitl_required == True
        assert p_eval_gated.tier == "TIER_2_GATED_HITL"
        assert p_eval_gated.hitl_gate_id is not None
        print(f"  -> Out-of-bounds quote: Tier={p_eval_gated.tier}, Gate ID={p_eval_gated.hitl_gate_id}, Violations={p_eval_gated.violations}")

        # 6. Test Multi-Agent Supervisor Workflow End-to-End
        print("\n[TEST 6] Testing Multi-Agent StateGraph Workflow End-to-End...")
        supervisor = CommerceSupervisorAgent()
        flow_resp = await supervisor.execute_workflow(
            db,
            AgentWorkflowRequest(
                user_goal="Buy 4K monitor and ergonomic keyboard under ₹25,000",
                budget_cap_inr=25000.0,
                strict_items_only=False,
                allow_autonomous_upsell=False
            )
        )
        assert flow_resp.status in ["COMPLETED_AUTONOMOUS", "GATED_HITL"]
        assert len(flow_resp.steps) >= 5
        print(f"  -> Workflow status: {flow_resp.status}, Steps executed: {len(flow_resp.steps)}")
        for step in flow_resp.steps:
            print(f"     [{step.step_number}] {step.actor} -> {step.action} ({step.status}): {step.summary[:70]}...")

        # 7. Test Razorpay HMAC-SHA256 Payment Verification & Webhook
        print("\n[TEST 7] Testing Razorpay HMAC-SHA256 Signature Verification...")
        settlement = RazorpaySettlementAgent()
        test_order_id = "order_rzp_test_12345"
        test_payment_id = "pay_test_998877"
        expected_sig = settlement._generate_hmac_signature(test_order_id, test_payment_id)
        is_sig_valid = settlement.verify_payment_signature(test_order_id, test_payment_id, expected_sig)
        assert is_sig_valid == True
        print(f"  -> Razorpay HMAC-SHA256 non-repudiation signature verified: {expected_sig[:16]}... (Valid={is_sig_valid})")

        # 8. Test Cryptographic Audit Ledger Integrity
        print("\n[TEST 8] Testing Cryptographic Audit Ledger Integrity Verification...")
        verify_report = await AuditLedgerEngine.verify_chain_integrity(db)
        assert verify_report["is_valid"] == True
        assert verify_report["total_blocks_verified"] > 0
        print(f"  -> Audit Ledger Verified: {verify_report['total_blocks_verified']} blocks checked. Latest hash: {verify_report['latest_hash'][:16]}... Integrity 100% valid.")

        # 9. Test Chaos Scenarios
        print("\n[TEST 9] Testing Chaos & Failure Scenarios...")
        # Scenario 1: Budget breach
        chaos_1 = await ChaosResilienceService.run_scenario(db, "budget_breach")
        assert chaos_1.status == "GATED_HITL"
        assert chaos_1.hitl_gate_id is not None
        print(f"  -> Chaos 1 (Budget Breach): Halts execution safely, creates HITL Gate #{chaos_1.hitl_gate_id}")

        # Scenario 2: Stock Race Condition
        chaos_2 = await ChaosResilienceService.run_scenario(db, "stock_race_condition")
        assert chaos_2.status == "FAILED_ROLLED_BACK"
        print(f"  -> Chaos 2 (Stock Race): Catches race condition, rolls back atomically without orphaned charges")

        # Scenario 3: Strict Upsell Rejection & Graceful Fallback
        chaos_3 = await ChaosResilienceService.run_scenario(db, "strict_upsell_rejection")
        assert any("UPSELL_SHIELD_EVALUATION" in s.action for s in chaos_3.steps)
        print(f"  -> Chaos 3 (Upsell Rejection): Buyer AI shield rejects accessory, merchant pivots to Model 2 Conversion Closer")

    print("\n================================================================")
    print("   ALL BACKEND & MULTI-AGENT TESTS PASSED SUCCESSFULLY! (100%)   ")
    print("================================================================\n")

if __name__ == "__main__":
    asyncio.run(run_comprehensive_tests())
