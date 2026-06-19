from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT / "dist"

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "data",
    "dist",
}
EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".db",
    ".sqlite",
    ".log",
    ".png",
}
EXCLUDED_NAMES = {
    ".env",
    ".env.local",
    ".env.production.generated",
    ".env.production.generated.test",
    "food_saver.db",
    "server.out.log",
    "server.err.log",
}


def should_include(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in EXCLUDED_DIRS for part in rel.parts):
        return False
    if path.name in EXCLUDED_NAMES:
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if path.name.startswith("qa-"):
        return False
    return True


def build_package(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    zip_path = output_dir / f"sacuvaj-hranu-adriahost-{timestamp}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and should_include(path):
                archive.write(path, path.relative_to(ROOT).as_posix())
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Gradi ZIP paket za AdriaHost/DirectAdmin upload.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    zip_path = build_package(Path(args.output_dir).resolve())
    print(f"AdriaHost paket: {zip_path}")
    print("Ne sadrži .env, lokalnu bazu, venv, logove, backup ni QA slike.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
