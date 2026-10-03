from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CREATIVE = ROOT / "frontend" / "public" / "banner-creatives" / "klikzarada-app-coming-soon-v2.png"
MAIN = ROOT / "app" / "main.py"

with Image.open(CREATIVE) as image:
    width, height = image.size

checks = [
    CREATIVE.is_file(),
    (width, height) == (2172, 724),
    width / height == 3,
    'version="11.18.54"' in MAIN.read_text(encoding="utf-8"),
]

labels = [
    "KlikZarada kreativa postoji",
    "kreativa ima planiranu rezoluciju 2172x724",
    "kreativa koristi nativni odnos 3:1",
    "FastAPI verzija je povecana",
]

for label, passed in zip(labels, checks):
    print("OK" if passed else "FAIL", label)

print("RESULT:", "PASS" if all(checks) else "CHECK_FAILED")
raise SystemExit(0 if all(checks) else 1)
