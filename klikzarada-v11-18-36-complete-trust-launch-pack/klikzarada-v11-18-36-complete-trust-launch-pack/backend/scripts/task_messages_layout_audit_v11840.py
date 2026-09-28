"""Audit advertiser message spacing and readable conversation previews."""

import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402


assert app.version == "11.18.40"
suite = unittest.defaultTestLoader.loadTestsFromName(
    "tests.test_ui_contract.UiContractTests.test_advertiser_messages_have_spacing_and_readable_preview"
)
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
print("Task messages layout audit: OK")
