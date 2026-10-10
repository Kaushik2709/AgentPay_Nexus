"""Database-backed purchase invariants; provider calls are isolated test doubles."""
import asyncio
import datetime as dt
import hashlib
import hmac
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.auth import authenticate, identity
from app.commerce import persist_quote, write_transaction, expire_reservations
from app.db.models import Base, Product, Quote, Order, PaymentEvent, AuditEntry
from app.razorpay.settlement_agent import RazorpaySettlementAgent
from app.schemas.agent_schemas import DynamicQuoteResponse, QuoteItem, RazorpayCreateOrderRequest
from app.agents.supervisor import CommerceSupervisorAgent
from app.agents.purchase_intent import parse_purchase_intent, select_products
from app.api.razorpay_router import router as payment_router
from app.db.session import get_db


def quote(name="q_one", owner="buyer", expiry=None):
    return DynamicQuoteResponse(quote_id=name, buyer_agent_id=owner,
        items=[QuoteItem(sku="item_mouse", name="Wireless Mouse", unit_price=100, original_price=100, category="mice")],
        base_subtotal=100, discount_total=0, warranty_total=0, final_total=100,
        merchant_gross_margin_pct=0.5, applied_growth_model="standard", savings_breakdown="",
        merchant_signature="signed", explainability_note="", expires_at=(expiry or dt.datetime.utcnow()+dt.timedelta(minutes=15)).isoformat())


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.middleware("http")(authenticate)
        @self.app.get("/api/merchant/dashboard")
        async def endpoint(): return {"ok": True}
        @self.app.get("/api/agent/orders")
        async def buyer(): return {"owner": identity.get()["id"]}
        self.client = TestClient(self.app)

    def headers(self, path, role="buyer", timestamp=None):
        stamp = str(timestamp or int(time.time()))
        message="\n".join([stamp,"GET",path,"buyer",role,"0",hashlib.sha256(b"").hexdigest()])
        return {"X-User-Id":"buyer","X-User-Role":role,"X-Auth-Timestamp":stamp,
                "X-Auth-Signature":hmac.new(b"test-secret",message.encode(),hashlib.sha256).hexdigest()}

    def test_anonymous_forged_and_stale_identities_are_rejected(self):
        with patch.dict(os.environ,{"BACKEND_AUTH_SECRET":"test-secret"}):
            self.assertEqual(self.client.get("/api/agent/orders").status_code,401)
            headers=self.headers("/api/agent/orders"); headers["X-User-Id"]="other"
            self.assertEqual(self.client.get("/api/agent/orders",headers=headers).status_code,401)
            self.assertEqual(self.client.get("/api/agent/orders",headers=self.headers("/api/agent/orders",timestamp=int(time.time())-120)).status_code,401)

    def test_buyer_admin_roles_and_identity(self):
        with patch.dict(os.environ,{"BACKEND_AUTH_SECRET":"test-secret"}):
            self.assertEqual(self.client.get("/api/merchant/dashboard",headers=self.headers("/api/merchant/dashboard")).status_code,403)
            self.assertEqual(self.client.get("/api/merchant/dashboard",headers=self.headers("/api/merchant/dashboard","admin")).status_code,200)
            self.assertEqual(self.client.get("/api/merchant/dashboard",headers=self.headers("/api/merchant/dashboard","seller")).status_code,200)
            for path in ["/api/audit/ledger", "/api/chaos/scenarios"]:
                self.assertEqual(self.client.get(path,headers=self.headers(path,"seller")).status_code,403)
            self.assertEqual(self.client.get("/api/agent/orders",headers=self.headers("/api/agent/orders")).json()["owner"],"buyer")
            forged = self.headers("/api/agent/orders"); forged["X-Strong-Auth"] = "1"
            self.assertEqual(self.client.get("/api/agent/orders",headers=forged).status_code,401)

    def test_webhook_http_rejects_unsigned_and_invalid_payloads(self):
        app=FastAPI(); app.include_router(payment_router,prefix="/api")
        async def no_db(): yield None
        app.dependency_overrides[get_db]=no_db
        client=TestClient(app)
        self.assertEqual(client.post("/api/razorpay/webhook",json={"event":"payment.captured"}).status_code,400)
        agent=RazorpaySettlementAgent(webhook_secret="webhook-secret")
        for body in [b"not-json",b"[]",b'{"event":"payment.captured"}']:
            signature=hmac.new(b"webhook-secret",body,hashlib.sha256).hexdigest()
            with patch("app.api.razorpay_router.RazorpaySettlementAgent",return_value=agent):
                self.assertEqual(client.post("/api/razorpay/webhook",content=body,headers={"X-Razorpay-Signature":signature}).status_code,400)

    def test_valid_non_capture_event_cannot_regress_payment_state(self):
        app=FastAPI(); app.include_router(payment_router,prefix="/api")
        async def no_db(): yield None
        app.dependency_overrides[get_db]=no_db
        body=b'{"event":"payment.authorized"}'
        signature=hmac.new(b"webhook-secret",body,hashlib.sha256).hexdigest()
        agent=RazorpaySettlementAgent(webhook_secret="webhook-secret")
        with patch("app.api.razorpay_router.RazorpaySettlementAgent",return_value=agent):
            response=TestClient(app).post("/api/razorpay/webhook",content=body,headers={"X-Razorpay-Signature":signature})
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()["status"],"ignored")


class CommerceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.engine=create_async_engine(f"sqlite+aiosqlite:///{Path(self.tmp.name)/'test.db'}", connect_args={"timeout":15})
        async with self.engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
        self.sessions=async_sessionmaker(self.engine,expire_on_commit=False)
        self.token=identity.set({"id":"buyer","role":"buyer"})
        self.agent=RazorpaySettlementAgent(key_id="rzp_test_fixture",key_secret="fixture-secret",webhook_secret="webhook-secret")
        self.agent.client=Mock()
        self.agent.client.order.create.side_effect=lambda data: {"id":"order_"+data["notes"]["quote_id"],"amount":data["amount"],"currency":"INR"}
        async with self.sessions() as db:
            db.add(Product(sku="item_mouse",name="Wireless Mouse",category="mice",description="mouse",cost_price=50,retail_price=100,stock_quantity=1))
            await db.commit()

    async def asyncTearDown(self):
        identity.reset(self.token)
        await self.engine.dispose()
        self.tmp.cleanup()

    async def prepare(self,name="q_one",status="CHECKOUT_READY",expiry=None,owner="buyer"):
        async with self.sessions() as db:
            await persist_quote(db,quote(name,owner,expiry),100)
            stored=await db.get(Quote,name); stored.status=status
            await db.commit()

    async def create(self,name="q_one",amount=100):
        async with self.sessions() as db:
            return await self.agent.create_order(db,RazorpayCreateOrderRequest(quote_id=name,amount_inr=amount,buyer_agent_id="buyer"))

    def payment(self,name="q_one",**changes):
        return {"id":"pay_one","order_id":"order_"+name,"amount":10000,"currency":"INR","status":"captured",**changes}

    async def test_checkout_retries_reuse_order_and_stock_hold(self):
        await self.prepare()
        first=await self.create(); second=await self.create()
        self.assertEqual(first.razorpay_order_id,second.razorpay_order_id)
        self.agent.client.order.create.assert_called_once()
        async with self.sessions() as db:
            self.assertEqual((await db.execute(select(Product.stock_quantity))).scalar(),0)

    async def test_last_unit_cannot_be_reserved_twice(self):
        await self.prepare(); await self.prepare("q_two")
        results=await asyncio.gather(self.create(),self.create("q_two"),return_exceptions=True)
        self.assertEqual(sum(not isinstance(r,Exception) for r in results),1)
        self.agent.client.order.create.assert_called_once()

    async def test_quote_expiry_amount_policy_and_ownership(self):
        for name,status,expiry,owner,amount,expected in [
            ("q_exp","CHECKOUT_READY",dt.datetime.utcnow()-dt.timedelta(seconds=1),"buyer",100,409),
            ("q_price","CHECKOUT_READY",None,"buyer",1,422),
            ("q_gate","QUOTED",None,"buyer",100,403),
            ("q_other","CHECKOUT_READY",None,"other",100,404)]:
            await self.prepare(name,status,expiry,owner)
            with self.assertRaises(HTTPException) as ctx: await self.create(name,amount)
            self.assertEqual(ctx.exception.status_code,expected)
        self.agent.client.order.create.assert_not_called()

    async def test_duplicate_and_concurrent_capture_is_one_commit(self):
        await self.prepare(); await self.create()
        async def settle():
            async with self.sessions() as db:
                return await self.agent.settle_order(db,"order_q_one","pay_one",payment=self.payment())
        results=await asyncio.gather(settle(),settle())
        self.assertTrue(all(r.status=="PAID" for r in results))
        async with self.sessions() as db:
            self.assertEqual((await db.execute(select(func.count(PaymentEvent.id)))).scalar(),1)
            self.assertEqual((await db.execute(select(func.count(AuditEntry.id)))).scalar(),1)
            self.assertEqual((await db.execute(select(Product.stock_quantity))).scalar(),0)

    async def test_wrong_amount_currency_uncaptured_and_unknown_payment(self):
        await self.prepare(); await self.create()
        for changes in [{"amount":1},{"currency":"USD"},{"status":"authorized"},{"order_id":"order_other"}]:
            async with self.sessions() as db:
                with self.assertRaises(HTTPException): await self.agent.settle_order(db,"order_q_one","pay_one",payment=self.payment(**changes))
        async with self.sessions() as db:
            with self.assertRaises(HTTPException) as ctx: await self.agent.settle_order(db,"unknown","pay_one",payment=self.payment())
            self.assertEqual(ctx.exception.status_code,404)

    async def test_provider_failure_never_creates_fake_checkout(self):
        await self.prepare()
        self.agent.client.order.create.side_effect=TimeoutError("uncertain provider result")
        with self.assertRaises(HTTPException): await self.create()
        async with self.sessions() as db:
            self.assertEqual((await db.get(Order,"q_one")).status,"RECONCILIATION_REQUIRED")
        with self.assertRaises(HTTPException): await self.create()
        self.agent.client.order.create.assert_called_once()

    async def test_workflow_idempotency_replays_success_and_failure(self):
        import httpx
        from app.api.agent_router import router
        from app.schemas.agent_schemas import AgentWorkflowResponse
        from unittest.mock import AsyncMock
        app=FastAPI(); app.include_router(router,prefix="/api")
        async def database():
            async with self.sessions() as db: yield db
        app.dependency_overrides[get_db]=database
        result=AgentWorkflowResponse(workflow_id="wf_test",user_goal="Buy a mouse",status="NEEDS_CLARIFICATION",steps=[])
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:
            with patch("app.api.agent_router.CommerceSupervisorAgent") as supervisor:
                supervisor.return_value.execute_workflow=AsyncMock(return_value=result)
                responses=await asyncio.gather(*[client.post("/api/agent/orchestrate",json={"user_goal":"Buy a mouse"},headers={"Idempotency-Key":"same-request"}) for _ in range(2)])
                self.assertTrue(all(r.status_code in {200,409} for r in responses))
                retry=await client.post("/api/agent/orchestrate",json={"user_goal":"Buy a mouse"},headers={"Idempotency-Key":"same-request"})
                self.assertEqual(retry.json()["workflow_id"],"wf_test")
                supervisor.return_value.execute_workflow.assert_awaited_once()
                changed=await client.post("/api/agent/orchestrate",json={"user_goal":"Buy a keyboard"},headers={"Idempotency-Key":"same-request"})
                self.assertEqual(changed.status_code,409)
            with patch("app.api.agent_router.CommerceSupervisorAgent") as supervisor:
                supervisor.return_value.execute_workflow=AsyncMock(side_effect=ValueError("Unavailable pricing"))
                for _ in range(2):
                    response=await client.post("/api/agent/orchestrate",json={"user_goal":"Buy a mouse"},headers={"Idempotency-Key":"failed-request"})
                    self.assertEqual(response.status_code,422)
                supervisor.return_value.execute_workflow.assert_awaited_once()

    async def test_margin_floor_is_not_overridden_by_minimum_discount(self):
        from app.db.models import Merchant
        from app.agents.merchant_agent import MerchantGrowthAgent
        from app.schemas.agent_schemas import DynamicQuoteRequest, BuyerContext
        async with self.sessions() as db:
            product=(await db.execute(select(Product))).scalar_one()
            product.cost_price=80
            db.add(Merchant(id="merchant_techgear_01",name="Test merchant",margin_floor_pct=0.2))
            await db.commit()
            response=await MerchantGrowthAgent().generate_dynamic_quote(db,DynamicQuoteRequest(
                requested_skus=["item_mouse"],buyer_context=BuyerContext(budget_cap_inr=500),preferred_growth_model="conversion_closer"))
            self.assertEqual(response.discount_total,0)
            self.assertGreaterEqual(response.merchant_gross_margin_pct,0.2)

    async def test_concurrent_audit_writers_preserve_chain(self):
        from app.audit.ledger import AuditLedgerEngine
        async def append(index):
            async with self.sessions() as db:
                await AuditLedgerEngine.append_entry(db,"Test","CONCURRENT_EVENT",{"index":index})
        await asyncio.gather(*(append(index) for index in range(5)))
        async with self.sessions() as db:
            result=await AuditLedgerEngine.verify_chain_integrity(db)
            self.assertTrue(result["is_valid"])
            self.assertEqual(result["total_blocks_verified"],5)

    async def test_expired_hold_releases_stock_and_late_capture_requires_review(self):
        await self.prepare(); await self.create()
        from app.db.models import StockReservation
        async with self.sessions() as db:
            hold=(await db.execute(select(StockReservation))).scalar_one()
            hold.expires_at=dt.datetime.utcnow()-dt.timedelta(seconds=1); await db.commit()
            await write_transaction(db); await expire_reservations(db); await db.commit()
        async with self.sessions() as db:
            settled=await self.agent.settle_order(db,"order_q_one","pay_one",payment=self.payment())
            self.assertEqual(settled.status,"PAID_REQUIRES_REVIEW")
            self.assertEqual((await db.execute(select(Product.stock_quantity))).scalar(),1)

    async def test_high_value_gate_and_insufficient_adjustment_stay_closed(self):
        from app.db.models import HITLApprovalQueue
        await self.prepare(status="QUOTED")
        async with self.sessions() as db:
            db.add(HITLApprovalQueue(id="gate",order_id="q_one",buyer_agent_id="buyer",trigger_reason="BUDGET",details_json=json.dumps({"quote":quote().model_dump(),"tier":"TIER_2_GATED_HITL"})))
            await db.commit()
        async with self.sessions() as db:
            result=await CommerceSupervisorAgent().resume_hitl_workflow(db,"gate","ADJUST_BUDGET",50)
            self.assertFalse(result["success"])
            self.assertEqual((await db.get(HITLApprovalQueue,"gate")).status,"PENDING")
        async with self.sessions() as db:
            gate=await db.get(HITLApprovalQueue,"gate")
            gate.details_json=json.dumps({"quote":quote().model_dump(),"tier":"TIER_3_HARD_GATE"})
            await db.commit()
        async with self.sessions() as db:
            result=await CommerceSupervisorAgent().resume_hitl_workflow(db,"gate","APPROVE")
            self.assertFalse(result["success"])
            self.assertIn("authenticator",result["message"])

    def test_webhook_signature_and_refresh_rate_constraints(self):
        self.assertFalse(self.agent.verify_webhook_signature(b"{}",None))
        self.assertFalse(self.agent.verify_webhook_signature(b"{}","invalid"))
        self.assertTrue(self.agent.verify_webhook_signature(b"{}",hmac.new(b"webhook-secret",b"{}",hashlib.sha256).hexdigest()))
        from types import SimpleNamespace
        product=SimpleNamespace(name="4K 120Hz Monitor",description="",specifications="{}",sku="item_monitor",retail_price=100,stock_quantity=1)
        self.assertEqual(select_products([product],parse_purchase_intent("Buy 144 Hz monitor",500)),[])

if __name__ == "__main__": unittest.main()
