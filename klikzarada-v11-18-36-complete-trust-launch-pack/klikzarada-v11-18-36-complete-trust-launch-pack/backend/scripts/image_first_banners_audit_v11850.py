from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "frontend" / "src" / "pages" / "Landing.tsx"
MAIN = ROOT / "app" / "main.py"


def assert_contains(path: Path, text: str, label: str) -> bool:
    found = text in path.read_text(encoding="utf-8")
    print(("OK" if found else "FAIL"), label)
    return found


checks = [
    assert_contains(LANDING, "object-cover object-center", "slika ispunjava ceo banner"),
    assert_contains(LANDING, "h-1/4 bg-gradient-to-t", "gradijent zauzima samo donju cetvrtinu"),
    assert_contains(LANDING, "bg-slate-950/78 px-3 py-2", "tekst je tanka donja traka"),
    assert_contains(LANDING, "truncate font-extrabold", "naslov je jedna skratena linija"),
    assert_contains(LANDING, "Otvori →", "poziv na akciju je kompaktan"),
    assert_contains(MAIN, 'version="11.18.50"', "FastAPI verzija je povecana"),
]

print("RESULT:", "PASS" if all(checks) else "CHECK_FAILED")
raise SystemExit(0 if all(checks) else 1)
