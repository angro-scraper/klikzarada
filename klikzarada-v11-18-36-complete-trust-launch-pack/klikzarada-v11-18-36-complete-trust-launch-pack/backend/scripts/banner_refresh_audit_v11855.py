from pathlib import Path
from struct import unpack


ROOT = Path(__file__).resolve().parents[1]
CREATIVES = ROOT / "frontend" / "public" / "banner-creatives"
LANDING = ROOT / "frontend" / "src" / "pages" / "Landing.tsx"
PANEL = ROOT / "frontend" / "src" / "pages" / "AdvertiserPanel.tsx"
MAIN = ROOT / "app" / "main.py"


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as image:
        assert image.read(8) == b"\x89PNG\r\n\x1a\n"
        image.read(4)
        assert image.read(4) == b"IHDR"
        return unpack(">II", image.read(8))


stock_png = CREATIVES / "stock-radar-beta-v2.png"
stock_webp = CREATIVES / "stock-radar-beta-v2.webp"
checks = [
    png_size(stock_png) == (2172, 724),
    stock_webp.is_file() and stock_webp.stat().st_size > 50_000,
    all(token in LANDING.read_text(encoding="utf-8") for token in ("stock-radar-beta.png", "-v2.webp")),
    "firstBookableBannerDate" in PANEL.read_text(encoding="utf-8"),
    'version="11.18.55"' in MAIN.read_text(encoding="utf-8"),
]
labels = [
    "Stock Radar v2 je nativni 3:1 PNG",
    "Stock Radar v2 WebP je dostupan",
    "aktivni Stock Radar koristi v2 kreativnu sliku",
    "obrazac bira prvi stvarno dostupan termin",
    "FastAPI verzija je povecana",
]

for label, passed in zip(labels, checks):
    print("OK" if passed else "FAIL", label)

print("RESULT:", "PASS" if all(checks) else "CHECK_FAILED")
raise SystemExit(0 if all(checks) else 1)
