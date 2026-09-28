"""Audit the role-isolated task message inbox and sidebar entry."""

import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402


assert app.version == "11.18.42"
suite = unittest.TestSuite()
suite.addTests(unittest.defaultTestLoader.loadTestsFromName("tests.test_task_chat"))
suite.addTests(unittest.defaultTestLoader.loadTestsFromName(
    "tests.test_ui_contract.UiContractTests.test_task_messages_have_separate_sidebar_destinations"
))
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
print("Task message inbox audit: OK")
