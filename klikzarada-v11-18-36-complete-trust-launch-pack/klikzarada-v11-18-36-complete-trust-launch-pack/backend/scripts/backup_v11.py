from pathlib import Path
import shutil
import datetime

db = Path("klikzarada_v11.db")
backup_dir = Path("backups")
backup_dir.mkdir(exist_ok=True)

if not db.exists():
    print("Database file not found:", db)
    raise SystemExit(1)

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
target = backup_dir / f"klikzarada_v11_backup_{stamp}.db"
shutil.copy2(db, target)
print("Backup created:", target)
