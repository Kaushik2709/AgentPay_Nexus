"""Separate-process checkout worker; all payment interactions are local mocks."""
import asyncio
import sys
import time
from unittest.mock import Mock
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.auth import identity
from app.razorpay.settlement_agent import RazorpaySettlementAgent
from app.schemas.agent_schemas import RazorpayCreateOrderRequest


async def operation(url, connect_args, quote_id, action):
    engine = create_async_engine(url, connect_args=connect_args)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    token = identity.set({"id":"buyer","role":"buyer"})
    agent = RazorpaySettlementAgent(key_id="rzp_test_fixture",key_secret="fixture-secret")
    agent.client = Mock()
    agent.client.order.create.side_effect = lambda data: {
        "id":"order_"+data["notes"]["quote_id"],"amount":data["amount"],"currency":"INR"}
    started = time.perf_counter()
    try:
        async with sessions() as db:
            if action == "create":
                result = await agent.create_order(db, RazorpayCreateOrderRequest(
                    quote_id=quote_id,amount_inr=100,buyer_agent_id="buyer"))
                status = result.status
            else:
                payment = {"id":"pay_one","order_id":"order_"+quote_id,
                    "amount":10000,"currency":"INR","status":"captured"}
                result = await agent.settle_order(db, "order_"+quote_id, "pay_one", payment=payment)
                status = result.status
        return {"status":status,"provider_submissions":agent.client.order.create.call_count,
                "latency_ms":(time.perf_counter()-started)*1000}
    except (HTTPException, ValueError) as error:
        return {"status":getattr(error,"status_code","stock_conflict"),
                "provider_submissions":agent.client.order.create.call_count,
                "latency_ms":(time.perf_counter()-started)*1000}
    finally:
        identity.reset(token)
        await engine.dispose()


def worker(url, connect_args, quote_id, action, ready, start, output):
    ready.put(True)
    if not start.wait(30):
        output.put({"error":"worker start timeout"}); return
    try:
        if sys.platform == "win32":
            result = asyncio.run(operation(url,connect_args,quote_id,action),loop_factory=asyncio.SelectorEventLoop)
        else:
            result = asyncio.run(operation(url,connect_args,quote_id,action))
        output.put(result)
    except Exception as error:
        output.put({"error":type(error).__name__ + ": " + str(error)})
