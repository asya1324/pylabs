from __future__ import annotations

from datetime import date, timedelta

from task_manager.analytics import (
    apply_predicate,
    count_by_priority,
    count_by_status,
    dashboard_statistics,
    filter_by_statuses,
    filter_tasks,
    group_by_priority,
    group_by_status,
    index_by_id,
    index_by_title,
    incomplete_tasks,
    make_task_predicate,
    priority_numeric_statistics,
    search_task,
    sort_by_priority,
    unique_statuses,
)
from task_manager.domain import Task
from task_manager.enums import Priority, TaskStatus


def sample_tasks() -> list[Task]:
    return [
        Task(id=1, title="Write API", description="Endpoints", priority=Priority.HIGH),
        Task(id=2, title="Fix bug", description="Login", priority=Priority.CRITICAL, status=TaskStatus.COMPLETED),
        Task(id=3, title="Write tests", description="Unit tests", priority=Priority.MEDIUM, status=TaskStatus.IN_PROGRESS, assigned_to=7),
        Task(id=4, title="Late report", description="Past due", priority=Priority.LOW, deadline=date.today() - timedelta(days=1)),
    ]


def test_status_priority_analytics() -> None:
    tasks = sample_tasks()
    assert unique_statuses(tasks) == {"todo", "completed", "in_progress"}
    assert count_by_status(tasks) == {
        "todo": 2, "completed": 1, "in_progress": 1
    }
    assert count_by_priority(tasks) == {
        "high": 1, "critical": 1, "medium": 1, "low": 1
    }
    assert len(incomplete_tasks(tasks)) == 3
    assert set(group_by_status(tasks)) == {"todo", "completed", "in_progress"}
    assert set(group_by_priority(tasks)) == {"high", "critical", "medium", "low"}


def test_search_index_sort_and_argument_patterns() -> None:
    tasks = sample_tasks()
    assert search_task(tasks, "api")[0].id == 1
    assert index_by_id(tasks)[2].title == "Fix bug"
    assert len(index_by_title(tasks)["write tests"]) == 1
    assert sort_by_priority(tasks)[0].priority is Priority.CRITICAL
    assert len(filter_by_statuses(tasks, TaskStatus.TODO, TaskStatus.IN_PROGRESS)) == 3
    assert len(filter_tasks(tasks, priority="high", status="todo")) == 1
    assert len(filter_tasks(tasks, assigned_to=7)) == 1


def test_closure_lazy_predicate_and_dashboard() -> None:
    tasks = sample_tasks()
    predicate = make_task_predicate(status="todo", priority="high")
    result = list(apply_predicate(tasks, predicate))
    assert [task.id for task in result] == [1]
    stats = dashboard_statistics(tasks)
    assert stats["total"] == 4
    assert stats["completed"] == 1
    assert priority_numeric_statistics(tasks)["maximum"] == 4.0


def test_numeric_aggregate_approximation_and_dunder_sorting() -> None:
    import pytest

    tasks = sample_tasks()
    values = priority_numeric_statistics(tasks)
    assert values["mean"] == pytest.approx(2.5)
    assert str(tasks[0]).startswith("#1 [high]")
    assert sorted(tasks)[0].priority is Priority.CRITICAL
