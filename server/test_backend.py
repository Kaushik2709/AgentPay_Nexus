"""Compatibility entrypoint for the isolated mocked regression suite.

Historical smoke checks used the configured database/provider. This entrypoint
now delegates to tests/ and never performs a real or sandbox payment.
"""
import unittest
from pathlib import Path

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent / "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
