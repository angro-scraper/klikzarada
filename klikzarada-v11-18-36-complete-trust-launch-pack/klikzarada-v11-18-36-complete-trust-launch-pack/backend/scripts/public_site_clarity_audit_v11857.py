"""Static release guard for the V11.18.57 public website update."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(relative: str, marker: str) -> None:
    source = (ROOT / relative).read_text(encoding="utf-8")
    if marker not in source:
        raise SystemExit(f"FAIL {relative}: {marker}")
    print(f"OK {relative}: {marker}")


require("app/main.py", 'version="11.18.57"')
require("app/main.py", 'Disallow: /admin')
require("app/ui_api.py", '@router.get("/public/tasks/{task_id}")')
require("app/ui_api.py", '@router.get("/public/service-terms")')
require("app/ui_api.py", 'class BannerTargetUpdatePayload')
require("frontend/src/App.tsx", "'/oglasavanje'")
require("frontend/src/pages/TasksPublic.tsx", "PublicTaskDetail")
require("frontend/src/pages/Landing.tsx", "targetUrl ? <a")
print("RESULT: PASS")
