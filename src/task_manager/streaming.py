"""Lazy CSV readers and generator pipelines for large task datasets (Lab 3)."""

from __future__ import annotations

import csv
import itertools
import logging
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from task_manager.config import TaskValidationConfig, load_task_validation_config
from task_manager.domain import Task
from task_manager.enums import Priority, TaskStatus
from task_manager.exceptions import ImportFormatError, TaskValidationError

logger = logging.getLogger(__name__)
REQUIRED_COLUMNS = ("task_id", "title", "description", "priority", "status")


def read_task_rows(path: Path | str) -> Iterator[dict[str, str]]:
    """Yield CSV records one by one without reading the whole file into memory."""
    source = Path(path)
    try:
        with source.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames is None:
                raise ImportFormatError("CSV file has no header")
            missing = set(REQUIRED_COLUMNS) - set(reader.fieldnames)
            if missing:
                raise ImportFormatError(f"Missing CSV columns: {', '.join(sorted(missing))}")
            for row in reader:
                yield {str(key): str(value or "") for key, value in row.items() if key is not None}
    except OSError as exc:
        raise ImportFormatError(f"Cannot read CSV file: {source}") from exc


def task_from_row(
    row: dict[str, str],
    config: TaskValidationConfig | None = None,
) -> Task:
    """Convert and validate one CSV row into a domain Task."""
    settings = config or load_task_validation_config()
    try:
        task_id = int(row["task_id"])
        title = row["title"].strip()
        description = row.get("description", "").strip()
        priority = row["priority"].strip().lower()
        status = row["status"].strip().lower()
        if task_id < 1:
            raise ValueError("task_id must be positive")
        if not title:
            raise ValueError("title must not be empty")
        if priority not in settings.allowed_priorities:
            raise ValueError(f"priority must be one of {sorted(settings.allowed_priorities)}")
        if status not in settings.allowed_statuses:
            raise ValueError(f"status must be one of {sorted(settings.allowed_statuses)}")
        assigned_raw = row.get("assigned_to", "").strip()
        deadline_raw = row.get("deadline", "").strip()
        from datetime import date

        deadline = date.fromisoformat(deadline_raw) if deadline_raw else None
        return Task(
            id=task_id,
            title=title,
            description=description,
            priority=Priority.from_value(priority),
            status=TaskStatus.from_value(status),
            assigned_to=int(assigned_raw) if assigned_raw else None,
            deadline=deadline,
        )
    except (KeyError, TypeError, ValueError, TaskValidationError) as exc:
        raise ImportFormatError(f"Invalid task row {row!r}: {exc}") from exc


def iter_valid_tasks(
    path: Path | str,
    *,
    strict: bool = False,
    config: TaskValidationConfig | None = None,
) -> Iterator[Task]:
    """Stream valid tasks; tolerant mode logs and skips malformed rows."""
    for line_number, row in enumerate(read_task_rows(path), start=2):
        try:
            yield task_from_row(row, config)
        except ImportFormatError:
            if strict:
                raise
            logger.warning("Skipping invalid task at CSV line %d", line_number, exc_info=True)


def lazy_filter(
    tasks: Iterable[Task],
    *,
    status: TaskStatus | None = None,
    priority: Priority | None = None,
) -> Iterator[Task]:
    """Lazy filtering stage by task status and/or priority."""
    return (
        task
        for task in tasks
        if (status is None or task.status is status)
        and (priority is None or task.priority is priority)
    )


def find_task_lazy(tasks: Iterable[Task], query: str) -> Task | None:
    """Return first task whose ID or title matches; consumes only as far as needed."""
    normalized = query.strip().casefold()
    if not normalized:
        return None
    return next(
        (
            task
            for task in tasks
            if str(task.id) == normalized or normalized in task.title.casefold()
        ),
        None,
    )


def count_completed_incomplete(tasks: Iterable[Task]) -> tuple[int, int]:
    """Count completed and incomplete tasks in one pass."""
    completed = 0
    incomplete = 0
    for task in tasks:
        if task.status is TaskStatus.COMPLETED:
            completed += 1
        else:
            incomplete += 1
    return completed, incomplete


def group_tasks(tasks: Iterable[Task], key: str = "status") -> dict[str, list[Task]]:
    """Group tasks with itertools.groupby after sorting by the same key."""
    if key not in {"status", "priority"}:
        raise ValueError("key must be 'status' or 'priority'")
    key_function = (lambda task: task.status.value) if key == "status" else (lambda task: task.priority.label)
    ordered = sorted(tasks, key=key_function)
    return {
        group_key: list(group)
        for group_key, group in itertools.groupby(ordered, key=key_function)
    }


def first_incomplete(tasks: Iterable[Task], limit: int) -> Iterator[Task]:
    """Return at most N incomplete tasks without materializing the source."""
    if limit < 0:
        raise ValueError("limit must not be negative")
    return itertools.islice(
        (task for task in tasks if task.status is not TaskStatus.COMPLETED),
        limit,
    )


def batches(items: Iterable[Any], size: int) -> Iterator[list[Any]]:
    """Yield fixed-size batches (last batch may be smaller)."""
    if size < 1:
        raise ValueError("batch size must be positive")
    iterator = iter(items)
    while batch := list(itertools.islice(iterator, size)):
        yield batch


def short_task_views(tasks: Iterable[Task]) -> Iterator[dict[str, object]]:
    """Lazy transformation to compact task dictionaries."""
    return (
        {
            "id": task.id,
            "title": task.title,
            "priority": task.priority.label,
            "status": task.status.value,
        }
        for task in tasks
    )


class TaskBatchIterator:
    """Iterator object that yields batches from a reusable task sequence."""

    def __init__(self, tasks: Iterable[Task], size: int) -> None:
        if size < 1:
            raise ValueError("batch size must be positive")
        self._iterator = iter(tasks)
        self._size = size

    def __iter__(self) -> "TaskBatchIterator":
        return self

    def __next__(self) -> list[Task]:
        batch = list(itertools.islice(self._iterator, self._size))
        if not batch:
            raise StopIteration
        return batch


def iter_batches_with_yield_from(tasks: Iterable[Task], size: int) -> Iterator[list[Task]]:
    """Generator using yield from to delegate batch production."""
    yield from batches(tasks, size)
