"""Database engine, connection pooling, and session management for ConfiRoute.

Supports both Supabase PostgreSQL (via DATABASE_URL) and local SQLite with seamless fallback.
"""

from contextlib import contextmanager
import os
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Tuple

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from confiroute.config import get_config
from confiroute.db.models import Base, User, Profile

load_dotenv()

_engine: Optional[Engine] = None
_SessionFactory: Optional[sessionmaker] = None


def reset_engine() -> None:
    """Dispose and reset cached engine and session factory."""
    global _engine, _SessionFactory
    if _engine is not None:
        try:
            _engine.dispose()
        except Exception:
            pass
    _engine = None
    _SessionFactory = None


def is_postgres() -> bool:
    """Return True if active database engine dialect is PostgreSQL."""
    try:
        engine = get_engine()
        return engine.dialect.name.startswith("postgres")
    except Exception:
        return False


def normalize_database_url(url: Optional[str]) -> str:
    """Normalize and format database connection URL for SQLAlchemy with automatic SSL handling."""
    if not url or not url.strip():
        config = get_config()
        db_path = config.database_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # SQLite URL
        return f"sqlite:///{db_path.resolve().as_posix()}"

    cleaned = url.strip()
    # Handle Heroku / Supabase postgres:// -> postgresql+psycopg2://
    if cleaned.startswith("postgres://"):
        cleaned = cleaned.replace("postgres://", "postgresql+psycopg2://", 1)
    elif cleaned.startswith("postgresql://") and not cleaned.startswith("postgresql+"):
        cleaned = cleaned.replace("postgresql://", "postgresql+psycopg2://", 1)

    # For remote PostgreSQL / Supabase instances, ensure sslmode is specified
    if "postgresql" in cleaned and "sslmode=" not in cleaned:
        if "localhost" not in cleaned and "127.0.0.1" not in cleaned:
            separator = "&" if "?" in cleaned else "?"
            cleaned = f"{cleaned}{separator}sslmode=require"

    return cleaned


def get_engine(custom_url: Optional[str] = None) -> Engine:
    """Return or initialize SQLAlchemy Engine with connection pooling."""
    global _engine, _SessionFactory
    raw_url = custom_url or os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    db_url = normalize_database_url(raw_url)

    if _engine is None or custom_url is not None:
        if db_url.startswith("sqlite"):
            engine = create_engine(
                db_url,
                connect_args={"check_same_thread": False},
                pool_pre_ping=True,
            )
        else:
            # PostgreSQL / Supabase with production connection pool
            engine = create_engine(
                db_url,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_pre_ping=True,
                pool_recycle=1800,
            )
        if custom_url is None:
            _engine = engine
            _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            return _engine
        return engine

    return _engine


def get_session_factory() -> sessionmaker:
    """Return configured SQLAlchemy session factory."""
    global _SessionFactory
    if _SessionFactory is None:
        get_engine()
    return _SessionFactory


