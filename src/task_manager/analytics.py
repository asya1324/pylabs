"""Functional analytics for task collections (Lab 2 and Lab 9)."""

from __future__ import annotations

import logging
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Iterator, Sequence
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from task_manager.domain import Task
from task_manager.enums import Priority, TaskStatus

logger = logging.getLogger(__name__)
P = ParamSpec("P")
R = TypeVar("R")

# Immutable tuple is suitable for stable sort keys / fixed metadata.
PRIORITY_ORDER: tuple[Priority, ...] = (
    Priority.CRITICAL,
    Priority.HIGH,
    Priority.MEDIUM,
    Priority.LOW,
)


def log_execution(function: Callable[P, R]) -> Callable[P, R]:
    """Decorator that records elapsed time while preserving the wrapped function."""

    @wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        started = time.perf_counter()
        try:
            return function(*args, **kwargs)
        finally:
            logger.debug("%s completed in %.6fs", function.__name__, time.perf_counter() - started)

    return wrapper


def unique_statuses(tasks: Iterable[Task]) -> set[str]:
    """Return unique task statuses (set comprehension)."""
    return {task.status.value for task in tasks}


def count_by_status(tasks: Iterable[Task]) -> dict[str, int]:
    """Count tasks by status using Counter."""
    return dict(Counter(task.status.value for task in tasks))


def count_by_priority(tasks: Iterable[Task]) -> dict[str, int]:
    """Count tasks by priority using Counter."""
    return dict(Counter(task.priority.label for task in tasks))


def incomplete_tasks(tasks: Iterable[Task]) -> list[Task]:
    """Return all tasks not in the completed state."""
    return [task for task in tasks if task.status is not TaskStatus.COMPLETED]


def group_by_status(tasks: Iterable[Task]) -> dict[str, list[Task]]:
    """Group tasks by status using defaultdict."""
    grouped: defaultdict[str, list[Task]] = defaultdict(list)
    for task in tasks:
        grouped[task.status.value].append(task)
    return dict(grouped)


def group_by_priority(tasks: Iterable[Task]) -> dict[str, list[Task]]:
    """Group tasks by priority."""
    grouped: defaultdict[str, list[Task]] = defaultdict(list)
    for task in tasks:
        grouped[task.priority.label].append(task)
    return dict(grouped)


@log_execution
def sort_by_priority(tasks: Iterable[Task]) -> list[Task]:
    """Sort tasks by descending priority, then by title."""
    return sorted(tasks, key=lambda task: (-task.priority.rank, task.title.casefold()))


def search_task(tasks: Iterable[Task], query: str) -> list[Task]:
    """Case-insensitive search in task title and description."""
    normalized = query.strip().casefold()
    if not normalized:
        return []
    return [
        task
        for task in tasks
        if normalized in task.title.casefold() or normalized in task.description.casefold()
    ]


def index_by_id(tasks: Iterable[Task]) -> dict[int, Task]:
    """Build a dictionary index by ID; average lookup is O(1)."""
    return {task.id: task for task in tasks if task.id is not None}


def index_by_title(tasks: Iterable[Task]) -> dict[str, list[Task]]:
    """Build a dictionary index by normalized title."""
    index: defaultdict[str, list[Task]] = defaultdict(list)
    for task in tasks:
        index[task.title.casefold()].append(task)
    return dict(index)


def filter_by_statuses(tasks: Iterable[Task], *statuses: TaskStatus) -> list[Task]:
    """Example of a variadic positional argument (*args)."""
    selected = set(statuses)
    return [task for task in tasks if task.status in selected]


def filter_tasks(tasks: Iterable[Task], **criteria: object) -> list[Task]:
    """Filter by optional status, priority, assignee and overdue flag (**kwargs)."""
    status_value = criteria.get("status")
    priority_value = criteria.get("priority")
    assignee_value = criteria.get("assigned_to")
    overdue_value = criteria.get("overdue")
    result = list(tasks)
    if status_value is not None:
        status = TaskStatus.from_value(str(status_value))
        result = [task for task in result if task.status is status]
    if priority_value is not None:
        priority = Priority.from_value(str(priority_value))
        result = [task for task in result if task.priority is priority]
    if assignee_value is not None:
        result = [task for task in result if task.assigned_to == int(str(assignee_value))]
    if overdue_value is not None:
        expected = str(overdue_value).lower() in {"true", "1", "yes"}
        result = [task for task in result if task.is_overdue is expected]
    return result


def make_task_predicate(**criteria: object) -> Callable[[Task], bool]:
    """Create a closure that remembers criteria for repeated filtering."""
    status = TaskStatus.from_value(str(criteria["status"])) if criteria.get("status") else None
    priority = Priority.from_value(str(criteria["priority"])) if criteria.get("priority") else None
    assigned_to = int(str(criteria["assigned_to"])) if criteria.get("assigned_to") is not None else None

    def predicate(task: Task) -> bool:
        return (
            (status is None or task.status is status)
            and (priority is None or task.priority is priority)
            and (assigned_to is None or task.assigned_to == assigned_to)
        )

    return predicate


def apply_predicate(tasks: Iterable[Task], predicate: Callable[[Task], bool]) -> Iterator[Task]:
    """Lazy pipeline stage returning an iterator."""
    return filter(predicate, tasks)


def dashboard_statistics(tasks: Sequence[Task]) -> dict[str, Any]:
    """Build a compact dashboard summary from a materialized task sequence."""
    completed = sum(task.is_completed for task in tasks)
    return {
        "total": len(tasks),
        "completed": completed,
        "incomplete": len(tasks) - completed,
        "by_status": count_by_status(tasks),
        "by_priority": count_by_priority(tasks),
    }


def priority_numeric_statistics(tasks: Sequence[Task]) -> dict[str, float]:
    """Use NumPy for numeric aggregation over encoded priorities."""
    try:
        import numpy as np
    except ImportError:
        values = [float(task.priority.rank) for task in tasks]
        if not values:
            return {"mean": 0.0, "maximum": 0.0}
        return {"mean": sum(values) / len(values), "maximum": max(values)}

    values = np.fromiter((task.priority.rank for task in tasks), dtype=np.float64)
    if values.size == 0:
        return {"mean": 0.0, "maximum": 0.0}
    return {"mean": float(values.mean()), "maximum": float(values.max())}
