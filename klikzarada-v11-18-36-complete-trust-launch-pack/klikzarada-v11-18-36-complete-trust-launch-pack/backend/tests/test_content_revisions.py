"""Approved campaigns and banners remain unchanged until an admin reviews edits."""

import os
import sys
import unittest
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request


BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base  # noqa: E402
from app.models import ModeratedContentRevision, PaidAdBannerV111, Task, User  # noqa: E402
from app.security import create_session_token  # noqa: E402
from app.ui_api import (  # noqa: E402
    BannerContentEditPayload,
    BannerTargetUpdatePayload,
    CampaignContentEditPayload,
    ContentRevisionReviewPayload,
    admin_content_revisions,
    advertiser_content_revisions,
    edit_active_campaign_content,
    edit_advertiser_banner,
    review_content_revision,
    update_advertiser_banner_target,
)


class ContentRevisionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.owner = User(full_name="Vlasnik", email="owner@example.com", password_hash="hash", role="oglasivac")
        self.other = User(full_name="Drugi", email="other@example.com", password_hash="hash", role="oglasivac")
        self.admin = User(full_name="Admin", email="admin@example.com", password_hash="hash", role="admin")
        self.db.add_all([self.owner, self.other, self.admin])
        self.db.flush()
        self.task = Task(
            advertiser_id=self.owner.id, title="Stara kampanja", category="Testiranje sajta ili aplikacije",
            task_type="web", target_url="https://example.com/old", description="Stari opis kampanje",
            instructions="Ne menjati uslove testa", proof_required="Izveštaj", reward_rsd=20,
            total_slots=10, status="active",
        )
        self.banner = PaidAdBannerV111(
            advertiser_id=self.owner.id, title="Stari banner", body="Stari opis",
            image_url=None, target_url="https://example.com/old", status="active", days_count=7,
        )
        self.db.add_all([self.task, self.banner])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    @staticmethod
    def request(user):
        return Request({
            "type": "http", "method": "PUT", "scheme": "https", "path": "/api/ui/advertiser/content-revisions",
            "headers": [(b"cookie", f"kz_session={create_session_token(user.id)}".encode())],
            "client": ("198.51.100.20", 443),
        })

    def test_active_campaign_edit_requires_admin_and_preserves_economics(self):
        submitted = edit_active_campaign_content(
            self.task.id,
            CampaignContentEditPayload(title="Novi naslov", description="Novi opis kampanje", target_url="https://example.com/new"),
            self.request(self.owner), self.db,
        )
        self.db.refresh(self.task)
        self.assertEqual(self.task.title, "Stara kampanja")
        self.assertEqual(self.task.target_url, "https://example.com/old")
        self.assertEqual(self.task.reward_rsd, 20)
        self.assertEqual(submitted["revision"]["status"], "pending")
        self.assertEqual(len(advertiser_content_revisions(self.request(self.owner), self.db)["revisions"]), 1)
        self.assertEqual(len(advertiser_content_revisions(self.request(self.other), self.db)["revisions"]), 0)
        self.assertEqual(len(admin_content_revisions(self.request(self.admin), self.db)["revisions"]), 1)
        with self.assertRaises(HTTPException) as duplicate:
            edit_active_campaign_content(
                self.task.id,
                CampaignContentEditPayload(title="Treći naslov", description="Još jedan opis kampanje"),
                self.request(self.owner), self.db,
            )
        self.assertEqual(duplicate.exception.status_code, 409)
        reviewed = review_content_revision(
            submitted["revision"]["id"], ContentRevisionReviewPayload(status="approved"),
            self.request(self.admin), self.db,
        )
        self.db.refresh(self.task)
        self.assertEqual(reviewed["revision"]["status"], "approved")
        self.assertEqual(self.task.title, "Novi naslov")
        self.assertEqual(self.task.target_url, "https://example.com/new")
        self.assertEqual(self.task.instructions, "Ne menjati uslove testa")
        self.assertEqual(self.task.reward_rsd, 20)
        self.assertEqual(self.task.status, "active")

    def test_other_advertiser_cannot_edit_campaign(self):
        with self.assertRaises(HTTPException) as caught:
            edit_active_campaign_content(
                self.task.id,
                CampaignContentEditPayload(title="Tuđ naslov", description="Novi opis kampanje"),
                self.request(self.other), self.db,
            )
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(self.db.query(ModeratedContentRevision).count(), 0)

    def test_active_banner_target_change_is_staged_even_through_legacy_route(self):
        result = update_advertiser_banner_target(
            self.banner.id, BannerTargetUpdatePayload(target_url="https://example.com/new"),
            self.request(self.owner), self.db,
        )
        self.db.refresh(self.banner)
        self.assertEqual(self.banner.target_url, "https://example.com/old")
        self.assertEqual(result["revision"]["changes"]["target_url"], "https://example.com/new")
        review_content_revision(
            result["revision"]["id"], ContentRevisionReviewPayload(status="rejected", note="Link nije odgovarajući"),
            self.request(self.admin), self.db,
        )
        self.db.refresh(self.banner)
        self.assertEqual(self.banner.target_url, "https://example.com/old")
        self.assertEqual(self.db.query(ModeratedContentRevision).first().status, "rejected")

    def test_pending_banner_can_be_edited_but_stays_pending(self):
        self.banner.status = "pending"
        self.db.commit()
        result = edit_advertiser_banner(
            self.banner.id,
            BannerContentEditPayload(title="Novi banner", body="Novi tekst", target_url="https://example.com/new"),
            self.request(self.owner), self.db,
        )
        self.db.refresh(self.banner)
        self.assertIsNone(result["revision"])
        self.assertEqual(self.banner.title, "Novi banner")
        self.assertEqual(self.banner.status, "pending")
        self.assertEqual(self.db.query(ModeratedContentRevision).count(), 0)

    def test_active_banner_is_unchanged_until_admin_approval(self):
        submitted = edit_advertiser_banner(
            self.banner.id,
            BannerContentEditPayload(
                title="Novi banner", body="Novi tekst",
                image_url="https://example.com/new.png", target_url="https://example.com/new",
            ),
            self.request(self.owner), self.db,
        )
        self.db.refresh(self.banner)
        self.assertEqual(self.banner.title, "Stari banner")
        self.assertEqual(self.banner.days_count, 7)
        self.assertEqual(self.banner.target_url, "https://example.com/old")
        with self.assertRaises(HTTPException) as duplicate:
            edit_advertiser_banner(
                self.banner.id,
                BannerContentEditPayload(title="Drugi banner"),
                self.request(self.owner), self.db,
            )
        self.assertEqual(duplicate.exception.status_code, 409)
        with self.assertRaises(HTTPException) as forbidden:
            review_content_revision(
                submitted["revision"]["id"], ContentRevisionReviewPayload(status="approved"),
                self.request(self.other), self.db,
            )
        self.assertEqual(forbidden.exception.status_code, 403)
        review_content_revision(
            submitted["revision"]["id"], ContentRevisionReviewPayload(status="approved"),
            self.request(self.admin), self.db,
        )
        self.db.refresh(self.banner)
        self.assertEqual(self.banner.title, "Novi banner")
        self.assertEqual(self.banner.target_url, "https://example.com/new")
        self.assertEqual(self.banner.status, "active")
        self.assertEqual(self.banner.days_count, 7)

    def test_rejection_requires_reason_on_server(self):
        submitted = edit_active_campaign_content(
            self.task.id,
            CampaignContentEditPayload(title="Novi naslov", description="Novi opis kampanje"),
            self.request(self.owner), self.db,
        )
        with self.assertRaises(HTTPException) as caught:
            review_content_revision(
                submitted["revision"]["id"], ContentRevisionReviewPayload(status="rejected"),
                self.request(self.admin), self.db,
            )
        self.assertEqual(caught.exception.status_code, 400)
        self.db.refresh(self.task)
        self.assertEqual(self.task.title, "Stara kampanja")


if __name__ == "__main__":
    unittest.main()
