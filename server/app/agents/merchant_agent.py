import hmac
import hashlib
import json
import uuid
import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.catalog.catalog_service import CatalogService
from app.db.models import Product, Merchant
from app.schemas.agent_schemas import (
    DynamicQuoteRequest,
    DynamicQuoteResponse,
    QuoteItem
)
from app.config import settings

class MerchantGrowthAgent:
    """
    Merchant Revenue Optimizer Engine.
    Implements the 4 AI Revenue Growth Models:
    1. Quality Upgrade (Vertical Upsell - Better product, not more products)
    2. Conversion Closer (Dynamic Anti-Abandonment Discount)
    3. Bulk / Subscription (Future LTV Lock-In)
    4. Value-Add Services & Protection (Digital Care / Warranty)
    """
    def __init__(self, merchant_id: str = "merchant_techgear_01"):
        self.merchant_id = merchant_id

    def _sign_quote(self, payload: Dict[str, Any], secret_key: str) -> str:
        """Signs the quote using HMAC-SHA256 for non-repudiation."""
        serialized = json.dumps(payload, sort_keys=True)
        return hmac.new(secret_key.encode("utf-8"), serialized.encode("utf-8"), hashlib.sha256).hexdigest()

    async def generate_dynamic_quote(
        self,
        db: AsyncSession,
        request: DynamicQuoteRequest
    ) -> DynamicQuoteResponse:
        # Load Merchant config
        merchant_query = select(Merchant).where(Merchant.id == self.merchant_id)
        m_res = await db.execute(merchant_query)
        merchant = m_res.scalar_one_or_none()
        margin_floor = merchant.margin_floor_pct if merchant else settings.DEFAULT_MERCHANT_MARGIN_FLOOR
        merchant_api_key = merchant.api_key if merchant else "sec_live_merchant_default"

        # Load requested products from DB
        requested_products: List[Product] = []
        for sku in request.requested_skus:
            p = await CatalogService.get_product_by_sku(db, sku)
            if p:
                requested_products.append(p)
            else:
                raise ValueError(f"Unknown requested SKU: {sku}")

        if len(set(request.requested_skus)) != len(request.requested_skus):
            raise ValueError("Duplicate SKUs are unsupported. Specify explicit quantities instead.")
        if not requested_products or any(p.stock_quantity <= 0 for p in requested_products):
            raise ValueError("Every requested product must be in stock.")

        if not requested_products:
            # Return empty baseline quote
            quote_id = f"q_{uuid.uuid4().hex[:12]}"
            return DynamicQuoteResponse(
                quote_id=quote_id,
                buyer_agent_id=request.buyer_agent_id,
                merchant_id=self.merchant_id,
                items=[],
                base_subtotal=0.0,
                discount_total=0.0,
                warranty_total=0.0,
                final_total=0.0,
                merchant_gross_margin_pct=0.0,
                applied_growth_model="standard",
                savings_breakdown="No products selected",
                merchant_signature="",
                explainability_note="No matching inventory found.",
                expires_at=(datetime.datetime.utcnow() + datetime.timedelta(minutes=15)).isoformat()
            )

        budget_cap = request.buyer_context.budget_cap_inr
        strict_items = request.buyer_context.strict_items_only
        allow_upsell = request.buyer_context.allow_autonomous_upsell
        forced_model = request.preferred_growth_model
        enabled = json.loads(merchant.active_growth_models) if merchant else ["quality_upgrade", "conversion_closer", "bulk_subscription", "value_services"]
        if forced_model and forced_model not in enabled:
            raise ValueError("This pricing strategy is disabled by the merchant.")

        # Calculate base metrics
        base_subtotal = sum(p.retail_price for p in requested_products)
        total_cost = sum(p.cost_price for p in requested_products)
        budget_headroom = budget_cap - base_subtotal

        # Strategy Decision Matrix
        selected_model = forced_model
        if not selected_model:
            # Check for subscriptions
            has_subscription = any(p.is_subscription for p in requested_products)
            if has_subscription:
                selected_model = "bulk_subscription"
            elif strict_items:
                # If strict items and headroom > 1500, attempt vertical quality upgrade
                can_upgrade = any(p.upgrade_to_sku for p in requested_products)
                if can_upgrade and budget_headroom >= 1500 and allow_upsell:
                    selected_model = "quality_upgrade"
                else:
                    # Conversion Closer gives instant checkout discount
                    selected_model = "conversion_closer"
            else:
                # Not strict items
                if allow_upsell and budget_headroom >= 2500 and any(p.upgrade_to_sku for p in requested_products):
                    selected_model = "quality_upgrade"
                elif any(p.warranty_price and p.warranty_price > 0 for p in requested_products):
                    selected_model = "value_services"
                else:
                    selected_model = "conversion_closer"

        if selected_model not in enabled:
            selected_model = "conversion_closer" if "conversion_closer" in enabled else "standard"
        if selected_model == "quality_upgrade" and not allow_upsell:
            selected_model = "conversion_closer" if "conversion_closer" in enabled else "standard"
        quote_items: List[QuoteItem] = []
        discount_total = 0.0
        warranty_total = 0.0
        explainability_note = ""
        savings_breakdown = ""

        # ----------------------------------------------------
        # EXECUTE MODEL 1: Quality Upgrade (Vertical Upsell)
        # ----------------------------------------------------
        if selected_model == "quality_upgrade":
            upgraded_any = False
            for p in requested_products:
                if p.upgrade_to_sku and not upgraded_any:
                    upgraded_prod = await CatalogService.get_product_by_sku(db, p.upgrade_to_sku)
                    if upgraded_prod and upgraded_prod.stock_quantity > 0:
                        # Offer upgrade with bundle discount
                        upgrade_discount = p.upgrade_bundle_discount or 1000.0
                        upgrade_unit_price = upgraded_prod.retail_price - upgrade_discount
                        
                        # Verify margin floor
                        prospective_margin = (upgrade_unit_price - upgraded_prod.cost_price) / upgrade_unit_price
                        if (prospective_margin >= margin_floor) and (base_subtotal - p.retail_price + upgrade_unit_price) <= budget_cap:
                            quote_items.append(QuoteItem(
                                sku=upgraded_prod.sku,
                                name=upgraded_prod.name,
                                quantity=1,
                                unit_price=upgrade_unit_price,
                                original_price=upgraded_prod.retail_price,
                                is_upgraded=True,
                                upgraded_from_sku=p.sku,
                                is_warranty=False,
                                is_unrequested_upsell=False,
                                category=upgraded_prod.category
                            ))
                            discount_total += upgrade_discount
                            total_cost = total_cost - p.cost_price + upgraded_prod.cost_price
                            upgraded_any = True
                            explainability_note = f"Deployed Growth Model 1 (Quality Upgrade): Upgraded {p.name} -> {upgraded_prod.name} (120Hz Mini-LED) with ₹{int(upgrade_discount)} bundle discount. Zero physical clutter."
                            savings_breakdown = f"Saved ₹{int(upgrade_discount)} on Tier-1 Creator Upgrade."
                            continue
                
                # Standard item
                quote_items.append(QuoteItem(
                    sku=p.sku,
                    name=p.name,
                    quantity=1,
                    unit_price=p.retail_price,
                    original_price=p.retail_price,
                    is_upgraded=False,
                    is_warranty=False,
                    is_unrequested_upsell=False,
                    category=p.category
                ))
            
            if not upgraded_any:
                # Fallback to conversion closer
                selected_model = "conversion_closer"

        # ----------------------------------------------------
        # EXECUTE MODEL 2: Conversion Closer (Anti-Abandonment)
        # ----------------------------------------------------
        if selected_model == "conversion_closer":
            quote_items = []
            # Calculate maximum safe discount while respecting margin floor
            # Current margin = (base_subtotal - total_cost) / base_subtotal
            current_margin = (base_subtotal - total_cost) / max(base_subtotal, 1.0)
            available_margin_slack = max(0.0, current_margin - margin_floor)
            # Give 2.5% to 4% dynamic discount
            discount_pct = min(0.035, available_margin_slack * 0.5)
            max_discount = max(0.0, 1 - total_cost / (max(base_subtotal, 1.0) * (1 - margin_floor)))
            discount_pct = min(discount_pct, max_discount)
            
            for p in requested_products:
                item_discount = round(p.retail_price * discount_pct, 2)
                item_final_price = p.retail_price - item_discount
                discount_total += item_discount
                quote_items.append(QuoteItem(
                    sku=p.sku,
                    name=p.name,
                    quantity=1,
                    unit_price=item_final_price,
                    original_price=p.retail_price,
                    is_upgraded=False,
                    is_warranty=False,
                    is_unrequested_upsell=False,
                    category=p.category
                ))
            explainability_note = f"Deployed Growth Model 2 (Conversion Closer): Applied dynamic {discount_pct*100:.1f}% instant-settlement discount (₹{int(discount_total)}) to secure order closure."
            savings_breakdown = f"Instant Autonomous Discount: ₹{int(discount_total)} ({discount_pct*100:.1f}% off)"

        # ----------------------------------------------------
        # EXECUTE MODEL 3: Bulk / Subscription (Recurring LTV)
        # ----------------------------------------------------
        elif selected_model == "bulk_subscription":
            quote_items = []
            sub_discount_pct = 0.15  # 15% discount for recurring mandate commitment
            for p in requested_products:
                if p.is_subscription:
                    item_discount = round(p.retail_price * sub_discount_pct, 2)
                    item_final_price = p.retail_price - item_discount
                    discount_total += item_discount
                    quote_items.append(QuoteItem(
                        sku=p.sku,
                        name=p.name,
                        quantity=1,
                        unit_price=item_final_price,
                        original_price=p.retail_price,
                        is_upgraded=False,
                        is_warranty=False,
                        is_unrequested_upsell=False,
                        category=p.category
                    ))
                else:
                    quote_items.append(QuoteItem(
                        sku=p.sku,
                        name=p.name,
                        quantity=1,
                        unit_price=p.retail_price,
                        original_price=p.retail_price,
                        is_upgraded=False,
                        is_warranty=False,
                        is_unrequested_upsell=False,
                        category=p.category
                    ))
            explainability_note = f"Deployed Growth Model 3 (Bulk / Subscription): 15% subscription-style quote discount (₹{discount_total:,.2f}). This is a one-time test order; recurring mandates are not implemented."
            savings_breakdown = f"Subscription-style pricing discount: ₹{discount_total:,.2f} (15%)"

        # ----------------------------------------------------
        # EXECUTE MODEL 4: Value-Add Services & Protection
        # ----------------------------------------------------
        elif selected_model == "value_services":
            quote_items = []
            for p in requested_products:
                quote_items.append(QuoteItem(
                    sku=p.sku,
                    name=p.name,
                    quantity=1,
                    unit_price=p.retail_price,
                    original_price=p.retail_price,
                    is_upgraded=False,
                    is_warranty=False,
                    is_unrequested_upsell=False,
                    category=p.category
                ))
            
            # Attach 2-Year Express Warranty service
            primary_item = requested_products[0]
            warranty_fee = primary_item.warranty_price or 999.0
            warranty_cost = warranty_fee * 0.10  # 90% gross margin on digital warranty
            total_cost += warranty_cost
            warranty_total += warranty_fee
            
            quote_items.append(QuoteItem(
                sku=f"srv_warranty_{primary_item.sku}",
                name=f"2-Year Express Replacement Care ({primary_item.name})",
                quantity=1,
                unit_price=warranty_fee,
                original_price=warranty_fee,
                is_upgraded=False,
                is_warranty=True,
                is_unrequested_upsell=True,  # Is an unrequested add-on
                category="services"
            ))
            explainability_note = f"Deployed Growth Model 4 (Value-Add Services): Added 2-Year Express Replacement Care for ₹{int(warranty_fee)} (90% Merchant Gross Margin)."
            savings_breakdown = f"Protection Added: 2-Year Full Hardware Coverage (₹{int(warranty_fee)})"

        # Calculate final totals and gross margin as ratio e.g. 0.2046 (20.5%)
        if selected_model == "standard":
            quote_items = [QuoteItem(sku=p.sku, name=p.name, unit_price=p.retail_price,
                original_price=p.retail_price, category=p.category) for p in requested_products]
        items_subtotal = sum(i.unit_price * i.quantity for i in quote_items)
        final_total = round(items_subtotal, 2)
        effective_margin = round((final_total - total_cost) / max(final_total, 1.0), 4)
        if final_total <= 0 or effective_margin < margin_floor - 0.0001:
            raise ValueError("No quote can satisfy the merchant margin floor. Adjust pricing or strategy.")

        quote_id = f"q_{uuid.uuid4().hex[:12]}"
        expires_at = (datetime.datetime.utcnow() + datetime.timedelta(minutes=15)).isoformat()

        payload_for_signing = {
            "quote_id": quote_id,
            "merchant_id": self.merchant_id,
            "buyer_agent_id": request.buyer_agent_id,
            "final_total": final_total,
            "expires_at": expires_at,
            "items": [i.model_dump() for i in quote_items]
        }
        signature = self._sign_quote(payload_for_signing, merchant_api_key)

        return DynamicQuoteResponse(
            quote_id=quote_id,
            buyer_agent_id=request.buyer_agent_id,
            merchant_id=self.merchant_id,
            items=quote_items,
            base_subtotal=base_subtotal,
            discount_total=round(discount_total, 2),
            warranty_total=round(warranty_total, 2),
            final_total=final_total,
            merchant_gross_margin_pct=effective_margin,
            applied_growth_model=selected_model,
            savings_breakdown=savings_breakdown,
            merchant_signature=signature,
            explainability_note=explainability_note,
            expires_at=expires_at
        )
