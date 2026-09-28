"""Login security checks against an isolated in-memory database."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

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
from app.login_guard import authenticate_login  # noqa: E402
from app.main import login as legacy_login  # noqa: E402
from app.models import LoginAttemptV11, User  # noqa: E402
from app.security import create_session_token, hash_password  # noqa: E402
from app.ui_api import Credentials, _current_user, login as api_login  # noqa: E402


def request(path: str, client: str = "198.51.100.10", cookie: str = "") -> Request:
    headers = [(b"x-forwarded-proto", b"https")]
    if cookie:
        headers.append((b"cookie", cookie.encode()))
    return Request({"type": "http", "method": "POST", "scheme": "https", "path": path, "headers": headers, "client": (client, 443)})


class LoginGuardTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_failed_attempts_are_shared_across_login_forms_and_devices(self):
        for index in range(8):
            with self.assertRaises(HTTPException) as caught:
                api_login(Credentials(email="OWNER@example.com", password="wrongpassword"), request("/api/ui/auth/login", client=f"198.51.100.{index}"), Response(), self.db)
            self.assertEqual(caught.exception.status_code, 401)

        blocked = legacy_login(request("/login", "203.0.113.5"), "owner@example.com", "wrongpassword", self.db)
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(self.db.query(LoginAttemptV11).count(), 8)
        self.assertTrue(all("@" not in item.email for item in self.db.query(LoginAttemptV11).all()))

    def test_only_configured_owner_admin_can_hold_admin_session_on_any_device(self):
        owner = User(full_name="Owner", email="owner@example.com", password_hash=hash_password("strongpassword"), role="admin", status="active", referral_code="OWNER")
        other = User(full_name="Other", email="other@example.com", password_hash=hash_password("strongpassword"), role="admin", status="active", referral_code="OTHER")
        self.db.add_all([owner, other])
        self.db.commit()
        with patch.dict(os.environ, {"ADMIN_OWNER_USER_ID": str(owner.id), "ADMIN_OWNER_EMAIL": owner.email, "ADMIN_BOOTSTRAP_EMAIL": owner.email}):
            for client in ("198.51.100.10", "203.0.113.20"):
                result = api_login(Credentials(email=owner.email, password="strongpassword"), request("/api/ui/auth/login", client), Response(), self.db)
                self.assertEqual(result["user"]["id"], owner.id)
            with self.assertRaises(HTTPException) as caught:
                authenticate_login(self.db, other.email, "strongpassword")
            self.assertEqual(caught.exception.status_code, 401)
            self.assertIsNone(_current_user(request("/api/ui/session", cookie=f"kz_session={create_session_token(other.id)}"), self.db))
            self.assertEqual(_current_user(request("/api/ui/session", cookie=f"kz_session={create_session_token(owner.id)}"), self.db).id, owner.id)

    def test_legacy_admin_login_returns_to_admin_panel(self):
        owner = User(full_name="Owner", email="owner@example.com", password_hash=hash_password("strongpassword"), role="admin", status="active", referral_code="OWNER")
        self.db.add(owner)
        self.db.commit()
        with patch.dict(os.environ, {"ADMIN_OWNER_USER_ID": str(owner.id), "ADMIN_OWNER_EMAIL": owner.email}):
            response = legacy_login(request("/login"), owner.email, "strongpassword", self.db)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/admin")
        self.assertIn("Secure", response.headers["set-cookie"])
