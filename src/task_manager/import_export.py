"""Robust task CSV import, validation reports and atomic JSON export (Lab 5)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from task_manager.config import TaskValidationConfig, load_task_validation_config
from task_manager.domain import Task
from task_manager.exceptions import ImportFormatError
from task_manager.resources import AtomicTextWriter
from task_manager.streaming import read_task_rows, task_from_row

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ImportIssue:
    """Description of one invalid source record."""

    row_number: int
    message: str


@dataclass(slots=True)
class ImportReport:
    """Outcome of strict or tolerant CSV import."""

    tasks: list[Task]
    issues: list[ImportIssue]

    @property
    def total_rows(self) -> int:
        return len(self.tasks) + len(self.issues)

    @property
    def valid_count(self) -> int:
        return len(self.tasks)

    @property
    def invalid_count(self) -> int:
        return len(self.issues)

    def statistics(self) -> dict[str, int]:
        return {
            "total_rows": self.total_rows,
            "valid_tasks": self.valid_count,
            "invalid_tasks": self.invalid_count,
        }


def import_tasks_csv(
    source: Path | str,
    *,
    strict: bool = False,
    config: TaskValidationConfig | None = None,
) -> ImportReport:
    """Import valid tasks; strict mode raises at first invalid row."""
    settings = config or load_task_validation_config()
    tasks: list[Task] = []
    issues: list[ImportIssue] = []
    for row_number, row in enumerate(read_task_rows(source), start=2):
        try:
            tasks.append(task_from_row(row, settings))
        except ImportFormatError as exc:
            logger.warning("Invalid task in %s at line %d: %s", source, row_number, exc)
            if strict:
                raise ImportFormatError(f"Line {row_number}: {exc}") from exc
            issues.append(ImportIssue(row_number=row_number, message=str(exc)))
    return ImportReport(tasks=tasks, issues=issues)


def _task_to_dict(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority.label,
        "status": task.status.value,
        "assigned_to": task.assigned_to,
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "created_at": task.created_at.isoformat(),
        "overdue": task.is_overdue,
    }


def export_tasks_json(tasks: list[Task], destination: Path | str) -> Path:
    """Write JSON atomically: failed serialization never leaves partial output."""
    output_path = Path(destination)
    try:
        with AtomicTextWriter(output_path) as stream:
            json.dump(
                [_task_to_dict(task) for task in tasks],
                stream,
                ensure_ascii=False,
                indent=2,
            )
        return output_path
    except (OSError, TypeError, ValueError) as exc:
        logger.exception("Atomic JSON export failed for %s", output_path)
        raise ImportFormatError(f"Could not export tasks to {output_path}") from exc


def read_tasks_json(source: Path | str) -> list[dict[str, Any]]:
    """Read JSON task export and validate its top-level structure."""
    try:
        data = json.loads(Path(source).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ImportFormatError(f"Could not read JSON file: {source}") from exc
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ImportFormatError("Task JSON must be a list of objects")
    return data
