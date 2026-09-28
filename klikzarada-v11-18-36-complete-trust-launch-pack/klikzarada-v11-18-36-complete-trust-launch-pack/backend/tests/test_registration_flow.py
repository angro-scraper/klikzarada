"""Isolated registration checks that never use the local or production database."""

import os
import sys
import unittest
from datetime import datetime, timedelta
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
from app.models import AppTesterEnrollment, EmailOutboxV8, EmailVerificationTokenV11, Task, TaskVerificationSessionV1, User, UserConsentV11  # noqa: E402
from app.security import create_session_token  # noqa: E402
from app.ui_api import ProfilePayload, Registration, TesterCohortStartPayload as CohortStartPayload, TesterEnrollmentPayload as EnrollmentPayload, advertiser_dashboard, correct_account_role_to_user, enable_advertiser_workspace, register, request_tester_enrollment, save_user_profile, start_tester_cohort, user_dashboard  # noqa: E402


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
        self.assertEqual(user_dashboard(Request({
            "type": "http", "method": "GET", "scheme": "https", "path": "/api/ui/user/dashboard",
            "headers": [(b"cookie", f"kz_session={create_session_token(referrer.id)}".encode())],
            "client": ("198.51.100.20", 443),
        }), self.db)["referral_earned_rsd"], 0)

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
        tester_request = Request({
            "type": "http", "method": "GET", "scheme": "https", "path": "/api/ui/user/dashboard",
            "headers": [(b"cookie", f"kz_session={create_session_token(tester.id)}".encode())],
            "client": ("198.51.100.20", 443),
        })
        dashboard = user_dashboard(tester_request, self.db)
        self.assertEqual(dashboard["my_tasks"][0]["tester_enrollment"]["status"], "invited")
        self.assertEqual(dashboard["my_tasks"][0]["tester_enrollment"]["testing_email"], "tester@example.com")
        self.assertEqual(dashboard["my_tasks"][0]["tester_enrollment"]["account_email"], "tester@example.com")
        task.status = "paused"
        self.db.commit()
        self.assertEqual(user_dashboard(tester_request, self.db)["my_tasks"][0]["status"], "paused")

        other = User(full_name="Drugi nalog", email="other@example.com", password_hash="hash", referral_code="OTHER001")
        self.db.add(other)
        self.db.commit()
        task.status = "active"
        self.db.commit()
        other_request = Request({
            "type": "http", "method": "POST", "scheme": "https", "path": f"/api/ui/user/tasks/{task.id}/tester-enrollments",
            "headers": [(b"cookie", f"kz_session={create_session_token(other.id)}".encode())],
            "client": ("198.51.100.20", 443),
        })
        with self.assertRaises(HTTPException) as caught:
            request_tester_enrollment(task.id, EnrollmentPayload(testing_email="tester@example.com"), other_request, self.db)
        self.assertEqual(caught.exception.status_code, 409)

    def test_profile_does_not_confuse_city_with_account_email(self):
        self._register()
        user = self.db.query(User).filter(User.email == "test@example.com").one()
        user.city = "other@example.com"
        self.db.commit()
        request = Request({
            "type": "http", "method": "PUT", "scheme": "https", "path": "/api/ui/user/profile",
            "headers": [(b"cookie", f"kz_session={create_session_token(user.id)}".encode())],
            "client": ("198.51.100.20", 443),
        })
        profile = user_dashboard(request, self.db)["user"]
        self.assertEqual(profile["email"], "test@example.com")
        self.assertIsNone(profile["city"])
        self.assertTrue(profile["city_needs_correction"])
        with self.assertRaises(HTTPException) as caught:
            save_user_profile(ProfilePayload(full_name="Test Korisnik", city="other@example.com"), request, self.db)
        self.assertEqual(caught.exception.status_code, 400)
        corrected = save_user_profile(ProfilePayload(full_name="Test Korisnik"), request, self.db)
        self.assertFalse(corrected["user"]["city_needs_correction"])
        self.assertIsNone(user.city)

    def test_started_verification_is_visible_only_to_its_owner_while_valid(self):
        owner = User(full_name="Prvi korisnik", email="first@example.com", password_hash="hash", role="korisnik")
        other = User(full_name="Drugi korisnik", email="second@example.com", password_hash="hash", role="korisnik")
        self.db.add_all([owner, other])
        self.db.flush()
        task = Task(
            advertiser_id=owner.id, title="Provera stranice", category="Testiranje", task_type="website_test",
            description="Testiraj stranicu.", instructions="Pošalji dokaz.", proof_required="Snimak",
            reward_rsd=20, total_slots=10, status="active",
        )
        self.db.add(task)
        self.db.flush()
        session = TaskVerificationSessionV1(
            token="temporary-verification-token-123", user_id=owner.id, task_id=task.id,
            status="started", started_at=datetime.utcnow(),
        )
        self.db.add(session)
        self.db.commit()

        def dashboard(account):
            request = Request({
                "type": "http", "method": "GET", "scheme": "https", "path": "/api/ui/user/dashboard",
                "headers": [(b"cookie", f"kz_session={create_session_token(account.id)}".encode())],
                "client": ("198.51.100.20", 443),
            })
            return user_dashboard(request, self.db)

        self.assertEqual([item["id"] for item in dashboard(owner)["my_tasks"]], [task.id])
        self.assertTrue(dashboard(owner)["my_tasks"][0]["verification_in_progress"])
        self.assertEqual(dashboard(other)["my_tasks"], [])
        session.started_at = datetime.utcnow() - timedelta(hours=3)
        self.db.commit()
        self.assertEqual(dashboard(owner)["my_tasks"], [])

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

    def test_user_advertiser_and_admin_workspaces_are_separate(self):
        user = User(full_name="Korisnik", email="workspace@example.com", password_hash="hash", role="korisnik")
        advertiser = User(full_name="Oglašivač", email="campaign@example.com", password_hash="hash", role="oglasivac")
        admin = User(full_name="Admin", email="admin@example.com", password_hash="hash", role="admin")
        self.db.add_all([user, advertiser, admin])
        self.db.commit()
        def auth_request(account):
            return Request({
                "type": "http", "method": "GET", "scheme": "https", "path": "/api/ui/user/dashboard",
                "headers": [(b"cookie", f"kz_session={create_session_token(account.id)}".encode())],
                "client": ("198.51.100.20", 443),
            })

        self.assertEqual(user_dashboard(auth_request(user), self.db)["user"]["role"], "korisnik")
        for account in (advertiser, admin):
            with self.subTest(account=account.role), self.assertRaises(HTTPException) as caught:
                user_dashboard(auth_request(account), self.db)
            self.assertEqual(caught.exception.status_code, 403)
        with self.assertRaises(HTTPException) as caught:
            advertiser_dashboard(auth_request(user), self.db)
        self.assertEqual(caught.exception.status_code, 403)
        self.assertEqual(advertiser_dashboard(auth_request(advertiser), self.db)["user"]["role"], "oglasivac")
        self.assertEqual(advertiser_dashboard(auth_request(admin), self.db)["user"]["role"], "admin")
        with self.assertRaises(HTTPException) as caught:
            enable_advertiser_workspace(auth_request(user), self.db)
        self.assertEqual(caught.exception.status_code, 409)
        self.db.refresh(user)
        self.assertEqual(user.role, "korisnik")


if __name__ == "__main__":
    unittest.main()
