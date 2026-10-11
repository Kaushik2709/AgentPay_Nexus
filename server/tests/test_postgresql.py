"""Run the database-backed contract on real PostgreSQL, in isolated schemas.

TEST_POSTGRES_URL must point to a disposable test database. No provider calls.
"""
import os
import unittest
from tests import test_reliability as suite


@unittest.skipUnless(os.getenv("TEST_POSTGRES_URL"), "Set TEST_POSTGRES_URL for real PostgreSQL verification")
class PostgresCommerceTests(suite.CommerceTests):
    postgres_url = os.getenv("TEST_POSTGRES_URL")
