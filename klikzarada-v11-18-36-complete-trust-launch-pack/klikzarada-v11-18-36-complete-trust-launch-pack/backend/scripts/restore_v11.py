from pathlib import Path
import shutil
import sys

if len(sys.argv) < 2:
    print("Usage: python scripts/restore_v11.py backups/filename.db")
    raise SystemExit(1)

src = Path(sys.argv[1])
dst = Path("klikzarada_v11.db")

if not src.exists():
    print("Backup file not found:", src)
    raise SystemExit(1)

if dst.exists():
    safety = Path("klikzarada_v11_before_restore.db")
    shutil.copy2(dst, safety)
    print("Current DB copied to:", safety)

shutil.copy2(src, dst)
print("Restored:", src, "->", dst)
