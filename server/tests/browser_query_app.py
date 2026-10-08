"""Local browser QA app: in-memory DB, read-only catalog copy, no provider calls.
Run from server: python -m uvicorn tests.browser_query_app:app --port 8001
Never mount this app in the production server.
"""
import json
import sqlite3
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.api.agent_router import router
from app.db.models import Base, Product, Merchant, Policy
from app.db.session import get_db
from app.razorpay.settlement_agent import RazorpaySettlementAgent
from app.schemas.agent_schemas import RazorpayOrderResponse

engine = create_async_engine("sqlite+aiosqlite:///:memory:")
sessions = async_sessionmaker(engine, expire_on_commit=False)

async def fixture_order(self, db, request, **kwargs):
    return RazorpayOrderResponse(razorpay_order_id="order_rzp_fixture_" + uuid.uuid4().hex[:8], amount_in_paise=round(request.amount_inr * 100), amount_inr=request.amount_inr, currency="INR", status="created", receipt="browser-qa", payment_link="", key_id="rzp_test_ui_fixture", notes={"test_only": "true"})

@asynccontextmanager
async def lifespan(app):
    source = Path(__file__).resolve().parents[1] / "agentpay.db"
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        columns = [c.name for c in Product.__table__.columns if c.name not in ("created_at", "updated_at")]
        rows = [dict(row) for row in connection.execute("SELECT " + ",".join(columns) + " FROM products")]
    async with engine.begin() as db:
        await db.run_sync(Base.metadata.create_all)
    async with sessions() as db:
        db.add_all([Product(**row) for row in rows])
        db.add(Merchant(id="merchant_techgear_01", name="Browser QA fixture", margin_floor_pct=.2, active_growth_models='["quality_upgrade","conversion_closer","bulk_subscription","value_services"]', api_key="fixture-only"))
        db.add(Policy(id="fixture", user_id="aarav_buyer_01", max_tx_amount=25000, daily_velocity_cap=50000, category_whitelist=json.dumps(["monitors","keyboards","mice","electronics","accessories","subscriptions","services"]), allow_autonomous_upsell=False))
        await db.commit()
    # Scope the stub to this test application's lifetime, including every request.
    with patch.object(RazorpaySettlementAgent, "create_order", fixture_order):
        yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)
app.include_router(router, prefix="/api")
async def fixture_db():
    async with sessions() as db:
        yield db
app.dependency_overrides[get_db] = fixture_db

@app.get("/qa/health")
async def health():
    return {"database": "in-memory", "settlement": "stubbed", "source_catalog": "read-only"}
