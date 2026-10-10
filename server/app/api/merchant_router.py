import json
from typing import Optional, List, Literal
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.db.models import Merchant, Order, Product

router = APIRouter(prefix="/merchant", tags=["Merchant Revenue Dashboard"])

@router.get("/dashboard")
async def get_merchant_dashboard(
    merchant_id: str = "merchant_techgear_01",
    db: AsyncSession = Depends(get_db)
):
    """Returns merchant revenue growth configurations, active models, sales, and AOV metrics."""
    m_query = select(Merchant).where(Merchant.id == merchant_id)
    m_res = await db.execute(m_query)
    merchant = m_res.scalar_one_or_none()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found.")

    # Calculate real order revenue statistics from Orders table
    orders_query = select(Order).where(Order.merchant_id == merchant_id, Order.status == "PAID")
    o_res = await db.execute(orders_query)
    paid_orders = o_res.scalars().all()

    total_revenue = sum(o.total_amount for o in paid_orders)
    total_orders_count = len(paid_orders)
    avg_order_value = (total_revenue / total_orders_count) if total_orders_count > 0 else 0.0
    total_discounts_given = sum(o.discount_amount for o in paid_orders)

    # Product count and inventory health
    prod_query = select(func.count(Product.id), func.sum(Product.stock_quantity))
    p_res = await db.execute(prod_query)
    sku_count, total_units = p_res.first()

    return {
        "merchant_id": merchant.id,
        "name": merchant.name,
        "margin_floor_pct": merchant.margin_floor_pct,
        "active_growth_models": json.loads(merchant.active_growth_models or "[]"),
        "metrics": {
            "total_revenue_inr": total_revenue,
            "total_orders_completed": total_orders_count,
            "avg_order_value_inr": round(avg_order_value, 2),
            "total_discounts_granted_inr": total_discounts_given,
            "sku_count": sku_count or 0,
            "total_units_in_stock": total_units or 0
        },
        "growth_models_info": {
            "quality_upgrade": {
                "name": "Model 1: Quality Upgrade (Vertical Upsell)",
                "description": "Upgrades requested base items to higher-tier specifications when budget headroom exists, delivering higher AOV without physical clutter.",
                "target_margin": "25-35%"
            },
            "conversion_closer": {
                "name": "Model 2: Conversion Closer (Dynamic Anti-Abandonment)",
                "description": "Calculates margin floor and offers instant 2.5-4% autonomous discount to secure order closure on strict-intent buyers.",
                "target_margin": "Min 20% Floor"
            },
            "bulk_subscription": {
                "name": "Model 3: Bulk / Subscription (Future Recurring LTV)",
                "description": "Applies 15% discount for automated monthly replenishment commitments via UPI Autopay / Subscriptions.",
                "target_margin": "Long-term LTV"
            },
            "value_services": {
                "name": "Model 4: Value-Add Services & Protection",
                "description": "Subsidized 2-Year Express Warranty & Priority Care delivering 90% gross margins for merchant.",
                "target_margin": "90% Gross Margin"
            }
        }
    }

@router.post("/config")
async def update_merchant_config(
    margin_floor_pct: Optional[float] = Body(None, ge=0.05, le=0.50, allow_inf_nan=False),
    active_growth_models: Optional[List[Literal["quality_upgrade", "conversion_closer", "bulk_subscription", "value_services"]]] = Body(None),
    merchant_id: str = "merchant_techgear_01",
    db: AsyncSession = Depends(get_db)
):
    """Updates merchant profit margin floor and enabled growth models."""
    m_query = select(Merchant).where(Merchant.id == merchant_id)
    m_res = await db.execute(m_query)
    merchant = m_res.scalar_one_or_none()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found.")

    if margin_floor_pct is not None:
        merchant.margin_floor_pct = max(0.05, min(0.50, margin_floor_pct))
    if active_growth_models is not None:
        merchant.active_growth_models = json.dumps(active_growth_models)

    await db.commit()
    await db.refresh(merchant)

    return {
        "success": True,
        "merchant_id": merchant.id,
        "margin_floor_pct": merchant.margin_floor_pct,
        "active_growth_models": json.loads(merchant.active_growth_models or "[]")
    }
