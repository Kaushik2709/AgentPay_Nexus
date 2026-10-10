from typing import List, Dict, Any
import json
import datetime
import hashlib
import uuid
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import HITLApprovalQueue
from app.db.models import WorkflowRun, Quote, Order
from app.auth import buyer_id, identity, is_admin
from app.commerce import write_transaction, persist_quote
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
    request.buyer_agent_id = buyer_id()
    await write_transaction(db)
    try:
        quote = await merchant_agent.generate_dynamic_quote(db, request)
        await persist_quote(db, quote, request.buyer_context.budget_cap_inr)
        await db.commit()
        return quote
    except ValueError as error:
        await db.rollback()
        raise HTTPException(422, str(error)) from error

@router.post("/orchestrate", response_model=AgentWorkflowResponse)
async def orchestrate_agent_workflow(
    request: AgentWorkflowRequest,
    db: AsyncSession = Depends(get_db),
    idempotency_key: str = Header(None)
):
    """
    Executes the full Multi-Agent StateGraph workflow.
    Supervisor delegates to BuyerAgent, MerchantGrowthAgent, PolicyGuard, and SettlementAgent.
    """
    supervisor = CommerceSupervisorAgent()
    if identity.get() and request.simulate_stock_race and not is_admin():
        raise HTTPException(403, "Scenario simulation requires administrator access.")
    run = None
    if db is not None:
        if idempotency_key and (len(idempotency_key) > 100 or not idempotency_key.replace("-", "").isalnum()):
            raise HTTPException(422, "Invalid idempotency key.")
        key = hashlib.sha256(f"{buyer_id()}:{idempotency_key or uuid.uuid4().hex}".encode()).hexdigest()
        request_hash = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
        await write_transaction(db)
        run = await db.get(WorkflowRun, key)
        if run:
            if run.request_hash != request_hash:
                raise HTTPException(409, "Idempotency key was used for a different request.")
            if run.result_json:
                result = json.loads(run.result_json)
                if "error" in result:
                    raise HTTPException(result.get("status", 409), result["error"])
                return AgentWorkflowResponse(**result)
            raise HTTPException(409, "This request is already running or needs reconciliation. Check order history.")
        run = WorkflowRun(id=key, buyer_agent_id=buyer_id(), request_hash=request_hash)
        db.add(run)
        await db.commit()
    try:
        response = await supervisor.execute_workflow(db, request)
        if run:
            run.status = response.status
            run.result_json = response.model_dump_json()
            await db.commit()
        return response
    except ValueError as error:
        if db is not None:
            await db.rollback()
            stored_run = await db.get(WorkflowRun, key)
            if stored_run:
                stored_run.status = "FAILED"
                stored_run.result_json = json.dumps({"error": str(error), "status": 422})
                await db.commit()
        raise HTTPException(status_code=422, detail=str(error)) from error
    except HTTPException as error:
        if db is not None:
            await db.rollback()
            stored_run = await db.get(WorkflowRun, key)
            if stored_run:
                stored_run.status = "FAILED" if error.status_code < 500 else "RECONCILIATION_REQUIRED"
                stored_run.result_json = json.dumps({"error": error.detail, "status": error.status_code})
                await db.commit()
        raise

@router.get("/hitl/pending")
async def list_pending_hitl_gates(db: AsyncSession = Depends(get_db)):
    """Lists all pending HITL gated authorizations."""
    query = select(HITLApprovalQueue).where(HITLApprovalQueue.status == "PENDING").order_by(HITLApprovalQueue.created_at.desc())
    if identity.get():
        query = query.where(HITLApprovalQueue.buyer_agent_id == buyer_id())
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
        next_step=result.get("next_step", "COMPLETED"),
        razorpay_order=result.get("razorpay_order")
    )

@router.get("/orders")
async def list_orders(db: AsyncSession = Depends(get_db)):
    query = select(Order).where(Order.buyer_agent_id == buyer_id()).order_by(Order.created_at.desc()).limit(50)
    orders = (await db.execute(query)).scalars().all()
    output = []
    for order in orders:
        quote = await db.get(Quote, order.id)
        output.append({"id": order.id, "status": order.status, "amount_inr": order.total_amount,
            "razorpay_order_id": order.razorpay_order_id, "created_at": order.created_at.isoformat(),
            "checkout": json.loads(quote.checkout_json) if quote and quote.checkout_json and order.status == "CREATED" and quote.expires_at > datetime.datetime.utcnow() else None})
    return output
