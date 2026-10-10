import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import Policy
from app.schemas.agent_schemas import PolicyUpdateRequest
from app.auth import user_id as authenticated_user_id

router = APIRouter(prefix="/policy", tags=["Safety & Policy Sentinel"])

@router.get("/config")
async def get_policy_config(
    user_id: str = "aarav_buyer_01",
    db: AsyncSession = Depends(get_db)
):
    """Fetches active user spending policies and boundaries."""
    user_id = authenticated_user_id()
    query = select(Policy).where(Policy.user_id == user_id)
    res = await db.execute(query)
    policy = res.scalar_one_or_none()
    
    if not policy:
        policy = Policy(id=f"policy_{user_id}", user_id=user_id)
        db.add(policy)
        await db.commit()
        await db.refresh(policy)
        
    return {
        "id": policy.id,
        "user_id": policy.user_id,
        "max_tx_amount": policy.max_tx_amount,
        "daily_velocity_cap": policy.daily_velocity_cap,
        "category_whitelist": json.loads(policy.category_whitelist or "[]"),
        "allow_autonomous_upsell": policy.allow_autonomous_upsell,
        "price_drift_tolerance_pct": policy.price_drift_tolerance_pct,
        "updated_at": policy.updated_at.isoformat() if policy.updated_at else None
    }

@router.put("/config")
async def update_policy_config(
    request: PolicyUpdateRequest,
    user_id: str = "aarav_buyer_01",
    db: AsyncSession = Depends(get_db)
):
    """Updates user spending policies and limits in real time."""
    user_id = authenticated_user_id()
    query = select(Policy).where(Policy.user_id == user_id)
    res = await db.execute(query)
    policy = res.scalar_one_or_none()
    
    if not policy:
        policy = Policy(id=f"policy_{user_id}", user_id=user_id)
        db.add(policy)

    if request.max_tx_amount is not None:
        policy.max_tx_amount = request.max_tx_amount
    if request.daily_velocity_cap is not None:
        policy.daily_velocity_cap = request.daily_velocity_cap
    if request.category_whitelist is not None:
        policy.category_whitelist = json.dumps(request.category_whitelist)
    if request.allow_autonomous_upsell is not None:
        policy.allow_autonomous_upsell = request.allow_autonomous_upsell
    if request.price_drift_tolerance_pct is not None:
        policy.price_drift_tolerance_pct = request.price_drift_tolerance_pct

    await db.commit()
    await db.refresh(policy)

    return {
        "success": True,
        "policy": {
            "id": policy.id,
            "user_id": policy.user_id,
            "max_tx_amount": policy.max_tx_amount,
            "daily_velocity_cap": policy.daily_velocity_cap,
            "category_whitelist": json.loads(policy.category_whitelist or "[]"),
            "allow_autonomous_upsell": policy.allow_autonomous_upsell,
            "price_drift_tolerance_pct": policy.price_drift_tolerance_pct
        }
    }
