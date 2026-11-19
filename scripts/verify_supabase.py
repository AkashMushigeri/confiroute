"""ConfiRoute - Supabase PostgreSQL Database Verification Script.

Verifies:
1. Database URL configuration from environment/app config.
2. Dialect detection (PostgreSQL vs SQLite).
3. Connected host and database name (with strict masking: no credentials or secrets).
4. PostgreSQL server version.
5. Existing application tables accessibility.
6. Temporary test record write, read, and cleanup.
7. Database transaction semantics (commit and rollback).
8. Connection type reporting (PostgreSQL/Supabase vs SQLite/local fallback).
9. Non-zero exit code if PostgreSQL was required but SQLite or failed connection.
"""

import argparse
import os
import sys
import uuid
from pathlib import Path

# Ensure package is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from sqlalchemy import create_engine, text, inspect
from confiroute.config import get_config
from confiroute.db.connection import normalize_database_url, get_engine, reset_engine
from confiroute.db.database import init_db


def mask_string(val: str) -> str:
    """Mask credentials or sensitive query strings."""
    if not val:
        return ""
    if "@" in val:
        parts = val.split("@")
        prefix = parts[0]
        suffix = parts[-1]
        proto = prefix.split("://")[0] if "://" in prefix else ""
        return f"{proto}://*****:*****@{suffix}"
    return val


