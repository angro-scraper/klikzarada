from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import sys

from sqlalchemy import Date, DateTime, delete, insert, select


ROOT = Path(__file__).resolve().parent
DEFAULT_EXPORT = ROOT / "data" / "live_data_export.json"


def load_models():
    from app.database import Base, SessionLocal, engine
    from app import finance_models, models  # noqa: F401 - registers tables

    return Base, SessionLocal, engine


def serialize_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def parse_value(column, value):
    if value is None:
        return None
    if isinstance(column.type, DateTime) and isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    if isinstance(column.type, Date) and isinstance(value, str):
        return date.fromisoformat(value[:10])
    return value


def table_order(Base):
    return list(Base.metadata.sorted_tables)


def export_data(output: Path) -> dict:
    Base, SessionLocal, engine = load_models()
    payload = {
        "format": "sacuvaj-hranu-live-data-v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_database": engine.url.drivername,
        "tables": {},
    }
    db = SessionLocal()
    try:
        for table in table_order(Base):
            rows = []
            for row in db.execute(select(table)).mappings().all():
                rows.append({key: serialize_value(value) for key, value in dict(row).items()})
            payload["tables"][table.name] = rows
    finally:
        db.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def validate_payload(payload: dict) -> list[str]:
    Base, _, _ = load_models()
    errors: list[str] = []
    if payload.get("format") != "sacuvaj-hranu-live-data-v1":
        errors.append("Nepoznat format export fajla.")
    tables = payload.get("tables")
    if not isinstance(tables, dict):
        errors.append("Nedostaje tables objekat.")
        return errors
    expected = {table.name for table in table_order(Base)}
    missing = sorted(expected - set(tables.keys()))
    if missing:
        errors.append("Nedostaju tabele: " + ", ".join(missing))
    for table in table_order(Base):
        rows = tables.get(table.name, [])
        if not isinstance(rows, list):
            errors.append(f"Tabela {table.name} nije lista.")
            continue
        columns = {column.name for column in table.columns}
        for idx, row in enumerate(rows[:5]):
            extra = set(row.keys()) - columns
            if extra:
                errors.append(f"Tabela {table.name}, red {idx}: nepoznate kolone {sorted(extra)}")
    return errors


def import_data(input_path: Path, *, replace_existing: bool, dry_run: bool) -> dict:
    if not input_path.exists():
        raise FileNotFoundError(str(input_path))
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    errors = validate_payload(payload)
    if errors:
        return {"ok": False, "errors": errors}

    Base, SessionLocal, engine = load_models()
    tables = payload["tables"]
    imported: dict[str, int] = {}
    db = SessionLocal()
    try:
        existing_nonempty = []
        for table in table_order(Base):
            existing_count = db.execute(select(table)).first()
            if existing_count:
                existing_nonempty.append(table.name)
            if existing_count and not dry_run and not replace_existing and tables.get(table.name):
                return {
                    "ok": False,
                    "errors": [f"Tabela {table.name} nije prazna. Koristi --replace-existing za novu produkcionu bazu."],
                }
        if dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "target_database": engine.url.drivername,
                "existing_nonempty_tables": existing_nonempty,
                "replace_existing_required": bool(existing_nonempty),
                "counts": {name: len(rows) for name, rows in tables.items()},
            }
        if replace_existing:
            for table in reversed(table_order(Base)):
                db.execute(delete(table))
        for table in table_order(Base):
            rows = []
            for row in tables.get(table.name, []):
                rows.append({column.name: parse_value(column, row.get(column.name)) for column in table.columns if column.name in row})
            if rows:
                db.execute(insert(table), rows)
            imported[table.name] = len(rows)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return {"ok": True, "target_database": engine.url.drivername, "imported": imported}


def main() -> int:
    parser = argparse.ArgumentParser(description="Export/import live podataka za Sacuvaj Hranu.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    export_parser = sub.add_parser("export", help="Izvezi trenutnu bazu u JSON.")
    export_parser.add_argument("--output", default=str(DEFAULT_EXPORT))

    validate_parser = sub.add_parser("validate", help="Validiraj export JSON.")
    validate_parser.add_argument("--input", default=str(DEFAULT_EXPORT))

    import_parser = sub.add_parser("import", help="Uvezi JSON u ciljnu bazu.")
    import_parser.add_argument("--input", default=str(DEFAULT_EXPORT))
    import_parser.add_argument("--database-url", help="Ciljni DATABASE_URL. Ako nije zadato, koristi env/.env.")
    import_parser.add_argument("--replace-existing", action="store_true", help="Obriši postojeće redove pre importa.")
    import_parser.add_argument("--dry-run", action="store_true", help="Samo proveri šta bi bilo uvezeno.")

    args = parser.parse_args()
    if getattr(args, "database_url", None):
        os.environ["DATABASE_URL"] = args.database_url

    if args.cmd == "export":
        payload = export_data(Path(args.output).resolve())
        print(json.dumps({"ok": True, "output": str(Path(args.output).resolve()), "counts": {k: len(v) for k, v in payload["tables"].items()}}, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "validate":
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        errors = validate_payload(payload)
        print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2))
        return 0 if not errors else 1
    if args.cmd == "import":
        result = import_data(Path(args.input).resolve(), replace_existing=args.replace_existing, dry_run=args.dry_run)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
