from __future__ import annotations

import json
import sys

from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateIndex, CreateTable
from sqlalchemy import String

from app.database import Base
from app import finance_models, models  # noqa: F401 - registers tables


def main() -> int:
    dialect = mysql.dialect()
    ddl_errors: list[dict] = []
    warnings: list[dict] = []
    compiled_tables: list[str] = []

    for table in Base.metadata.sorted_tables:
        try:
            str(CreateTable(table).compile(dialect=dialect))
            compiled_tables.append(table.name)
        except Exception as exc:
            ddl_errors.append({"table": table.name, "error": str(exc)})
        for column in table.columns:
            if (column.index or column.unique) and isinstance(column.type, String):
                length = column.type.length or 0
                if length > 500:
                    warnings.append({
                        "table": table.name,
                        "column": column.name,
                        "length": length,
                        "issue": "Indeksirani String je predugačak za sigurnu MySQL/MariaDB kompatibilnost.",
                    })
        for index in table.indexes:
            try:
                str(CreateIndex(index).compile(dialect=dialect))
            except Exception as exc:
                ddl_errors.append({"index": index.name, "table": table.name, "error": str(exc)})

    result = {
        "ok": not ddl_errors and not warnings,
        "compiled_tables": compiled_tables,
        "ddl_errors": ddl_errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        print("MYSQL SCHEMA PREFLIGHT FAILED")
        return 1
    print("MYSQL SCHEMA PREFLIGHT PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
