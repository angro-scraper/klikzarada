"""Legacy homepage and UI API must agree about scheduled banner delivery."""

import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base  # noqa: E402
from app.main import v11817_active_banner_map, v11863_start_platform_banner_once  # noqa: E402
from app.models import HomeBannerSlotV111, PaidAdBannerV111, SystemSetting, User  # noqa: E402
from app.ui_api import _banner_public_target, public_banners  # noqa: E402


class HomeBannerDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        admin = User(full_name="Admin", email="admin@example.com", password_hash="hash", role="admin")
        slot = HomeBannerSlotV111(code="home_dashboard_banner", title="Početna ispod isplate", is_active=True)
        self.db.add_all([admin, slot])
        self.db.flush()
        now = datetime.utcnow()
        self.banner = PaidAdBannerV111(
            advertiser_id=admin.id, slot_id=slot.id, title="KlikZarada aplikacija uskoro stiže",
            status="active", target_url="https://testflight.apple.com/join/aFqfk5Am",
            starts_at=now + timedelta(hours=1), ends_at=now + timedelta(days=7, hours=1), days_count=7,
        )
        self.db.add(self.banner)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_scheduled_banner_is_absent_from_both_public_surfaces(self):
        self.assertNotIn("home_dashboard_banner", v11817_active_banner_map(self.db))
        self.assertNotIn(self.banner.id, [item["id"] for item in public_banners(self.db)["banners"]])

    def test_live_banner_leads_to_task_on_both_public_surfaces(self):
        self.banner.starts_at = datetime.utcnow() - timedelta(minutes=1)
        self.db.commit()
        homepage = v11817_active_banner_map(self.db)
        self.assertEqual(homepage["home_dashboard_banner"].id, self.banner.id)
        self.assertEqual(_banner_public_target(homepage["home_dashboard_banner"]), "/zadaci/7")
        api_banner = next(item for item in public_banners(self.db)["banners"] if item["id"] == self.banner.id)
        self.assertEqual(api_banner["target_url"], "/zadaci/7")

    def test_owner_requested_activation_starts_full_seven_days_once(self):
        self.assertEqual(v11863_start_platform_banner_once(self.db), "started")
        first_start = self.banner.starts_at
        self.assertLess(abs((datetime.utcnow() - first_start).total_seconds()), 10)
        self.assertEqual(self.banner.ends_at - first_start, timedelta(days=7))
        self.assertIn("home_dashboard_banner", v11817_active_banner_map(self.db))
        self.assertEqual(v11863_start_platform_banner_once(self.db), "already_processed")
        self.assertEqual(self.banner.starts_at, first_start)

    def test_conflicting_booking_is_not_moved(self):
        now = datetime.utcnow()
        other = PaidAdBannerV111(
            advertiser_id=self.banner.advertiser_id, slot_id=self.banner.slot_id,
            title="Druga rezervacija", status="active",
            starts_at=now - timedelta(minutes=5), ends_at=now + timedelta(days=1), days_count=1,
        )
        self.db.add(other)
        self.db.commit()
        old_start = self.banner.starts_at
        self.assertEqual(v11863_start_platform_banner_once(self.db), "slot_conflict")
        self.assertEqual(self.banner.starts_at, old_start)
        self.assertEqual(other.starts_at, now - timedelta(minutes=5))
        self.assertEqual(self.db.query(SystemSetting).filter_by(key="v11863_klikzarada_ios_banner_start").one().value, "slot_conflict")


if __name__ == "__main__":
    unittest.main()
