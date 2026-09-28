"""Small no-network checks for the browser-facing API contract."""

import os
import sys
import unittest
from inspect import signature
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402
from app.ui_api import _public_app_url  # noqa: E402


class UiContractTests(unittest.TestCase):
    def test_browser_entry_routes_load_without_intercepting_private_api(self):
        from app import main

        with TemporaryDirectory() as directory, patch.object(main, "SPA_DIR", Path(directory)):
            (Path(directory) / "index.html").write_text("<html>app shell</html>", encoding="utf-8")
            client = TestClient(app)
            for path in (
                "/", "/registracija", "/prijava", "/korisnik/panel",
                "/korisnik/zadaci", "/korisnik/moji-zadaci", "/korisnik/zadaci/123",
                "/korisnik/profil", "/oglasivac/panel", "/admin",
            ):
                with self.subTest(path=path):
                    response = client.get(path, headers={"accept": "text/html"})
                    self.assertEqual(response.status_code, 200)
                    self.assertIn("app shell", response.text)
            self.assertEqual(client.get("/api/ui/user/dashboard").status_code, 401)

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
            "/api/ui/analytics/funnel",
            "/api/ui/user/program/rewards/{reward_key}",
            "/admin/analitika-v117",
            "/r/{referral_code}",
        }
        self.assertTrue(expected.issubset(paths))

    def test_referral_link_reaches_react_registration_with_a_real_code(self):
        main_source = (BACKEND_DIR / "app" / "main.py").read_text(encoding="utf-8")
        auth_source = (BACKEND_DIR / "frontend" / "src" / "pages" / "Auth.tsx").read_text(encoding="utf-8")
        self.assertIn('"/r/"', main_source)
        self.assertIn('urlencode({\'ref\': referrer.referral_code})', main_source)
        self.assertIn("get('ref')", auth_source)
        self.assertNotIn('placeholder="npr. USER123"', auth_source)

    def test_email_public_url_helper_does_not_require_a_request(self):
        """Registration and password reset must be able to create email links."""
        self.assertEqual(len(signature(_public_app_url).parameters), 0)

    def test_react_shell_is_not_cached_between_deployments(self):
        """A stale HTML shell must not reference a bundle removed by a deploy."""
        main_source = (BACKEND_DIR / "app" / "main.py").read_text(encoding="utf-8")
        self.assertIn('Cache-Control"] = "no-store, max-age=0, must-revalidate"', main_source)
        self.assertIn("class AppUiStaticFiles", main_source)

    def test_public_entry_does_not_ship_private_workspaces(self):
        """All workspaces render directly instead of replacing the page with a loader."""
        app_source = (BACKEND_DIR / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
        main_source = (BACKEND_DIR / "app" / "main.py").read_text(encoding="utf-8")
        self.assertIn("import Auth from './pages/Auth'", app_source)
        self.assertIn("import TasksPublic from './pages/TasksPublic'", app_source)
        self.assertIn("import AdminHub from './pages/AdminHub'", app_source)
        self.assertIn("import AdvertiserPanel from './pages/AdvertiserPanel'", app_source)
        self.assertIn("import UserDashboard from './pages/UserDashboard'", app_source)
        self.assertNotIn("RouteLoader", app_source)
        self.assertNotIn("lazy(() => import('./pages/AdminHub'))", app_source)
        self.assertIn("GZipMiddleware", main_source)
        self.assertIn('public, max-age=31536000, immutable', main_source)

    def test_user_beta_task_detail_has_its_input_component(self):
        """Opening a closed-beta task must not fail because its form component is missing."""
        source = (BACKEND_DIR / "frontend" / "src" / "pages" / "UserDashboard.tsx").read_text(encoding="utf-8")
        self.assertIn("Alert, Input } from '../components/ui'", source)
        self.assertIn('<Input label="Tvoj Google Play email za ovaj test"', source)

    def test_tester_enrollments_keep_emails_and_actions_visible(self):
        source = (BACKEND_DIR / "frontend" / "src" / "pages" / "AdvertiserPanel.tsx").read_text(encoding="utf-8")
        cards = source.split('Prijavljeni testeri</h3>', 1)[1].split("{testerCheckins.length > 0", 1)[0]
        self.assertNotIn("<Table", cards)
        self.assertIn("2xl:grid-cols-4", cards)
        self.assertIn("break-all select-all", cards)
        self.assertIn("Google Play email za test", cards)
        self.assertIn("Status i akcije", cards)

    def test_advertiser_messages_have_spacing_and_readable_preview(self):
        source = (BACKEND_DIR / "frontend" / "src" / "pages" / "AdvertiserPanel.tsx").read_text(encoding="utf-8")
        messages = source.split("{unreadChatNotifications.length > 0 && <Card", 1)[1].split("{testerEnrollments.length > 0", 1)[0]
        self.assertEqual(messages.count("sm:p-6"), 2)
        self.assertIn("Otvori razgovor", messages)
        self.assertIn("line-clamp-2 break-words", messages)
        self.assertNotIn("truncate text-sm", messages)

    def test_pageview_tracking_excludes_non_browser_traffic(self):
        """Traffic counters must only accept deliberate public navigations."""
        source = (BACKEND_DIR / "app" / "main.py").read_text(encoding="utf-8")
        self.assertIn('"facebookexternalhit"', source)
        self.assertIn('user_agent.lower().startswith("mozilla/")', source)
        self.assertIn('fetch_mode == "navigate"', source)
        self.assertIn('fetch_user == "?1"', source)
        self.assertIn('fetch_site in {"cross-site", "none"}', source)
        self.assertIn('timedelta(minutes=20)', source)
        self.assertIn('is_public_pageview_path(path)', source)

        from app.analytics import is_public_pageview_path
        self.assertTrue(is_public_pageview_path("/registracija"))
        self.assertTrue(is_public_pageview_path("/zadaci"))
        self.assertTrue(is_public_pageview_path("/zadaci/42"))
        self.assertTrue(is_public_pageview_path("/za-korisnike"))
        self.assertFalse(is_public_pageview_path("/korisnik/zadaci"))
        self.assertFalse(is_public_pageview_path("/oglasivac/panel"))

    def test_analytics_reset_starts_a_clean_series(self):
        """A clean start must hide legacy traffic without deleting business data."""
        source = (BACKEND_DIR / "app" / "ui_api.py").read_text(encoding="utf-8")
        self.assertIn("start_clean_pageview_measurement(db, datetime.utcnow(), force=True)", source)
        self.assertIn('"legacy_measurements_hidden": True', source)
        self.assertIn("PlatformVisitV117.path.like(\"/zadaci/%\")", source)

    def test_utm_registration_funnel_is_privacy_preserving_and_complete(self):
        """Paid traffic should be attributable without storing raw visitor data."""
        main_source = (BACKEND_DIR / "app" / "main.py").read_text(encoding="utf-8")
        api_source = (BACKEND_DIR / "app" / "ui_api.py").read_text(encoding="utf-8")
        auth_source = (BACKEND_DIR / "frontend" / "src" / "pages" / "Auth.tsx").read_text(encoding="utf-8")
        self.assertIn('event_type="ad_landing"', main_source)
        self.assertIn('class PublicFunnelEventV12', (BACKEND_DIR / "app" / "models.py").read_text(encoding="utf-8"))
        self.assertIn('"registration_completed"', api_source)
        self.assertIn('/analytics/funnel', api_source)
        self.assertIn("trackPublicFunnel('registration_opened')", auth_source)
        self.assertIn("trackPublicFunnel('registration_submitted')", auth_source)
        self.assertIn("registration_failed", api_source)
        self.assertIn("trackPublicFunnel('registration_failed', registrationFailureReason(caught))", auth_source)
        self.assertIn('"network_error"', api_source)
        self.assertIn('"server_error"', api_source)
        self.assertIn("caught.status === 422", auth_source)

    def test_registration_failure_diagnostics_never_retain_form_values(self):
        """The admin funnel may show categories, but never a user's submitted data."""
        api_source = (BACKEND_DIR / "app" / "ui_api.py").read_text(encoding="utf-8")
        model_source = (BACKEND_DIR / "app" / "models.py").read_text(encoding="utf-8")
        auth_source = (BACKEND_DIR / "frontend" / "src" / "pages" / "Auth.tsx").read_text(encoding="utf-8")
        self.assertIn("class PublicFunnelFailureReasonV12", model_source)
        self.assertIn("_record_public_funnel_failure_reason", api_source)
        self.assertIn('"failure_reasons": failure_reasons', api_source)
        self.assertIn("registrationFailureReason", auth_source)
        self.assertNotIn("email_value", model_source)
        self.assertNotIn("phone_value", model_source)

    def test_registration_explains_missing_required_fields(self):
        """Ad visitors must never get a silent no-op when the form is incomplete."""
        source = (BACKEND_DIR / "frontend" / "src" / "pages" / "Auth.tsx").read_text(encoding="utf-8")
        api_source = (BACKEND_DIR / "app" / "ui_api.py").read_text(encoding="utf-8")
        self.assertIn('Za registraciju još nedostaje:', source)
        self.assertIn('label="Telefon (opciono)"', source)
        self.assertNotIn("&& 'telefon'", source)
        self.assertIn('if phone and len(phone.replace("+", "")) < 7:', api_source)
        self.assertIn("disabled={submitted}", source)

    def test_registration_role_stays_aligned_with_the_selected_route(self):
        """A user route must never retain the advertiser form state after navigation."""
        auth_source = (BACKEND_DIR / "frontend" / "src" / "pages" / "Auth.tsx").read_text(encoding="utf-8")
        app_source = (BACKEND_DIR / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
        self.assertIn("setMode(initialMode)", auth_source)
        self.assertIn("onNavigate(isRegister ? 'register' : 'login')", auth_source)
        self.assertIn("onNavigate(isRegister ? 'advertiser-register' : 'advertiser-login')", auth_source)
        self.assertIn('key="register" initialMode="register"', app_source)
        self.assertIn('key="advertiser-register" initialMode="advertiser-register"', app_source)

    def test_private_workspaces_explain_a_wrong_account_without_mixing_roles(self):
        app_source = (BACKEND_DIR / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
        auth_source = (BACKEND_DIR / "frontend" / "src" / "pages" / "Auth.tsx").read_text(encoding="utf-8")
        self.assertIn('section="Admin panel" loginRoute="admin-login"', app_source)
        self.assertIn('section="Korisnički panel" loginRoute="login"', app_source)
        self.assertIn('section="Oglašivački panel" loginRoute="advertiser-login"', app_source)
        self.assertIn("Podaci i zadaci različitih naloga se ne mešaju", app_source)
        self.assertIn("Nalog ${result.user.email} je", auth_source)
        self.assertIn("await api.logout().catch(() => undefined)", auth_source)

    def test_closed_testers_can_start_individually(self):
        api_source = (BACKEND_DIR / "app" / "ui_api.py").read_text(encoding="utf-8")
        advertiser_source = (BACKEND_DIR / "frontend" / "src" / "pages" / "AdvertiserPanel.tsx").read_text(encoding="utf-8")
        self.assertIn('requested_count = payload.count or 1', api_source)
        self.assertNotIn('Početna Google kohorta mora imati', api_source)
        self.assertIn('Aktiviraj sada', advertiser_source)
        self.assertIn('Ne čeka se ciljnih 20 prijava', advertiser_source)

    def test_operational_screens_use_the_available_workspace_width(self):
        """Dashboards must not leave a narrow fixed-width column beside the sidebar."""
        pages = ("AdvertiserPanel.tsx", "UserDashboard.tsx", "AdminHub.tsx", "TasksPublic.tsx")
        for page in pages:
            source = (BACKEND_DIR / "frontend" / "src" / "pages" / page).read_text(encoding="utf-8")
            self.assertIn("w-full max-w-none", source, page)
            self.assertNotIn("max-w-4xl mx-auto", source, page)
            self.assertNotIn("max-w-5xl mx-auto", source, page)

    def test_proof_badges_are_backed_by_dashboard_data(self):
        """Proof navigation must not display placeholder demo counts."""
        user_source = (BACKEND_DIR / "frontend" / "src" / "pages" / "UserDashboard.tsx").read_text(encoding="utf-8")
        advertiser_source = (BACKEND_DIR / "frontend" / "src" / "pages" / "AdvertiserPanel.tsx").read_text(encoding="utf-8")
        self.assertNotIn("label: 'Moji dokazi', icon: '✅', badge: 2", user_source)
        self.assertNotIn("label: 'Dokazi korisnika', icon: '📎', badge: 5", advertiser_source)
        self.assertIn("badge: proofCount || undefined", user_source)
        self.assertIn("badge: proofBadge || undefined", advertiser_source)

    def test_rewards_and_badges_are_not_demo_values(self):
        """Engagement screens must calculate progress on the server, not in JSX."""
        user_source = (BACKEND_DIR / "frontend" / "src" / "pages" / "UserDashboard.tsx").read_text(encoding="utf-8")
        api_source = (BACKEND_DIR / "app" / "ui_api.py").read_text(encoding="utf-8")
        model_source = (BACKEND_DIR / "app" / "models.py").read_text(encoding="utf-8")
        self.assertNotIn("Streak: 7 dana", user_source)
        self.assertNotIn("unlocked: true", user_source)
        self.assertIn("claimProgramReward", user_source)
        self.assertIn("def _claimable_program_reward", api_source)
        self.assertIn("Dnevna nagrada se otključava nakon prvog stvarno poslatog dokaza", api_source)
        self.assertIn("class UserProgramRewardClaim", model_source)

    def test_campaign_delivery_controls_have_a_real_proof_revision_flow(self):
        """A revision must reuse the held task slot instead of creating a second reward."""
        api_source = (BACKEND_DIR / "app" / "ui_api.py").read_text(encoding="utf-8")
        advertiser_source = (BACKEND_DIR / "frontend" / "src" / "pages" / "AdvertiserPanel.tsx").read_text(encoding="utf-8")
        user_source = (BACKEND_DIR / "frontend" / "src" / "pages" / "UserDashboard.tsx").read_text(encoding="utf-8")
        self.assertIn('payload.status not in {"approved", "rejected", "needs_revision"}', api_source)
        self.assertIn('if is_revision:', api_source)
        self.assertIn('submission.revision_count = int(submission.revision_count or 0) + 1', api_source)
        self.assertIn("Traži doradu", advertiser_source)
        self.assertIn("Pokreni doradu dokaza", user_source)


if __name__ == "__main__":
    unittest.main()
