from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "dist" / "live_release_manifest_latest.json"


def main() -> int:
    if not MANIFEST.exists():
        print("Nema live release manifesta. Prvo pokreni: .\\build_live_release.ps1")
        return 2

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    artifacts = {item["role"]: item for item in manifest.get("artifacts", [])}
    public_html = artifacts.get("public_html_latest")
    app_zip = artifacts.get("adriahost_app_latest")

    print("SAČUVAJ HRANU - LIVE UPLOAD PLAN")
    print("=" * 38)
    print(f"Domen: {manifest.get('domain')}")
    print(f"Server IP: {manifest.get('target_ip')}")
    print()
    print("1. Pre upload-a pokreni provere:")
    print("   .\\run_live_verify.ps1")
    print("   .\\check_mysql_schema.ps1")
    print("   .\\check_live_release.ps1")
    print("   .\\check_public_html_package.ps1")
    print()
    if public_html:
        print("2. Public_html paket za trenutno aktivnu stranicu:")
        print(f"   {public_html['file']}")
        print(f"   SHA256: {public_html['sha256']}")
        print("   Upload cilj: DirectAdmin -> File Manager -> domains/sacuvaj-hranu.rs/public_html")
        print("   Raspakuj u public_html tako da index.html bude direktno u public_html folderu.")
        print()
    if app_zip:
        print("3. Full app paket za backend, kada hosting potvrdi Python/Application Manager:")
        print(f"   {app_zip['file']}")
        print(f"   SHA256: {app_zip['sha256']}")
        print("   Ako Basic paket nema Python app manager, backend ide na Render/Railway/VPS.")
        print()
    print("4. Posle upload-a proveri:")
    print("   .\\run_remote_smoke.ps1 -BaseUrl https://sacuvaj-hranu.rs")
    print("   .\\check_domain_ready.ps1 -Domain https://sacuvaj-hranu.rs -ExpectedIp 37.48.77.143")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
