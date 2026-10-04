"""Submitted image evidence is durable and visible only to its participants."""

import os
import sys
import unittest
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base  # noqa: E402
from app.main import save_file, submission_proof_asset  # noqa: E402
from app.models import SubmissionProofAsset, Task, TaskSubmission, User  # noqa: E402
from app.security import create_session_token  # noqa: E402


class ProofStorageTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)
        self.db = self.session()
        self.owner = User(full_name="Owner", email="proof-owner@example.com", password_hash="hash", role="oglasivac")
        self.worker = User(full_name="Worker", email="proof-worker@example.com", password_hash="hash", role="korisnik")
        self.other = User(full_name="Other", email="proof-other@example.com", password_hash="hash", role="korisnik")
        self.db.add_all([self.owner, self.worker, self.other])
        self.db.flush()
        self.task = Task(advertiser_id=self.owner.id, title="Proof", category="Test", task_type="standard", description="Test", instructions="Test", proof_required="Screenshot", reward_rsd=20, total_slots=1, status="active")
        self.db.add(self.task)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    @staticmethod
    def request(user=None):
        headers = [(b"cookie", f"kz_session={create_session_token(user.id)}".encode())] if user else []
        return Request({"type": "http", "method": "GET", "scheme": "https", "path": "/proof-assets/test.png", "headers": headers, "client": ("198.51.100.20", 443)})

    def test_new_proof_survives_new_session_and_denies_others(self):
        output = BytesIO()
        Image.new("RGB", (100, 100), "green").save(output, format="PNG")
        proof_url = save_file(UploadFile(filename="evidence.png", file=BytesIO(output.getvalue())), self.db)
        self.db.add(TaskSubmission(user_id=self.worker.id, task_id=self.task.id, proof="Done", proof_file=proof_url, reward_rsd=20))
        self.db.commit()
        self.assertEqual(self.db.query(SubmissionProofAsset).count(), 1)
        filename = proof_url.rsplit("/", 1)[-1]
        with self.session() as new_session:
            for user in (self.worker, self.owner):
                response = submission_proof_asset(filename, self.request(user), new_session)
                self.assertEqual(response.media_type, "image/png")
                self.assertEqual(response.headers["cache-control"], "private, no-store")
            for user in (self.other, None):
                with self.assertRaises(HTTPException) as denied:
                    submission_proof_asset(filename, self.request(user), new_session)
                self.assertEqual(denied.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
