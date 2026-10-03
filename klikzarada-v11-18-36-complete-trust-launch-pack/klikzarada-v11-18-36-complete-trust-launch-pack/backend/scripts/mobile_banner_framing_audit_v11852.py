from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "frontend" / "src" / "pages" / "Landing.tsx"
MAIN = ROOT / "app" / "main.py"


def assert_contains(path: Path, text: str, label: str) -> bool:
    found = text in path.read_text(encoding="utf-8")
    print(("OK" if found else "FAIL"), label)
    return found


checks = [
    assert_contains(LANDING, "min-h-[152px] sm:min-h-[230px]", "hero banner je nizi na telefonu"),
    assert_contains(LANDING, "min-h-[118px] sm:min-h-[190px]", "kartice koriste mobilnu visinu"),
    assert_contains(LANDING, "object-contain object-center", "mobilni prikaz ne sece kreativnu sliku"),
    assert_contains(LANDING, "sm:gap-2 sm:px-4 sm:py-2", "tekstualna traka se siri tek na vecem ekranu"),
    assert_contains(LANDING, "text-xs sm:text-sm md:text-base", "naslov se prilagodjava sirini telefona"),
    assert_contains(MAIN, 'version="11.18.52"', "FastAPI verzija je povecana"),
]

print("RESULT:", "PASS" if all(checks) else "CHECK_FAILED")
raise SystemExit(0 if all(checks) else 1)
