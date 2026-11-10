from __future__ import annotations

from pathlib import Path

import pytest

from task_manager.config import load_task_validation_config
from task_manager.exceptions import ImportFormatError
from task_manager.import_export import export_tasks_json, import_tasks_csv, read_tasks_json
from task_manager.streaming import (
    TaskBatchIterator,
    batches,
    count_completed_incomplete,
    first_incomplete,
    find_task_lazy,
    group_tasks,
    iter_batches_with_yield_from,
    iter_valid_tasks,
    lazy_filter,
    short_task_views,
)
from task_manager.enums import Priority

DATA = Path(__file__).parents[1] / "data"


def test_tolerant_import_and_json_export(tmp_path: Path) -> None:
    report = import_tasks_csv(DATA / "tasks_with_errors.csv", strict=False)
    assert report.valid_count == 1
    assert report.invalid_count == 4
    assert report.statistics() == {"total_rows": 5, "valid_tasks": 1, "invalid_tasks": 4}
    output = export_tasks_json(report.tasks, tmp_path / "tasks.json")
    data = read_tasks_json(output)
    assert data[0]["title"] == "Valid task"
    assert data[0]["priority"] == "high"


def test_strict_import_stops_on_invalid_row() -> None:
    with pytest.raises(ImportFormatError):
        import_tasks_csv(DATA / "tasks_with_errors.csv", strict=True)


def test_configuration_and_streaming_pipeline() -> None:
    config = load_task_validation_config(DATA.parent / "config.yaml")
    tasks = list(iter_valid_tasks(DATA / "tasks.csv", strict=True, config=config))
    assert len(tasks) == 5
    assert len(list(lazy_filter(tasks, priority=Priority.HIGH))) == 2
    assert find_task_lazy(iter(tasks), "fix login") is not None
    assert count_completed_incomplete(tasks) == (1, 4)
    assert len(list(first_incomplete(tasks, 2))) == 2
    assert set(group_tasks(tasks, key="status")) == {"in_progress", "todo", "completed", "cancelled"}
    assert len(list(short_task_views(tasks))) == 5


def test_batch_generator_and_iterator_protocol() -> None:
    tasks = list(iter_valid_tasks(DATA / "tasks.csv", strict=True))
    assert [len(part) for part in batches(tasks, 2)] == [2, 2, 1]
    iterator = TaskBatchIterator(tasks, 3)
    assert iter(iterator) is iterator
    assert [len(part) for part in iterator] == [3, 2]
    assert [len(part) for part in iter_batches_with_yield_from(tasks, 4)] == [4, 1]


def test_json_export_is_atomic_on_serialization_failure(tmp_path: Path) -> None:
    target = tmp_path / "existing.json"
    target.write_text("original", encoding="utf-8")
    class BadTask:
        pass
    # A malformed input must fail before replace; original target remains intact.
    with pytest.raises((TypeError, AttributeError, ImportFormatError)):
        export_tasks_json([BadTask()], target)  # type: ignore[list-item]
    assert target.read_text(encoding="utf-8") == "original"
