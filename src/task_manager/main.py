"""Command-line entry point for the Task Manager project."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from task_manager.config import AppSettings
from task_manager.database import create_tables
from task_manager.domain import Task
from task_manager.enums import Priority, TaskStatus
from task_manager.import_export import export_tasks_json, import_tasks_csv
from task_manager.performance import run_performance_experiment


def _demo() -> None:
    tasks = [
        Task(
            id=1,
            title="Prepare API documentation",
            description="Describe endpoints and examples",
            priority=Priority.HIGH,
            status=TaskStatus.IN_PROGRESS,
        ),
        Task(
            id=2,
            title="Fix login defect",
            description="Validate password reset flow",
            priority=Priority.CRITICAL,
            status=TaskStatus.TODO,
        ),
        Task(
            id=3,
            title="Write unit tests",
            description="Cover service and repository layers",
            priority=Priority.MEDIUM,
            status=TaskStatus.COMPLETED,
        ),
    ]
    completed = sum(task.is_completed for task in tasks)
    print("Task Manager — variant 14")
    print("=" * 32)
    for task in sorted(tasks, key=lambda item: (-item.priority.rank, item.title.casefold())):
        print(task.short_description())
    print(f"\nTotal: {len(tasks)} | Completed: {completed} | Incomplete: {len(tasks) - completed}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Task Manager — variant 14")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("demo", help="show a small in-memory task board")
    subparsers.add_parser("db-init", help="create local database tables")

    import_parser = subparsers.add_parser("import-csv", help="convert task CSV to JSON")
    import_parser.add_argument("source", type=Path)
    import_parser.add_argument("destination", type=Path)
    import_parser.add_argument("--strict", action="store_true", help="stop on the first invalid row")

    profile_parser = subparsers.add_parser("profile", help="profile 100k+ generated tasks")
    profile_parser.add_argument("--count", type=int, default=100_000)
    profile_parser.add_argument("--workers", type=int, default=4)
    profile_parser.add_argument("--cpu-sample-size", type=int, default=None)
    return parser


def main() -> None:
    settings = AppSettings.from_env()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = build_parser()
    args = parser.parse_args()
    if args.command in {None, "demo"}:
        _demo()
    elif args.command == "db-init":
        create_tables()
        print(f"Database initialized: {settings.database_url}")
    elif args.command == "import-csv":
        report = import_tasks_csv(args.source, strict=args.strict)
        export_tasks_json(report.tasks, args.destination)
        print(json.dumps(report.statistics(), ensure_ascii=False, indent=2))
        print(f"JSON written to {args.destination}")
    elif args.command == "profile":
        if args.count < 100_000:
            parser.error("--count must be at least 100000 for Lab 9")
        report = run_performance_experiment(
            count=args.count,
            workers=args.workers,
            cpu_sample_size=args.cpu_sample_size,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
