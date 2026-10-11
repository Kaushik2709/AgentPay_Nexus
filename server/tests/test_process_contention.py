"""Real independent processes and database connections, with mocked providers."""
import datetime
import multiprocessing as mp
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from sqlalchemy import create_engine, select, func, text
from app.db.models import Base, Product, Quote, Order, PaymentEvent, StockReservation, AuditEntry
from tests.process_worker import worker
from tests.test_reliability import quote


def contend(url, connect_args, quote_ids, action):
    context = mp.get_context("spawn")
    ready, output, start = context.Queue(), context.Queue(), context.Event()
    processes = [context.Process(target=worker,args=(url,connect_args,name,action,ready,start,output)) for name in quote_ids]
    try:
        for process in processes: process.start()
        for _ in processes: ready.get(timeout=30)
        start.set()
        results = [output.get(timeout=45) for _ in processes]
        for process in processes:
            process.join(timeout=10)
            if process.exitcode != 0: raise AssertionError(f"Worker exit code {process.exitcode}")
        if any("error" in result for result in results): raise AssertionError(results)
        return results
    finally:
        start.set()
        for process in processes:
            if process.is_alive(): process.terminate(); process.join(timeout=5)
        ready.close(); output.close()


class ProcessContentionTests(unittest.TestCase):
    postgres_url = None

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.admin=None
        if self.postgres_url:
            self.schema="test_"+uuid.uuid4().hex
            self.admin=create_engine(self.postgres_url)
            with self.admin.begin() as conn: conn.execute(text(f'CREATE SCHEMA "{self.schema}"'))
            self.url=self.postgres_url
            self.connect_args={"options":f"-csearch_path={self.schema}"}
            self.sync=create_engine(self.url,connect_args=self.connect_args)
        else:
            path=Path(self.tmp.name)/"process.db"
            self.url=f"sqlite+aiosqlite:///{path}"
            self.connect_args={"timeout":30}
            self.sync=create_engine(f"sqlite:///{path}")
        Base.metadata.create_all(self.sync)
        with self.sync.begin() as conn:
            conn.execute(Product.__table__.insert().values(sku="item_mouse",name="Mouse",category="mice",description="",cost_price=50,retail_price=100,stock_quantity=1))

    def tearDown(self):
        self.sync.dispose()
        if self.admin:
            with self.admin.begin() as conn: conn.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
            self.admin.dispose()
        self.tmp.cleanup()

    def prepare(self, names):
        with self.sync.begin() as conn:
            for name in names:
                value=quote(name)
                conn.execute(Quote.__table__.insert().values(id=name,buyer_agent_id="buyer",amount_paise=10000,
                    budget_paise=10000,data_json=value.model_dump_json(),expires_at=datetime.datetime.fromisoformat(value.expires_at),status="CHECKOUT_READY"))

    def assert_inventory(self):
        with self.sync.connect() as conn:
            self.assertEqual(conn.execute(select(Product.stock_quantity)).scalar(),0)
            self.assertEqual(conn.execute(select(func.count(StockReservation.id))).scalar(),1)
            self.assertEqual(conn.execute(select(func.count(Order.id))).scalar(),1)

    def test_last_unit_across_four_processes(self):
        names=[f"q_{i}" for i in range(4)]; self.prepare(names)
        results=contend(self.url,self.connect_args,names,"create")
        self.assertEqual(sum(result["status"] == "created" for result in results),1)
        self.assertEqual(sum(result["provider_submissions"] for result in results),1)
        self.assert_inventory()

    def test_repeated_checkout_across_four_processes(self):
        self.prepare(["q_one"])
        results=contend(self.url,self.connect_args,["q_one"]*4,"create")
        self.assertEqual(sum(result["provider_submissions"] for result in results),1)
        self.assertTrue(all(result["status"] in {"created",409} for result in results))
        self.assert_inventory()

    def test_duplicate_settlement_across_four_processes(self):
        self.prepare(["q_one"])
        contend(self.url,self.connect_args,["q_one"],"create")
        results=contend(self.url,self.connect_args,["q_one"]*4,"settle")
        self.assertTrue(all(result["status"] == "PAID" for result in results))
        with self.sync.connect() as conn:
            self.assertEqual(conn.execute(select(func.count(PaymentEvent.id))).scalar(),1)
            self.assertEqual(conn.execute(select(func.count(AuditEntry.id))).scalar(),1)
        self.assert_inventory()


@unittest.skipUnless(os.getenv("TEST_POSTGRES_URL"), "Set TEST_POSTGRES_URL for PostgreSQL process contention")
class PostgresProcessContentionTests(ProcessContentionTests):
    postgres_url=os.getenv("TEST_POSTGRES_URL")
