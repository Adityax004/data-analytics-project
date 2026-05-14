from __future__ import annotations

import sqlite3

import pandas as pd

from config import DATABASE_PATH, PROCESSED_DIR, SQL_DIR, ensure_directories


TABLE_LOAD_ORDER = ["customers", "products", "orders", "order_items", "returns"]


def build_database() -> None:
    ensure_directories()
    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()

    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        schema_sql = (SQL_DIR / "sqlite_schema.sql").read_text(encoding="utf-8")
        views_sql = (SQL_DIR / "sqlite_views.sql").read_text(encoding="utf-8")
        conn.executescript(schema_sql)

        for table in TABLE_LOAD_ORDER:
            df = pd.read_csv(PROCESSED_DIR / f"{table}.csv")
            df.to_sql(table, conn, if_exists="append", index=False)

        conn.executescript(views_sql)
        conn.commit()
    finally:
        conn.close()


def main() -> None:
    build_database()
    print(f"SQLite database created: {DATABASE_PATH}")


if __name__ == "__main__":
    main()