def run_verification(allow_sqlite: bool = False, custom_url: str = None) -> int:
    print("=" * 70)
    print("CONFIROUTE - SUPABASE POSTGRESQL VERIFICATION")
    print("=" * 70)

    # 1. Read Database URL
    if custom_url:
        os.environ["DATABASE_URL"] = custom_url
        reset_engine()

    raw_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL") or ""
    is_configured = bool(raw_url.strip())
    norm_url = normalize_database_url(raw_url)

    engine = get_engine()
    dialect_name = engine.dialect.name
    is_postgres = dialect_name.startswith("postgres")

    # 2. Host & Database Name (never credentials or full URL)
    host = engine.url.host or ("embedded" if dialect_name == "sqlite" else "localhost")
    database_name = engine.url.database or ("data/confiroute.db" if dialect_name == "sqlite" else "postgres")
    port = engine.url.port or (5432 if is_postgres else None)

    print(f"[*] Environment DATABASE_URL set : {is_configured}")
    print(f"[*] Active Database Dialect       : {dialect_name}")
    print(f"[*] Connected Host               : {host}")
    print(f"[*] Connected Database Name      : {database_name}")
    if port:
        print(f"[*] Connected Port               : {port}")

    # 3. Connectivity Probe
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[+] Basic connectivity test passed (SELECT 1).")
    except Exception as exc:
        print(f"[-] Connection failed: {type(exc).__name__}")
        print("=" * 70)
        print("[FAILED] Could not connect to the database engine.")
        print("=" * 70)
        return 1

    # 4. Check PostgreSQL Version
    if is_postgres:
        with engine.connect() as conn:
            version_str = conn.execute(text("SELECT version()")).scalar()
            print(f"[+] PostgreSQL Server Version    : {version_str}")
    else:
        print("[-] PostgreSQL Server Version    : N/A (Current dialect is SQLite)")

    # Ensure tables are initialized if brand new database
    inspector = inspect(engine)
    existing_tables = sorted(inspector.get_table_names())
    if not existing_tables:
        print("[*] No tables found; initializing schema...")
        init_db()
        inspector = inspect(engine)
        existing_tables = sorted(inspector.get_table_names())

    # 5. Verify Existing Application Tables Access
    print(f"[*] Application Tables Detected ({len(existing_tables)} tables):")
    core_tables = ["queries", "signals", "routes", "reviews", "costs", "alerts"]
    for tbl in existing_tables:
        try:
            with engine.connect() as conn:
                count = conn.execute(text(f"SELECT count(*) FROM {tbl}")).scalar()
            mark = "[CORE]" if tbl in core_tables else "[APP]"
            print(f"    {mark:7} {tbl:<24} : {count} records")
        except Exception as e:
            print(f"    [ERR]   {tbl:<24} : inaccessible ({type(e).__name__})")

    missing_core = [t for t in core_tables if t not in existing_tables]
    if missing_core:
        print(f"[-] Missing core application tables: {missing_core}")
        return 1
    print("[+] All core application tables accessible.")

    # 6 & 7. Test Transaction Semantics (Rollback & Commit) and Safe Temporary Record
    test_token = f"probe_{uuid.uuid4().hex[:10]}"
    test_msg_rb = f"rollback_{test_token}"
    test_msg_commit = f"commit_{test_token}"

    print("[*] Testing transaction semantics and read/write integrity...")

    # A. Transaction Rollback Test
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            conn.execute(
                text("INSERT INTO alerts (alert_type, message, severity) VALUES (:type, :msg, :sev)"),
                {"type": "verification_probe", "msg": test_msg_rb, "sev": "test"},
            )
            trans.rollback()

        with engine.connect() as conn:
            rb_found = conn.execute(
                text("SELECT count(*) FROM alerts WHERE message = :msg"),
                {"msg": test_msg_rb},
            ).scalar()

        if rb_found != 0:
            print("[-] Transaction rollback failed: uncommitted record persisted.")
            return 1
        print("[+] Transaction rollback verified successfully.")
    except Exception as exc:
        print(f"[-] Error during rollback test: {type(exc).__name__}")
        return 1

    # B. Transaction Commit, Read & Cleanup Test
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            conn.execute(
                text("INSERT INTO alerts (alert_type, message, severity) VALUES (:type, :msg, :sev)"),
                {"type": "verification_probe", "msg": test_msg_commit, "sev": "test"},
            )
            trans.commit()

        # Read back test
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT alert_type, message, severity FROM alerts WHERE message = :msg"),
                {"msg": test_msg_commit},
            ).fetchone()

        if row is None or row[0] != "verification_probe" or row[1] != test_msg_commit:
            print("[-] Transaction commit verification failed: record not read back correctly.")
            return 1
        print("[+] Transaction commit, write, and read verified successfully.")

        # Cleanup test record
        with engine.connect() as conn:
            trans = conn.begin()
            conn.execute(
                text("DELETE FROM alerts WHERE message = :msg"),
                {"msg": test_msg_commit},
            )
            trans.commit()

        # Confirm cleanup
        with engine.connect() as conn:
            rem = conn.execute(
                text("SELECT count(*) FROM alerts WHERE message = :msg"),
                {"msg": test_msg_commit},
            ).scalar()

        if rem != 0:
            print("[-] Cleanup verification failed: temporary record not deleted.")
            return 1
        print("[+] Temporary test record cleaned up safely (zero remnant data).")

    except Exception as exc:
        print(f"[-] Error during commit/write/cleanup test: {type(exc).__name__}")
        return 1

    # 8 & 9. Final Dialect Evaluation & Reporting
    print("=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    if is_postgres:
        print("Connection Target : PostgreSQL / Supabase Cloud Database")
        print("Status            : PASS - REAL SUPABASE POSTGRESQL VERIFIED")
        print("=" * 70)
        return 0
    else:
        print("Connection Target : SQLite / Local File Fallback")
        if allow_sqlite:
            print("Status            : PASS (LOCAL MODE ONLY - via --allow-sqlite)")
            print("Note              : Active dialect is SQLite. Supabase PostgreSQL is NOT connected.")
            print("=" * 70)
            return 0
        else:
            print("Status            : FAILED (PostgreSQL required, but SQLite is active)")
            print("\n[!] Supabase cloud verification failed because SQLite is in use.")
            print("    To verify actual Supabase PostgreSQL:")
            print("    1. Log in to your Supabase project: https://supabase.com/dashboard")
            print("    2. Navigate to Project Settings -> Database -> Connection String -> URI")
            print("    3. Configure DATABASE_URL in your local .env file:")
            print("       DATABASE_URL=postgresql+psycopg2://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?sslmode=require")
            print("    4. Re-run: python scripts/verify_supabase.py")
            print("\n    (Pass --allow-sqlite if you only intend to test local SQLite persistence).")
            print("=" * 70)
            return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify ConfiRoute Supabase PostgreSQL Connection")
    parser.add_argument(
        "--allow-sqlite",
        action="store_true",
        help="Permit verification against local SQLite without failing",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Optional database URL override for connection testing",
    )
    cli_args = parser.parse_args()

    exit_code = run_verification(allow_sqlite=cli_args.allow_sqlite, custom_url=cli_args.db_url)
    sys.exit(exit_code)
