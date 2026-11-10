"""Abstractions used to keep domain services independent of infrastructure."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Protocol, TypeVar

from task_manager.domain import Task, User
from task_manager.enums import TaskStatus

EntityT = TypeVar("EntityT")
RepositoryT = TypeVar("RepositoryT", covariant=True)


class Repository(Protocol[RepositoryT]):
    """Generic structural repository contract."""

    def get(self, entity_id: int) -> RepositoryT | None: ...


class TaskRepository(Protocol):
    """Persistence contract required by TaskService."""

    def create(self, task: Task) -> Task: ...

    def get(self, task_id: int) -> Task | None: ...

    def list_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        priority: str | None = None,
        user_id: int | None = None,
        search: str | None = None,
    ) -> list[Task]: ...

    def update(self, task: Task) -> Task: ...

    def delete(self, task_id: int) -> bool: ...


class UserRepository(Protocol):
    """Persistence contract for users."""

    def create(self, user: User) -> User: ...

    def get(self, user_id: int) -> User | None: ...

    def list_users(self) -> list[User]: ...


class Notifier(Protocol):
    """Notification abstraction, replaceable with email/Slack/etc."""

    def notify(self, message: str) -> None: ...


class TaskPolicy(ABC):
    """Abstract policy for validating task status transitions."""

    @abstractmethod
    def can_transition(self, current: TaskStatus, target: TaskStatus) -> bool:
        """Return whether the target status is allowed."""


class AsyncTaskSource(Protocol):
    """Asynchronous source for loading tasks for multiple users."""

    async def fetch_for_users(self, user_ids: Sequence[int]) -> dict[int, list[dict[str, object]]]: ...
