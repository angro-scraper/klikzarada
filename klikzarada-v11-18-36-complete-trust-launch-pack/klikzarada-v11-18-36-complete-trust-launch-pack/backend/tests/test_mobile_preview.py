import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base, get_db
from app.models import Task, User
from app.security import create_session_token
from app.ui_api import PLATFORM_FEE_PERCENT


class MobilePreviewTests(unittest.TestCase):
    def test_separate_mobile_entry_uses_existing_protected_api(self):
        with TemporaryDirectory() as directory, patch.object(main, "MOBILE_DIR", Path(directory)):
            (Path(directory) / "index.html").write_text("<html>mobile shell</html>", encoding="utf-8")
            client = TestClient(main.app)
            response = client.get("/mobilna", headers={"accept": "text/html"})
            self.assertEqual(response.status_code, 200)
            self.assertIn("mobile shell", response.text)
            self.assertIn("no-store", response.headers["cache-control"])
            self.assertEqual(client.get("/api/ui/user/dashboard").status_code, 401)

    def test_mobile_logout_returns_valid_response_and_clears_session(self):
        client = TestClient(main.app)
        client.cookies.set("kz_session", "test-session", domain="testserver.local", path="/")

        response = client.post("/api/ui/auth/logout")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertIn("kz_session=", response.headers["set-cookie"])
        self.assertIn("Max-Age=0", response.headers["set-cookie"])
        self.assertNotIn("kz_session", client.cookies)

    def test_mobile_campaign_uses_advertiser_api_and_reserves_budget(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine)
        db = session_factory()
        advertiser = User(full_name="Test oglašivač", email="mobile-advertiser@example.com", password_hash="hash", role="oglasivac", advertiser_budget_rsd=1000)
        db.add(advertiser)
        db.commit()
        db.refresh(advertiser)
        main.app.dependency_overrides[get_db] = lambda: db
        try:
            client = TestClient(main.app)
            client.cookies.set("kz_session", create_session_token(advertiser.id, advertiser.password_hash), domain="testserver.local", path="/")
            response = client.post("/api/ui/advertiser/campaigns", json={
                "title": "Mobilni UX test", "category": "Testiranje sajta ili aplikacije", "task_type": "UX test sajta",
                "description": "Proveri tok na sajtu.", "instructions": "Otvori stranicu i pošalji izveštaj.",
                "proof_required": "Kratak izveštaj", "reward_rsd": 20, "total_slots": 3,
                "campaign_duration_days": 30, "requires_tester_enrollment": False,
            })

            self.assertEqual(response.status_code, 201)
            expected_reserve = 20 * 3 * (1 + PLATFORM_FEE_PERCENT / 100)
            self.assertEqual(response.json()["reserved_rsd"], expected_reserve)
            self.assertEqual(db.query(Task).one().status, "pending")
            self.assertEqual(db.query(Task).one().advertiser_id, advertiser.id)
            db.refresh(advertiser)
            self.assertEqual(advertiser.advertiser_budget_rsd, 1000 - expected_reserve)
            dashboard = client.get("/api/ui/advertiser/dashboard")
            self.assertEqual(dashboard.status_code, 200)
            self.assertEqual(dashboard.json()["tasks"][0]["title"], "Mobilni UX test")
            self.assertEqual(dashboard.json()["tasks"][0]["status"], "pending")
            self.assertEqual(dashboard.json()["user"]["advertiser_reserved_rsd"], expected_reserve)
        finally:
            main.app.dependency_overrides.pop(get_db, None)
            db.close()
            engine.dispose()

    def test_mobile_beta_campaign_preserves_daily_reward_and_owner(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine)
        db = session_factory()
        advertiser = User(full_name="Beta oglašivač", email="beta-advertiser@example.com", password_hash="hash", role="oglasivac", advertiser_budget_rsd=10000)
        other = User(full_name="Drugi oglašivač", email="other-advertiser@example.com", password_hash="hash", role="oglasivac", advertiser_budget_rsd=1000)
        db.add_all([advertiser, other])
        db.commit()
        db.refresh(advertiser)
        db.refresh(other)
        main.app.dependency_overrides[get_db] = lambda: db
        try:
            client = TestClient(main.app)
            client.cookies.set("kz_session", create_session_token(advertiser.id, advertiser.password_hash), domain="testserver.local", path="/")
            response = client.post("/api/ui/advertiser/campaigns", json={
                "title": "Mobilni beta test", "category": "Testiranje sajta ili aplikacije",
                "task_type": "Zatvoreni beta test aplikacije", "description": "Testiraj aplikaciju 14 dana.",
                "instructions": "Pošalji dnevni izveštaj.", "proof_required": "Dnevni izveštaj",
                "reward_rsd": 280, "total_slots": 12, "campaign_duration_days": 30,
                "requires_tester_enrollment": True, "tester_required_count": 12,
                "tester_duration_days": 14, "tester_daily_minutes": 5, "tester_daily_reward_rsd": 20,
            })
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["reserved_rsd"], 280 * 12 * (1 + PLATFORM_FEE_PERCENT / 100))
            task = db.query(Task).one()
            self.assertTrue(task.requires_tester_enrollment)
            self.assertEqual(task.tester_daily_reward_rsd, 20)
            self.assertEqual(task.advertiser_id, advertiser.id)
            client.cookies.set("kz_session", create_session_token(other.id, other.password_hash), domain="testserver.local", path="/")
            self.assertEqual(client.get("/api/ui/advertiser/dashboard").json()["tasks"], [])
        finally:
            main.app.dependency_overrides.pop(get_db, None)
            db.close()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
