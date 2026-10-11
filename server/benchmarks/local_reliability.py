"""Controlled local API and four-process benchmarks. Never contacts Razorpay.

python -m benchmarks.local_reliability --output ../docs/benchmarks/local.json
TEST_POSTGRES_URL optionally adds actual PostgreSQL process measurements.
"""
import argparse
import asyncio
import hashlib
import hmac
import json
import math
import os
import platform
import datetime
import sqlite3
from importlib.metadata import version
import statistics
import time
from pathlib import Path
from unittest.mock import patch
import httpx
from fastapi import FastAPI
from app.auth import authenticate
from app.api.agent_router import router
from app.db.session import get_db
from tests import test_reliability as fixtures
from tests.test_process_contention import ProcessContentionTests, contend


def stats(values):
    ordered=sorted(values)
    return {"n":len(values),"p50_ms":round(statistics.median(ordered),3),
            "p95_ms":round(ordered[math.ceil(len(ordered)*0.95)-1],3),
            "max_ms":round(max(ordered),3)}


async def api_benchmark():
    fixture=fixtures.CommerceTests(methodName="test_checkout_retries_reuse_order_and_stock_hold")
    await fixture.asyncSetUp()
    app=FastAPI(); app.middleware("http")(authenticate); app.include_router(router,prefix="/api")
    async def database():
        async with fixture.sessions() as db: yield db
    app.dependency_overrides[get_db]=database
    path="/api/agent/orchestrate"
    body=b'{"user_goal":"Buy a mouse","budget_cap_inr":100,"strict_items_only":true}'
    def headers(key):
        stamp=str(int(time.time()))
        message="\n".join([stamp,"POST",path,"buyer","buyer","0",hashlib.sha256(body).hexdigest()])
        return {"Content-Type":"application/json","X-User-Id":"buyer","X-User-Role":"buyer",
            "X-Auth-Timestamp":stamp,"X-Auth-Signature":hmac.new(b"benchmark-only-secret",message.encode(),hashlib.sha256).hexdigest(),
            "Idempotency-Key":key}
    try:
        with patch.dict(os.environ,{"BACKEND_AUTH_SECRET":"benchmark-only-secret"}), patch(
                "app.agents.supervisor.RazorpaySettlementAgent",return_value=fixture.agent):
            from app.db.models import Product, Order, PaymentEvent
            from sqlalchemy import update, select, func
            async with fixture.sessions() as db:
                await db.execute(update(Product).values(stock_quantity=100)); await db.commit()
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://benchmark") as client:
                async def measure(key, expected):
                    start=time.perf_counter()
                    response=await client.post(path,content=body,headers=headers(key))
                    elapsed=(time.perf_counter()-start)*1000
                    assert response.status_code == 200, response.text
                    assert response.json()["status"] == expected, response.text
                    return elapsed
                await measure("warmup", "AWAITING_PAYMENT")
                creation=[await measure(f"new-{i}","AWAITING_PAYMENT") for i in range(50)]
                replays=[await measure("warmup","AWAITING_PAYMENT") for _ in range(100)]
                gate=asyncio.Semaphore(8)
                async def limited(i):
                    async with gate: return await measure(f"burst-{i}","AWAITING_PAYMENT")
                burst=await asyncio.gather(*(limited(i) for i in range(32)))
                async with fixture.sessions() as db:
                    remaining=(await db.execute(select(Product.stock_quantity))).scalar_one()
                    orders=(await db.execute(select(func.count(Order.id)))).scalar_one()
                    events=(await db.execute(select(func.count(PaymentEvent.id)))).scalar_one()
                assert (remaining,orders,events) == (17,83,0)
                assert fixture.agent.client.order.create.call_count == 83
                return {"transport":"httpx ASGI in-process, signed requests, SQLite file; no TCP/TLS/browser",
                    "provider":"Mock order creation; no added network delay", "new_checkout_sequential":stats(creation),
                    "idempotent_replay_sequential":stats(replays),"new_checkout_concurrency_8":stats(burst),
                    "provider_submissions":fixture.agent.client.order.create.call_count,
                    "remaining_stock":remaining,"orders":orders,"payment_events":events}
    finally:
        await fixture.asyncTearDown()


def process_benchmark(postgres_url=None):
    fixture=ProcessContentionTests(methodName="test_last_unit_across_four_processes")
    fixture.postgres_url=postgres_url; fixture.setUp()
    try:
        names=[f"q_{i}" for i in range(4)]; fixture.prepare(names)
        results=contend(fixture.url,fixture.connect_args,names,"create")
        fixture.assert_inventory()
        assert sum(r["provider_submissions"] for r in results) == 1
        assert sum(r["status"] == "created" for r in results) == 1
        from sqlalchemy import text
        with fixture.sync.connect() as conn:
            database_version=conn.execute(text("SHOW server_version")).scalar() if postgres_url else sqlite3.sqlite_version
        return {"database_version":database_version,"processes":4,"last_unit_winners":1,"provider_submissions":1,
                "remaining_stock":0,"reservations":1,"latency":stats([r["latency_ms"] for r in results]),
                "statuses":[r["status"] for r in results],"timing":"inside workers after start barrier; includes connection establishment, excludes process startup"}
    finally:
        fixture.tearDown()


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--output",required=True); args=parser.parse_args()
    runner={"loop_factory":asyncio.SelectorEventLoop} if platform.system()=="Windows" else {}
    result={"measured_at_utc":datetime.datetime.now(datetime.UTC).isoformat(),"python":platform.python_version(),"platform":platform.platform(),
        "sqlalchemy":version("sqlalchemy"),"psycopg":version("psycopg") if os.getenv("TEST_POSTGRES_URL") else None,
        "cpu_count":os.cpu_count(),"api":asyncio.run(api_benchmark(),**runner),
        "sqlite_processes":process_benchmark()}
    if os.getenv("TEST_POSTGRES_URL"):
        result["postgres_processes"]=process_benchmark(os.environ["TEST_POSTGRES_URL"])
    destination=Path(args.output); destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__ == "__main__": main()
