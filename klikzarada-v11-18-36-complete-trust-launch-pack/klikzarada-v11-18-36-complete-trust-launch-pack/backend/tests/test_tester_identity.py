"""Prevent Google Play tester emails from linking different KlikZarada accounts."""

import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request


BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base  # noqa: E402
from app.models import AppTesterDailyCheckin, AppTesterEnrollment, Task, User, WalletTransaction  # noqa: E402
from app.security import create_session_token  # noqa: E402
from app.ui_api import (  # noqa: E402
    TesterCohortStartPayload,
    TesterDailyCheckinPayload,
    TesterEnrollmentPayload,
    TesterEnrollmentStatusPayload,
    AdminStatusPayload,
    advertiser_dashboard,
    create_tester_daily_checkin,
    request_tester_enrollment,
    review_tester_daily_checkin,
    start_tester_cohort,
    update_tester_enrollment,
    user_dashboard,
)


class TesterIdentityTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.owner = User(full_name="Oglašivač", email="owner@example.com", password_hash="hash", role="oglasivac")
        self.first = User(full_name="Isto ime", email="first@example.com", password_hash="hash", role="korisnik")
        self.second = User(full_name="Isto ime", email="second@example.com", password_hash="hash", role="korisnik")
        self.db.add_all([self.owner, self.first, self.second])
        self.db.flush()
        self.tasks = []
        for title in ("Prvi test", "Drugi test"):
            task = Task(advertiser_id=self.owner.id, title=title, category="Testiranje", task_type="app_beta", description="Test", instructions="Dnevni izveštaj", proof_required="Izveštaj", reward_rsd=20, total_slots=20, status="active", requires_tester_enrollment=True)
            self.db.add(task)
            self.tasks.append(task)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def request(self, user):
        return Request({
            "type": "http", "method": "POST", "scheme": "https", "path": "/api/ui/user/tasks/tester-enrollments",
            "headers": [(b"cookie", f"kz_session={create_session_token(user.id)}".encode())],
            "client": ("198.51.100.20", 443),
        })

    def test_test_email_matching_another_account_is_rejected(self):
        with self.assertRaises(HTTPException) as caught:
            request_tester_enrollment(self.tasks[0].id, TesterEnrollmentPayload(testing_email="SECOND@example.com"), self.request(self.first), self.db)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(self.db.query(AppTesterEnrollment).count(), 0)

    def test_test_email_cannot_be_shared_across_campaigns_by_different_accounts(self):
        request_tester_enrollment(self.tasks[0].id, TesterEnrollmentPayload(testing_email="play@example.com"), self.request(self.first), self.db)
        with self.assertRaises(HTTPException) as caught:
            request_tester_enrollment(self.tasks[1].id, TesterEnrollmentPayload(testing_email="PLAY@example.com"), self.request(self.second), self.db)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(self.db.query(AppTesterEnrollment).count(), 1)
        request_tester_enrollment(self.tasks[1].id, TesterEnrollmentPayload(testing_email="play@example.com"), self.request(self.first), self.db)
        self.assertEqual(self.db.query(AppTesterEnrollment).count(), 2)

    def test_legacy_collision_is_flagged_without_reassigning_the_user(self):
        legacy = AppTesterEnrollment(task_id=self.tasks[0].id, user_id=self.first.id, testing_email=self.second.email, status="requested")
        self.db.add(legacy)
        self.db.commit()
        rows = advertiser_dashboard(self.request(self.owner), self.db)["tester_enrollments"]
        self.assertEqual(rows[0]["user_id"], self.first.id)
        self.assertEqual(rows[0]["account_email"], self.first.email)
        self.assertEqual(rows[0]["testing_email"], self.second.email)
        self.assertTrue(rows[0]["email_conflict"])
        user_task = user_dashboard(self.request(self.first), self.db)["my_tasks"][0]
        self.assertTrue(user_task["tester_enrollment"]["email_conflict"])
        with self.assertRaises(HTTPException) as caught:
            update_tester_enrollment(legacy.id, TesterEnrollmentStatusPayload(status="invited"), self.request(self.owner), self.db)
        self.assertEqual(caught.exception.status_code, 409)
        with self.assertRaises(HTTPException) as caught:
            start_tester_cohort(self.tasks[0].id, TesterCohortStartPayload(count=1), self.request(self.owner), self.db)
        self.assertEqual(caught.exception.status_code, 409)
        self.db.refresh(legacy)
        self.assertEqual(legacy.user_id, self.first.id)
        self.assertEqual(legacy.status, "requested")

    def test_legacy_active_collision_cannot_create_or_approve_rewards(self):
        legacy = AppTesterEnrollment(
            task_id=self.tasks[0].id, user_id=self.first.id,
            testing_email=self.second.email, status="invited", invited_at=datetime.utcnow(),
        )
        self.db.add(legacy)
        self.db.commit()
        with self.assertRaises(HTTPException) as caught:
            create_tester_daily_checkin(
                self.tasks[0].id, TesterDailyCheckinPayload(note="Testirao sam aplikaciju"),
                self.request(self.first), self.db,
            )
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(self.db.query(AppTesterDailyCheckin).count(), 0)

        pending = AppTesterDailyCheckin(
            task_id=self.tasks[0].id, user_id=self.first.id, day_number=1,
            note="Raniji izveštaj", reward_rsd=20, status="pending",
        )
        self.db.add(pending)
        self.db.commit()
        with self.assertRaises(HTTPException) as caught:
            review_tester_daily_checkin(
                pending.id, AdminStatusPayload(status="approved"), self.request(self.owner), self.db,
            )
        self.assertEqual(caught.exception.status_code, 409)
        self.db.refresh(pending)
        self.assertEqual(pending.status, "pending")
        self.assertEqual(self.first.balance_rsd, 0)

    def test_daily_checkin_cannot_be_submitted_twice(self):
        self.tasks[0].tester_daily_reward_rsd = 20
        self.db.add(AppTesterEnrollment(
            task_id=self.tasks[0].id, user_id=self.first.id,
            testing_email=self.first.email, status="invited", invited_at=datetime.utcnow(),
        ))
        self.db.commit()
        payload = TesterDailyCheckinPayload(note="Testirao sam prijavu i navigaciju")
        create_tester_daily_checkin(self.tasks[0].id, payload, self.request(self.first), self.db)
        with self.assertRaises(HTTPException) as caught:
            create_tester_daily_checkin(self.tasks[0].id, payload, self.request(self.first), self.db)
        self.assertEqual(caught.exception.status_code, 409)
        self.db.refresh(self.first)
        self.assertEqual(self.db.query(AppTesterDailyCheckin).count(), 1)
        self.assertEqual(self.first.pending_rsd, 20)

    def test_invited_tester_sees_today_deadline_in_utc(self):
        self.db.add(AppTesterEnrollment(
            task_id=self.tasks[0].id, user_id=self.first.id,
            testing_email=self.first.email, status="invited", invited_at=datetime.utcnow(),
        ))
        self.db.commit()
        progress = user_dashboard(self.request(self.first), self.db)["my_tasks"][0]["tester_progress"]
        self.assertEqual(progress["current_day"], 1)
        self.assertTrue(progress["can_check_in"])
        deadline = datetime.fromisoformat(progress["day_ends_at"].replace("Z", "+00:00"))
        self.assertEqual((deadline - datetime.utcnow().astimezone(deadline.tzinfo)).days, 0)
        self.assertEqual((deadline.hour, deadline.minute), (0, 0))

    def test_another_advertiser_cannot_review_checkin_or_credit_wallet(self):
        stranger = User(full_name="Drugi oglašivač", email="stranger@example.com", password_hash="hash", role="oglasivac")
        self.db.add(stranger)
        self.db.flush()
        checkin = AppTesterDailyCheckin(
            task_id=self.tasks[0].id, user_id=self.first.id, day_number=1,
            note="Dnevni izveštaj", reward_rsd=20, status="pending",
        )
        self.db.add(checkin)
        self.db.commit()
        with self.assertRaises(HTTPException) as caught:
            review_tester_daily_checkin(
                checkin.id, AdminStatusPayload(status="approved"), self.request(stranger), self.db,
            )
        self.assertEqual(caught.exception.status_code, 404)
        self.db.refresh(checkin)
        self.db.refresh(self.first)
        self.assertEqual(checkin.status, "pending")
        self.assertEqual(self.first.balance_rsd, 0)
        self.assertEqual(self.db.query(WalletTransaction).count(), 0)


if __name__ == "__main__":
    unittest.main()
