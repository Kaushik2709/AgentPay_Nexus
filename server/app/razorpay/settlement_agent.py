import hmac
import hashlib
import json
import uuid
import datetime
from typing import Dict, Any, Optional
import razorpay
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.db.models import Order, Product
from app.catalog.catalog_service import CatalogService
from app.schemas.agent_schemas import (
    RazorpayCreateOrderRequest,
    RazorpayOrderResponse,
    PaymentVerificationRequest,
    PaymentVerificationResponse
)

class RazorpaySettlementAgent:
    """
    Fintech & Settlement Worker Agent.
    - Interacts with Razorpay Orders API (POST /v1/orders).
    - Generates Razorpay Checkout payload and payment links.
    - Verifies cryptographic HMAC-SHA256 signatures on client checkout & webhooks.
    - Manages atomic stock commit and order state transitions.
    """
    def __init__(
        self,
        key_id: str = None,
        key_secret: str = None,
        webhook_secret: str = None
    ):
        self.key_id = key_id or settings.RAZORPAY_KEY_ID
        self.key_secret = key_secret or settings.RAZORPAY_KEY_SECRET
        self.webhook_secret = webhook_secret or settings.RAZORPAY_WEBHOOK_SECRET
        
        # Initialize Razorpay official client
        try:
            self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
        except Exception:
            self.client = None

    def _generate_hmac_signature(self, order_id: str, payment_id: str) -> str:
        """Generates standard Razorpay SHA256 HMAC for testing/verification."""
        msg = f"{order_id}|{payment_id}"
        return hmac.new(
            self.key_secret.encode("utf-8"),
            msg.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    async def create_order(
        self,
        db: AsyncSession,
        request: RazorpayCreateOrderRequest,
        items_payload: list = None,
        growth_model: str = "standard",
        discount_amount: float = 0.0,
        warranty_amount: float = 0.0,
        explainability: str = ""
    ) -> RazorpayOrderResponse:
        amount_paise = int(round(request.amount_inr * 100))
        receipt = f"{request.receipt_prefix}_{uuid.uuid4().hex[:8]}"
        rzp_order_id = f"order_rzp_{uuid.uuid4().hex[:14]}"

        # Attempt creating order via Razorpay client if valid online credentials
        if self.client and not self.key_id.startswith("rzp_test_Nexus"):
            try:
                order_data = {
                    "amount": amount_paise,
                    "currency": request.currency,
                    "receipt": receipt,
                    "notes": request.notes or {}
                }
                rzp_resp = self.client.order.create(data=order_data)
                rzp_order_id = rzp_resp.get("id", rzp_order_id)
            except Exception as e:
                print(f"[RazorpaySettlementAgent] Falling back to sandbox order generator: {e}")

        # Construct payment link
        payment_link = f"https://api.razorpay.com/v1/checkout/hosted?order_id={rzp_order_id}"

        # Persist Order in DB
        db_order = Order(
            id=request.quote_id or f"ord_{uuid.uuid4().hex[:12]}",
            razorpay_order_id=rzp_order_id,
            buyer_agent_id=request.buyer_agent_id,
            merchant_id="merchant_techgear_01",
            status="CREATED",
            base_amount=round(request.amount_inr + discount_amount - warranty_amount, 2),
            discount_amount=round(discount_amount, 2),
            warranty_amount=round(warranty_amount, 2),
            total_amount=round(request.amount_inr, 2),
            currency=request.currency,
            growth_model_applied=growth_model,
            items_json=json.dumps(items_payload or []),
            explainability_summary=explainability
        )
        db.add(db_order)
        await db.commit()

        notes = request.notes or {}
        notes.update({
            "quote_id": request.quote_id,
            "buyer_agent_id": request.buyer_agent_id,
            "engine": "AgentPay_Nexus_v1.1"
        })

        return RazorpayOrderResponse(
            razorpay_order_id=rzp_order_id,
            amount_in_paise=amount_paise,
            amount_inr=round(request.amount_inr, 2),
            currency=request.currency,
            status="created",
            receipt=receipt,
            payment_link=payment_link,
            key_id=self.key_id,
            notes=notes
        )

    def verify_payment_signature(
        self,
        order_id: str,
        payment_id: str,
        signature: str
    ) -> bool:
        """Cryptographically verifies Razorpay Checkout HMAC-SHA256 signature."""
        expected_sig = self._generate_hmac_signature(order_id, payment_id)
        return hmac.compare_digest(expected_sig, signature)

    def verify_webhook_signature(
        self,
        raw_body: bytes,
        signature: str
    ) -> bool:
        """Verifies X-Razorpay-Signature HMAC from Webhook."""
        expected_sig = hmac.new(
            self.webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_sig, signature)

    async def settle_order(
        self,
        db: AsyncSession,
        order_id_or_rzp_id: str,
        payment_id: str
    ) -> Optional[Order]:
        """Marks order as PAID and locks in the transaction."""
        from sqlalchemy import select
        query = select(Order).where(
            (Order.id == order_id_or_rzp_id) | (Order.razorpay_order_id == order_id_or_rzp_id)
        )
        res = await db.execute(query)
        order = res.scalar_one_or_none()
        if not order:
            return None

        order.status = "PAID"
        order.razorpay_payment_id = payment_id
        
        # Decrement real stock for physical items
        items = json.loads(order.items_json or "[]")
        for itm in items:
            sku = itm.get("sku")
            if sku and not itm.get("is_warranty"):
                await CatalogService.reserve_and_decrement_stock(db, sku, itm.get("quantity", 1))

        await db.commit()
        await db.refresh(order)
        return order
