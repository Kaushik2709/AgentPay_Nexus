import json
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.models import Product
from app.schemas.agent_schemas import CatalogProductResponse

class CatalogService:
    @staticmethod
    async def query_catalog(
        db: AsyncSession,
        category: Optional[str] = None,
        query_text: Optional[str] = None,
        specs: Optional[Dict[str, Any]] = None,
        max_price: Optional[float] = None,
        in_stock_only: bool = True
    ) -> List[Product]:
        query = select(Product)
        
        if category:
            query = query.where(Product.category == category.lower())
            
        if in_stock_only:
            query = query.where(Product.stock_quantity > 0)
            
        if max_price is not None:
            query = query.where(Product.retail_price <= max_price)
            
        result = await db.execute(query)
        products = result.scalars().all()
        
        filtered: List[Product] = []
        for p in products:
            # Full-text / substring match if requested
            if query_text:
                q = query_text.lower()
                matches_name = q in p.name.lower()
                matches_desc = q in p.description.lower()
                matches_cat = q in p.category.lower()
                if not (matches_name or matches_desc or matches_cat):
                    continue
            
            # Spec filtering
            if specs:
                p_specs = json.loads(p.specifications or "{}")
                match_specs = True
                for k, v in specs.items():
                    if k in p_specs:
                        if str(v).lower() not in str(p_specs[k]).lower():
                            match_specs = False
                            break
                if not match_specs:
                    continue
                    
            filtered.append(p)
            
        return filtered

    @staticmethod
    async def get_product_by_sku(db: AsyncSession, sku: str) -> Optional[Product]:
        query = select(Product).where(Product.sku == sku)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_products(db: AsyncSession) -> List[Product]:
        query = select(Product).order_by(Product.id.asc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def reserve_and_decrement_stock(db: AsyncSession, sku: str, quantity: int = 1) -> bool:
        """Atomically validates and decrements stock. Returns False if insufficient stock."""
        product = await CatalogService.get_product_by_sku(db, sku)
        if not product or product.stock_quantity < quantity:
            return False
        
        product.stock_quantity -= quantity
        await db.commit()
        await db.refresh(product)
        return True

    @staticmethod
    async def release_stock(db: AsyncSession, sku: str, quantity: int = 1) -> bool:
        """Atomically restores stock in case of transaction rollback."""
        product = await CatalogService.get_product_by_sku(db, sku)
        if not product:
            return False
        
        product.stock_quantity += quantity
        await db.commit()
        await db.refresh(product)
        return True

    @staticmethod
    async def update_inventory(
        db: AsyncSession,
        sku: str,
        stock_quantity: Optional[int] = None,
        retail_price: Optional[float] = None,
        cost_price: Optional[float] = None
    ) -> Optional[Product]:
        product = await CatalogService.get_product_by_sku(db, sku)
        if not product:
            return None
        
        if stock_quantity is not None:
            product.stock_quantity = stock_quantity
        if retail_price is not None:
            product.retail_price = retail_price
        if cost_price is not None:
            product.cost_price = cost_price
            
        await db.commit()
        await db.refresh(product)
        return product

    @staticmethod
    def to_schema(product: Product) -> CatalogProductResponse:
        return CatalogProductResponse(
            id=product.id,
            sku=product.sku,
            name=product.name,
            category=product.category,
            description=product.description,
            specifications=json.loads(product.specifications or "{}"),
            retail_price=product.retail_price,
            cost_price=product.cost_price,
            stock_quantity=product.stock_quantity,
            upgrade_to_sku=product.upgrade_to_sku,
            upgrade_bundle_discount=product.upgrade_bundle_discount or 0.0,
            warranty_price=product.warranty_price or 0.0,
            json_ld_schema=json.loads(product.json_ld_schema or "{}"),
            is_subscription=product.is_subscription
        )
