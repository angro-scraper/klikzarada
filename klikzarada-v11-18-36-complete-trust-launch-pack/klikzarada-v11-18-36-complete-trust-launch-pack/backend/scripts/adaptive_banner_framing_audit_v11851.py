from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "frontend" / "src" / "pages" / "Landing.tsx"
MAIN = ROOT / "app" / "main.py"


def assert_contains(path: Path, text: str, label: str) -> bool:
    found = text in path.read_text(encoding="utf-8")
    print(("OK" if found else "FAIL"), label)
    return found


checks = [
    assert_contains(LANDING, "opacity-35 blur-2xl", "pozadina popunjava okvir istom slikom"),
    assert_contains(LANDING, "object-contain object-center", "jasna slika ostaje cela bez secenja"),
    assert_contains(LANDING, "aria-hidden=\"true\"", "pozadinska kopija nije citana kao sadrzaj"),
    assert_contains(LANDING, "from-slate-950/55", "donja traka ostaje citljiva"),
    assert_contains(LANDING, "truncate font-extrabold", "tekst ostaje jedna kratka linija"),
    assert_contains(MAIN, 'version="11.18.51"', "FastAPI verzija je povecana"),
]

print("RESULT:", "PASS" if all(checks) else "CHECK_FAILED")
raise SystemExit(0 if all(checks) else 1)
