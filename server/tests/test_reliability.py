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
import sys
import uuid
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.auth import authenticate, identity
from app.commerce import persist_quote, write_transaction, expire_reservations
from app.db.models import Base, Product, Quote, Order, PaymentEvent, AuditEntry, StockReservation, Policy, HITLApprovalQueue
from app.razorpay.settlement_agent import RazorpaySettlementAgent
from app.schemas.agent_schemas import DynamicQuoteResponse, QuoteItem, RazorpayCreateOrderRequest
from app.agents.supervisor import CommerceSupervisorAgent
from app.agents.purchase_intent import parse_purchase_intent, select_products
from app.api.razorpay_router import router as payment_router
from app.db.session import get_db


def quote(name="q_one", owner="buyer", expiry=None):
    value = DynamicQuoteResponse(quote_id=name, buyer_agent_id=owner,
        items=[QuoteItem(sku="item_mouse", name="Wireless Mouse", unit_price=100, original_price=100, category="mice")],
        base_subtotal=100, discount_total=0, warranty_total=0, final_total=100,
        merchant_gross_margin_pct=0.5, applied_growth_model="standard", savings_breakdown="",
        merchant_signature="signed", explainability_note="", expires_at=(expiry or dt.datetime.utcnow()+dt.timedelta(minutes=15)).isoformat())
    from app.commerce import quote_signature
    value.merchant_signature = quote_signature(value, "sec_live_merchant_default")
    return value


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
    if sys.platform == "win32":
        loop_factory = asyncio.SelectorEventLoop

    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.admin_engine = None
        if getattr(self, "postgres_url", None):
            self.schema = "test_" + uuid.uuid4().hex
            self.admin_engine = create_async_engine(self.postgres_url)
            async with self.admin_engine.begin() as conn:
                await conn.execute(text(f'CREATE SCHEMA "{self.schema}"'))
            self.engine=create_async_engine(self.postgres_url, connect_args={"options":f"-csearch_path={self.schema}"})
        else:
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
        if self.admin_engine:
            async with self.admin_engine.begin() as conn:
                await conn.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
            await self.admin_engine.dispose()
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

    async def test_capture_of_old_order_counts_in_current_rolling_spend(self):
        from app.agents.policy_guard import PolicyGuardAgent
        await self.prepare(); await self.create()
        async with self.sessions() as db:
            (await db.get(Order,"q_one")).created_at=dt.datetime.utcnow()-dt.timedelta(days=2)
            await db.commit()
            result=await self.agent.settle_order(db,"order_q_one","pay_one",payment=self.payment())
            self.assertEqual(await PolicyGuardAgent()._get_24h_spent_velocity(db,"buyer"),100)
            timestamp=result.settled_at
        async with self.sessions() as db:
            result=await self.agent.settle_order(db,"order_q_one","pay_one",payment=self.payment())
            self.assertEqual(result.settled_at,timestamp)

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

    async def gated(self, categories='["mice"]', max_tx=50):
        from app.agents.policy_guard import PolicyGuardAgent
        await self.prepare(status="QUOTED")
        async with self.sessions() as db:
            db.add(Policy(id="policy", user_id="buyer", max_tx_amount=max_tx,
                daily_velocity_cap=50000, category_whitelist=categories))
            await db.commit()
            value = DynamicQuoteResponse(**json.loads((await db.get(Quote,"q_one")).data_json))
            result = await PolicyGuardAgent().evaluate_quote(db, value, "buyer", 100)
            return result.hitl_gate_id

    async def test_category_violation_cannot_be_human_overridden(self):
        gate = await self.gated(categories='["monitors"]')
        async with self.sessions() as db:
            result = await CommerceSupervisorAgent().resume_hitl_workflow(db, gate, "APPROVE")
            self.assertFalse(result["success"])
            self.assertIn("Category", result["message"])
        self.agent.client.order.create.assert_not_called()

    async def test_changed_cap_with_same_violation_code_requires_new_approval(self):
        gate = await self.gated()
        async with self.sessions() as db:
            (await db.get(Policy, "policy")).max_tx_amount = 25
            await db.commit()
        async with self.sessions() as db:
            result = await CommerceSupervisorAgent().resume_hitl_workflow(db, gate, "APPROVE")
            self.assertFalse(result["success"])
            self.assertIn("Policy boundaries changed", result["message"])

    async def test_expired_or_consumed_approval_cannot_prepare_checkout(self):
        gate = await self.gated()
        for expired in (True, False):
            async with self.sessions() as db:
                stored = await db.get(Quote, "q_one")
                stored.expires_at = dt.datetime.utcnow() + dt.timedelta(seconds=-1 if expired else 300)
                stored.status = "QUOTED" if expired else "CONSUMED"
                await db.commit()
            async with self.sessions() as db:
                result = await CommerceSupervisorAgent().resume_hitl_workflow(db, gate, "APPROVE")
                self.assertFalse(result["success"])
        self.agent.client.order.create.assert_not_called()

    async def test_stale_signature_and_tampered_lines_never_reach_provider(self):
        await self.prepare()
        for change in ("merchant_signature", "unit_price"):
            async with self.sessions() as db:
                stored = await db.get(Quote, "q_one")
                data = quote().model_dump()
                if change == "unit_price":
                    data["items"][0]["unit_price"] = 1
                else:
                    data["merchant_signature"] = "stale-key-signature"
                stored.data_json = json.dumps(data)
                await db.commit()
            with self.assertRaises(HTTPException):
                await self.create()
        self.agent.client.order.create.assert_not_called()

    async def test_partial_cart_reservation_rolls_back_even_if_caller_commits(self):
        from app.commerce import reserve_stock
        value = quote()
        value.items.append(QuoteItem(sku="z_missing", name="Missing", unit_price=100, original_price=100))
        async with self.sessions() as db:
            await write_transaction(db)
            with self.assertRaises(ValueError):
                await reserve_stock(db, value)
            await db.commit()
        async with self.sessions() as db:
            self.assertEqual((await db.execute(select(Product.stock_quantity))).scalar(), 1)
            self.assertEqual((await db.execute(select(func.count(StockReservation.id)))).scalar(), 0)

    async def test_multi_item_expiry_releases_all_lines_exactly_once(self):
        value = quote()
        value.items.append(QuoteItem(sku="item_keyboard", name="Keyboard", unit_price=100, original_price=100, category="keyboards"))
        value.final_total = value.base_subtotal = 200
        from app.commerce import quote_signature
        value.merchant_signature = quote_signature(value, "sec_live_merchant_default")
        async with self.sessions() as db:
            db.add(Product(sku="item_keyboard", name="Keyboard", category="keyboards", description="", cost_price=50, retail_price=100, stock_quantity=1))
            await persist_quote(db, value, 200)
            (await db.get(Quote, value.quote_id)).status = "CHECKOUT_READY"
            await db.commit()
        await self.create(amount=200)
        async with self.sessions() as db:
            for hold in (await db.execute(select(StockReservation))).scalars():
                hold.expires_at = dt.datetime.utcnow()-dt.timedelta(seconds=1)
            await db.commit()
        for _ in range(2):
            async with self.sessions() as db:
                await write_transaction(db); await expire_reservations(db); await db.commit()
        async with self.sessions() as db:
            self.assertEqual(list((await db.execute(select(Product.stock_quantity))).scalars()), [1, 1])
            self.assertTrue(all(s == "RELEASED" for s in (await db.execute(select(StockReservation.status))).scalars()))

    async def test_provider_timeout_recovers_by_receipt_without_second_submission(self):
        from app.maintenance import reconcile_once
        await self.prepare()
        self.agent.client.order.create.side_effect = TimeoutError("response lost after submission")
        with self.assertRaises(HTTPException): await self.create()
        async with self.sessions() as db:
            receipt = json.loads((await db.get(Quote, "q_one")).data_json)["provider_receipt"]
        self.agent.client.order.all.return_value = {"items": [{"id":"order_q_one", "receipt":receipt,
            "amount":10000,"currency":"INR","notes":{"quote_id":"q_one"}}]}
        self.agent.client.order.payments.return_value = {"items": [self.payment()]}
        await reconcile_once(self.sessions, self.agent)
        await reconcile_once(self.sessions, self.agent)
        async with self.sessions() as db:
            self.assertEqual((await db.get(Order,"q_one")).status, "PAID")
            self.assertEqual((await db.execute(select(func.count(PaymentEvent.id)))).scalar(), 1)
        self.agent.client.order.create.assert_called_once()

    async def test_unresolved_or_conflicting_provider_lookup_keeps_stock_held(self):
        await self.prepare()
        self.agent.client.order.create.side_effect = TimeoutError()
        with self.assertRaises(HTTPException): await self.create()
        for items in ([], [{"id":"wrong","amount":1}], [{"id":"a"},{"id":"b"}]):
            self.agent.client.order.all.return_value = {"items": items}
            async with self.sessions() as db:
                self.assertFalse(await self.agent.recover_order(db,"q_one"))
        async with self.sessions() as db:
            for hold in (await db.execute(select(StockReservation))).scalars():
                hold.expires_at = dt.datetime.utcnow()-dt.timedelta(days=2)
            (await db.get(Order,"q_one")).created_at = dt.datetime.utcnow()-dt.timedelta(days=2)
            await db.commit()
            await write_transaction(db); await expire_reservations(db); await db.commit()
        from app.agents.policy_guard import PolicyGuardAgent
        async with self.sessions() as db:
            self.assertEqual((await db.get(Order,"q_one")).status,"RECONCILIATION_REQUIRED")
            self.assertEqual((await db.execute(select(Product.stock_quantity))).scalar(),0)
            self.assertEqual(await PolicyGuardAgent()._get_24h_spent_velocity(db,"buyer"),100)

    async def test_no_write_lock_is_held_during_provider_submission(self):
        import threading
        started, release = threading.Event(), threading.Event()
        await self.prepare()
        def provider(data):
            started.set()
            if not release.wait(5): raise TimeoutError("test release not signalled")
            return {"id":"order_q_one","amount":10000,"currency":"INR"}
        self.agent.client.order.create.side_effect = provider
        task = asyncio.create_task(self.create())
        try:
            self.assertTrue(await asyncio.to_thread(started.wait, 3))
            async def writer():
                async with self.sessions() as db:
                    await write_transaction(db)
                    self.assertEqual((await db.get(Order,"q_one")).status,"CREATING")
                    await db.commit()
            await asyncio.wait_for(writer(), 2)
        finally:
            release.set()
            await task

    async def test_recovery_capture_racing_create_response_never_regresses_paid(self):
        import threading
        started,release=threading.Event(),threading.Event()
        await self.prepare()
        def provider(data):
            started.set()
            if not release.wait(5): raise TimeoutError()
            return {"id":"order_q_one","amount":10000,"currency":"INR"}
        self.agent.client.order.create.side_effect=provider
        task=asyncio.create_task(self.create())
        try:
            self.assertTrue(await asyncio.to_thread(started.wait,3))
            async with self.sessions() as db:
                receipt=json.loads((await db.get(Quote,"q_one")).data_json)["provider_receipt"]
            self.agent.client.order.all.return_value={"items":[{"id":"order_q_one","amount":10000,
                "currency":"INR","receipt":receipt,"notes":{"quote_id":"q_one"}}]}
            async with self.sessions() as db: self.assertTrue(await self.agent.recover_order(db,"q_one"))
            async with self.sessions() as db:
                await self.agent.settle_order(db,"order_q_one","pay_one",payment=self.payment())
        finally:
            release.set(); await task
        async with self.sessions() as db: self.assertEqual((await db.get(Order,"q_one")).status,"PAID")

    async def test_cancelled_provider_submission_is_durable_and_uncertain(self):
        import threading
        started,release=threading.Event(),threading.Event()
        await self.prepare()
        def provider(data):
            started.set(); release.wait(5)
            return {"id":"order_q_one","amount":10000,"currency":"INR"}
        self.agent.client.order.create.side_effect=provider
        task=asyncio.create_task(self.create())
        try:
            self.assertTrue(await asyncio.to_thread(started.wait,3))
            task.cancel()
            with self.assertRaises(asyncio.CancelledError): await task
        finally:
            release.set()
        async with self.sessions() as db:
            self.assertEqual((await db.get(Order,"q_one")).status,"RECONCILIATION_REQUIRED")
            self.assertEqual((await db.execute(select(Product.stock_quantity))).scalar(),0)

    async def test_changed_policy_between_quote_and_direct_checkout_is_rechecked(self):
        await self.prepare()
        async with self.sessions() as db:
            db.add(Policy(id="p",user_id="buyer",max_tx_amount=50,daily_velocity_cap=50000))
            await db.commit()
        with self.assertRaises(HTTPException) as result: await self.create()
        self.assertEqual(result.exception.status_code,409)
        self.agent.client.order.create.assert_not_called()

    async def test_concurrent_checkout_reserves_rolling_spend_capacity(self):
        await self.prepare(); await self.prepare("q_two")
        async with self.sessions() as db:
            product=(await db.execute(select(Product))).scalar_one(); product.stock_quantity=2
            db.add(Policy(id="p",user_id="buyer",max_tx_amount=1000,daily_velocity_cap=150))
            await db.commit()
        results=await asyncio.gather(self.create(),self.create("q_two"),return_exceptions=True)
        self.assertEqual(sum(not isinstance(result,Exception) for result in results),1)
        async with self.sessions() as db:
            self.assertEqual((await db.execute(select(Product.stock_quantity))).scalar(),1)

    async def test_missing_reservation_line_makes_capture_require_review(self):
        await self.prepare(); await self.create()
        async with self.sessions() as db:
            order=await db.get(Order,"q_one")
            order.items_json=json.dumps([*json.loads(order.items_json),{"sku":"missing","quantity":1}])
            await db.commit()
            result=await self.agent.settle_order(db,"order_q_one","pay_one",payment=self.payment())
            self.assertEqual(result.status,"PAID_REQUIRES_REVIEW")

    async def test_capture_does_not_depend_on_mutable_quote_amount(self):
        await self.prepare(); await self.create()
        async with self.sessions() as db:
            (await db.get(Quote,"q_one")).amount_paise=1
            await db.commit()
            with self.assertRaises(HTTPException):
                await self.agent.settle_order(db,"order_q_one","pay_one",payment=self.payment(amount=1))
        async with self.sessions() as db:
            result=await self.agent.settle_order(db,"order_q_one","pay_one",payment=self.payment())
            self.assertEqual(result.status,"PAID")

    async def test_same_event_id_cannot_settle_another_order(self):
        await self.prepare(); await self.create()
        async with self.sessions() as db:
            await self.agent.settle_order(db,"order_q_one","pay_one",payment=self.payment(),event_id="event_one")
        await self.prepare("q_two")
        async with self.sessions() as db:
            (await db.execute(select(Product))).scalar_one().stock_quantity=1; await db.commit()
        await self.create("q_two")
        async with self.sessions() as db:
            with self.assertRaises(HTTPException) as result:
                await self.agent.settle_order(db,"order_q_two","pay_two",payment=self.payment("q_two",id="pay_two"),event_id="event_one")
            self.assertEqual(result.exception.status_code,409)
        async with self.sessions() as db:
            self.assertEqual((await db.get(Order,"q_two")).status,"CREATED")

    async def test_provider_fetch_failure_cannot_mark_order_paid(self):
        await self.prepare(); await self.create()
        self.agent.client.payment.fetch.side_effect=TimeoutError()
        async with self.sessions() as db:
            with self.assertRaises(HTTPException) as result:
                await self.agent.settle_order(db,"order_q_one","pay_one")
            self.assertEqual(result.exception.status_code,503)
            self.assertEqual((await db.get(Order,"q_one")).status,"CREATED")

    async def test_response_persistence_failure_recovers_creating_attempt(self):
        from unittest.mock import AsyncMock
        await self.prepare()
        with patch.object(self.agent,"_bind_provider_order",AsyncMock(side_effect=RuntimeError("database connection lost"))):
            with self.assertRaises(RuntimeError): await self.create()
        async with self.sessions() as db:
            self.assertEqual((await db.get(Order,"q_one")).status,"CREATING")
            receipt=json.loads((await db.get(Quote,"q_one")).data_json)["provider_receipt"]
        self.agent.client.order.all.return_value={"items":[{"id":"order_q_one","receipt":receipt,
            "amount":10000,"currency":"INR","notes":{"quote_id":"q_one"}}]}
        async with self.sessions() as db:
            self.assertTrue(await self.agent.recover_order(db,"q_one"))
        self.agent.client.order.create.assert_called_once()
        self.assertEqual((await self.create()).razorpay_order_id,"order_q_one")

    async def test_pricing_strategies_keep_fractional_rupees_on_minor_unit_grid(self):
        from app.db.models import Merchant
        from app.agents.merchant_agent import MerchantGrowthAgent
        from app.schemas.agent_schemas import DynamicQuoteRequest, BuyerContext
        async with self.sessions() as db:
            product=(await db.execute(select(Product))).scalar_one()
            product.retail_price=19.99; product.cost_price=10.01
            product.warranty_price=0.15; product.is_subscription=True
            db.add(Merchant(id="merchant_techgear_01",name="Test",margin_floor_pct=0.2))
            await db.commit()
            for model in ("conversion_closer","quality_upgrade","bulk_subscription","value_services"):
                value=await MerchantGrowthAgent().generate_dynamic_quote(db,DynamicQuoteRequest(
                    requested_skus=["item_mouse"],buyer_context=BuyerContext(budget_cap_inr=500,allow_autonomous_upsell=True),preferred_growth_model=model))
                from app.commerce import paise
                self.assertEqual(sum(paise(item.unit_price)*item.quantity for item in value.items),paise(value.final_total))
                self.assertGreaterEqual(value.merchant_gross_margin_pct,0.2)

    async def test_audit_genesis_link_cannot_be_replaced_even_with_new_hash(self):
        from app.audit.ledger import AuditLedgerEngine
        async with self.sessions() as db:
            entry=await AuditLedgerEngine.append_entry(db,"test","event",{})
            entry.prev_hash="f"*64
            entry.entry_hash=AuditLedgerEngine.compute_hash(entry.sequence_number,entry.actor,entry.action,entry.timestamp,entry.prev_hash,entry.payload_json)
            await db.commit()
            self.assertFalse((await AuditLedgerEngine.verify_chain_integrity(db))["is_valid"])

    async def test_money_rounding_and_fractional_paise_provider_amount(self):
        from app.commerce import paise
        self.assertEqual(paise("1.005"),101)
        await self.prepare(); await self.create()
        async with self.sessions() as db:
            with self.assertRaises(HTTPException):
                await self.agent.settle_order(db,"order_q_one","pay_one",payment=self.payment(amount=10000.0))

    def test_live_keys_do_not_create_provider_adapter(self):
        self.assertIsNone(RazorpaySettlementAgent(key_id="rzp_live_forbidden",key_secret="fixture").client)

    def test_provider_transport_has_timeouts_and_order_retry_is_disabled(self):
        from app.razorpay.settlement_agent import ProviderSession
        with patch("requests.Session.request",return_value=Mock()) as request:
            ProviderSession().request("GET","https://example.invalid")
            self.assertEqual(request.call_args.kwargs["timeout"],(3.05,10))
        agent=RazorpaySettlementAgent(key_id="rzp_test_fixture",key_secret="fixture")
        self.assertFalse(agent.client.retry_enabled)

    def test_webhook_signature_and_refresh_rate_constraints(self):
        self.assertFalse(self.agent.verify_webhook_signature(b"{}",None))
        self.assertFalse(self.agent.verify_webhook_signature(b"{}","invalid"))
        self.assertTrue(self.agent.verify_webhook_signature(b"{}",hmac.new(b"webhook-secret",b"{}",hashlib.sha256).hexdigest()))
        from types import SimpleNamespace
        product=SimpleNamespace(name="4K 120Hz Monitor",description="",specifications="{}",sku="item_monitor",retail_price=100,stock_quantity=1)
        self.assertEqual(select_products([product],parse_purchase_intent("Buy 144 Hz monitor",500)),[])

if __name__ == "__main__": unittest.main()
