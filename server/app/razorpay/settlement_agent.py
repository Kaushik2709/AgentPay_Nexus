import asyncio
import datetime
import hashlib
import hmac
import json
import uuid
import razorpay
import requests
from fastapi import HTTPException
from sqlalchemy import select
from app.config import settings
from app.auth import buyer_id, identity
from app.commerce import paise, reserve_stock, write_transaction, validate_quote
from app.db.models import Order, Quote, StockReservation, PaymentEvent
from app.schemas.agent_schemas import DynamicQuoteResponse, RazorpayOrderResponse


class ProviderSession(requests.Session):
    """Bound connection/read waits; SDK retries stay disabled for order submission."""
    def request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", (3.05, 10))
        return super().request(method, url, **kwargs)


class RazorpaySettlementAgent:
    def __init__(self, key_id=None, key_secret=None, webhook_secret=None):
        self.key_id = key_id or settings.RAZORPAY_KEY_ID
        self.key_secret = key_secret or settings.RAZORPAY_KEY_SECRET
        self.webhook_secret = webhook_secret or settings.RAZORPAY_WEBHOOK_SECRET
        # Live keys never construct an operational adapter, including maintenance.
        self.client = razorpay.Client(session=ProviderSession(), auth=(self.key_id, self.key_secret)) if self.key_id.startswith("rzp_test_") and self.key_secret else None

    def _generate_hmac_signature(self, order_id, payment_id):
        return hmac.new(self.key_secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()

    def verify_payment_signature(self, order_id, payment_id, signature):
        return bool(self.key_secret and signature) and hmac.compare_digest(self._generate_hmac_signature(order_id, payment_id), signature)

    def verify_webhook_signature(self, raw_body, signature):
        expected = hmac.new(self.webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return bool(self.webhook_secret and signature) and hmac.compare_digest(expected, signature)

    async def create_order(self, db, request, items_payload=None, growth_model="standard",
                           discount_amount=0.0, warranty_amount=0.0, explainability=""):
        await write_transaction(db)
        stored = await db.get(Quote, request.quote_id, populate_existing=True)
        if not stored or (identity.get() and stored.buyer_agent_id != buyer_id()):
            raise HTTPException(404, "Quote not found.")
        if paise(request.amount_inr) != stored.amount_paise or request.currency != "INR":
            raise HTTPException(422, "Checkout amount must match the stored quote.")
        existing = await db.get(Order, request.quote_id, populate_existing=True)
        if existing:
            if existing.status == "CREATED" and stored.checkout_json and stored.expires_at > datetime.datetime.utcnow():
                return RazorpayOrderResponse(**json.loads(stored.checkout_json))
            raise HTTPException(409, f"Order is {existing.status}. Check its status before retrying.")
        if stored.expires_at <= datetime.datetime.utcnow():
            raise HTTPException(409, "Quote expired. Request a fresh quote.")
        if stored.status not in {"CHECKOUT_READY", "APPROVED"}:
            raise HTTPException(403, "Quote must pass policy or human approval before checkout.")
        quote = DynamicQuoteResponse(**json.loads(stored.data_json))
        try:
            await validate_quote(db, stored, quote)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        if not self.client or not self.key_id.startswith("rzp_test_"):
            raise HTTPException(503, "Configure Razorpay test credentials before checkout.")
        from app.agents.policy_guard import PolicyGuardAgent
        from app.auth import user_id
        current = await PolicyGuardAgent().evaluate_quote(db, quote, user_id=user_id(),
            user_override_budget=stored.budget_paise / 100, create_gate=False)
        codes = {value.split(":", 1)[0] for value in current.violations}
        if "UNAPPROVED_CATEGORY" in codes or (stored.status == "CHECKOUT_READY" and codes):
            raise HTTPException(409, "Policy changed before checkout. Request a new decision.")
        await reserve_stock(db, quote)
        receipt = f"nexus_{uuid.uuid4().hex[:24]}"
        stored.data_json = json.dumps({**json.loads(stored.data_json), "provider_receipt": receipt})
        order = Order(id=quote.quote_id, razorpay_order_id=f"pending_{uuid.uuid4().hex}",
            buyer_agent_id=quote.buyer_agent_id, merchant_id=quote.merchant_id,
            status="CREATING", base_amount=quote.base_subtotal, discount_amount=quote.discount_total,
            warranty_amount=quote.warranty_total, total_amount=stored.amount_paise / 100,
            amount_paise=stored.amount_paise,
            currency="INR", growth_model_applied=quote.applied_growth_model,
            items_json=json.dumps([i.model_dump() for i in quote.items]), explainability_summary=quote.explainability_note)
        db.add(order)
        stored.status = "CONSUMED"
        await db.commit()
        amount = stored.amount_paise
        try:
            provider = await asyncio.to_thread(self.client.order.create, data={
                "amount": amount, "currency": "INR", "receipt": receipt,
                "notes": {"quote_id": quote.quote_id}})
            if not provider.get("id") or type(provider.get("amount")) is not int or provider.get("amount") != amount or provider.get("currency") != "INR":
                raise ValueError("Unexpected Razorpay order response")
        except (Exception, asyncio.CancelledError) as error:
            await write_transaction(db)
            await db.refresh(order)
            if order.status == "CREATING":
                order.status = "RECONCILIATION_REQUIRED"
            await db.commit()
            if isinstance(error, asyncio.CancelledError):
                raise
            raise HTTPException(503, "Provider order outcome is uncertain. Check order status; do not create another payment.") from error
        return await self._bind_provider_order(db, quote.quote_id, provider, receipt)

    async def _bind_provider_order(self, db, quote_id, provider, receipt):
        await write_transaction(db)
        order = await db.get(Order, quote_id, populate_existing=True)
        stored = await db.get(Quote, quote_id, populate_existing=True)
        if not order or not stored:
            raise HTTPException(409, "Local provider attempt missing.")
        if order.status not in {"CREATING", "RECONCILIATION_REQUIRED"}:
            if order.razorpay_order_id != provider["id"]:
                raise HTTPException(409, "Conflicting provider order; manual review required.")
            return RazorpayOrderResponse(**json.loads(stored.checkout_json))
        order.razorpay_order_id = provider["id"]
        order.status = "CREATED"
        result = RazorpayOrderResponse(razorpay_order_id=provider["id"], amount_in_paise=order.amount_paise,
            amount_inr=order.amount_paise / 100, currency="INR", status="created", receipt=receipt,
            payment_link="", key_id=self.key_id, notes={"quote_id": quote_id})
        stored.checkout_json = json.dumps(result.model_dump())
        await db.commit()
        return result

    async def recover_order(self, db, quote_id):
        """Read-only provider lookup; never resubmit an uncertain creation attempt."""
        order = await db.get(Order, quote_id)
        stored = await db.get(Quote, quote_id)
        if not order or not stored or order.status not in {"CREATING", "RECONCILIATION_REQUIRED"}:
            await db.rollback()
            return False
        receipt = json.loads(stored.data_json).get("provider_receipt")
        amount = order.amount_paise
        # No transaction/lock is held across the provider call.
        await db.rollback()
        if not receipt or not self.client:
            return False
        response = await asyncio.to_thread(self.client.order.all, {"receipt": receipt, "count": 100})
        matches = response.get("items", [])
        if len(matches) != 1:
            return False  # Zero or ambiguous matches retain stock and spend holds.
        provider = matches[0]
        if (not provider.get("id") or provider.get("receipt") != receipt
                or type(provider.get("amount")) is not int or provider.get("amount") != amount
                or provider.get("currency") != "INR"
                or provider.get("notes", {}).get("quote_id") != quote_id):
            return False
        await self._bind_provider_order(db, quote_id, provider, receipt)
        return True

    async def fetch_payment(self, payment_id):
        if not self.client:
            raise HTTPException(503, "Payment provider unavailable.")
        try:
            return await asyncio.to_thread(self.client.payment.fetch, payment_id)
        except Exception as error:
            raise HTTPException(503, "Payment status is pending verification. Do not pay again.") from error

    async def settle_order(self, db, order_id_or_rzp_id, payment_id, payment=None, event_id=None):
        payment = payment or await self.fetch_payment(payment_id)
        await write_transaction(db)
        order = (await db.execute(select(Order).where(Order.razorpay_order_id == order_id_or_rzp_id)
            .execution_options(populate_existing=True))).scalar_one_or_none()
        if not order or (identity.get() and order.buyer_agent_id != buyer_id()):
            raise HTTPException(404, "Order not found.")
        amount = order.amount_paise
        if type(payment.get("amount")) is not int or payment.get("id") != payment_id or payment.get("order_id") != order.razorpay_order_id or payment.get("amount") != amount or payment.get("currency") != order.currency:
            raise HTTPException(422, "Payment does not match this order.")
        if payment.get("status") != "captured":
            raise HTTPException(409, "Payment is not captured yet. Await verification; do not pay again.")
        if event_id:
            existing_event = await db.get(PaymentEvent, event_id)
            if existing_event and (existing_event.payment_id != payment_id or existing_event.order_id != order.id):
                raise HTTPException(409, "Webhook event was already associated with another payment.")
        if order.status in {"PAID", "PAID_REQUIRES_REVIEW"}:
            if order.razorpay_payment_id != payment_id:
                raise HTTPException(409, "A different payment was already recorded for this order.")
            return order
        previous = (await db.execute(select(PaymentEvent).where(PaymentEvent.payment_id == payment_id))).scalar_one_or_none()
        if previous:
            raise HTTPException(409, "Payment was already associated with another order.")
        holds = (await db.execute(select(StockReservation).where(StockReservation.order_id == order.id))).scalars().all()
        expected = {item["sku"]: item.get("quantity", 1) for item in json.loads(order.items_json) if not item.get("is_warranty")}
        intact = bool(expected) and {hold.sku: hold.quantity for hold in holds if hold.status == "HELD"} == expected
        order.status = "PAID" if intact else "PAID_REQUIRES_REVIEW"
        order.razorpay_payment_id = payment_id
        order.settled_at = datetime.datetime.utcnow()
        for hold in holds:
            if hold.status == "HELD":
                hold.status = "CONSUMED"
        db.add(PaymentEvent(id=event_id or f"checkout_{payment_id}", payment_id=payment_id,
            order_id=order.id, amount_paise=amount))
        from app.audit.ledger import AuditLedgerEngine
        await AuditLedgerEngine.append_entry(db, "RazorpaySettlementAgent", "PAYMENT_CAPTURED",
            {"order_id": order.id, "payment_id": payment_id, "amount_paise": amount,
             "status": order.status}, commit=False)
        await db.commit()
        return order
