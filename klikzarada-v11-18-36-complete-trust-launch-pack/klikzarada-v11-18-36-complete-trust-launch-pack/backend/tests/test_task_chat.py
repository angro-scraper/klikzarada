"""Task-bound chat and authorization checks on an isolated in-memory database."""

import os
import sys
import unittest
from pathlib import Path

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request


BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import AppTesterEnrollment, Notification, Task, TaskChatMessage, User  # noqa: E402
from app.security import create_session_token  # noqa: E402
from app.ui_api import TaskChatPayload, advertiser_task_chats, get_task_chat, send_task_chat_message, user_task_chats  # noqa: E402


class TaskChatTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.owner = User(full_name="Vlasnik", email="owner@example.com", password_hash="hash", role="oglasivac")
        self.tester = User(full_name="Tester", email="tester@example.com", password_hash="hash", role="korisnik")
        self.stranger = User(full_name="Drugi", email="other@example.com", password_hash="hash", role="korisnik")
        self.other_owner = User(full_name="Drugi oglašivač", email="other-owner@example.com", password_hash="hash", role="oglasivac")
        self.db.add_all([self.owner, self.tester, self.stranger, self.other_owner])
        self.db.flush()
        self.task = Task(
            advertiser_id=self.owner.id,
            title="Test aplikacije",
            category="Testiranje",
            task_type="app_beta",
            description="Test aplikacije.",
            instructions="Pošalji izveštaj.",
            proof_required="Izveštaj",
            reward_rsd=20,
            total_slots=20,
            status="active",
            requires_tester_enrollment=True,
        )
        self.db.add(self.task)
        self.db.flush()
        self.db.add(AppTesterEnrollment(task_id=self.task.id, user_id=self.tester.id, testing_email="tester@gmail.com", status="requested"))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def request(self, user):
        return Request({
            "type": "http", "method": "GET", "scheme": "https", "path": "/api/ui/task-chat",
            "headers": [(b"cookie", f"kz_session={create_session_token(user.id)}".encode())],
            "client": ("198.51.100.20", 443),
        })

    def test_messages_are_private_and_notify_only_counterparty(self):
        result = send_task_chat_message(self.task.id, self.tester.id, TaskChatPayload(body="  Da li imate test link?  "), self.request(self.tester), self.db)
        self.assertEqual(result["message"]["body"], "Da li imate test link?")
        self.assertEqual(self.db.query(Notification).one().user_id, self.owner.id)

        send_task_chat_message(self.task.id, self.tester.id, TaskChatPayload(body="https://play.google.com/apps/testing/example"), self.request(self.owner), self.db)
        self.assertEqual([item["sender_id"] for item in get_task_chat(self.task.id, self.tester.id, self.request(self.tester), self.db)["messages"]], [self.tester.id, self.owner.id])
        self.assertEqual(self.db.query(Notification).order_by(Notification.id.desc()).first().user_id, self.tester.id)
        self.assertEqual(self.db.query(TaskChatMessage).count(), 2)
        inbox = advertiser_task_chats(self.request(self.owner), self.db)["threads"]
        self.assertEqual(len(inbox), 1)
        self.assertEqual(inbox[0]["participant_id"], self.tester.id)
        self.assertEqual(advertiser_task_chats(self.request(self.other_owner), self.db)["threads"], [])
        user_inbox = user_task_chats(self.request(self.tester), self.db)["threads"]
        self.assertEqual(len(user_inbox), 1)
        self.assertEqual(user_inbox[0]["task_id"], self.task.id)
        self.assertEqual(user_task_chats(self.request(self.stranger), self.db)["threads"], [])
        with self.assertRaises(HTTPException):
            advertiser_task_chats(self.request(self.tester), self.db)
        with self.assertRaises(HTTPException):
            user_task_chats(self.request(self.owner), self.db)

    def test_unrelated_accounts_and_nonparticipants_cannot_read_or_send(self):
        for account in (self.stranger, self.other_owner):
            with self.subTest(account=account.email):
                with self.assertRaises(HTTPException) as caught:
                    get_task_chat(self.task.id, self.tester.id, self.request(account), self.db)
                self.assertEqual(caught.exception.status_code, 403)
                with self.assertRaises(HTTPException) as caught:
                    send_task_chat_message(self.task.id, self.tester.id, TaskChatPayload(body="Poruka"), self.request(account), self.db)
                self.assertEqual(caught.exception.status_code, 403)
        with self.assertRaises(HTTPException) as caught:
            get_task_chat(self.task.id, self.stranger.id, self.request(self.owner), self.db)
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(self.db.query(TaskChatMessage).count(), 0)

    def test_blank_message_does_not_create_notification(self):
        with self.assertRaises(HTTPException) as caught:
            send_task_chat_message(self.task.id, self.tester.id, TaskChatPayload(body="  "), self.request(self.owner), self.db)
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(self.db.query(Notification).count(), 0)

    def test_http_routes_use_the_same_access_checks(self):
        def test_db():
            yield self.db

        app.dependency_overrides[get_db] = test_db
        try:
            client = TestClient(app)
            path = f"/api/ui/task-chat/{self.task.id}/{self.tester.id}"
            anonymous = client.get(path)
            self.assertIn(anonymous.status_code, {401, 403})
            other = client.get(path, headers={"cookie": f"kz_session={create_session_token(self.stranger.id)}"})
            self.assertEqual(other.status_code, 403)
            owner = client.post(path, json={"body": "Test link je poslat."}, headers={"cookie": f"kz_session={create_session_token(self.owner.id)}"})
            self.assertEqual(owner.status_code, 200)
            tester = client.get(path, headers={"cookie": f"kz_session={create_session_token(self.tester.id)}"})
            self.assertEqual(tester.status_code, 200)
            self.assertEqual(tester.json()["messages"][0]["body"], "Test link je poslat.")
        finally:
            app.dependency_overrides.pop(get_db, None)


if __name__ == "__main__":
    unittest.main()
