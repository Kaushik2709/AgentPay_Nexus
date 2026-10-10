import asyncio
import logging
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import Order, Quote
from app.commerce import write_transaction, expire_reservations
from app.razorpay.settlement_agent import RazorpaySettlementAgent

logger = logging.getLogger(__name__)

async def maintain_orders():
    while True:
        try:
            agent = RazorpaySettlementAgent()
            async with AsyncSessionLocal() as db:
                pending = (await db.execute(select(Order.razorpay_order_id).join(Quote, Quote.id == Order.id).where(
                    Order.status.in_(["CREATED", "EXPIRED"])).limit(100))).scalars().all()
            if agent.client:
                for order_id in pending:
                    try:
                        payments = await asyncio.to_thread(agent.client.order.payments, order_id)
                        for payment in payments.get("items", []):
                            if payment.get("status") == "captured":
                                async with AsyncSessionLocal() as db:
                                    await agent.settle_order(db, order_id, payment["id"], payment=payment)
                    except Exception:
                        logger.warning("Payment reconciliation pending for order %s", order_id)
            async with AsyncSessionLocal() as db:
                await write_transaction(db)
                await expire_reservations(db)
                await db.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Order maintenance failed; will retry")
        await asyncio.sleep(60)
