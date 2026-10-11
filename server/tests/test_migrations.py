import os
import tempfile
import unittest
import uuid
from pathlib import Path
from sqlalchemy import create_engine, text
from app.db.migrations import migrate


class MigrationTests(unittest.TestCase):
    postgres_url = None

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.admin=None
        if self.postgres_url:
            self.schema="test_"+uuid.uuid4().hex
            self.admin=create_engine(self.postgres_url)
            with self.admin.begin() as conn: conn.execute(text(f'CREATE SCHEMA "{self.schema}"'))
            self.engine=create_engine(self.postgres_url,connect_args={"options":f"-csearch_path={self.schema}"})
        else:
            self.engine=create_engine(f"sqlite:///{Path(self.tmp.name)/'legacy.db'}")

    def tearDown(self):
        self.engine.dispose()
        if self.admin:
            with self.admin.begin() as conn: conn.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
            self.admin.dispose()
        self.tmp.cleanup()

    def test_additive_migration_preserves_legacy_amounts_and_is_repeatable(self):
        with self.engine.begin() as conn:
            conn.execute(text("CREATE TABLE orders (id VARCHAR(64) PRIMARY KEY, total_amount FLOAT NOT NULL, razorpay_order_id VARCHAR(64) NOT NULL)"))
            conn.execute(text("INSERT INTO orders VALUES ('legacy', 1.005, 'order_legacy')"))
        migrate(self.engine); migrate(self.engine)
        with self.engine.connect() as conn:
            row=conn.execute(text("SELECT total_amount, amount_paise FROM orders WHERE id='legacy'")).one()
            self.assertEqual(row.amount_paise,101)
            self.assertEqual(row.total_amount,1.005)
            self.assertEqual(conn.execute(text("SELECT COUNT(*) FROM commerce_lock WHERE id=1")).scalar(),1)

    def test_new_schema_migration_is_repeatable(self):
        migrate(self.engine); migrate(self.engine)
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(text("SELECT COUNT(*) FROM orders")).scalar(),0)


@unittest.skipUnless(os.getenv("TEST_POSTGRES_URL"),"Set TEST_POSTGRES_URL for PostgreSQL migrations")
class PostgresMigrationTests(MigrationTests):
    postgres_url=os.getenv("TEST_POSTGRES_URL")
