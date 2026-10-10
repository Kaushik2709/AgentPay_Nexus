"""Persisted quotes, stock holds and local transaction boundaries."""
import datetime
import json
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select, update, text
from app.db.models import Quote, Order, Product, StockReservation

def paise(value) -> int:
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

async def write_transaction(db):
    # SQLite serializes writes; BEGIN IMMEDIATE also protects read-then-write decisions.
    if not db.in_transaction():
        if db.bind.dialect.name == "sqlite":
            await db.execute(text("BEGIN IMMEDIATE"))
        else:
            await db.begin()

async def persist_quote(db, quote, budget):
    db.add(Quote(id=quote.quote_id, buyer_agent_id=quote.buyer_agent_id,
        amount_paise=paise(quote.final_total), data_json=json.dumps(quote.model_dump()),
        budget_paise=paise(budget), expires_at=datetime.datetime.fromisoformat(quote.expires_at)))
    await db.flush()

async def expire_reservations(db):
    now = datetime.datetime.utcnow()
    rows = (await db.execute(select(StockReservation).where(
        StockReservation.status == "HELD", StockReservation.expires_at < now))).scalars().all()
    for row in rows:
        order = await db.get(Order, row.order_id)
        # Never release uncertain provider operations automatically.
        if not order or order.status not in {"CREATED", "FAILED"}:
            continue
        claimed = await db.execute(update(StockReservation).where(
            StockReservation.id == row.id, StockReservation.status == "HELD").values(status="RELEASED"))
        if claimed.rowcount:
            await db.execute(update(Product).where(Product.sku == row.sku).values(
                stock_quantity=Product.stock_quantity + row.quantity))
            if order.status == "CREATED":
                order.status = "EXPIRED"

async def reserve_stock(db, quote):
    for item in quote.items:
        if item.is_warranty:
            continue
        result = await db.execute(update(Product).where(Product.sku == item.sku,
            Product.stock_quantity >= item.quantity).values(stock_quantity=Product.stock_quantity - item.quantity))
        if result.rowcount != 1:
            raise ValueError(f"Insufficient stock for {item.sku}. No checkout was created.")
        db.add(StockReservation(order_id=quote.quote_id, sku=item.sku, quantity=item.quantity,
            expires_at=datetime.datetime.fromisoformat(quote.expires_at), status="HELD"))
    await db.flush()
