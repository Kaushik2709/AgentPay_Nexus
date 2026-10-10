from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.razorpay.settlement_agent import RazorpaySettlementAgent
from app.audit.ledger import AuditLedgerEngine
import json
from sqlalchemy import select
from app.db.models import Order, AuditEntry
from app.auth import buyer_id
from app.schemas.agent_schemas import (
    RazorpayCreateOrderRequest,
    RazorpayOrderResponse,
    PaymentVerificationRequest,
    PaymentVerificationResponse
)

router = APIRouter(prefix="/razorpay", tags=["Razorpay Fintech Rails"])

@router.post("/create-order", response_model=RazorpayOrderResponse)
async def create_razorpay_order(
    request: RazorpayCreateOrderRequest,
    db: AsyncSession = Depends(get_db)
):
    """Creates a real Razorpay Test Order with amount in paise."""
    settlement_agent = RazorpaySettlementAgent()
    return await settlement_agent.create_order(db, request)

@router.post("/verify-payment", response_model=PaymentVerificationResponse)
async def verify_razorpay_payment(
    request: PaymentVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verifies the HMAC-SHA256 signature from standard Razorpay Checkout modal
    and locks in the order transaction.
    """
    settlement_agent = RazorpaySettlementAgent()
    local_order = (await db.execute(select(Order).where(
        Order.razorpay_order_id == request.razorpay_order_id,
        Order.buyer_agent_id == buyer_id()))).scalar_one_or_none()
    if not local_order:
        raise HTTPException(404, "Order not found.")
    stored_order_id = local_order.razorpay_order_id
    await db.rollback()
    is_valid = settlement_agent.verify_payment_signature(
        order_id=stored_order_id,
        payment_id=request.razorpay_payment_id,
        signature=request.razorpay_signature
    )

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail="Cryptographic verification FAILED. Invalid Razorpay HMAC-SHA256 signature."
        )

    # Settle order in database and update inventory
    settled_order = await settlement_agent.settle_order(
        db=db,
        order_id_or_rzp_id=request.razorpay_order_id,
        payment_id=request.razorpay_payment_id
    )

    # Record to immutable audit ledger
    entries = (await db.execute(select(AuditEntry).where(AuditEntry.action == "PAYMENT_CAPTURED")
        .order_by(AuditEntry.sequence_number.desc()))).scalars().all()
    audit_entry = next(entry for entry in entries if json.loads(entry.payload_json).get("payment_id") == request.razorpay_payment_id)

    return PaymentVerificationResponse(
        success=True,
        status=settled_order.status,
        transaction_hash=audit_entry.entry_hash,
        audit_sequence=audit_entry.sequence_number,
        message="Payment capture verified." if settled_order.status == "PAID" else "Payment captured; fulfillment requires review.",
        digital_receipt={
            "order_id": request.razorpay_order_id,
            "payment_id": request.razorpay_payment_id,
            "amount": settled_order.total_amount if settled_order else 0.0,
            "currency": "INR",
            "audit_hash": audit_entry.entry_hash
        }
    )

@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Razorpay Webhook receiver.
    Intercepts payment.captured and verifies X-Razorpay-Signature HMAC.
    """
    raw_body = await request.body()
    settlement_agent = RazorpaySettlementAgent()

    if not x_razorpay_signature or not settlement_agent.verify_webhook_signature(raw_body, x_razorpay_signature):
        raise HTTPException(status_code=400, detail="Valid webhook signature required")

    try:
        payload = await request.json()
    except ValueError as error:
        raise HTTPException(400, "Malformed webhook payload") from error
    if not isinstance(payload, dict):
        raise HTTPException(400, "Malformed webhook payload")
    event_type = payload.get("event")
    if event_type != "payment.captured":
        return {"status": "ignored", "event": event_type}
    event_id = request.headers.get("x-razorpay-event-id")
    if not event_id or len(event_id) > 128:
        raise HTTPException(400, "Webhook event ID required")
    event_payload = payload.get("payload")
    if not isinstance(event_payload, dict) or not isinstance(event_payload.get("payment"), dict):
        raise HTTPException(400, "Payment entity required")
    entity = event_payload["payment"].get("entity", {})
    if not isinstance(entity, dict) or not entity.get("id") or not entity.get("order_id"):
        raise HTTPException(400, "Payment entity required")

    # Record webhook to audit ledger
    await settlement_agent.settle_order(db, entity["order_id"], entity["id"], payment=entity, event_id=event_id)

    return {"status": "ok", "event_processed": event_type}
