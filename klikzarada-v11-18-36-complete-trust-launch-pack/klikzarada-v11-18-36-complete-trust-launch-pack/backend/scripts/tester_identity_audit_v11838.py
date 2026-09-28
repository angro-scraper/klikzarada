"""Audit that tester email and account identity stay separate and collision-safe."""

import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402


assert app.version == "11.18.38"
suite = unittest.defaultTestLoader.loadTestsFromName("tests.test_tester_identity")
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
print("Tester identity audit: OK")
