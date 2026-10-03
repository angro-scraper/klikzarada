"""Public terms must not expose private invitation or moderation data."""

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from app.models import Task, User  # noqa: E402
from app.ui_api import _public_task_data, public_advertising_info  # noqa: E402
from app.main import _public_spa_document  # noqa: E402


class PublicTaskTermsTests(unittest.TestCase):
    def test_closed_test_hides_private_link_and_internal_notes(self):
        task = Task(
            id=42, title="Test aplikacije", category="Testiranje", task_type="app_test",
            description="Opis posla", instructions="Privatni link https://example.test/invite",
            proof_required="Dnevni izveštaj", target_url="https://example.test/invite",
            reward_rsd=280, total_slots=20, used_slots=1, estimated_minutes=5,
            requires_tester_enrollment=True, tester_duration_days=14,
            tester_daily_minutes=5, tester_daily_reward_rsd=20,
            status="active", moderation_note="Interna beleška",
        )
        task.advertiser = User(full_name="Vlasnik", email="private@example.test", role="oglasivac")
        data = _public_task_data(task)
        self.assertIsNone(data["target_url"])
        self.assertIsNone(data["moderation_note"])
        self.assertEqual(data["instructions"], "")
        self.assertNotIn("private@example.test", str(data))
        self.assertEqual(data["tester_daily_reward_rsd"], 20)

    def test_shareable_task_html_shows_daily_terms_without_private_data(self):
        task = SimpleNamespace(
            id=42, title="Test aplikacije", description="Dnevno testiranje",
            reward_rsd=280, estimated_minutes=5, requires_tester_enrollment=True,
            tester_duration_days=14, tester_daily_reward_rsd=20,
            tester_daily_minutes=5,
        )
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = task
        session = Mock()
        session.__enter__ = Mock(return_value=db)
        session.__exit__ = Mock(return_value=False)
        index = Mock()
        index.read_text.return_value = '<html><head><title>Old</title></head><body><div id="root"></div></body></html>'
        with patch("app.main.SessionLocal", return_value=session), patch.dict(os.environ, {"APP_ENV": "production"}):
            document = _public_spa_document("/zadaci/42", index)
        self.assertIn("280 RSD za 14 dana", document)
        self.assertIn("20 RSD po odobrenom danu", document)
        self.assertIn("5 minuta dnevno", document)
        self.assertIn('content="index, follow"', document)
        self.assertNotIn("private@example.test", document)

    def test_incomplete_beta_terms_do_not_invent_reward(self):
        task = SimpleNamespace(
            id=43, title="Nepotpun beta test", description="Opis",
            reward_rsd=280, estimated_minutes=5, requires_tester_enrollment=True,
            tester_duration_days=None, tester_daily_reward_rsd=None,
            tester_daily_minutes=None,
        )
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = task
        session = Mock()
        session.__enter__ = Mock(return_value=db)
        session.__exit__ = Mock(return_value=False)
        index = Mock()
        index.read_text.return_value = '<html><head><title>Old</title></head><body><div id="root"></div></body></html>'
        with patch("app.main.SessionLocal", return_value=session):
            document = _public_spa_document("/zadaci/43", index)
        self.assertIn("Nepotpun beta test", document)
        self.assertNotIn("280 RSD", document)

    def test_advertising_info_exposes_prices_without_bookings(self):
        slot = SimpleNamespace(
            id=4, title="Gornji banner", placement="home_top_wide",
            width_label="wide", price_rsd=1200,
        )
        db = Mock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [slot]
        result = public_advertising_info(db)
        self.assertEqual(result["slots"][0]["price_rsd"], 1200)
        self.assertEqual(result["banner_price_basis_days"], 7)
        self.assertNotIn("schedule", result["slots"][0])
        self.assertNotIn("advertiser_id", result["slots"][0])

    def test_public_advertising_metadata_and_private_noindex(self):
        index = Mock()
        index.read_text.return_value = '<html><head><title>Old</title></head><body><div id="root"></div></body></html>'
        with patch.dict(os.environ, {"APP_ENV": "production", "PUBLIC_APP_URL": "https://klikzarada.onrender.com"}):
            public = _public_spa_document("/oglasavanje", index)
            private = _public_spa_document("/korisnik/panel", index)
        self.assertIn("Oglašavanje i testeri | KlikZarada", public)
        self.assertIn('content="index, follow"', public)
        self.assertIn('href="https://klikzarada.onrender.com/oglasavanje"', public)
        self.assertIn('content="noindex, nofollow"', private)


if __name__ == "__main__":
    unittest.main()
