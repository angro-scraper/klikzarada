from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
PUBLIC_HTML_PACK = ROOT / "public_html_pack"


def main() -> int:
    DIST.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    zip_path = DIST / f"sacuvaj-hranu-public-html-landing-{timestamp}.zip"
    source = ROOT / "deploy_static_landing.html"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(source, "index.html")
        if PUBLIC_HTML_PACK.exists():
            for path in sorted(PUBLIC_HTML_PACK.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(PUBLIC_HTML_PACK).as_posix())
    print(zip_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
