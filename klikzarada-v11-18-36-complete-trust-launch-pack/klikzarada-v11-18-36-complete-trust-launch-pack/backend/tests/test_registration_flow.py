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
from app.models import EmailOutboxV8, EmailVerificationTokenV11, User, UserConsentV11  # noqa: E402
from app.ui_api import Registration, register  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
