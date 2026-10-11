import asyncio
import logging
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import Order, Quote
from app.commerce import write_transaction, expire_reservations
from app.razorpay.settlement_agent import RazorpaySettlementAgent

logger = logging.getLogger(__name__)

async def reconcile_once(sessions=AsyncSessionLocal, agent=None):
    """One sweep, independently testable with provider doubles."""
    agent = agent or RazorpaySettlementAgent()
    async with sessions() as db:
        # Scan all unresolved records; do not starve later orders behind a fixed LIMIT.
        pending = (await db.execute(select(Order.id, Order.razorpay_order_id, Order.status).where(
            Order.status.in_(["CREATING", "RECONCILIATION_REQUIRED", "CREATED", "EXPIRED"]))
            .order_by(Order.id))).all()
    if agent.client:
        for quote_id, order_id, status in pending:
            try:
                if status in {"CREATING", "RECONCILIATION_REQUIRED"}:
                    async with sessions() as db:
                        if not await agent.recover_order(db, quote_id):
                            continue
                        order_id = (await db.get(Order, quote_id)).razorpay_order_id
                payments = await asyncio.to_thread(agent.client.order.payments, order_id)
                for payment in payments.get("items", []):
                    if payment.get("status") == "captured":
                        async with sessions() as db:
                            await agent.settle_order(db, order_id, payment["id"], payment=payment)
            except Exception:
                logger.warning("Payment reconciliation pending for order %s", quote_id)
    async with sessions() as db:
        await write_transaction(db)
        await expire_reservations(db)
        await db.commit()


async def maintain_orders():
    while True:
        try:
            await reconcile_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Order maintenance failed; will retry")
        await asyncio.sleep(60)
