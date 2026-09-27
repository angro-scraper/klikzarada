"""Small no-network checks for the browser-facing API contract."""

import os
import sys
import unittest
from inspect import signature
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402
from app.ui_api import _public_app_url  # noqa: E402


class UiContractTests(unittest.TestCase):
    def test_production_routes_are_registered(self):
        paths = app.openapi()["paths"]
        expected = {
            "/api/ui/advertiser/banners/upload",
            "/api/ui/advertiser/promotions",
            "/api/ui/admin/promotions",
            "/api/ui/admin/dashboard",
            "/api/ui/tickets/{ticket_id}/messages",
            "/api/ui/account/password",
            "/api/ui/advertiser/campaigns/{task_id}/lifecycle",
            "/api/ui/public/overview",
            "/api/ui/public/waitlist",
            "/admin/analitika-v117",
        }
        self.assertTrue(expected.issubset(paths))

    def test_email_public_url_helper_does_not_require_a_request(self):
        """Registration and password reset must be able to create email links."""
        self.assertEqual(len(signature(_public_app_url).parameters), 0)

    def test_react_shell_is_not_cached_between_deployments(self):
        """A stale HTML shell must not reference a bundle removed by a deploy."""
        main_source = (BACKEND_DIR / "app" / "main.py").read_text(encoding="utf-8")
        self.assertIn('Cache-Control"] = "no-store, max-age=0, must-revalidate"', main_source)
        self.assertIn("class AppUiStaticFiles", main_source)


if __name__ == "__main__":
    unittest.main()
