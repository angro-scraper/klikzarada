"""Audit the dedicated light task-chat message surface."""

import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402


assert app.version == "11.18.41"
suite = unittest.defaultTestLoader.loadTestsFromName(
    "tests.test_ui_contract.UiContractTests.test_task_chat_has_a_light_dedicated_background"
)
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
print("Task chat surface audit: OK")
