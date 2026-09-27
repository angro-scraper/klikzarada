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

        self.assertEqual(result["user"]["email"], "test@example.com")
        self.assertIsNone(result["user"]["phone"])

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


if __name__ == "__main__":
    unittest.main()
