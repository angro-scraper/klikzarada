"""Focused task-chat audit; uses only an isolated in-memory test database."""

import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402
from app.models import TaskChatMessage  # noqa: E402
from app.ui_api import router as ui_router  # noqa: E402


assert tuple(map(int, app.version.split("."))) >= (11, 18, 37)
assert TaskChatMessage.__tablename__ == "task_chat_messages"
for method, path in (
    ("GET", "/api/ui/task-chat/{task_id}/{participant_id}"),
    ("POST", "/api/ui/task-chat/{task_id}/{participant_id}"),
    ("GET", "/api/ui/advertiser/task-chats"),
):
    assert any(path == route.path and method in route.methods for route in ui_router.routes), (method, path)

suite = unittest.defaultTestLoader.loadTestsFromName("tests.test_task_chat")
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
print("Task chat audit: OK")
