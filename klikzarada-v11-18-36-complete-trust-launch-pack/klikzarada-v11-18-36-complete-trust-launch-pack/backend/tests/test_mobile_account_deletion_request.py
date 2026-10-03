"""Account deletion requests must not delete accounts or change balances."""

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base, get_db
from app.models import SupportTicket, User
from app.security import create_session_token, hash_password


class MobileAccountDeletionRequestTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.user = User(
            full_name="Test korisnik",
            email="brisanje@example.com",
            password_hash=hash_password("test-lozinka-123"),
            role="korisnik",
            balance_rsd=250,
        )
        self.other = User(
            full_name="Drugi korisnik",
            email="drugi@example.com",
            password_hash=hash_password("druga-lozinka-123"),
            role="korisnik",
        )
        self.db.add_all([self.user, self.other])
        self.db.commit()
        main.app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(main.app)

    def tearDown(self):
        main.app.dependency_overrides.pop(get_db, None)
        self.db.close()
        self.engine.dispose()

    def login_as(self, user):
        self.client.cookies.set(
            "kz_session",
            create_session_token(user.id, user.password_hash),
            domain="testserver.local",
            path="/",
        )

    def test_authenticated_request_is_idempotent_and_preserves_account(self):
        path = "/api/ui/account/deletion-request"
        payload = {"password": "test-lozinka-123", "confirmation": "OBRIŠI NALOG"}
        self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.post(path, json=payload).status_code, 401)

        self.login_as(self.user)
        self.assertEqual(self.client.get(path).json()["requested"], False)
        self.assertEqual(self.client.post("/api/ui/tickets", json={
            "subject": "Lazni zahtev", "body": "Ovo nije potvrdjeno lozinkom.", "category": "account_deletion",
        }).status_code, 400)
        self.assertEqual(self.client.post(path, json={**payload, "password": "pogresno"}).status_code, 400)
        self.assertEqual(self.client.post(path, json={**payload, "confirmation": "NE"}).status_code, 422)
        self.assertEqual(self.db.query(SupportTicket).count(), 0)

        response = self.client.post(path, json=payload)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["requested"])
        self.assertTrue(response.json()["requested_at"])
        self.assertEqual(self.db.query(SupportTicket).count(), 1)
        self.assertEqual(self.db.query(SupportTicket).one().user_id, self.user.id)
        self.db.refresh(self.user)
        self.assertEqual(self.user.status, "active")
        self.assertEqual(self.user.balance_rsd, 250)

        self.assertEqual(self.client.post(path, json=payload).status_code, 201)
        self.assertEqual(self.db.query(SupportTicket).count(), 1)
        self.login_as(self.other)
        self.assertEqual(self.client.get(path).json()["requested"], False)


if __name__ == "__main__":
    unittest.main()
