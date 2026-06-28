"""
KlikZarada V11.18.24
Run automation once.

PowerShell:
    cd backend
    .\.venv\Scripts\Activate.ps1
    python scripts\run_automation_once_v11824.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app.main  # noqa
from app.database import SessionLocal

def main():
    app.main.startup()
    db = SessionLocal()
    try:
        result = app.main.v11823_run_automation(db)
        print(json.dumps({"status": "ok", "result": result}, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False, indent=2))
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    raise SystemExit(main())
