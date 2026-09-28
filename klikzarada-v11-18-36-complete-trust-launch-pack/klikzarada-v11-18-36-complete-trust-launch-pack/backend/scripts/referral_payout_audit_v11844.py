"""Audit the 100/50 RSD referral reward without touching live balances."""

import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402


assert app.version == "11.18.44"
suite = unittest.TestSuite()
suite.addTests(unittest.defaultTestLoader.loadTestsFromName("tests.test_referral_payout"))
suite.addTests(unittest.defaultTestLoader.loadTestsFromName(
    "tests.test_registration_flow.RegistrationFlowTests.test_generated_referral_code_can_be_used_by_another_registration"
))
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
print("Referral payout audit: OK")
