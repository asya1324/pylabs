"""SQLAlchemy engine, declarative base and session dependency."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from task_manager.config import AppSettings


class Base(DeclarativeBase):
    """Declarative base for SQLAlchemy records."""


def _prepare_sqlite_directory(database_url: str) -> None:
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite" and url.database not in {None, ":memory:"}:
        database_path = Path(url.database)
        if not database_path.is_absolute():
            database_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            database_path.parent.mkdir(parents=True, exist_ok=True)


def build_engine(database_url: str) -> Engine:
    """Create an engine with SQLite's thread check disabled for FastAPI."""
    _prepare_sqlite_directory(database_url)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, future=True, pool_pre_ping=True)


settings = AppSettings.from_env()
engine = build_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def create_tables(target_engine: Engine = engine) -> None:
    """Create tables for a fresh local/demo database; use Alembic for upgrades."""
    # Import registers mapped classes on Base.metadata.
    from task_manager import db_models  # noqa: F401

    Base.metadata.create_all(bind=target_engine)


def get_session() -> Generator[Session, None, None]:
    """Yield a request-scoped database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
