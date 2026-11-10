from __future__ import annotations

from task_manager.analytics import priority_numeric_statistics
from task_manager.enums import Priority
from task_manager.performance import analyze_tasks_sequential, generate_synthetic_tasks


def test_synthetic_dataset_and_analytics() -> None:
    tasks = generate_synthetic_tasks(250, seed=7)
    assert len(tasks) == 250
    assert tasks[0].id == 1
    report = analyze_tasks_sequential(tasks)
    assert report["sorted_count"] == 250
    assert report["completed_count"] + report["incomplete_count"] == 250
    assert priority_numeric_statistics(tasks)["maximum"] == float(Priority.CRITICAL.rank)


def test_empty_numeric_statistics() -> None:
    assert priority_numeric_statistics([]) == {"mean": 0.0, "maximum": 0.0}


def test_thread_load_and_process_pool_comparison() -> None:
    from pathlib import Path

    from task_manager.performance import compare_cpu_strategies, load_task_files_parallel

    data_file = Path(__file__).parents[1] / "data" / "tasks.csv"
    loaded = load_task_files_parallel([data_file, data_file], workers=2)
    assert len(loaded) == 10
    comparison = compare_cpu_strategies(generate_synthetic_tasks(12), workers=2)
    assert comparison["sample_size"] == 12
    assert comparison["process_seconds"] > 0


def test_profile_collects_timeit_cprofile_and_memory(tmp_path, monkeypatch) -> None:
    from task_manager.performance import profile_dataset

    monkeypatch.chdir(tmp_path)
    report = profile_dataset(generate_synthetic_tasks(20))
    assert report["peak_memory_bytes"] > 0
    assert report["timeit_status_count_seconds"] >= 0
    assert (tmp_path / "output" / "task_manager.prof").exists()


def test_dashboard_cache_accelerates_repeated_reads() -> None:
    from task_manager.performance import compare_dashboard_cache

    result = compare_dashboard_cache(generate_synthetic_tasks(2_000))
    assert result["cache_speedup"] > 1.0
