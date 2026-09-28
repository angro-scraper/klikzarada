"""Audit notification navigation for user, advertiser, and admin panels."""

import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402


assert app.version == "11.18.43"
suite = unittest.defaultTestLoader.loadTestsFromName(
    "tests.test_ui_contract.UiContractTests.test_notifications_are_available_in_every_role_sidebar"
)
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
print("Notification sidebar audit: OK")
