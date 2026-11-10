from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import Mock

import pytest

from task_manager.enums import Priority, TaskStatus
from task_manager.exceptions import InvalidStatusTransitionError
from task_manager.services import DashboardCache, TaskService


def test_service_workflow_notifier_and_policy(task_service: TaskService) -> None:
    notifier = Mock()
    service = TaskService(task_service.task_repository, task_service.user_repository, notifier=notifier)
    user = service.create_user("Ada", "ada@example.com")
    task = service.create_task("Prepare release", "Release notes", Priority.HIGH, assigned_to=user.id)
    assert task.id is not None
    updated = service.change_status(task.id, TaskStatus.IN_PROGRESS)
    assert updated.status is TaskStatus.IN_PROGRESS
    updated = service.update_task(task.id, priority="critical", assigned_to=None)
    assert updated.priority is Priority.CRITICAL
    service.delete_task(task.id)
    notifier.notify.assert_called()


def test_invalid_transition_and_overdue(task_service: TaskService) -> None:
    user = task_service.create_user("Lin", "lin@example.com")
    task = task_service.create_task("Cancelled", priority=Priority.LOW, assigned_to=user.id)
    task_service.change_status(task.id or 0, TaskStatus.CANCELLED)
    with pytest.raises(InvalidStatusTransitionError):
        task_service.change_status(task.id or 0, TaskStatus.TODO)
    overdue = task_service.create_task(
        "Old task", priority=Priority.HIGH, deadline=date.today() - timedelta(days=1)
    )
    assert [item.id for item in task_service.overdue_tasks()] == [overdue.id]


def test_dashboard_cache_invalidates_after_mutation(task_service: TaskService) -> None:
    first = task_service.dashboard_statistics()
    assert first["total"] == 0
    task_service.create_task("New task")
    second = task_service.dashboard_statistics()
    assert second["total"] == 1
    assert second is not first


def test_dashboard_cache_reuses_same_revision() -> None:
    cache = DashboardCache()
    calls = 0
    def load() -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"total": calls}
    assert cache.get(1, load) == {"total": 1}
    assert cache.get(1, load) == {"total": 1}
    assert calls == 1
    cache.invalidate()
    assert cache.get(2, load) == {"total": 2}


def test_mock_side_effect_and_magic_mock_notifier() -> None:
    from unittest.mock import MagicMock

    from task_manager.domain import Task
    from task_manager.protocols import Notifier, TaskRepository, UserRepository
    from task_manager.enums import Priority

    task_repository = Mock(spec=TaskRepository)
    user_repository = Mock(spec=UserRepository)
    notifier = Mock(spec=Notifier)
    task_repository.create.side_effect = lambda task: Task(
        id=42,
        title=task.title,
        description=task.description,
        priority=task.priority,
        status=task.status,
    )
    notifier.notify.side_effect = RuntimeError("notification gateway unavailable")
    service = TaskService(task_repository, user_repository, notifier=notifier)
    with pytest.raises(RuntimeError):
        service.create_task("Persist first", priority=Priority.HIGH)
    task_repository.create.assert_called_once()
    notifier.notify.assert_called_once()

    magic_notifier = MagicMock(spec=Notifier)
    magic_notifier.notify("hello")
    magic_notifier.notify.assert_called_once_with("hello")
