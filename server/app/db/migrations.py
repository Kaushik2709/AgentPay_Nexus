"""Small additive migration, usable on SQLite and PostgreSQL without data resets.

Run with API/maintenance stopped: python -m app.db.migrations
Back up existing databases first. Deliberately no destructive downgrade.
"""
from decimal import Decimal, ROUND_HALF_UP
import datetime
from sqlalchemy import inspect, text
from app.db.models import Base


def migrate(engine):
    with engine.begin() as conn:
        tables = inspect(conn).get_table_names()
        if "orders" in tables:
            columns = {column["name"] for column in inspect(conn).get_columns("orders")}
            if "amount_paise" not in columns:
                conn.execute(text("ALTER TABLE orders ADD COLUMN amount_paise BIGINT"))
            if "settled_at" not in columns:
                conn.execute(text("ALTER TABLE orders ADD COLUMN settled_at TIMESTAMP"))
            if "status" in columns:
                # Legacy capture time is unknown: conservatively reserve one new
                # 24h spend window at migration rather than undercount late captures.
                conn.execute(text("UPDATE orders SET settled_at=:now WHERE settled_at IS NULL AND status IN ('PAID', 'PAID_REQUIRES_REVIEW')"),
                             {"now":datetime.datetime.utcnow()})
            rows = conn.execute(text("SELECT id, total_amount FROM orders WHERE amount_paise IS NULL")).all()
            for order_id, amount in rows:
                value = int((Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
                if value <= 0:
                    raise ValueError(f"Invalid legacy order amount for {order_id}; manual review required")
                conn.execute(text("UPDATE orders SET amount_paise=:value WHERE id=:id"), {"id": order_id, "value": value})
        Base.metadata.create_all(conn)
        # Unique indexes also apply to pre-existing tables; duplicate legacy data
        # intentionally fails migration instead of silently discarding evidence.
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_reservation_order_sku ON stock_reservations(order_id, sku)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_order_provider_id ON orders(razorpay_order_id)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_policy_user ON policies(user_id)"))


if __name__ == "__main__":
    from app.db.session import sync_engine
    migrate(sync_engine)
    print("Additive reliability migration complete.")
