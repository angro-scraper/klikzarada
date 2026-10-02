"""Audit iOS prikaza kampanje bez linka za dopunu budzeta."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app


def main() -> None:
    src = Path(__file__).resolve().parents[1] / "mobile" / "src"
    live = (src / "LiveApp.tsx").read_text(encoding="utf-8")
    builder = (src / "CampaignBuilder.tsx").read_text(encoding="utf-8")
    assert app.version == "11.18.47"
    assert "native_platform') === 'ios'" in live
    assert "allowTopupLink={!isIosApp}" in live
    assert "allowTopupLink ?" in builder
    assert "Trenutni budžet nije dovoljan za ovu kampanju." in builder
    print("OK: iOS mobilni prikaz ne nudi dopunu budzeta; ostali prikazi je zadrzavaju")


if __name__ == "__main__":
    main()
