"""Check that legacy campaign details are not duplicated in public descriptions."""

import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402


if __name__ == "__main__":
    assert app.version == "11.18.59"
    suite = unittest.defaultTestLoader.discover(str(BACKEND_DIR / "tests"), pattern="test_content_revisions.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
