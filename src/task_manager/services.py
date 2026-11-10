"""Application services and domain policies."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from task_manager.domain import Task, User
from task_manager.enums import Priority, TaskStatus
from task_manager.exceptions import (
    InvalidStatusTransitionError,
    TaskNotFoundError,
    UserNotFoundError,
)
from task_manager.protocols import AsyncTaskSource, Notifier, TaskPolicy, TaskRepository, UserRepository

logger = logging.getLogger(__name__)


class DefaultTaskPolicy(TaskPolicy):
    """Explicit status transition policy; cancelled tasks are terminal."""

    _TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
        TaskStatus.TODO: frozenset(
            {TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED, TaskStatus.CANCELLED}
        ),
        TaskStatus.IN_PROGRESS: frozenset(
            {TaskStatus.TODO, TaskStatus.COMPLETED, TaskStatus.CANCELLED}
        ),
        TaskStatus.COMPLETED: frozenset({TaskStatus.IN_PROGRESS}),
        TaskStatus.CANCELLED: frozenset(),
    }

    def can_transition(self, current: TaskStatus, target: TaskStatus) -> bool:
        return current is target or target in self._TRANSITIONS[current]


class LoggingNotifier:
    """Default notification adapter; logs notifications without external services."""

    def notify(self, message: str) -> None:
        logger.info("Task notification: %s", message)


@dataclass(slots=True)
class DashboardCache:
    """Single-entry dashboard cache with explicit mutation invalidation."""

    _revision: int = -1
    _value: dict[str, Any] | None = None

    def get(self, revision: int, loader: Any) -> dict[str, Any]:
        if self._value is None or self._revision != revision:
            self._value = loader()
            self._revision = revision
        return dict(self._value)

    def invalidate(self) -> None:
        self._revision = -1
        self._value = None


class TaskService:
    """Coordinates domain policies, repositories, notifications and analytics."""

    def __init__(
        self,
        task_repository: TaskRepository,
        user_repository: UserRepository,
        notifier: Notifier | None = None,
        policy: TaskPolicy | None = None,
    ) -> None:
        self.task_repository = task_repository
        self.user_repository = user_repository
        self.notifier = notifier or LoggingNotifier()
        self.policy = policy or DefaultTaskPolicy()
        self._revision = 0
        self._dashboard_cache = DashboardCache()

    def _changed(self) -> None:
        self._revision += 1
        self._dashboard_cache.invalidate()

    def create_user(self, name: str, email: str) -> User:
        return self.user_repository.create(User(name=name, email=email))

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: Priority = Priority.MEDIUM,
        status: TaskStatus = TaskStatus.TODO,
        assigned_to: int | None = None,
        deadline: Any = None,
    ) -> Task:
        if assigned_to is not None and self.user_repository.get(assigned_to) is None:
            raise UserNotFoundError(f"User {assigned_to} was not found")
        task = Task(
            title=title,
            description=description,
            priority=priority,
            status=status,
            assigned_to=assigned_to,
            deadline=deadline,
        )
        created = self.task_repository.create(task)
        self._changed()
        self.notifier.notify(f"Created task #{created.id}: {created.title}")
        return created

    def get_task(self, task_id: int) -> Task:
        task = self.task_repository.get(task_id)
        if task is None:
            raise TaskNotFoundError(f"Task {task_id} was not found")
        return task

    def list_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        priority: Priority | None = None,
        user_id: int | None = None,
        search: str | None = None,
    ) -> list[Task]:
        return self.task_repository.list_tasks(
            status=status,
            priority=priority.value if priority is not None else None,
            user_id=user_id,
            search=search,
        )

    def change_status(self, task_id: int, target: TaskStatus) -> Task:
        task = self.get_task(task_id)
        if not self.policy.can_transition(task.status, target):
            raise InvalidStatusTransitionError(
                f"Cannot move task {task_id} from {task.status.value} to {target.value}"
            )
        task.status = target
        updated = self.task_repository.update(task)
        self._changed()
        self.notifier.notify(f"Task #{task_id} status changed to {target.value}")
        return updated

    def update_task(self, task_id: int, **changes: Any) -> Task:
        task = self.get_task(task_id)
        if "status" in changes and changes["status"] is not None:
            target = TaskStatus.from_value(changes.pop("status"))
            if not self.policy.can_transition(task.status, target):
                raise InvalidStatusTransitionError(
                    f"Cannot move task {task_id} from {task.status.value} to {target.value}"
                )
            task.status = target
        if "priority" in changes and changes["priority"] is not None:
            task.priority = Priority.from_value(changes.pop("priority"))
        if "assigned_to" in changes:
            assignee_id = changes.pop("assigned_to")
            if assignee_id is not None and self.user_repository.get(assignee_id) is None:
                raise UserNotFoundError(f"User {assignee_id} was not found")
            task.assigned_to = assignee_id
        if "deadline" in changes:
            task.deadline = changes.pop("deadline")
        if "title" in changes and changes["title"] is not None:
            task.title = str(changes.pop("title"))
        if "description" in changes and changes["description"] is not None:
            task.description = str(changes.pop("description"))
        if changes:
            unexpected = ", ".join(sorted(changes))
            raise ValueError(f"Unsupported task fields: {unexpected}")
        # Re-run domain validation after mutable attribute changes.
        task.__post_init__()
        updated = self.task_repository.update(task)
        self._changed()
        self.notifier.notify(f"Updated task #{task_id}")
        return updated

    def delete_task(self, task_id: int) -> None:
        if not self.task_repository.delete(task_id):
            raise TaskNotFoundError(f"Task {task_id} was not found")
        self._changed()
        self.notifier.notify(f"Deleted task #{task_id}")

    def overdue_tasks(self) -> list[Task]:
        overdue_method = getattr(self.task_repository, "overdue", None)
        if callable(overdue_method):
            return overdue_method()
        from datetime import date

        return [
            task
            for task in self.task_repository.list_tasks()
            if task.deadline is not None
            and task.deadline < date.today()
            and task.status not in {TaskStatus.COMPLETED, TaskStatus.CANCELLED}
        ]

    def dashboard_statistics(self) -> dict[str, Any]:
        def load() -> dict[str, Any]:
            tasks = self.task_repository.list_tasks()
            completed = sum(task.is_completed for task in tasks)
            return {
                "total": len(tasks),
                "completed": completed,
                "incomplete": len(tasks) - completed,
                "overdue": len(self.overdue_tasks()),
                "by_status": {
                    status.value: sum(task.status is status for task in tasks)
                    for status in TaskStatus
                },
                "by_priority": {
                    priority.label: sum(task.priority is priority for task in tasks)
                    for priority in Priority
                },
            }

        return self._dashboard_cache.get(self._revision, load)


class AsyncTaskWorkflowService:
    """Application service around an asynchronous multi-user task source."""

    def __init__(self, source: AsyncTaskSource) -> None:
        self.source = source

    async def collect_for_users(self, user_ids: list[int]) -> dict[int, list[dict[str, object]]]:
        return await self.source.fetch_for_users(user_ids)
