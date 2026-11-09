"""CLI script to initialize ConfiRoute SQLite database."""

import sys
from pathlib import Path

# Ensure package is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from confiroute.config import get_config
from confiroute.db.database import init_db, get_connection


def main():
    config = get_config()
    db_path = config.database_path
    print(f"[INIT] Initializing ConfiRoute database at: {db_path}...")
    init_db()

    conn = get_connection()
    try:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        ).fetchall()
        table_names = [t["name"] for t in tables]
        print(f"[SUCCESS] Database initialized successfully with {len(table_names)} tables:")
        for name in table_names:
            count = conn.execute(f"SELECT count(*) as c FROM {name}").fetchone()["c"]
            print(f"  - {name}: {count} records")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
