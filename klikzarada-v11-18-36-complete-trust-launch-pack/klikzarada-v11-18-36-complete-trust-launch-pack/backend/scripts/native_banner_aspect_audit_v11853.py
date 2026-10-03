from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "frontend" / "src" / "pages" / "Landing.tsx"
MAIN = ROOT / "app" / "main.py"
CREATIVES = ROOT / "frontend" / "public" / "banner-creatives"


def assert_contains(path: Path, text: str, label: str) -> bool:
    found = text in path.read_text(encoding="utf-8")
    print(("OK" if found else "FAIL"), label)
    return found


checks = [
    assert_contains(LANDING, "aspect-[3/1]", "kartice koriste nativni odnos stranica bannera"),
    assert_contains(LANDING, "object-contain object-center", "slika ostaje cela u okviru"),
    assert_contains(LANDING, "opacity-35 blur-2xl", "pozadina popunjava samo minimalna odstupanja"),
    assert_contains(LANDING, "h-full flex-col justify-end", "traka se vezuje za dno bannera"),
    assert_contains(MAIN, 'version="11.18.53"', "FastAPI verzija je povecana"),
    (CREATIVES / "stock-radar-beta.png").stat().st_size > 100_000,
    (CREATIVES / "parkiraj-me-beta.png").stat().st_size > 100_000,
]

print("OK" if checks[-2] else "FAIL", "Stock Radar kreativa je lokalno dostupna")
print("OK" if checks[-1] else "FAIL", "Parkiraj Me kreativa je lokalno dostupna")
print("RESULT:", "PASS" if all(checks) else "CHECK_FAILED")
raise SystemExit(0 if all(checks) else 1)
