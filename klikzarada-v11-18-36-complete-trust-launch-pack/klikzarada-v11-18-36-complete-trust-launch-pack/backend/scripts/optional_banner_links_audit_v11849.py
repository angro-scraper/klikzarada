from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "app" / "main.py"
UI_API = ROOT / "app" / "ui_api.py"
ADVERTISER_PANEL = ROOT / "frontend" / "src" / "pages" / "AdvertiserPanel.tsx"
API_CLIENT = ROOT / "frontend" / "src" / "lib" / "api.ts"
LANDING = ROOT / "frontend" / "src" / "pages" / "Landing.tsx"


def assert_contains(path: Path, text: str, label: str) -> bool:
    found = text in path.read_text(encoding="utf-8")
    print(("OK" if found else "FAIL"), label)
    return found


checks = [
    assert_contains(UI_API, "target_url: str | None = Field(default=None, max_length=500)", "API dozvoljava banner bez linka"),
    assert_contains(UI_API, "if not url:\n        return None", "prazan link se cuva kao None"),
    assert_contains(ADVERTISER_PANEL, "!bannerTitle.trim() || !Number.isInteger(daysCount)", "forma ne zahteva link"),
    assert_contains(ADVERTISER_PANEL, "target_url: bannerUrl.trim() || undefined", "forma salje link samo kada postoji"),
    assert_contains(ADVERTISER_PANEL, "Link na koji vodi banner (opciono)", "forma oznacava opcioni link"),
    assert_contains(API_CLIENT, "target_url?: string; days_count", "klijent podrzava opcioni link"),
    assert_contains(LANDING, "return targetUrl ?", "javni banner nije klikabilan bez linka"),
    assert_contains(MAIN, 'version="11.18.49"', "FastAPI verzija je povecana"),
]

print("RESULT:", "PASS" if all(checks) else "CHECK_FAILED")
raise SystemExit(0 if all(checks) else 1)
