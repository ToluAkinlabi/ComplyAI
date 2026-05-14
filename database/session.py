import os
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from database.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./complyai.db")


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def _is_postgres(url: str) -> bool:
    return url.startswith("postgresql") or url.startswith("postgres")


def _strict_migrations_enabled() -> bool:
    return os.getenv("STRICT_MIGRATIONS", "false").lower() == "true"


pool_recycle_seconds = int(os.getenv("DB_POOL_RECYCLE_SECONDS", "1800"))
pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))

engine_kwargs = {
    "pool_pre_ping": True,
}

if _is_sqlite(DATABASE_URL):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
elif _is_postgres(DATABASE_URL):
    engine_kwargs["pool_recycle"] = pool_recycle_seconds
    engine_kwargs["pool_size"] = pool_size
    engine_kwargs["max_overflow"] = max_overflow
    if "sslmode=" not in DATABASE_URL:
        engine_kwargs["connect_args"] = {"sslmode": os.getenv("DB_SSLMODE", "require")}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_database() -> None:
    if _strict_migrations_enabled():
        return
    if os.getenv("AUTO_INIT_DB", "true").lower() != "true":
        return
    Base.metadata.create_all(bind=engine)


def verify_database_schema() -> None:
    """Validate required tables exist, useful for strict migration mode."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    required_tables = set(Base.metadata.tables.keys())
    missing = sorted(required_tables - existing_tables)
    if missing:
        raise RuntimeError(
            "Database schema is incomplete. Missing tables: "
            + ", ".join(missing)
            + ". Apply migrations before starting the API."
        )


def ensure_database_ready() -> None:
    """Initialize schema when allowed and always verify schema readiness."""
    init_database()
    verify_database_schema()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
