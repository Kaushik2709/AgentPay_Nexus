"""Approval response regressions; no database, model download, or provider calls."""
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.agent_router import router
from app.db.session import get_db


class ApprovalContractTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router, prefix="/api")

        async def fake_db():
            yield None

        app.dependency_overrides[get_db] = fake_db
        self.client = TestClient(app)

    def submit(self, result, action="APPROVE"):
        with patch("app.api.agent_router.CommerceSupervisorAgent") as supervisor:
            supervisor.return_value.resume_hitl_workflow = AsyncMock(return_value=result)
            return self.client.post("/api/agent/hitl/resume", json={"gate_id": "gate_demo", "action": action})

    def test_approval_preserves_provider_checkout_payload(self):
        order = {
            "razorpay_order_id": "order_demo", "amount_in_paise": 125000,
            "amount_inr": 1250, "currency": "INR", "status": "created",
            "receipt": "receipt_demo", "payment_link": "", "key_id": "rzp_test_public_demo", "notes": {},
        }
        response = self.submit({"success": True, "status": "APPROVED", "message": "Approved", "razorpay_order": order, "next_step": "TRIGGER_CHECKOUT_MODAL"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["razorpay_order"], order)
        self.assertEqual(body["order_id"], order["razorpay_order_id"])
        self.assertEqual(body["next_step"], "TRIGGER_CHECKOUT_MODAL")
        self.assertNotIn("key_secret", body["razorpay_order"])

    def test_rejection_does_not_require_checkout_payload(self):
        response = self.submit({"success": True, "status": "REJECTED", "message": "Rejected"}, "REJECT")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["razorpay_order"])

    def test_already_resolved_gate_returns_failure(self):
        response = self.submit({"success": False, "message": "Gate already resolved"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Gate already resolved")


if __name__ == "__main__":
    unittest.main()
