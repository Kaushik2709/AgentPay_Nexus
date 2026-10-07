from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.razorpay.settlement_agent import RazorpaySettlementAgent
from app.audit.ledger import AuditLedgerEngine
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
    is_valid = settlement_agent.verify_payment_signature(
        order_id=request.razorpay_order_id,
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
    audit_entry = await AuditLedgerEngine.append_entry(
        db=db,
        actor="RazorpaySettlementAgent",
        action="PAYMENT_CAPTURED_AND_SETTLED",
        payload={
            "razorpay_order_id": request.razorpay_order_id,
            "razorpay_payment_id": request.razorpay_payment_id,
            "amount_paid": settled_order.total_amount if settled_order else 0.0,
            "verification": "HMAC_SHA256_VERIFIED"
        }
    )

    return PaymentVerificationResponse(
        success=True,
        status="PAID",
        transaction_hash=audit_entry.entry_hash,
        audit_sequence=audit_entry.sequence_number,
        message="Payment verified successfully via HMAC-SHA256 non-repudiation.",
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

    if x_razorpay_signature:
        is_valid = settlement_agent.verify_webhook_signature(raw_body, x_razorpay_signature)
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid Webhook HMAC Signature")

    payload = await request.json()
    event_type = payload.get("event", "payment.captured")

    # Record webhook to audit ledger
    await AuditLedgerEngine.append_entry(
        db=db,
        actor="RazorpayWebhook",
        action=f"WEBHOOK_{event_type.upper()}",
        payload=payload
    )

    return {"status": "ok", "event_processed": event_type}
