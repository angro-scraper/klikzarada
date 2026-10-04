"""New banner images must survive a new request without relying on local disk."""

import asyncio
import os
import sys
import unittest
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base  # noqa: E402
from app.models import BannerImageAsset, HomeBannerSlotV111, User  # noqa: E402
from app.security import create_session_token  # noqa: E402
from app.ui_api import upload_advertiser_banner, uploaded_banner_file  # noqa: E402
from app.main import v11819_make_banner_svg, v11819_save_banner_svg, v11828_save_uploaded_banner_packed  # noqa: E402


class BannerAssetTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)
        self.db = self.session()
        self.owner = User(full_name="Advertiser", email="banner-owner@example.com", password_hash="hash", role="oglasivac")
        self.db.add(self.owner)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def request(self):
        return Request({
            "type": "http", "method": "POST", "scheme": "https", "path": "/api/ui/advertiser/banners/upload",
            "headers": [(b"cookie", f"kz_session={create_session_token(self.owner.id)}".encode())],
            "client": ("198.51.100.20", 443),
        })

    @staticmethod
    def image_file():
        output = BytesIO()
        Image.new("RGB", (320, 120), "blue").save(output, format="PNG")
        return UploadFile(filename="banner.png", file=BytesIO(output.getvalue()), headers={"content-type": "image/png"})

    def test_upload_is_served_from_database_in_new_session(self):
        result = asyncio.run(upload_advertiser_banner(self.image_file(), self.request(), self.db))
        self.assertEqual(self.db.query(BannerImageAsset).count(), 1)
        self.assertNotIn("warning", result)
        filename = result["image_url"].rsplit("/", 1)[-1]
        with self.session() as new_session:
            response = uploaded_banner_file(filename, new_session)
            self.assertEqual(response.media_type, "image/png")
            self.assertEqual(response.body[:8], b"\x89PNG\r\n\x1a\n")

    def test_packed_and_generated_images_use_same_durable_route(self):
        slot = HomeBannerSlotV111(code="home_bottom_1", title="Bottom")
        packed_url = asyncio.run(v11828_save_uploaded_banner_packed(slot, "Test", self.image_file(), db=self.db))
        svg_url = v11819_save_banner_svg(slot.code, "Test", "Description", db=self.db)
        self.db.commit()
        with self.session() as new_session:
            packed = uploaded_banner_file(packed_url.rsplit("/", 1)[-1], new_session)
            generated = uploaded_banner_file(svg_url.rsplit("/", 1)[-1], new_session)
        self.assertEqual(packed.media_type, "image/jpeg")
        self.assertTrue(packed.body.startswith(b"\xff\xd8"))
        self.assertEqual(generated.media_type, "image/svg+xml")
        self.assertIn(b"<svg", generated.body)
        self.assertIn("sandbox", generated.headers["content-security-policy"])

    def test_generated_svg_rejects_attribute_injection_in_accent(self):
        svg = v11819_make_banner_svg("home_bottom_1", "Test", "Description", accent='red" onload="alert(1)')
        self.assertNotIn("onload", svg)
        self.assertIn('fill="#ffffff"', svg)


if __name__ == "__main__":
    unittest.main()
