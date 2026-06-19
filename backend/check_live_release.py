from __future__ import annotations

import json
from pathlib import Path

from build_live_release import sha256


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "dist" / "live_release_manifest_latest.json"


def main() -> int:
    if not MANIFEST.exists():
        print(json.dumps({"ok": False, "error": "Manifest ne postoji. Pokreni build_live_release.ps1."}, ensure_ascii=False, indent=2))
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    checks = []
    for item in manifest.get("artifacts", []):
        path = Path(item["file"])
        ok = path.exists() and sha256(path) == item.get("sha256")
        checks.append({
            "role": item.get("role"),
            "name": item.get("name"),
            "exists": path.exists(),
            "sha256_ok": ok,
            "bytes": path.stat().st_size if path.exists() else 0,
        })
    result = {"ok": all(item["sha256_ok"] for item in checks), "manifest": str(MANIFEST), "checks": checks}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
