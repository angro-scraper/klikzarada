from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import zipfile


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"

REQUIRED_FILES = {
    "index.html",
    ".htaccess",
    "robots.txt",
    "sitemap.xml",
    "site.webmanifest",
}

FORBIDDEN_PREFIXES = {
    "app/",
    "data/",
    "docs/",
    ".venv/",
    "__pycache__/",
}


def latest_public_html_zip() -> Path:
    alias = DIST / "sacuvaj-hranu-public-html-landing-latest.zip"
    if alias.exists():
        return alias
    matches = sorted(
        DIST.glob("sacuvaj-hranu-public-html-landing-*.zip"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not matches:
        raise FileNotFoundError("Nema public_html ZIP paketa u dist folderu.")
    return matches[0]


def inspect_zip(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        names = [name.replace("\\", "/") for name in archive.namelist()]

    files = {name.rstrip("/") for name in names if not name.endswith("/")}
    missing = sorted(REQUIRED_FILES - files)
    nested_required = sorted(
        required for required in REQUIRED_FILES if required not in files and any(name.endswith("/" + required) for name in files)
    )
    forbidden = sorted(
        name for name in files for prefix in FORBIDDEN_PREFIXES if name.startswith(prefix)
    )
    top_level_dirs = sorted({name.split("/", 1)[0] for name in files if "/" in name})

    return {
        "ok": not missing and not forbidden and not nested_required,
        "zip": str(path),
        "bytes": path.stat().st_size,
        "required_files": sorted(REQUIRED_FILES),
        "missing": missing,
        "nested_required_files": nested_required,
        "forbidden_entries": forbidden,
        "top_level_dirs": top_level_dirs,
        "upload_target": "DirectAdmin File Manager -> domains/sacuvaj-hranu.rs/public_html",
        "upload_action": "Raspakovati ZIP direktno u public_html tako da index.html bude u korenu public_html foldera.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Proverava da li je public_html ZIP spreman za AdriaHost upload.")
    parser.add_argument("--zip", dest="zip_path", help="Putanja do public_html ZIP paketa.")
    args = parser.parse_args()

    path = Path(args.zip_path).resolve() if args.zip_path else latest_public_html_zip()
    if not path.exists():
        print(json.dumps({"ok": False, "error": f"ZIP ne postoji: {path}"}, ensure_ascii=False, indent=2))
        return 2

    report = inspect_zip(path)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
