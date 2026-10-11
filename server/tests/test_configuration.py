import unittest
from app.config import validate_database_pair


class ConfigurationTests(unittest.TestCase):
    def test_matching_sqlite_and_postgres_pairs(self):
        validate_database_pair("sqlite+aiosqlite:///./same.db","sqlite:///same.db")
        validate_database_pair("postgresql+psycopg://test:one@localhost/db","postgresql+psycopg://test:one@localhost:5432/db")

    def test_split_database_and_memory_configuration_is_rejected(self):
        for left,right in [
            ("sqlite+aiosqlite:///one.db","sqlite:///two.db"),
            ("sqlite+aiosqlite:///:memory:","sqlite:///:memory:"),
            ("postgresql+psycopg://test@localhost/one","postgresql+psycopg://test@localhost/two")]:
            with self.subTest(left=left), self.assertRaises(ValueError):
                validate_database_pair(left,right)
