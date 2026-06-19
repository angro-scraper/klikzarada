from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[1].parent / "data"


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def data_file(name: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    safe = name.replace("/", "_").replace("..", "_")
    return DATA_DIR / safe


def read_json(name: str, default: Any) -> Any:
    path = data_file(name)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(name: str, payload: Any) -> Any:
    path = data_file(name)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def append_json_row(name: str, row: dict[str, Any], *, max_rows: int = 5000) -> dict[str, Any]:
    rows = read_json(name, [])
    if not isinstance(rows, list):
        rows = []
    payload = dict(row)
    payload.setdefault("id", f"{int(time.time() * 1000)}")
    payload.setdefault("created_at", utc_now())
    payload.setdefault("updated_at", payload["created_at"])
    rows.append(payload)
    write_json(name, rows[-max_rows:])
    return payload


def update_json_row(name: str, row_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    rows = read_json(name, [])
    if not isinstance(rows, list):
        return None
    for idx, row in enumerate(rows):
        if str(row.get("id")) == str(row_id):
            updated = dict(row)
            updated.update(patch)
            updated["updated_at"] = utc_now()
            rows[idx] = updated
            write_json(name, rows)
            return updated
    return None
