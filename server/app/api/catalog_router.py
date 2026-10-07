from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.catalog.catalog_service import CatalogService
from app.schemas.agent_schemas import (
    CatalogQueryRequest,
    CatalogProductResponse
)

router = APIRouter(prefix="/catalog", tags=["Catalog & MCP Discovery"])

@router.post("/agent-query", response_model=List[CatalogProductResponse])
async def agent_query_catalog(
    request: CatalogQueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Standardized Agent-Readable MCP Catalog Discovery Endpoint.
    Returns JSON-LD structured products filtered by specs, price bounds, and stock.
    """
    products = await CatalogService.query_catalog(
        db=db,
        category=request.category,
        query_text=request.query_text,
        specs=request.specs,
        max_price=request.max_price_inr,
        in_stock_only=request.in_stock_only
    )
    return [CatalogService.to_schema(p) for p in products]

@router.get("/products", response_model=List[CatalogProductResponse])
async def list_all_products(db: AsyncSession = Depends(get_db)):
    """Retrieves all merchant catalog products."""
    products = await CatalogService.get_all_products(db)
    return [CatalogService.to_schema(p) for p in products]

@router.patch("/products/{sku}", response_model=CatalogProductResponse)
async def update_product_inventory(
    sku: str,
    stock_quantity: Optional[int] = Body(None),
    retail_price: Optional[float] = Body(None),
    cost_price: Optional[float] = Body(None),
    db: AsyncSession = Depends(get_db)
):
    """Updates product stock and pricing in real time."""
    updated = await CatalogService.update_inventory(
        db=db,
        sku=sku,
        stock_quantity=stock_quantity,
        retail_price=retail_price,
        cost_price=cost_price
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Product SKU '{sku}' not found.")
    return CatalogService.to_schema(updated)
