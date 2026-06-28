"""
KlikZarada V11.18.24
Simple local scheduler loop.

PowerShell:
    cd backend
    .\.venv\Scripts\Activate.ps1
    python scripts\automation_scheduler_v11824.py --minutes 15

Stop: Ctrl+C
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app.main  # noqa
from app.database import SessionLocal

def run_once():
    app.main.startup()
    db = SessionLocal()
    try:
        result = app.main.v11823_run_automation(db)
        payload = {"at": datetime.utcnow().isoformat(), "status": "ok", "result": result}
        print(json.dumps(payload, ensure_ascii=False))
        return payload
    except Exception as e:
        payload = {"at": datetime.utcnow().isoformat(), "status": "error", "error": str(e)}
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        return payload
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=int, default=15)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    if args.once:
        run_once()
        return 0

    interval = max(1, args.minutes) * 60
    print(f"KlikZarada automation scheduler started. Interval: {args.minutes} min")
    while True:
        run_once()
        time.sleep(interval)

if __name__ == "__main__":
    raise SystemExit(main())
