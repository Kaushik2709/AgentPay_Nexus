from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.supervisor import CommerceSupervisorAgent
from app.schemas.agent_schemas import AgentWorkflowRequest, AgentWorkflowResponse

class ChaosResilienceService:
    """
    Failure & Chaos Testbed Service.
    Demonstrates deterministic resilience across the 3 critical evaluation cases:
    1. Budget Cap Breach & HITL Escalation
    2. Stock Race Condition & Atomic Rollback
    3. Unrequested Upsell Shield Rejection & Graceful Fallback
    """
    @staticmethod
    async def run_scenario(
        db: AsyncSession,
        scenario_id: str
    ) -> AgentWorkflowResponse:
        supervisor = CommerceSupervisorAgent()

        if scenario_id == "budget_breach":
            # Each item fits discovery; the combined cart exceeds the budget.
            req = AgentWorkflowRequest(
                user_goal="Buy me a 4K monitor and ergonomic keyboard",
                budget_cap_inr=20000.0,  # Below combined price (~₹23,000)
                strict_items_only=False,
                allow_autonomous_upsell=False
            )
            return await supervisor.execute_workflow(db, req)

        elif scenario_id == "stock_race_condition":
            # Scenario 2: Stock Race condition trigger
            req = AgentWorkflowRequest(
                user_goal="Buy StudioMaster Pro ANC Wireless Studio Headphones",
                budget_cap_inr=15000.0,
                strict_items_only=True,
                allow_autonomous_upsell=False,
                simulate_stock_race=True
            )
            return await supervisor.execute_workflow(db, req)

        elif scenario_id == "strict_upsell_rejection":
            # Scenario 3: User specifies strict items only, Merchant attempts value services upsell, Buyer AI shields user
            req = AgentWorkflowRequest(
                user_goal="Buy only a 4K UHD monitor",
                budget_cap_inr=25000.0,
                strict_items_only=True,  # Shield active!
                allow_autonomous_upsell=False,
                force_growth_model="value_services"  # Force merchant to attempt warranty add-on
            )
            return await supervisor.execute_workflow(db, req)

        else:
            # Default normal flow
            req = AgentWorkflowRequest(
                user_goal="Buy 4K UHD monitor and ergonomic keyboard under ₹25,000",
                budget_cap_inr=25000.0,
                strict_items_only=False,
                allow_autonomous_upsell=False
            )
            return await supervisor.execute_workflow(db, req)
