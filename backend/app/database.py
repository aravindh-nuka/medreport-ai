"""SQLAlchemy engine/session setup. Defaults to SQLite (zero-config, file-based,
fine for local dev) but works with Postgres too if DATABASE_URL is set to one —
e.g. a free Neon or Supabase instance, for deployments where data needs to
survive restarts (free hosting tiers use ephemeral disks that wipe SQLite on
every redeploy/restart/wake-from-sleep)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import get_settings

settings = get_settings()

# Neon, Supabase, Heroku, and most managed Postgres providers hand out
# connection strings starting with "postgres://", but SQLAlchemy 1.4+ only
# accepts "postgresql://" and raises an error on the old scheme. Normalizing
# here means DATABASE_URL can be pasted directly from any of those dashboards
# without editing it first.
database_url = settings.DATABASE_URL
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if "sqlite" in database_url else {}
engine = create_engine(database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Called once on app startup."""
    from app import models  # noqa: F401 ensures models are registered
    Base.metadata.create_all(bind=engine)
