"""Typed domain objects and the aggregate root for task management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from types import NotImplementedType
from typing import Iterator, TypedDict

from task_manager.enums import Priority, TaskStatus
from task_manager.exceptions import TaskValidationError


class TaskPayload(TypedDict, total=False):
    """Serialized task fields accepted by import and service functions."""

    id: int
    title: str
    description: str
    priority: str
    status: str
    assigned_to: int | None
    deadline: str | None


@dataclass(slots=True)
class Task:
    """A task with validated state and optional assignee/deadline."""

    title: str
    description: str
    priority: Priority
    status: TaskStatus = TaskStatus.TODO
    id: int | None = None
    assigned_to: int | None = None
    deadline: date | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        self.description = self.description.strip()
        try:
            self.priority = Priority.from_value(self.priority)
            self.status = TaskStatus.from_value(self.status)
        except ValueError as exc:
            raise TaskValidationError(str(exc)) from exc
        if not self.title:
            raise TaskValidationError("Task title must not be empty")
        if len(self.title) > 200:
            raise TaskValidationError("Task title must be at most 200 characters")
        if len(self.description) > 5000:
            raise TaskValidationError("Task description must be at most 5000 characters")
        if self.id is not None and self.id < 1:
            raise TaskValidationError("Task ID must be a positive integer")
        if self.assigned_to is not None and self.assigned_to < 1:
            raise TaskValidationError("Assignee ID must be a positive integer")

    @property
    def is_completed(self) -> bool:
        """Whether the task is completed."""
        return self.status is TaskStatus.COMPLETED

    @property
    def is_overdue(self) -> bool:
        """Whether an unfinished task has a deadline before today."""
        return (
            self.deadline is not None
            and self.deadline < date.today()
            and not self.is_completed
            and self.status is not TaskStatus.CANCELLED
        )

    def short_description(self) -> str:
        """Return a compact one-line representation."""
        return f"#{self.id or '-'} [{self.priority.label}] {self.title} ({self.status.value})"

    def __str__(self) -> str:
        """Return the human-readable task representation."""
        return self.short_description()

    def __lt__(self, other: object) -> bool | NotImplementedType:
        """Compare tasks by descending priority and then case-insensitive title."""
        if not isinstance(other, Task):
            return NotImplemented
        return (-self.priority.rank, self.title.casefold()) < (
            -other.priority.rank, other.title.casefold()
        )


@dataclass(slots=True)
class BugTask(Task):
    """Specialized task for bug fixes."""

    severity: str = "major"

    def __post_init__(self) -> None:
        super(BugTask, self).__post_init__()
        self.severity = self.severity.strip().lower()
        if self.severity not in {"minor", "major", "critical"}:
            raise TaskValidationError("Bug severity must be minor, major or critical")


@dataclass(slots=True)
class FeatureTask(Task):
    """Specialized task for feature work."""

    acceptance_criteria: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super(FeatureTask, self).__post_init__()
        self.acceptance_criteria = [item.strip() for item in self.acceptance_criteria if item.strip()]


@dataclass(slots=True)
class User:
    """A person who can be assigned tasks."""

    name: str
    email: str
    id: int | None = None

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.email = self.email.strip().lower()
        if not self.name:
            raise TaskValidationError("User name must not be empty")
        if "@" not in self.email or self.email.startswith("@"):
            raise TaskValidationError("A valid email address is required")


@dataclass(slots=True)
class TaskBoard:
    """In-memory aggregate used for domain-level task operations."""

    tasks: list[Task] = field(default_factory=list)

    def add(self, task: Task) -> None:
        """Add a task while preventing duplicate persistent IDs."""
        if task.id is not None and any(existing.id == task.id for existing in self.tasks):
            raise TaskValidationError(f"Task ID {task.id} already exists")
        self.tasks.append(task)

    def find(self, task_id: int) -> Task | None:
        """Find one task by ID; linear time O(n)."""
        return next((task for task in self.tasks if task.id == task_id), None)

    def filter(
        self,
        *,
        status: TaskStatus | None = None,
        priority: Priority | None = None,
    ) -> list[Task]:
        """Return tasks matching selected attributes."""
        return [
            task
            for task in self.tasks
            if (status is None or task.status is status)
            and (priority is None or task.priority is priority)
        ]

    def completed_counts(self) -> tuple[int, int]:
        """Return (completed, incomplete) task counts."""
        completed = sum(task.is_completed for task in self.tasks)
        return completed, len(self.tasks) - completed

    def __len__(self) -> int:
        return len(self.tasks)

    def __iter__(self) -> Iterator[Task]:
        return iter(self.tasks)

    def __contains__(self, task: object) -> bool:
        return task in self.tasks
