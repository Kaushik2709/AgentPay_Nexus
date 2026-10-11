"""Persisted quotes, stock holds and local transaction boundaries."""
import datetime
import json
import hmac
import hashlib
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select, update
from app.db.models import Quote, Order, Product, StockReservation, CommerceLock, Merchant

def paise(value) -> int:
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

def quote_signature(quote, secret):
    payload = {key: getattr(quote, key) for key in (
        "quote_id", "merchant_id", "buyer_agent_id", "final_total", "expires_at")}
    payload["items"] = [item.model_dump() for item in quote.items]
    payload["final_total"] = paise(quote.final_total) / 100
    return hmac.new(secret.encode(), json.dumps(payload, sort_keys=True).encode(), hashlib.sha256).hexdigest()

async def validate_quote(db, stored, quote):
    merchant = await db.get(Merchant, quote.merchant_id)
    secret = merchant.api_key if merchant else "sec_live_merchant_default"
    if (quote.quote_id != stored.id or quote.buyer_agent_id != stored.buyer_agent_id
            or paise(quote.final_total) != stored.amount_paise
            or sum(paise(item.unit_price) * item.quantity for item in quote.items) != stored.amount_paise
            or not hmac.compare_digest(quote_signature(quote, secret), quote.merchant_signature)):
        raise ValueError("Quote integrity changed. Request a fresh quote.")

async def write_transaction(db):
    # A no-op UPDATE acquires a writer lock even after SQLAlchemy's read autobegin.
    # PostgreSQL holds this row lock until commit/rollback; SQLite locks its writer.
    # Always acquire before business reads. Every process uses the same DB mutex.
    with db.no_autoflush:
        result = await db.execute(update(CommerceLock).where(CommerceLock.id == 1).values(id=1))
    if result.rowcount != 1:
        raise RuntimeError("Commerce lock missing; run database migrations.")

async def persist_quote(db, quote, budget):
    db.add(Quote(id=quote.quote_id, buyer_agent_id=quote.buyer_agent_id,
        amount_paise=paise(quote.final_total), data_json=json.dumps(quote.model_dump()),
        budget_paise=paise(budget), expires_at=datetime.datetime.fromisoformat(quote.expires_at)))
    await db.flush()

async def expire_reservations(db):
    now = datetime.datetime.utcnow()
    rows = (await db.execute(select(StockReservation).where(
        StockReservation.status == "HELD", StockReservation.expires_at < now))).scalars().all()
    orders = {row.order_id for row in rows}
    for order_id in orders:
        order = await db.get(Order, order_id)
        # Never release uncertain provider operations automatically.
        if not order or order.status not in {"CREATED", "FAILED"}:
            continue
        # Release the whole cart together; changing the order after the first line
        # used to strand every subsequent line in a multi-item reservation.
        holds = (await db.execute(select(StockReservation).where(
            StockReservation.order_id == order_id, StockReservation.status == "HELD"))).scalars().all()
        for row in holds:
            claimed = await db.execute(update(StockReservation).where(
                StockReservation.id == row.id, StockReservation.status == "HELD").values(status="RELEASED"))
            if claimed.rowcount:
                await db.execute(update(Product).where(Product.sku == row.sku).values(
                    stock_quantity=Product.stock_quantity + row.quantity))
        if order.status == "CREATED":
            order.status = "EXPIRED"

async def reserve_stock(db, quote):
    async with db.begin_nested():
        for item in sorted(quote.items, key=lambda line: line.sku):
            if item.is_warranty:
                continue
            result = await db.execute(update(Product).where(Product.sku == item.sku,
                Product.stock_quantity >= item.quantity).values(stock_quantity=Product.stock_quantity - item.quantity))
            if result.rowcount != 1:
                raise ValueError(f"Insufficient stock for {item.sku}. No checkout was created.")
            db.add(StockReservation(order_id=quote.quote_id, sku=item.sku, quantity=item.quantity,
                expires_at=datetime.datetime.fromisoformat(quote.expires_at), status="HELD"))
        await db.flush()
