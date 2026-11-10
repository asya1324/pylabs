"""Enums shared by the domain, persistence and API layers."""

from __future__ import annotations

from enum import StrEnum


class Priority(StrEnum):
    """Task priority labels with a separate numeric rank for sorting/analysis."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def from_value(cls, value: str | int | "Priority") -> "Priority":
        """Parse a case-insensitive label or legacy numeric value."""
        if isinstance(value, cls):
            return value
        if isinstance(value, int):
            numeric = {1: cls.LOW, 2: cls.MEDIUM, 3: cls.HIGH, 4: cls.CRITICAL}
            try:
                return numeric[value]
            except KeyError as exc:
                raise ValueError(f"Unsupported priority: {value}") from exc
        try:
            return cls(value.strip().lower())
        except ValueError as exc:
            raise ValueError(f"Unsupported priority: {value}") from exc

    @property
    def label(self) -> str:
        """Return the canonical lower-case label."""
        return self.value

    @property
    def rank(self) -> int:
        """Return a numeric rank for ordering and aggregate calculations."""
        return {
            Priority.LOW: 1,
            Priority.MEDIUM: 2,
            Priority.HIGH: 3,
            Priority.CRITICAL: 4,
        }[self]


class TaskStatus(StrEnum):
    """Lifecycle states supported by the task board."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    @classmethod
    def from_value(cls, value: str | "TaskStatus") -> "TaskStatus":
        """Parse a status value without silently accepting unknown labels."""
        if isinstance(value, cls):
            return value
        try:
            return cls(value.strip().lower())
        except ValueError as exc:
            raise ValueError(f"Unsupported status: {value}") from exc
