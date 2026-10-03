"""Focused release audit for campaign and banner edit moderation."""

import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402
from app.ui_api import router as ui_router  # noqa: E402


if __name__ == "__main__":
    assert app.version == "11.18.58"
    paths = {route.path for route in ui_router.routes if hasattr(route, "path")}
    expected = {
        "/api/ui/advertiser/campaigns/{task_id}/content",
        "/api/ui/advertiser/banners/{banner_id}",
        "/api/ui/advertiser/content-revisions",
        "/api/ui/admin/content-revisions",
        "/api/ui/admin/content-revisions/{revision_id}",
    }
    assert expected <= paths, f"Nedostaju rute: {expected - paths}"
    suite = unittest.defaultTestLoader.discover(str(BACKEND_DIR / "tests"), pattern="test_content_revisions.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
