"""Isolated registration checks that never use the local or production database."""

import os
import sys
import unittest
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import Response
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request


BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base  # noqa: E402
from app.models import AppTesterEnrollment, EmailOutboxV8, EmailVerificationTokenV11, Task, User, UserConsentV11  # noqa: E402
from app.security import create_session_token  # noqa: E402
from app.ui_api import Registration, TesterCohortStartPayload as CohortStartPayload, correct_account_role_to_user, enable_advertiser_workspace, register, start_tester_cohort, user_dashboard  # noqa: E402


class RegistrationFlowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.request = Request({
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": "/api/ui/auth/register",
            "headers": [(b"user-agent", b"Mozilla/5.0")],
            "client": ("198.51.100.20", 443),
        })

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _register(self, **changes):
        payload = {
            "full_name": "Test Korisnik",
            "email": "test@example.com",
            "password": "sigurna-lozinka",
            "role": "korisnik",
            "accept_terms": True,
        }
        payload.update(changes)
        return register(Registration(**payload), self.request, Response(), self.db)

    def test_user_can_register_without_phone(self):
        result = self._register()
        user = self.db.query(User).filter(User.email == "test@example.com").one()

        self.assertEqual(result["user"]["email"], "test@example.com")
        self.assertIsNone(result["user"]["phone"])
        self.assertEqual(self.db.query(UserConsentV11).filter(UserConsentV11.user_id == user.id).count(), 1)
        self.assertEqual(self.db.query(EmailVerificationTokenV11).filter(EmailVerificationTokenV11.user_id == user.id).count(), 1)
        self.assertEqual(self.db.query(EmailOutboxV8).filter(EmailOutboxV8.recipient_email == user.email).count(), 1)

    def test_registration_preserves_required_and_safety_checks(self):
        self._register()

        cases = (
            ({"email": "terms@example.com", "accept_terms": False}, 400),
            ({"email": "short@example.com", "phone": "123"}, 400),
            ({}, 409),
        )
        for changes, status_code in cases:
            with self.subTest(changes=changes), self.assertRaises(HTTPException) as caught:
                self._register(**changes)
            self.assertEqual(caught.exception.status_code, status_code)

    def test_generated_referral_code_can_be_used_by_another_registration(self):
        self._register(email="referrer@example.com", full_name="Referral Vlasnik")
        referrer = self.db.query(User).filter(User.email == "referrer@example.com").one()

        self._register(
            email="invited@example.com",
            full_name="Pozvani Korisnik",
            referral_code=f"  {referrer.referral_code.lower()}  ",
        )
        invited = self.db.query(User).filter(User.email == "invited@example.com").one()

        self.assertEqual(invited.referred_by_id, referrer.id)
        self.assertNotEqual(invited.referral_code, referrer.referral_code)

    def test_closed_beta_can_start_one_tester_without_waiting_for_target(self):
        advertiser = User(full_name="Oglašivač", email="advertiser@example.com", password_hash="hash", role="oglasivac", referral_code="ADV001")
        tester = User(full_name="Tester", email="tester@example.com", password_hash="hash", referral_code="TEST001")
        self.db.add_all([advertiser, tester])
        self.db.flush()
        task = Task(
            advertiser_id=advertiser.id,
            title="Zatvoreni beta test",
            category="Testiranje",
            task_type="app_beta",
            description="Testiraj aplikaciju.",
            instructions="Pošalji dnevni izveštaj.",
            proof_required="Dnevni izveštaj",
            reward_rsd=70,
            total_slots=20,
            status="active",
            requires_tester_enrollment=True,
            tester_required_count=20,
            tester_duration_days=14,
            tester_daily_reward_rsd=5,
        )
        self.db.add(task)
        self.db.flush()
        enrollment = AppTesterEnrollment(task_id=task.id, user_id=tester.id, testing_email="tester@example.com", status="requested")
        self.db.add(enrollment)
        self.db.commit()

        request = Request({
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": f"/api/ui/advertiser/tasks/{task.id}/tester-cohorts/start",
            "headers": [(b"cookie", f"kz_session={create_session_token(advertiser.id)}".encode())],
            "client": ("198.51.100.20", 443),
        })
        result = start_tester_cohort(task.id, CohortStartPayload(count=1), request, self.db)
        self.db.refresh(enrollment)
        self.db.refresh(task)

        self.assertEqual(result["activated_count"], 1)
        self.assertEqual(enrollment.status, "invited")
        self.assertIsNotNone(enrollment.invited_at)
        self.assertEqual(task.used_slots, 1)

    def test_accidental_empty_advertiser_account_can_switch_to_user(self):
        advertiser = User(full_name="Pogrešna uloga", email="wrong-role@example.com", password_hash="hash", role="oglasivac")
        self.db.add(advertiser)
        self.db.commit()
        request = Request({
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": "/api/ui/account/role/correct-to-user",
            "headers": [(b"cookie", f"kz_session={create_session_token(advertiser.id)}".encode())],
            "client": ("198.51.100.20", 443),
        })

        result = correct_account_role_to_user(request, self.db)
        self.db.refresh(advertiser)

        self.assertEqual(result["user"]["role"], "korisnik")
        self.assertEqual(advertiser.role, "korisnik")

    def test_one_account_can_restore_campaign_workspace_and_keep_task_access(self):
        user = User(full_name="Višenamenski nalog", email="workspace@example.com", password_hash="hash", role="korisnik")
        self.db.add(user)
        self.db.commit()
        request = Request({
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": "/api/ui/account/role/enable-advertiser",
            "headers": [(b"cookie", f"kz_session={create_session_token(user.id)}".encode())],
            "client": ("198.51.100.20", 443),
        })

        result = enable_advertiser_workspace(request, self.db)
        dashboard = user_dashboard(request, self.db)

        self.assertEqual(result["user"]["role"], "oglasivac")
        self.assertEqual(dashboard["user"]["role"], "oglasivac")


if __name__ == "__main__":
    unittest.main()
