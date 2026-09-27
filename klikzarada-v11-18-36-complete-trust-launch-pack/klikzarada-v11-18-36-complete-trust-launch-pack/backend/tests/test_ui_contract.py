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
            "/api/ui/client-errors",
            "/api/ui/admin/analytics/reset",
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

    def test_user_beta_task_detail_has_its_input_component(self):
        """Opening a closed-beta task must not fail because its form component is missing."""
        source = (BACKEND_DIR / "frontend" / "src" / "pages" / "UserDashboard.tsx").read_text(encoding="utf-8")
        self.assertIn("Alert, Input } from '../components/ui'", source)
        self.assertIn('<Input label="Email za pristup testiranju"', source)

    def test_pageview_tracking_excludes_non_browser_traffic(self):
        """Traffic counters must not be inflated by crawlers or prefetches."""
        source = (BACKEND_DIR / "app" / "main.py").read_text(encoding="utf-8")
        self.assertIn('"facebookexternalhit"', source)
        self.assertIn('user_agent.lower().startswith("mozilla/")', source)
        self.assertIn('is_document and not is_prefetch', source)

    def test_analytics_reset_preserves_today(self):
        """A clean analytics start must retain the current day's page views."""
        source = (BACKEND_DIR / "app" / "ui_api.py").read_text(encoding="utf-8")
        self.assertIn("PlatformVisitV117.created_at < today_start", source)
        self.assertIn('"preserved_today": True', source)

    def test_operational_screens_use_the_available_workspace_width(self):
        """Dashboards must not leave a narrow fixed-width column beside the sidebar."""
        pages = ("AdvertiserPanel.tsx", "UserDashboard.tsx", "AdminHub.tsx", "TasksPublic.tsx")
        for page in pages:
            source = (BACKEND_DIR / "frontend" / "src" / "pages" / page).read_text(encoding="utf-8")
            self.assertIn("w-full max-w-none", source, page)
            self.assertNotIn("max-w-4xl mx-auto", source, page)
            self.assertNotIn("max-w-5xl mx-auto", source, page)


if __name__ == "__main__":
    unittest.main()
