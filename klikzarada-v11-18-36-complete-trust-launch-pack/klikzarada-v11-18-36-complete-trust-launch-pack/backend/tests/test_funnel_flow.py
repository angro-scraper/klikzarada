"""Exercise paid landing and registration analytics without touching production data."""

import os
import sys
from tempfile import TemporaryDirectory
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, get_db  # noqa: E402
from app import main  # noqa: E402
from app.ui_api import _admin_dashboard_data  # noqa: E402


class FunnelFlowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        self.session_patch = patch.object(main, "SessionLocal", self.sessions)
        self.session_patch.start()
        self.spa_dir = TemporaryDirectory()
        Path(self.spa_dir.name, "index.html").write_text("<!doctype html><title>Funnel test</title>", encoding="utf-8")
        self.spa_patch = patch.object(main, "SPA_DIR", Path(self.spa_dir.name))
        self.spa_patch.start()

        def test_db():
            db = self.sessions()
            try:
                yield db
            finally:
                db.close()

        main.app.dependency_overrides[get_db] = test_db
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()
        main.app.dependency_overrides.clear()
        self.spa_patch.stop()
        self.spa_dir.cleanup()
        self.session_patch.stop()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_paid_visit_open_submit_and_registration_reach_admin_totals(self):
        navigation_headers = {
            "accept": "text/html",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "cross-site",
        }
        landing = "/?utm_source=ig&utm_medium=paid&utm_campaign=test_funnel"
        self.assertEqual(self.client.get(landing, headers=navigation_headers).status_code, 200)
        self.assertTrue(self.client.cookies.get("kz_visitor_id"))
        self.assertEqual(self.client.get(landing, headers=navigation_headers).status_code, 200)

        for event_type in ("registration_opened", "registration_submitted"):
            response = self.client.post("/api/ui/analytics/funnel", json={"event_type": event_type})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["recorded"])

        registration = self.client.post("/api/ui/auth/register", json={
            "full_name": "Test Paid Visitor",
            "email": "paid-visitor@example.invalid",
            "password": "safe-test-password",
            "role": "korisnik",
            "accept_terms": True,
        })
        self.assertEqual(registration.status_code, 201, registration.text)

        with self.sessions() as db:
            funnel = _admin_dashboard_data(db)["metrics"]["acquisition_funnel"]
        self.assertEqual({key: funnel[key] for key in ("landings", "opened", "submitted", "completed")}, {
            "landings": 1, "opened": 1, "submitted": 1, "completed": 1,
        })
        self.assertEqual(funnel["conversion_rate"], 100.0)
        self.assertEqual(funnel["sources"][0]["campaign"], "test_funnel")
