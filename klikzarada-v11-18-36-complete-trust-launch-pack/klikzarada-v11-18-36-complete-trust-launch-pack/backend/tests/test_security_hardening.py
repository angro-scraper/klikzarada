"""Security regression checks using only an isolated in-memory database."""

import base64
import hashlib
import hmac
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi import UploadFile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request


BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, get_db  # noqa: E402
from app import main, security  # noqa: E402
from app.login_guard import authenticate_login  # noqa: E402
from app.login_guard import admin_identity_allowed  # noqa: E402
from app.models import LoginAttemptV11, User, UserConsentV11  # noqa: E402
from app.security import create_session_token, hash_password, read_session_token, session_matches_user  # noqa: E402


class SecurityHardeningTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine)

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
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_public_home_and_legacy_pages_render_with_current_starlette(self):
        for path in ("/", "/login", "/pravila"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/html", response.headers["content-type"])

    def test_cross_site_registration_is_rejected_before_database_write(self):
        response = self.client.post("/api/ui/auth/register", json={
            "full_name": "Test Korisnik", "email": "csrf@example.com",
            "password": "strongpassword", "accept_terms": True,
        }, headers={"origin": "https://attacker.example", "sec-fetch-site": "cross-site"})
        self.assertEqual(response.status_code, 403)
        with self.sessions() as db:
            self.assertEqual(db.query(User).count(), 0)

    def test_legacy_registration_uses_terms_referral_and_consent_rules(self):
        form = {"full_name": "Test Korisnik", "email": "legacy@example.com", "password": "strongpassword", "role": "korisnik"}
        self.assertEqual(self.client.post("/registracija", data=form).status_code, 400)
        self.assertEqual(self.client.post("/registracija", data={**form, "accept_terms": "true", "referral_code": "DOESNOTEXIST"}).status_code, 400)
        response = self.client.post("/registracija", data={**form, "accept_terms": "true"}, follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn("kz_session=", response.headers["set-cookie"])
        with self.sessions() as db:
            user = db.query(User).filter(User.email == "legacy@example.com").one()
            self.assertEqual(db.query(UserConsentV11).filter(UserConsentV11.user_id == user.id).count(), 1)

    def test_honeypot_and_registration_rate_limit(self):
        data = {"full_name": "Test Korisnik", "email": "bot@example.com", "password": "strongpassword", "accept_terms": True}
        self.assertEqual(self.client.post("/api/ui/auth/register", json={**data, "website": "spam.example"}).status_code, 400)
        for _ in range(4):
            self.assertEqual(self.client.post("/api/ui/auth/register", json={**data, "accept_terms": False}).status_code, 400)
        self.assertEqual(self.client.post("/api/ui/auth/register", json=data).status_code, 429)

    def test_failed_logins_are_limited_by_source_as_well_as_account(self):
        with self.sessions() as db:
            request = Request({"type": "http", "method": "POST", "scheme": "https", "path": "/api/ui/auth/login", "headers": [], "client": ("198.51.100.55", 443)})
            for attempt in range(30):
                with self.assertRaises(HTTPException) as caught:
                    authenticate_login(db, f"missing{attempt}@example.com", "wrongpassword", request)
                self.assertEqual(caught.exception.status_code, 401)
            with self.assertRaises(HTTPException) as blocked:
                authenticate_login(db, "another@example.com", "wrongpassword", request)
            self.assertEqual(blocked.exception.status_code, 429)
            self.assertEqual(db.query(LoginAttemptV11).count(), 30)

    def test_sessions_expire_and_password_change_revokes_new_token(self):
        password_hash = hash_password("strongpassword")
        with patch.object(security.time, "time", return_value=1_800_000_000):
            token = create_session_token(42, password_hash)
        with patch.object(security.time, "time", return_value=1_800_000_001):
            self.assertEqual(read_session_token(token), 42)
            self.assertTrue(session_matches_user(token, password_hash, "korisnik"))
            self.assertFalse(session_matches_user(token, hash_password("newpassword"), "korisnik"))
        with patch.object(security.time, "time", return_value=1_800_000_000 + security.ADMIN_SESSION_TTL_SECONDS + 1):
            self.assertFalse(session_matches_user(token, password_hash, "admin"))
        with patch.object(security.time, "time", return_value=1_800_000_000 + security.SESSION_TTL_SECONDS + 1):
            self.assertIsNone(read_session_token(token))

    def test_legacy_cookie_has_fixed_grace_period_and_can_be_revoked(self):
        payload = base64.urlsafe_b64encode(b"42").decode().rstrip("=")
        signature = hmac.new(security.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        token = f"{payload}.{signature}"
        with patch.object(security.time, "time", return_value=security.LEGACY_SESSION_END - 1):
            self.assertEqual(read_session_token(token), 42)
            self.assertFalse(session_matches_user(token, "hash", "korisnik", legacy_revoked=True))
        with patch.object(security.time, "time", return_value=security.LEGACY_SESSION_END + 1):
            self.assertIsNone(read_session_token(token))

    def test_render_requires_real_secret_and_named_admin_owner(self):
        environment = dict(os.environ, RENDER="true", APP_ENV="development", KLIKZARADA_SECRET_KEY="")
        failed = subprocess.run([sys.executable, "-c", "import app.security"], cwd=BACKEND_DIR, env=environment, capture_output=True, text=True)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("KLIKZARADA_SECRET_KEY", failed.stderr)
        environment["KLIKZARADA_SECRET_KEY"] = "a-long-random-secret-for-isolated-test-only-123"
        passed = subprocess.run([sys.executable, "-c", "from app.security import running_in_production; assert running_in_production()"], cwd=BACKEND_DIR, env=environment, capture_output=True, text=True)
        self.assertEqual(passed.returncode, 0, passed.stderr)

        with self.sessions() as db:
            owner = User(full_name="Owner", email="owner@example.com", password_hash=hash_password("strongpassword"), role="admin", status="active", referral_code="OWNER")
            db.add(owner)
            db.commit()
            with patch.dict(os.environ, {"RENDER": "true", "ADMIN_OWNER_USER_ID": "", "ADMIN_OWNER_EMAIL": "", "ADMIN_BOOTSTRAP_EMAIL": ""}):
                self.assertFalse(admin_identity_allowed(owner))
            with patch.dict(os.environ, {"RENDER": "true", "ADMIN_OWNER_USER_ID": str(owner.id)}):
                self.assertTrue(admin_identity_allowed(owner))

    def test_legacy_upload_rejects_active_content(self):
        file = UploadFile(filename="evidence.svg", file=io.BytesIO(b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>'))
        with self.assertRaises(HTTPException) as caught:
            main.save_file(file)
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(self.client.get("/static/uploads/old-banner.svg").status_code, 404)

    def test_kyc_document_is_private_and_legacy_upload_works(self):
        with self.sessions() as db:
            owner = User(full_name="Owner", email="owner@example.com", password_hash=hash_password("ownerpassword"), role="korisnik", status="active", referral_code="OWNER")
            stranger = User(full_name="Stranger", email="stranger@example.com", password_hash=hash_password("strangerpassword"), role="korisnik", status="active", referral_code="STRANGER")
            db.add_all([owner, stranger])
            db.commit()
            owner_id, stranger_id = owner.id, stranger.id
            owner_cookie = create_session_token(owner_id, owner.password_hash)
            stranger_cookie = create_session_token(stranger_id, stranger.password_hash)
        with tempfile.TemporaryDirectory() as directory, patch.object(main, "KYC_UPLOAD_DIR", Path(directory)):
            image = io.BytesIO()
            from PIL import Image
            Image.new("RGB", (4, 4), "white").save(image, format="PNG")
            response = self.client.post("/korisnik/verifikacija", data={"doc_type": "identity"}, files={"proof_file": ("id.png", image.getvalue(), "image/png")}, headers={"cookie": f"kz_session={owner_cookie}"}, follow_redirects=False)
            self.assertEqual(response.status_code, 303, response.text)
            with self.sessions() as db:
                from app.models import KycDocument
                doc = db.query(KycDocument).filter(KycDocument.user_id == owner_id).one()
                self.assertEqual(doc.file_path, f"/kyc/files/{doc.id}")
                url = doc.file_path
            self.assertEqual(self.client.get(url).status_code, 401)
            self.assertEqual(self.client.get(url, headers={"cookie": f"kz_session={stranger_cookie}"}).status_code, 404)
            downloaded = self.client.get(url, headers={"cookie": f"kz_session={owner_cookie}"})
            self.assertEqual(downloaded.status_code, 200)
            self.assertEqual(downloaded.headers["cache-control"], "no-store")
            self.assertEqual(downloaded.content, image.getvalue())


if __name__ == "__main__":
    unittest.main()
