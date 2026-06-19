from __future__ import annotations

import argparse
import json
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Priprema i provera produkcione baze za Sacuvaj Hranu.")
    parser.add_argument("--database-url", help="DATABASE_URL za proveru. Ako nije zadato, koristi env/.env.")
    parser.add_argument("--create", action="store_true", help="Kreira sve tabele koje nedostaju.")
    parser.add_argument("--seed-pilot", action="store_true", help="Upisuje pilot partnere i ponude posle kreiranja tabela.")
    parser.add_argument("--require-postgres", action="store_true", help="Padni ako DATABASE_URL nije PostgreSQL.")
    parser.add_argument("--require-production-db", action="store_true", help="Padni ako DATABASE_URL nije PostgreSQL ili MySQL/MariaDB.")
    args = parser.parse_args()

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    from sqlalchemy import inspect, text

    from app.database import Base, SessionLocal, engine
    from app import finance_models, models  # noqa: F401 - registruje sve tabele

    db_url = str(engine.url)
    is_postgres = db_url.startswith("postgres")
    is_mysql = db_url.startswith("mysql") or db_url.startswith("mariadb")
    if args.require_postgres and not is_postgres:
        print("DATABASE PREP FAILED: DATABASE_URL nije PostgreSQL.", file=sys.stderr)
        print(db_url, file=sys.stderr)
        return 1
    if args.require_production_db and not (is_postgres or is_mysql):
        print("DATABASE PREP FAILED: DATABASE_URL nije PostgreSQL/MySQL/MariaDB.", file=sys.stderr)
        print(db_url, file=sys.stderr)
        return 1

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        print(f"DATABASE PREP FAILED: ne mogu da se povezem sa bazom: {exc}", file=sys.stderr)
        return 1

    if args.create:
        Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    expected_tables = set(Base.metadata.tables.keys())
    missing_tables = sorted(expected_tables - existing_tables)

    table_status = []
    missing_columns_total = []
    for table_name, table in sorted(Base.metadata.tables.items()):
        if table_name not in existing_tables:
            table_status.append({"table": table_name, "ok": False, "missing": "table"})
            continue
        existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
        expected_columns = {col.name for col in table.columns}
        missing_columns = sorted(expected_columns - existing_columns)
        for column in missing_columns:
            missing_columns_total.append(f"{table_name}.{column}")
        table_status.append({
            "table": table_name,
            "ok": not missing_columns,
            "columns": len(existing_columns),
            "missing_columns": missing_columns,
        })

    seed_result = None
    if args.seed_pilot:
        if missing_tables or missing_columns_total:
            print("DATABASE PREP FAILED: ne seedujem dok sema nije kompletna.", file=sys.stderr)
            return 1
        from app.pilot_live_routes import ensure_pilot_data

        db = SessionLocal()
        try:
            seed_result = ensure_pilot_data(db)
        finally:
            db.close()

    result = {
        "ok": not missing_tables and not missing_columns_total,
        "database": "postgresql" if is_postgres else ("mysql/mariadb" if is_mysql else "sqlite/local"),
        "url_driver": engine.url.drivername,
        "created_missing_tables": bool(args.create),
        "expected_tables": sorted(expected_tables),
        "missing_tables": missing_tables,
        "missing_columns": missing_columns_total,
        "tables": table_status,
        "seed_pilot": seed_result,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        print("DATABASE PREP FAILED: sema nije kompletna.")
        return 1
    print("DATABASE PREP PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
