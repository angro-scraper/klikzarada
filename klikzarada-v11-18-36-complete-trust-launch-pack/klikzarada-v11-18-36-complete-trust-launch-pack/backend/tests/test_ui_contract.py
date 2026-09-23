"""Small no-network checks for the browser-facing API contract."""

import os
import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402


class UiContractTests(unittest.TestCase):
    def test_production_routes_are_registered(self):
        paths = app.openapi()["paths"]
        expected = {
            "/api/ui/advertiser/banners/upload",
            "/api/ui/advertiser/promotions",
            "/api/ui/admin/promotions",
            "/api/ui/tickets/{ticket_id}/messages",
            "/api/ui/account/password",
            "/api/ui/advertiser/campaigns/{task_id}/lifecycle",
        }
        self.assertTrue(expected.issubset(paths))


if __name__ == "__main__":
    unittest.main()
