from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"


def run_python_script(script: str) -> str:
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(ROOT / script)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def latest(pattern: str) -> Path:
    matches = sorted(DIST.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(pattern)
    return matches[0]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact(path: Path, role: str) -> dict:
    return {
        "role": role,
        "file": str(path),
        "name": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def main() -> int:
    DIST.mkdir(parents=True, exist_ok=True)
    static_out = run_python_script("build_static_landing_package.py")
    app_out = run_python_script("build_adriahost_package.py")
    static_zip = latest("sacuvaj-hranu-public-html-landing-*.zip")
    app_zip = latest("sacuvaj-hranu-adriahost-*.zip")

    static_alias = DIST / "sacuvaj-hranu-public-html-landing-latest.zip"
    app_alias = DIST / "sacuvaj-hranu-adriahost-latest.zip"
    shutil.copy2(static_zip, static_alias)
    shutil.copy2(app_zip, app_alias)

    manifest = {
        "format": "sacuvaj-hranu-live-release-v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "domain": "sacuvaj-hranu.rs",
        "target_ip": "37.48.77.143",
        "artifacts": [
            artifact(static_zip, "public_html_timestamped"),
            artifact(static_alias, "public_html_latest"),
            artifact(app_zip, "adriahost_app_timestamped"),
            artifact(app_alias, "adriahost_app_latest"),
        ],
        "commands_before_upload": [
            ".\\run_live_verify.ps1",
            ".\\check_mysql_schema.ps1",
            ".\\build_live_release.ps1",
            ".\\check_live_release.ps1",
        ],
        "upload_order": [
            "Upload sacuvaj-hranu-public-html-landing-latest.zip u public_html i raspakuj preko default index.html.",
            "Ako hosting ima Python/Application Manager, upload sacuvaj-hranu-adriahost-latest.zip u aplikacioni folder.",
            "Podesi env vrednosti iz .env.production.example.",
            "Pokreni prepare_production_db i migrate_live_data tek kada baza postoji.",
        ],
        "verification_after_upload": [
            "https://sacuvaj-hranu.rs/",
            "https://sacuvaj-hranu.rs/robots.txt",
            "https://sacuvaj-hranu.rs/sitemap.xml",
            "https://sacuvaj-hranu.rs/site.webmanifest",
        ],
        "builder_output": {"static": static_out, "app": app_out},
    }
    manifest_path = DIST / f"live_release_manifest_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    latest_manifest = DIST / "live_release_manifest_latest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "manifest": str(manifest_path), "latest_manifest": str(latest_manifest), "artifacts": manifest["artifacts"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
