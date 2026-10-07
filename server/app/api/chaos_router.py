from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.chaos.chaos_service import ChaosResilienceService
from app.schemas.agent_schemas import (
    ChaosScenarioRequest,
    AgentWorkflowResponse
)

router = APIRouter(prefix="/chaos", tags=["Chaos & Failure Resilience Lab"])

@router.post("/trigger", response_model=AgentWorkflowResponse)
async def trigger_chaos_scenario(
    request: ChaosScenarioRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers one of the 3 critical evaluation failure scenarios:
    - `budget_breach`: Budget Cap Exceeded -> Tier 2 HITL Gate
    - `stock_race_condition`: Inventory Depleted -> Atomic Rollback
    - `strict_upsell_rejection`: Unrequested Upsell -> Buyer AI Shield & Dynamic Fallback
    """
    return await ChaosResilienceService.run_scenario(db, request.scenario_id)
