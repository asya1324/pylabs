from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from task_manager.database import create_tables
from task_manager.repositories import SQLAlchemyTaskRepository, SQLAlchemyUserRepository
from task_manager.services import TaskService


@pytest.fixture()
def test_engine() -> Generator[Engine, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    create_tables(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    factory = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def task_service(db_session: Session) -> TaskService:
    return TaskService(SQLAlchemyTaskRepository(db_session), SQLAlchemyUserRepository(db_session))
