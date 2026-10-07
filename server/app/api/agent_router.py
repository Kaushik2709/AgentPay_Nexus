from typing import List, Dict, Any
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import HITLApprovalQueue
from app.agents.merchant_agent import MerchantGrowthAgent
from app.agents.supervisor import CommerceSupervisorAgent
from app.schemas.agent_schemas import (
    DynamicQuoteRequest,
    DynamicQuoteResponse,
    AgentWorkflowRequest,
    AgentWorkflowResponse,
    HITLActionRequest,
    HITLActionResponse
)

router = APIRouter(prefix="/agent", tags=["Multi-Agent Orchestration"])

@router.post("/quote", response_model=DynamicQuoteResponse)
async def generate_quote(
    request: DynamicQuoteRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Direct Merchant Dynamic Quote Endpoint.
    Evaluates buyer constraints, margin floor, and applies one of the 4 Revenue Growth Models.
    """
    merchant_agent = MerchantGrowthAgent()
    return await merchant_agent.generate_dynamic_quote(db, request)

@router.post("/orchestrate", response_model=AgentWorkflowResponse)
async def orchestrate_agent_workflow(
    request: AgentWorkflowRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Executes the full Multi-Agent StateGraph workflow.
    Supervisor delegates to BuyerAgent, MerchantGrowthAgent, PolicyGuard, and SettlementAgent.
    """
    supervisor = CommerceSupervisorAgent()
    return await supervisor.execute_workflow(db, request)

@router.get("/hitl/pending")
async def list_pending_hitl_gates(db: AsyncSession = Depends(get_db)):
    """Lists all pending HITL gated authorizations."""
    query = select(HITLApprovalQueue).where(HITLApprovalQueue.status == "PENDING").order_by(HITLApprovalQueue.created_at.desc())
    res = await db.execute(query)
    gates = res.scalars().all()
    
    return [
        {
            "id": g.id,
            "gate_id": g.id,
            "order_id": g.order_id,
            "workflow_id": g.order_id,
            "buyer_agent_id": g.buyer_agent_id,
            "trigger_reason": g.trigger_reason,
            "status": g.status,
            "details": json.loads(g.details_json or "{}"),
            "quote_data": json.loads(g.details_json or "{}").get("quote", {}),
            "violations": json.loads(g.explainability_card_json or "{}").get("violations", [g.trigger_reason]),
            "explainability_card": json.loads(g.explainability_card_json or "{}"),
            "created_at": g.created_at.isoformat() if g.created_at else None
        }
        for g in gates
    ]

@router.post("/hitl/resume", response_model=HITLActionResponse)
async def resume_hitl_checkpoint(
    request: HITLActionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Resumes execution after Human-in-the-Loop decision (Approve, Reject, Adjust)."""
    supervisor = CommerceSupervisorAgent()
    result = await supervisor.resume_hitl_workflow(
        db=db,
        gate_id=request.gate_id,
        action=request.action,
        adjusted_budget=request.adjusted_budget
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "HITL action failed"))
    
    return HITLActionResponse(
        success=True,
        status=result.get("status", "RESOLVED"),
        message=result.get("message", "Success"),
        order_id=result.get("razorpay_order", {}).get("razorpay_order_id") if isinstance(result.get("razorpay_order"), dict) else None,
        next_step=result.get("next_step", "COMPLETED")
    )
