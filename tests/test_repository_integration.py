from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from task_manager.dbapi import bulk_update_statuses_dbapi, connect_sqlite, filter_tasks_dbapi
from task_manager.domain import Task, User
from task_manager.enums import Priority, TaskStatus
from task_manager.exceptions import TaskNotFoundError
from task_manager.repositories import SQLAlchemyTaskRepository, SQLAlchemyUserRepository


def test_sqlalchemy_crud_relationship_filters_and_aggregates(db_session) -> None:
    users = SQLAlchemyUserRepository(db_session)
    tasks = SQLAlchemyTaskRepository(db_session)
    user = users.create(User("Ada Lovelace", "ada@example.com"))
    created = tasks.create(Task(title="Write API", description="REST", priority=Priority.HIGH, assigned_to=user.id))
    assert created.id is not None
    assert tasks.get(created.id).title == "Write API"
    assert tasks.list_tasks(priority="high")[0].id == created.id
    assert tasks.list_tasks(user_id=user.id)[0].id == created.id
    updated = tasks.update(Task(
        id=created.id,
        title="Write REST API",
        description="REST endpoints",
        priority=Priority.CRITICAL,
        status=TaskStatus.IN_PROGRESS,
        assigned_to=user.id,
    ))
    assert updated.priority is Priority.CRITICAL
    assert tasks.status_counts()["in_progress"] == 1
    assert tasks.delete(created.id) is True
    assert tasks.get(created.id) is None
    assert tasks.delete(created.id) is False


def test_overdue_filter_and_bulk_transaction_rollback(db_session) -> None:
    repo = SQLAlchemyTaskRepository(db_session)
    old_task = repo.create(Task(
        title="Past due", description="", priority=Priority.HIGH,
        deadline=date.today() - timedelta(days=1),
    ))
    assert [task.id for task in repo.overdue()] == [old_task.id]
    with pytest.raises(TaskNotFoundError):
        repo.bulk_update_statuses([
            (old_task.id or 0, TaskStatus.COMPLETED),
            (9999, TaskStatus.CANCELLED),
        ])
    persisted = repo.get(old_task.id or 0)
    assert persisted is not None
    assert persisted.status is TaskStatus.TODO


def test_parameterized_dbapi_filters_and_rollback(tmp_path: Path, db_session, test_engine) -> None:
    # The ORM engine and DB-API connection share this temporary file in a separate fixture below.
    database_path = tmp_path / "dbapi.sqlite"
    connection = connect_sqlite(database_path)
    connection.execute(
        "CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT, priority TEXT, "
        "status TEXT, assigned_to INTEGER, deadline TEXT)"
    )
    connection.execute(
        "INSERT INTO tasks (id, title, priority, status) VALUES (?, ?, ?, ?)",
        (1, "Parameterized title", "high", "todo"),
    )
    connection.commit()
    rows = filter_tasks_dbapi(connection, status="todo", priority="high")
    assert rows[0]["title"] == "Parameterized title"
    assert bulk_update_statuses_dbapi(connection, [(1, TaskStatus.COMPLETED)]) == 1
    with pytest.raises(TaskNotFoundError):
        bulk_update_statuses_dbapi(connection, [(1, TaskStatus.TODO), (999, TaskStatus.TODO)])
    current = connection.execute("SELECT status FROM tasks WHERE id = ?", (1,)).fetchone()
    assert current["status"] == "completed"
    connection.close()
