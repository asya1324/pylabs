from __future__ import annotations

import pytest

from task_manager.domain import BugTask, FeatureTask, Task, TaskBoard, User
from task_manager.enums import Priority, TaskStatus
from task_manager.exceptions import TaskValidationError


def test_task_creation_and_short_description() -> None:
    task = Task(id=1, title="  Write tests ", description=" unit tests ", priority="high")
    assert task.title == "Write tests"
    assert task.description == "unit tests"
    assert task.priority is Priority.HIGH
    assert task.status is TaskStatus.TODO
    assert task.short_description() == "#1 [high] Write tests (todo)"


def test_bug_and_feature_task_specializations() -> None:
    bug = BugTask(title="Bug", description="Crash", priority=Priority.CRITICAL, severity="critical")
    feature = FeatureTask(
        title="Feature",
        description="New workflow",
        priority=Priority.MEDIUM,
        acceptance_criteria=[" Works ", "", "Has tests"],
    )
    assert bug.severity == "critical"
    assert feature.acceptance_criteria == ["Works", "Has tests"]
    with pytest.raises(TaskValidationError):
        BugTask(title="Bad", description="", priority=Priority.LOW, severity="catastrophic")


def test_task_validation_and_user_validation() -> None:
    with pytest.raises(TaskValidationError):
        Task(title=" ", description="", priority=Priority.LOW)
    with pytest.raises(TaskValidationError):
        Task(title="x", description="", priority="urgent")
    with pytest.raises(TaskValidationError):
        User(name="No Email", email="not-an-email")


def test_task_board_add_find_filter_and_counts() -> None:
    board = TaskBoard()
    board.add(Task(id=1, title="A", description="", priority=Priority.HIGH, status=TaskStatus.COMPLETED))
    board.add(Task(id=2, title="B", description="", priority=Priority.LOW))
    assert board.find(1) is not None
    assert board.find(99) is None
    assert len(board.filter(priority=Priority.HIGH)) == 1
    assert board.completed_counts() == (1, 1)
    with pytest.raises(TaskValidationError):
        board.add(Task(id=1, title="duplicate", description="", priority=Priority.LOW))


def test_empty_board_counts() -> None:
    assert TaskBoard().completed_counts() == (0, 0)


@pytest.mark.parametrize(
    ("source", "expected"),
    [("low", Priority.LOW), ("MEDIUM", Priority.MEDIUM), (3, Priority.HIGH), ("critical", Priority.CRITICAL)],
)
def test_priority_parser(source: str | int, expected: Priority) -> None:
    assert Priority.from_value(source) is expected
