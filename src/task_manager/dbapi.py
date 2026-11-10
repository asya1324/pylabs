"""Small sqlite3 DB-API examples used by Lab 7 (parameterized SQL + transactions)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path

from task_manager.enums import TaskStatus
from task_manager.exceptions import TaskNotFoundError


def connect_sqlite(database_path: Path | str) -> sqlite3.Connection:
    """Open a SQLite DB-API connection with foreign keys enabled."""
    connection = sqlite3.connect(str(database_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def filter_tasks_dbapi(
    connection: sqlite3.Connection,
    *,
    status: str | None = None,
    priority: str | None = None,
    user_id: int | None = None,
) -> list[dict[str, object]]:
    """Fetch tasks with safely parameterized status/priority/user filters."""
    conditions: list[str] = []
    parameters: list[object] = []
    if status is not None:
        conditions.append("status = ?")
        parameters.append(status)
    if priority is not None:
        conditions.append("priority = ?")
        parameters.append(priority)
    if user_id is not None:
        conditions.append("assigned_to = ?")
        parameters.append(user_id)
    query = "SELECT id, title, priority, status, assigned_to, deadline FROM tasks"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id"
    # Values are always passed separately; no string interpolation of user input.
    return [dict(row) for row in connection.execute(query, parameters).fetchall()]


def bulk_update_statuses_dbapi(
    connection: sqlite3.Connection,
    changes: Iterable[tuple[int, TaskStatus]],
) -> int:
    """Update statuses in one transaction and rollback all changes on failure."""
    updated = 0
    try:
        for task_id, status in changes:
            cursor = connection.execute(
                "UPDATE tasks SET status = ? WHERE id = ?",
                (status.value, task_id),
            )
            if cursor.rowcount != 1:
                raise TaskNotFoundError(f"Task {task_id} was not found")
            updated += 1
        connection.commit()
        return updated
    except Exception:
        connection.rollback()
        raise
