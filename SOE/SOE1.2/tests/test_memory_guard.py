import multiprocessing
import os
from pathlib import Path

import pytest

from soe1.application.memory import (
    GIB,
    MemoryGuardPolicy,
    MemorySnapshot,
    MemoryTelemetryWriter,
    SystemMemoryMonitor,
)
from soe1.application.scheduler import MemoryAwareBatchScheduler


def _fail_once_then_succeed(task):
    marker = Path(task["marker_path"])
    if not marker.exists():
        marker.write_text("failed once", encoding="utf-8")
        os._exit(7)
    return {
        "ok": True,
        "mode": task["mode"],
        "dataset_slug": task["metadata"]["dataset_slug"],
        "metrics": {"dataset_slug": task["metadata"]["dataset_slug"]},
    }


def test_proc_meminfo_parser_converts_kib_to_bytes():
    values = SystemMemoryMonitor._parse_proc_meminfo_text(
        "\n".join(
            [
                "MemTotal:       32343960 kB",
                "MemAvailable:   18269800 kB",
                "SwapFree:         260200 kB",
            ]
        )
    )

    assert values["MemTotal"] == 32343960 * 1024
    assert values["MemAvailable"] == 18269800 * 1024
    assert values["SwapFree"] == 260200 * 1024


def test_memory_policy_treats_five_workers_as_an_upper_bound():
    policy = MemoryGuardPolicy(
        minimum_available_gib=5.0,
        estimated_worker_peak_gib=4.0,
    )

    assert policy.safe_worker_capacity(25 * GIB, 5) == 5
    assert policy.safe_worker_capacity(17 * GIB, 5) == 3
    assert policy.safe_worker_capacity(8 * GIB, 5) == 0


def test_memory_policy_rejects_invalid_threshold():
    with pytest.raises(ValueError):
        MemoryGuardPolicy(
            minimum_available_gib=0.0,
        ).validate()


def test_scheduler_accounts_for_unmaterialized_worker_peak(tmp_path):
    policy = MemoryGuardPolicy(
        minimum_available_gib=5.0,
        estimated_worker_peak_gib=4.0,
    )
    scheduler = MemoryAwareBatchScheduler(
        worker_function=lambda task: task,
        maximum_workers=5,
        memory_policy=policy,
        telemetry_path=tmp_path / "memory.csv",
    )

    assert scheduler._has_launch_headroom(
        available_bytes=19 * GIB,
        active_rss_bytes=6 * GIB,
        active_count=2,
    )
    assert scheduler._has_launch_headroom(
        available_bytes=9 * GIB,
        active_rss_bytes=4 * GIB,
        active_count=1,
    )
    assert not scheduler._has_launch_headroom(
        available_bytes=int(8.9 * GIB),
        active_rss_bytes=4 * GIB,
        active_count=1,
    )


def test_memory_telemetry_writer_appends_a_readable_csv(tmp_path):
    path = Path(tmp_path) / "memory_telemetry.csv"
    snapshot = MemorySnapshot(
        total_bytes=30 * GIB,
        available_bytes=18 * GIB,
        swap_free_bytes=1 * GIB,
        timestamp_utc="2026-07-31T00:00:00+00:00",
    )
    with MemoryTelemetryWriter(path) as writer:
        writer.write(
            snapshot=snapshot,
            event="sample",
            active_workers=2,
            worker_limit=5,
            pending_tasks=88,
            active_worker_rss_bytes=8 * GIB,
            note="unit test",
        )

    text = path.read_text(encoding="utf-8")
    assert "available_memory_gib" in text
    assert "18.000000" in text
    assert "unit test" in text


def test_abrupt_worker_exit_is_retried_without_breaking_batch(tmp_path):
    policy = MemoryGuardPolicy(
        enabled=False,
        maximum_abrupt_retries=2,
    )
    scheduler = MemoryAwareBatchScheduler(
        worker_function=_fail_once_then_succeed,
        maximum_workers=2,
        memory_policy=policy,
        telemetry_path=tmp_path / "memory.csv",
        multiprocessing_context=multiprocessing.get_context("spawn"),
    )
    task = {
        "mode": "reconstruct",
        "metadata": {
            "dataset_slug": "retry_dataset",
            "source_path": "input.root",
        },
        "marker_path": str(tmp_path / "failed_once.txt"),
    }

    results = list(scheduler.iter_results([task]))

    assert len(results) == 1
    assert results[0]["ok"]
    assert scheduler.statistics.abrupt_exit_event_count == 1
    assert scheduler.statistics.retried_task_count == 1
    assert scheduler.statistics.final_worker_limit == 1