def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency yielding an isolated database session with auto-rollback."""
    factory = get_session_factory()
    db: Session = factory()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for standalone scripts or non-FastAPI tasks."""
    factory = get_session_factory()
    db: Session = factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def migrate_existing_tables(engine: Engine) -> None:
    """Gracefully alter existing tables to ensure newly introduced columns exist without data loss."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    is_sqlite = engine.dialect.name == "sqlite"

    with engine.begin() as conn:
        # Check users table
        if "users" in existing_tables:
            user_cols = {c["name"] for c in inspector.get_columns("users")}
            if "is_active" not in user_cols:
                bool_type = "INTEGER DEFAULT 1" if is_sqlite else "BOOLEAN DEFAULT TRUE"
                conn.execute(text(f"ALTER TABLE users ADD COLUMN is_active {bool_type}"))
            if "updated_at" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT NULL"))

        # Check conversations table
        if "conversations" in existing_tables:
            conv_cols = {c["name"] for c in inspector.get_columns("conversations")}
            if "status" not in conv_cols:
                conn.execute(text("ALTER TABLE conversations ADD COLUMN status VARCHAR(32) DEFAULT 'active'"))

        # Check conversation_messages table
        if "conversation_messages" in existing_tables:
            msg_cols = {c["name"] for c in inspector.get_columns("conversation_messages")}
            if "user_id" not in msg_cols:
                conn.execute(text("ALTER TABLE conversation_messages ADD COLUMN user_id VARCHAR(64)"))


def seed_admin_and_default_users(db: Session) -> None:
    """Ensure default clinical auditor and administrator accounts exist with secure PBKDF2 hashes."""
    from confiroute.db.database import hash_password

    # 1. Clinician / Reviewer Account
    clinician_email = "clinician@confiroute.ai"
    clinician = db.query(User).filter(User.email == clinician_email).first()
    if not clinician:
        pwd_hash, salt = hash_password("Clinical2026!")
        clinician = User(
            id="usr_clinician_01",
            email=clinician_email,
            name="Dr. Sarah Chen, MD",
            password_hash=pwd_hash,
            salt=salt,
            role="reviewer",
            department="Emergency Medicine & Critical Care",
            is_active=True,
        )
        db.add(clinician)
        db.flush()
        db.add(Profile(user_id=clinician.id, full_name=clinician.name))
    elif not clinician.profile:
        db.add(Profile(user_id=clinician.id, full_name=clinician.name))

    # 2. Administrator Account
    admin_email = "admin@confiroute.ai"
    admin = db.query(User).filter(User.email == admin_email).first()
    if not admin:
        pwd_hash, salt = hash_password("AdminSecure2026!")
        admin = User(
            id="usr_admin_01",
            email=admin_email,
            name="System Administrator",
            password_hash=pwd_hash,
            salt=salt,
            role="admin",
            department="Clinical AI Governance",
            is_active=True,
        )
        db.add(admin)
        db.flush()
        db.add(Profile(user_id=admin.id, full_name=admin.name))
    elif not admin.profile:
        db.add(Profile(user_id=admin.id, full_name=admin.name))

    # 3. Auditor Account
    auditor_email = "auditor@confiroute.ai"
    auditor = db.query(User).filter(User.email == auditor_email).first()
    if not auditor:
        pwd_hash, salt = hash_password("Auditor2026!")
        auditor = User(
            id="usr_auditor_01",
            email=auditor_email,
            name="Dr. James Wilson",
            password_hash=pwd_hash,
            salt=salt,
            role="reviewer",
            department="Internal Medicine Quality Assurance",
            is_active=True,
        )
        db.add(auditor)
        db.flush()
        db.add(Profile(user_id=auditor.id, full_name=auditor.name))
    elif not auditor.profile:
        db.add(Profile(user_id=auditor.id, full_name=auditor.name))

    db.commit()


def init_cloud_and_local_db(custom_url: Optional[str] = None) -> None:
    """Create all schema tables on target engine (SQLite or PostgreSQL), run migrations and seed accounts."""
    engine = get_engine(custom_url)
    # 1. Run migrations for any existing columns
    migrate_existing_tables(engine)
    # 2. Create any newly added tables
    Base.metadata.create_all(bind=engine)
    # 3. Seed users
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    with factory() as db:
        seed_admin_and_default_users(db)


def test_cloud_connection(custom_url: Optional[str] = None) -> Dict[str, Any]:
    """Inspect and verify connectivity, dialect, and table schema for the configured database."""
    engine = get_engine(custom_url)
    dialect_name = engine.dialect.name

    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1")).scalar()

    inspector = inspect(engine)
    tables = sorted(inspector.get_table_names())

    required_tables = [
        "users",
        "profiles",
        "user_sessions",
        "conversations",
        "conversation_messages",
        "routing_logs",
        "human_reviews",
        "audit_logs",
    ]
    missing_tables = [t for t in required_tables if t not in tables]

    return {
        "connected": res == 1,
        "dialect": dialect_name,
        "is_postgresql": dialect_name.startswith("postgres"),
        "tables_found": tables,
        "required_tables_present": len(missing_tables) == 0,
        "missing_tables": missing_tables,
    }
