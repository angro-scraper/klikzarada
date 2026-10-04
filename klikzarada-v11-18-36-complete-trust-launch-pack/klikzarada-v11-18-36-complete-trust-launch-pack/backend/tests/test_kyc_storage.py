"""KYC documents survive deploys without becoming public files."""

import os
import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

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
from app.main import kyc_file, user_kyc_upload  # noqa: E402
from app.models import KycDocument, KycDocumentAsset, User  # noqa: E402
from app.security import create_session_token  # noqa: E402


class KycStorageTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)
        self.db = self.session()
        self.owner = User(full_name="Owner", email="kyc-owner@example.com", password_hash="hash", role="korisnik")
        self.other = User(full_name="Other", email="kyc-other@example.com", password_hash="hash", role="korisnik")
        self.db.add_all([self.owner, self.other])
        self.db.commit()
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name) / "kyc"

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        self.temp.cleanup()

    @staticmethod
    def request(user=None, method="GET"):
        headers = [(b"cookie", f"kz_session={create_session_token(user.id)}".encode())] if user else []
        return Request({"type": "http", "method": method, "scheme": "https", "path": "/kyc/files/1", "headers": headers, "client": ("198.51.100.20", 443)})

    def test_new_document_is_durable_and_private(self):
        output = BytesIO()
        Image.new("RGB", (80, 80), "blue").save(output, format="PNG")
        with patch("app.main.KYC_UPLOAD_DIR", self.folder):
            response = user_kyc_upload(self.request(self.owner, "POST"), "identity", UploadFile(filename="id.png", file=BytesIO(output.getvalue())), self.db)
            self.assertEqual(response.status_code, 303)
            self.assertFalse(self.folder.exists())
            doc = self.db.query(KycDocument).one()
            self.assertEqual(doc.file_path, f"/kyc/files/{doc.id}")
            self.assertEqual(self.db.query(KycDocumentAsset).count(), 1)
            with self.session() as fresh_db:
                stored = kyc_file(doc.id, self.request(self.owner), fresh_db)
                self.assertEqual(stored.body, output.getvalue())
                self.assertEqual(stored.headers["cache-control"], "private, no-store")
                self.assertIn("attachment", stored.headers["content-disposition"])
                for user in (self.other, None):
                    with self.assertRaises(HTTPException) as denied:
                        kyc_file(doc.id, self.request(user), fresh_db)
                    self.assertIn(denied.exception.status_code, (401, 404))

    def test_existing_disk_document_remains_readable(self):
        doc = KycDocument(user_id=self.owner.id, doc_type="identity", file_path="/kyc/files/1", status="pending")
        self.db.add(doc)
        self.db.commit()
        self.folder.mkdir()
        (self.folder / f"{doc.id}.pdf").write_bytes(b"%PDF-legacy")
        with patch("app.main.KYC_UPLOAD_DIR", self.folder):
            response = kyc_file(doc.id, self.request(self.owner), self.db)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "private, no-store")
            with self.assertRaises(HTTPException) as denied:
                kyc_file(doc.id, self.request(self.other), self.db)
            self.assertEqual(denied.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
