"""Static audit for the beta-task banner handoff introduced in V11.18.56."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "app"
FRONTEND = ROOT / "frontend" / "src"


def require(path: Path, text: str, label: str) -> None:
    content = path.read_text(encoding="utf-8")
    if text not in content:
        raise SystemExit(f"FAIL {label}: missing {text!r} in {path}")
    print(f"OK {label}")


require(BACKEND / "main.py", 'version="11.18.56"', "FastAPI version")
require(BACKEND / "ui_api.py", '@router.patch("/advertiser/banners/{banner_id}/target")', "owned banner target endpoint")
require(BACKEND / "ui_api.py", "advertiser_banner_target_updated", "banner target audit event")
require(FRONTEND / "App.tsx", "keepsTaskContext", "task context survives auth navigation")
require(FRONTEND / "pages" / "UserDashboard.tsx", "Email za poziv na ovaj test", "neutral tester email label")
require(FRONTEND / "pages" / "AdvertiserPanel.tsx", "Sačuvaj link", "banner link editor")

print("RESULT: PASS")
