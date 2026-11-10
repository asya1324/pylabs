"""Profiling and optimization experiments for 100k+ tasks (Lab 9)."""

from __future__ import annotations

import cProfile
import json
import math
import multiprocessing
import random
import statistics
import time
import timeit
import tracemalloc
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from task_manager.analytics import priority_numeric_statistics, sort_by_priority
from task_manager.domain import Task
from task_manager.enums import Priority, TaskStatus
from task_manager.streaming import iter_valid_tasks
from task_manager.services import DashboardCache


def generate_synthetic_tasks(count: int = 100_000, seed: int = 42) -> list[Task]:
    """Generate a reproducible in-memory dataset for profiling."""
    if count < 0:
        raise ValueError("count must not be negative")
    rng = random.Random(seed)
    titles = ("Prepare report", "Review pull request", "Fix defect", "Plan release", "Write tests")
    descriptions = ("Backend", "API", "Database", "Documentation", "Quality checks")
    priorities = tuple(Priority)
    statuses = tuple(TaskStatus)
    today = date.today()
    return [
        Task(
            id=index + 1,
            title=f"{rng.choice(titles)} {index + 1}",
            description=rng.choice(descriptions),
            priority=rng.choice(priorities),
            status=rng.choice(statuses),
            assigned_to=rng.randint(1, 50),
            deadline=today + timedelta(days=rng.randint(-15, 30)),
        )
        for index in range(count)
    ]


def analyze_tasks_sequential(tasks: list[Task]) -> dict[str, Any]:
    """Baseline analytics over the whole data set."""
    started = time.perf_counter()
    critical = [task for task in tasks if task.priority is Priority.CRITICAL]
    ordered = sort_by_priority(tasks)
    completed = sum(task.status is TaskStatus.COMPLETED for task in tasks)
    overdue = sum(task.is_overdue for task in tasks)
    elapsed = time.perf_counter() - started
    return {
        "critical_count": len(critical),
        "sorted_count": len(ordered),
        "completed_count": completed,
        "incomplete_count": len(tasks) - completed,
        "overdue_count": overdue,
        "elapsed_seconds": elapsed,
    }


def _cpu_task_score(payload: tuple[int, int]) -> float:
    """Artificial but deterministic CPU-bound analytics kernel for comparison."""
    priority, task_id = payload
    value = float(priority + task_id % 13)
    for _ in range(35):
        value = math.sin(value) ** 2 + math.cos(value) ** 2 + math.sqrt(abs(value) + 1.0)
    return value


def compare_cpu_strategies(
    tasks: list[Task], *, workers: int = 4, sample_size: int | None = None
) -> dict[str, float | int]:
    """Compare sequential, threads and processes on a CPU-bound task score."""
    sample = tasks if sample_size is None else tasks[:sample_size]
    payloads = [(task.priority.rank, task.id or index) for index, task in enumerate(sample)]

    started = time.perf_counter()
    sequential = [_cpu_task_score(item) for item in payloads]
    sequential_seconds = time.perf_counter() - started

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        threaded = list(executor.map(_cpu_task_score, payloads))
    thread_seconds = time.perf_counter() - started

    started = time.perf_counter()
    with ProcessPoolExecutor(
        max_workers=workers, mp_context=multiprocessing.get_context("spawn")
    ) as executor:
        processed = list(executor.map(_cpu_task_score, payloads, chunksize=250))
    process_seconds = time.perf_counter() - started

    if sequential != threaded or sequential != processed:
        raise RuntimeError("Parallel CPU implementations returned inconsistent results")
    return {
        "sample_size": len(payloads),
        "sequential_seconds": sequential_seconds,
        "thread_seconds": thread_seconds,
        "process_seconds": process_seconds,
        "thread_speedup": sequential_seconds / thread_seconds if thread_seconds else 0.0,
        "process_speedup": sequential_seconds / process_seconds if process_seconds else 0.0,
    }


def load_task_files_parallel(paths: list[Path | str], *, workers: int = 4) -> list[Task]:
    """Load several CSV sources concurrently (I/O-bound; ThreadPoolExecutor)."""
    def load_one(path: Path | str) -> list[Task]:
        return list(iter_valid_tasks(path, strict=False))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        batches = list(executor.map(load_one, paths))
    return [task for batch in batches for task in batch]


def profile_dataset(tasks: list[Task]) -> dict[str, Any]:
    """Collect runtime, cProfile top functions and peak memory for baseline analytics."""
    profiler = cProfile.Profile()
    tracemalloc.start()
    profiler.enable()
    report = analyze_tasks_sequential(tasks)
    profiler.disable()
    current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    profile_path = Path("output") / "task_manager.prof"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profiler.dump_stats(str(profile_path))
    report["current_memory_bytes"] = current_bytes
    report["peak_memory_bytes"] = peak_bytes
    report["profile_file"] = str(profile_path)
    report["priority_numeric"] = priority_numeric_statistics(tasks)
    report["mean_priority"] = statistics.fmean(task.priority.rank for task in tasks) if tasks else 0.0
    report["timeit_status_count_seconds"] = timeit.timeit(
        lambda: sum(task.status is TaskStatus.COMPLETED for task in tasks), number=3
    ) / 3
    return report



def compare_dashboard_cache(tasks: list[Task]) -> dict[str, float]:
    """Measure repeated dashboard calculations with and without revision caching."""
    from task_manager.analytics import dashboard_statistics

    cache = DashboardCache()
    loader = lambda: dashboard_statistics(tasks)
    cache.get(1, loader)  # warm the cache before measuring repeated reads
    uncached_seconds = timeit.timeit(lambda: dashboard_statistics(tasks), number=5) / 5
    cached_seconds = timeit.timeit(lambda: cache.get(1, loader), number=500) / 500
    return {
        "uncached_seconds_per_call": uncached_seconds,
        "cached_seconds_per_call": cached_seconds,
        "cache_speedup": uncached_seconds / cached_seconds if cached_seconds else 0.0,
    }

def run_performance_experiment(
    count: int = 100_000,
    *,
    workers: int = 4,
    cpu_sample_size: int | None = None,
) -> dict[str, Any]:
    """Run a reproducible 100k+ task profile and optimized CPU comparison."""
    tasks = generate_synthetic_tasks(count)
    baseline = profile_dataset(tasks)
    cpu_comparison = compare_cpu_strategies(
        tasks,
        workers=workers,
        sample_size=cpu_sample_size,
    )
    result: dict[str, Any] = {
        "dataset_size": count,
        "baseline": baseline,
        "cpu_comparison": cpu_comparison,
        "cache_comparison": compare_dashboard_cache(tasks),
    }
    output = Path("output") / "performance_report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
