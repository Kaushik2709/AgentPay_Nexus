"""All backend routes against an isolated database; Razorpay is a test double."""
import asyncio
import hashlib
import hmac
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.main import app as production_app
from app.db.models import Base
from app.db.session import get_db
from app.db.seed import seed_database
from app.razorpay.settlement_agent import RazorpaySettlementAgent


class EndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        path = Path(self.tmp.name) / "endpoints.db"
        engine = create_engine(f"sqlite:///{path}")
        Base.metadata.create_all(engine)
        with patch("app.db.seed.SyncSessionLocal", sessionmaker(engine)), patch("app.db.seed.init_db"):
            seed_database()
        engine.dispose()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
        sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async def database():
            async with sessions() as db:
                yield db
        app = production_app
        app.dependency_overrides[get_db] = database
        self.client = TestClient(app)
        self.env = patch.dict(os.environ, {"BACKEND_AUTH_SECRET": "endpoint-secret"})
        self.env.start()
        self.provider = RazorpaySettlementAgent(key_id="rzp_test_fixture", key_secret="fixture-secret", webhook_secret="webhook-secret")
        self.provider.client = Mock()
        self.provider.client.order.create.side_effect = lambda data: {"id": "order_" + data["notes"]["quote_id"], "amount": data["amount"], "currency": "INR"}
        self.patches = [patch(f"{module}.RazorpaySettlementAgent", return_value=self.provider) for module in ["app.api.razorpay_router", "app.agents.supervisor"]]
        for p in self.patches: p.start()

    def tearDown(self):
        for p in self.patches: p.stop()
        self.env.stop()
        self.client.close()
        production_app.dependency_overrides.clear()
        asyncio.run(self.engine.dispose())
        self.tmp.cleanup()

    def request(self, method, path, body=None, role="buyer", uid="test-buyer", expected=200, extra=None):
        raw = json.dumps(body).encode() if body is not None else b""
        stamp = str(int(time.time()))
        message = "\n".join([stamp, method, path, uid, role, "0", hashlib.sha256(raw).hexdigest()])
        headers = {"Content-Type": "application/json", "X-User-Id": uid, "X-User-Role": role,
                   "X-Auth-Timestamp": stamp, "X-Auth-Signature": hmac.new(b"endpoint-secret", message.encode(), hashlib.sha256).hexdigest(), **(extra or {})}
        response = self.client.request(method, path, content=raw, headers=headers)
        self.assertEqual(response.status_code, expected, f"{method} {path}: {response.text}")
        return response.json()

    def workflow(self, goal="Buy a 4K monitor", budget=25000, **kwargs):
        return {"user_goal": goal, "budget_cap_inr": budget, "strict_items_only": True, **kwargs}

    def test_read_routes_and_roles(self):
        for path in ["/api/health", "/api/me", "/api/catalog/products", "/api/policy/config", "/api/agent/orders", "/api/agent/hitl/pending"]:
            with self.subTest(path=path): self.request("GET", path)
        self.assertTrue(all(p["cost_price"] is None for p in self.request("GET", "/api/catalog/products")))
        for path in ["/api/merchant/dashboard", "/api/audit/trail", "/api/audit/verify"]:
            self.request("GET", path, expected=403)
            self.request("GET", path, role="admin")
        self.assertEqual(self.request("GET", "/api/merchant/dashboard", role="seller")["metrics"]["avg_order_value_inr"], 0)
        self.request("GET", "/api/audit/verify", role="seller", expected=403)
        self.request("GET", "/api/audit/trail?limit=0", role="admin", expected=422)
        self.assertTrue(self.request("GET", "/api/audit/verify", role="admin")["is_valid"])

    def test_catalog_quote_and_validation(self):
        products = self.request("POST", "/api/catalog/agent-query", {"category": "monitors", "max_price_inr": 20000})
        self.assertTrue(products)
        sku = products[0]["sku"]
        self.request("PATCH", f"/api/catalog/products/{sku}", {"stock_quantity": 20}, expected=403)
        self.request("PATCH", f"/api/catalog/products/{sku}", {"stock_quantity": 20}, role="seller")
        self.request("PATCH", f"/api/catalog/products/{sku}", {"stock_quantity": -1}, role="seller", expected=422)
        self.request("PATCH", "/api/catalog/products/missing", {}, role="seller", expected=404)
        payload = {"requested_skus": [sku], "buyer_agent_id": "spoofed", "buyer_context": {"budget_cap_inr": 25000}}
        quote = self.request("POST", "/api/agent/quote", payload)
        self.assertEqual(quote["buyer_agent_id"], "test-buyer")
        for skus in [[], ["missing"], [sku, sku]]:
            self.request("POST", "/api/agent/quote", {**payload, "requested_skus": skus}, expected=422)
        self.request("POST", "/api/catalog/agent-query", {"max_price_inr": -1}, expected=422)

    def test_policy_and_merchant_writes(self):
        self.request("PUT", "/api/policy/config", {"max_tx_amount": 12000})
        own = self.request("GET", "/api/policy/config?user_id=someone-else")
        self.assertEqual(own["user_id"], "test-buyer")
        self.assertEqual(own["max_tx_amount"], 12000)
        self.assertNotEqual(self.request("GET", "/api/policy/config", uid="second-buyer")["max_tx_amount"], 12000)
        self.request("PUT", "/api/policy/config", {"max_tx_amount": -1}, expected=422)
        self.request("POST", "/api/merchant/config", {"margin_floor_pct": .25, "active_growth_models": ["conversion_closer"]}, role="seller")
        self.assertEqual(self.request("GET", "/api/merchant/dashboard", role="seller")["margin_floor_pct"], .25)
        self.request("POST", "/api/merchant/config", {"active_growth_models": ["nonexistent"]}, role="seller", expected=422)
        self.request("POST", "/api/merchant/config", {"margin_floor_pct": -1}, role="seller", expected=422)

    def test_workflow_gate_isolation_and_replay(self):
        self.request("PUT", "/api/policy/config", {"max_tx_amount": 1000})
        body = self.workflow()
        response = self.request("POST", "/api/agent/orchestrate", body, extra={"Idempotency-Key": "endpoint-run"})
        self.assertEqual(response["status"], "GATED_HITL")
        replay = self.request("POST", "/api/agent/orchestrate", body, extra={"Idempotency-Key": "endpoint-run"})
        self.assertEqual(replay["workflow_id"], response["workflow_id"])
        self.request("POST", "/api/agent/orchestrate", self.workflow(budget=24000), extra={"Idempotency-Key": "endpoint-run"}, expected=409)
        gate = response["hitl_gate_id"]
        self.assertTrue(self.request("GET", "/api/agent/hitl/pending"))
        self.assertEqual(self.request("GET", "/api/agent/hitl/pending", uid="second-buyer"), [])
        self.request("POST", "/api/agent/hitl/resume", {"gate_id": gate, "action": "REJECT"}, uid="second-buyer", expected=400)
        self.request("POST", "/api/agent/hitl/resume", {"gate_id": gate, "action": "REJECT"})
        self.assertEqual(self.request("GET", "/api/agent/hitl/pending"), [])
        for body in [self.workflow(goal=" "), self.workflow(budget=-1), self.workflow(force_growth_model="unknown")]:
            self.request("POST", "/api/agent/orchestrate", body, expected=422)
        self.request("POST", "/api/agent/orchestrate", self.workflow(simulate_stock_race=True), expected=403)

    def test_payment_capture_and_webhook(self):
        flow = self.request("POST", "/api/agent/orchestrate", self.workflow())
        self.assertEqual(flow["status"], "AWAITING_PAYMENT")
        quote, checkout = flow["quote"], flow["razorpay_order"]
        self.assertEqual(flow["total_spent"], 0)
        self.request("POST", "/api/razorpay/create-order", {"quote_id": quote["quote_id"], "amount_inr": quote["final_total"], "buyer_agent_id": "test-buyer"})
        self.request("POST", "/api/razorpay/create-order", {"quote_id": quote["quote_id"], "amount_inr": quote["final_total"], "buyer_agent_id": "second-buyer"}, uid="second-buyer", expected=404)
        order_id = checkout["razorpay_order_id"]
        self.provider.client.payment.fetch.return_value = {"id": "pay_fixture", "order_id": order_id, "amount": checkout["amount_in_paise"], "currency": "INR", "status": "captured"}
        verification = {"razorpay_order_id": order_id, "razorpay_payment_id": "pay_fixture", "razorpay_signature": "invalid"}
        self.request("POST", "/api/razorpay/verify-payment", verification, expected=400)
        verification["razorpay_signature"] = self.provider._generate_hmac_signature(order_id, "pay_fixture")
        self.assertEqual(self.request("POST", "/api/razorpay/verify-payment", verification)["status"], "PAID")
        self.assertEqual(self.request("POST", "/api/razorpay/verify-payment", verification)["status"], "PAID")
        body = json.dumps({"event": "payment.captured", "payload": {"payment": {"entity": self.provider.client.payment.fetch.return_value}}}).encode()
        headers = {"X-Razorpay-Signature": hmac.new(b"webhook-secret", body, hashlib.sha256).hexdigest(), "X-Razorpay-Event-Id": "event-fixture"}
        for _ in range(2): self.assertEqual(self.client.post("/api/razorpay/webhook", content=body, headers=headers).status_code, 200)
        self.assertEqual(self.request("GET", "/api/agent/orders")[0]["status"], "PAID")
        self.assertEqual(self.request("GET", "/api/agent/orders", uid="second-buyer"), [])
        metrics = self.request("GET", "/api/merchant/dashboard", role="seller")["metrics"]
        self.assertEqual(metrics["total_orders_completed"], 1)
        self.assertEqual(metrics["total_revenue_inr"], quote["final_total"])
        self.assertTrue(self.request("GET", "/api/audit/verify", role="admin")["is_valid"])

    def test_malformed_signed_webhook(self):
        for payload in [{"event": "payment.captured", "payload": []}, {"event": "payment.captured", "payload": {"payment": []}}]:
            body = json.dumps(payload).encode()
            signature = hmac.new(b"webhook-secret", body, hashlib.sha256).hexdigest()
            self.assertEqual(self.client.post("/api/razorpay/webhook", content=body, headers={"X-Razorpay-Signature": signature, "X-Razorpay-Event-Id": "malformed"}).status_code, 400)

    def test_chaos_routes(self):
        for scenario in ["budget_breach", "stock_race_condition", "strict_upsell_rejection"]:
            self.request("POST", "/api/chaos/trigger", {"scenario_id": scenario}, expected=403)
            result = self.request("POST", "/api/chaos/trigger", {"scenario_id": scenario}, role="admin")
            expected = {"budget_breach": "GATED_HITL", "stock_race_condition": "FAILED_ROLLED_BACK", "strict_upsell_rejection": "AWAITING_PAYMENT"}
            self.assertEqual(result["status"], expected[scenario])
        self.request("POST", "/api/chaos/trigger", {"scenario_id": "unknown"}, role="admin", expected=422)
