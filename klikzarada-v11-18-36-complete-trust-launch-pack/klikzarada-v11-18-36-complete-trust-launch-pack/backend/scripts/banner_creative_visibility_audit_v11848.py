from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "frontend" / "src" / "pages" / "Landing.tsx"
MAIN = ROOT / "app" / "main.py"


def assert_contains(path: Path, text: str, label: str) -> bool:
    found = text in path.read_text(encoding="utf-8")
    print(("OK" if found else "FAIL"), label)
    return found


checks = [
    assert_contains(LANDING, "object-contain", "cela slika se cuva u banner okviru"),
    assert_contains(LANDING, "bg-slate-950/78", "tekst koristi mali kontrastni panel"),
    assert_contains(LANDING, "const targetUrl = banner.target_url?.trim()", "link se proverava pre prikaza"),
    assert_contains(LANDING, "return targetUrl ?", "banner bez linka nije klikabilan"),
    assert_contains(MAIN, 'version="11.18.48"', "FastAPI verzija je povecana"),
]

print("RESULT:", "PASS" if all(checks) else "CHECK_FAILED")
raise SystemExit(0 if all(checks) else 1)
