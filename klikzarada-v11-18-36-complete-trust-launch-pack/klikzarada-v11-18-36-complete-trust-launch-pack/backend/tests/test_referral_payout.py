"""Referral rewards are verified only in an isolated in-memory database."""

import os
import sys
import unittest
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
from app.main import v11831_approve_submission  # noqa: E402
from app.models import AppTesterDailyCheckin, FraudSignalV11, Task, TaskSubmission, User, WalletTransaction  # noqa: E402
from app.security import create_session_token  # noqa: E402
from app.ui_api import AdminStatusPayload, review_advertiser_submission, review_tester_daily_checkin, user_dashboard  # noqa: E402


class ReferralPayoutTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.advertiser = User(full_name="Oglašivač", email="adv@example.com", password_hash="hash", role="oglasivac", status="active")
        self.inviter = User(full_name="Pozivalac", email="inviter@example.com", password_hash="hash", role="korisnik", status="active")
        self.db.add_all([self.advertiser, self.inviter])
        self.db.flush()
        self.friend = User(full_name="Prijatelj", email="friend@example.com", password_hash="hash", role="korisnik", status="active", referred_by_id=self.inviter.id, pending_rsd=20)
        self.db.add(self.friend)
        self.db.flush()
        self.task = Task(advertiser_id=self.advertiser.id, title="Test zadatak", task_type="feedback", description="Opis", instructions="Uputstvo", proof_required="Dokaz", reward_rsd=20, total_slots=10, status="active")
        self.db.add(self.task)
        self.db.flush()
        self.proof = TaskSubmission(user_id=self.friend.id, task_id=self.task.id, proof="Stvarni dokaz", status="pending", reward_rsd=20, advertiser_cost_rsd=0)
        self.db.add(self.proof)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def request(self, user):
        return Request({
            "type": "http", "method": "GET", "scheme": "https", "path": "/api/ui/user/dashboard",
            "headers": [(b"cookie", f"kz_session={create_session_token(user.id)}".encode())],
            "client": ("198.51.100.20", 443),
        })

    def assert_one_bonus(self):
        self.db.refresh(self.friend)
        self.db.refresh(self.inviter)
        self.assertEqual(self.friend.balance_rsd, 70)
        self.assertEqual(self.inviter.balance_rsd, 100)
        self.assertEqual(self.db.query(WalletTransaction).filter(WalletTransaction.user_id == self.friend.id, WalletTransaction.tx_type == "referral_joiner_bonus").one().amount_rsd, 50)
        self.assertEqual(self.db.query(WalletTransaction).filter(WalletTransaction.user_id == self.inviter.id, WalletTransaction.tx_type == "referral_inviter_bonus").one().amount_rsd, 100)
        self.assertEqual(user_dashboard(self.request(self.inviter), self.db)["referral_earned_rsd"], 100)
        self.assertEqual(user_dashboard(self.request(self.inviter), self.db)["referral_inviter_bonus_rsd"], 100)
        self.assertEqual(user_dashboard(self.request(self.inviter), self.db)["referral_joiner_bonus_rsd"], 50)

    def test_advertiser_approval_pays_100_and_50_once(self):
        self.assertEqual(user_dashboard(self.request(self.inviter), self.db)["referral_earned_rsd"], 0)
        self.assertEqual(self.db.query(WalletTransaction).count(), 0)
        review_advertiser_submission(self.proof.id, AdminStatusPayload(status="approved"), self.request(self.advertiser), self.db)
        self.assert_one_bonus()
        with self.assertRaises(HTTPException) as caught:
            review_advertiser_submission(self.proof.id, AdminStatusPayload(status="approved"), self.request(self.advertiser), self.db)
        self.assertEqual(caught.exception.status_code, 409)
        self.assert_one_bonus()
        self.friend.pending_rsd = 20
        later = TaskSubmission(user_id=self.friend.id, task_id=self.task.id, proof="Drugi dokaz", status="pending", reward_rsd=20, advertiser_cost_rsd=0)
        self.db.add(later)
        self.db.commit()
        self.assertEqual(v11831_approve_submission(self.db, self.advertiser, later), "approved")
        self.db.refresh(self.inviter)
        self.assertEqual(self.inviter.balance_rsd, 100)
        self.assertEqual(self.db.query(WalletTransaction).filter(WalletTransaction.tx_type == "referral_inviter_bonus").count(), 1)

    def test_legacy_approval_uses_the_same_referral_rule(self):
        self.assertEqual(v11831_approve_submission(self.db, self.advertiser, self.proof), "approved")
        self.assert_one_bonus()

    def test_beta_daily_approval_pays_once_and_later_proof_does_not_repeat(self):
        first_day = AppTesterDailyCheckin(task_id=self.task.id, user_id=self.friend.id, day_number=1, note="Testiran prvi dan", reward_rsd=20, status="pending")
        self.db.add(first_day)
        self.db.commit()
        review_tester_daily_checkin(first_day.id, AdminStatusPayload(status="approved"), self.request(self.advertiser), self.db)
        self.assert_one_bonus()
        with self.assertRaises(HTTPException) as caught:
            review_tester_daily_checkin(first_day.id, AdminStatusPayload(status="approved"), self.request(self.advertiser), self.db)
        self.assertEqual(caught.exception.status_code, 409)
        review_advertiser_submission(self.proof.id, AdminStatusPayload(status="approved"), self.request(self.advertiser), self.db)
        self.db.refresh(self.inviter)
        self.assertEqual(self.inviter.balance_rsd, 100)
        self.assertEqual(self.db.query(WalletTransaction).filter(WalletTransaction.tx_type == "referral_inviter_bonus").count(), 1)

    def test_high_risk_first_result_does_not_pay_bonus(self):
        self.db.add(FraudSignalV11(user_id=self.friend.id, signal_type="test_risk", risk_score=90, status="open"))
        self.db.commit()
        review_advertiser_submission(self.proof.id, AdminStatusPayload(status="approved"), self.request(self.advertiser), self.db)
        self.db.refresh(self.friend)
        self.db.refresh(self.inviter)
        self.assertEqual(self.friend.balance_rsd, 20)
        self.assertEqual(self.inviter.balance_rsd or 0, 0)
        self.assertEqual(self.db.query(WalletTransaction).filter(WalletTransaction.tx_type.like("referral_%")).count(), 0)


if __name__ == "__main__":
    unittest.main()
