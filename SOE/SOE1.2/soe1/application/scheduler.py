from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import multiprocessing
from pathlib import Path
import time
import traceback
from typing import Any, Callable, Deque, Dict, Iterable, Iterator, Optional

from .memory import (
    GIB,
    MemoryGuardPolicy,
    MemoryTelemetryWriter,
    SystemMemoryMonitor,
)


def _isolated_process_entry(worker_function, task, send_connection):
    """
    在一次性子进程中执行一组数据。

    无论成功还是普通Python异常，结果都通过单向Pipe返回。段错误、SIGKILL或
    OOM等无法捕获的退出由父进程根据exit code识别。
    """

    try:
        result = worker_function(task)
    except BaseException as error:
        metadata = task.get("metadata", {})
        result = {
            "ok": False,
            "mode": task.get("mode", "unknown"),
            "dataset_slug": metadata.get("dataset_slug", "unknown"),
            "source_path": metadata.get("source_path"),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
        }
    try:
        send_connection.send(result)
    finally:
        send_connection.close()


@dataclass
class _PendingTask:
    task: Dict[str, object]
    abrupt_attempts: int = 0


@dataclass
class _ActiveWorker:
    process: Any
    receive_connection: Any
    pending_task: _PendingTask
    started_monotonic: float


@dataclass
class SchedulerStatistics:
    configured_max_workers: int
    initial_worker_limit: int
    final_worker_limit: int
    maximum_active_workers: int = 0
    completed_process_count: int = 0
    memory_pressure_event_count: int = 0
    abrupt_exit_event_count: int = 0
    retried_task_count: int = 0
    minimum_available_gib: float = float("inf")
    peak_active_worker_rss_gib: float = 0.0
    telemetry_csv: str = ""

    def to_dict(self) -> Dict[str, object]:
        minimum_available = (
            None
            if self.minimum_available_gib == float("inf")
            else self.minimum_available_gib
        )
        return {
            "configured_max_workers": self.configured_max_workers,
            "initial_worker_limit": self.initial_worker_limit,
            "final_worker_limit": self.final_worker_limit,
            "maximum_active_workers": self.maximum_active_workers,
            "completed_process_count": self.completed_process_count,
            "memory_pressure_event_count": (
                self.memory_pressure_event_count
            ),
            "abrupt_exit_event_count": self.abrupt_exit_event_count,
            "retried_task_count": self.retried_task_count,
            "minimum_available_gib": minimum_available,
            "peak_active_worker_rss_gib": (
                self.peak_active_worker_rss_gib
            ),
            "telemetry_csv": self.telemetry_csv,
        }


class MemoryAwareBatchScheduler:
    """
    按内存余量调度相互独立的数据集，并为每组创建一次性进程。

    设计目的：
      1. parallel_workers只是上限，内存不足时自动少开；
      2. 每组结束后进程退出，把NumPy/Pandas/Matplotlib内存归还给系统；
      3. 单进程被SIGKILL、段错误或OOM杀掉时只重试该组，不污染其余任务；
      4. 内存逼近保留线时主动终止最新worker并降低后续并发。
    """

    def __init__(
        self,
        worker_function: Callable[[Dict[str, object]], Dict[str, object]],
        maximum_workers: int,
        memory_policy: MemoryGuardPolicy,
        telemetry_path: Path,
        memory_monitor: Optional[SystemMemoryMonitor] = None,
        multiprocessing_context=None,
    ):
        if int(maximum_workers) <= 0:
            raise ValueError("maximum_workers 必须大于 0。")
        if memory_policy.minimum_worker_limit > int(maximum_workers):
            raise ValueError(
                "memory_guard.minimum_worker_limit 不能大于最大worker数。"
            )
        self.worker_function = worker_function
        self.maximum_workers = int(maximum_workers)
        self.policy = memory_policy
        self.monitor = memory_monitor or SystemMemoryMonitor()
        self.context = (
            multiprocessing_context
            if multiprocessing_context is not None
            else multiprocessing.get_context()
        )
        self.telemetry_path = Path(telemetry_path)
        self.current_worker_limit = self.maximum_workers
        self.statistics = SchedulerStatistics(
            configured_max_workers=self.maximum_workers,
            initial_worker_limit=self.maximum_workers,
            final_worker_limit=self.maximum_workers,
            telemetry_csv=str(self.telemetry_path),
        )

    def iter_results(
        self,
        tasks: Iterable[Dict[str, object]],
    ) -> Iterator[Dict[str, object]]:
        pending: Deque[_PendingTask] = deque(
            _PendingTask(task=dict(task)) for task in tasks
        )
        active: Dict[int, _ActiveWorker] = {}
        last_telemetry = 0.0
        last_waiting_log = 0.0

        initial_snapshot = self.monitor.snapshot()
        initial_capacity = self.policy.safe_worker_capacity(
            initial_snapshot.available_bytes,
            self.maximum_workers,
        )
        if self.policy.enabled:
            self.current_worker_limit = min(
                self.maximum_workers,
                max(
                    self.policy.minimum_worker_limit,
                    initial_capacity,
                ),
            )
        self.statistics.initial_worker_limit = self.current_worker_limit
        self.statistics.final_worker_limit = self.current_worker_limit

        print(
            "[memory guard] total="
            + f"{initial_snapshot.total_gib:.2f}"
            + " GiB, available="
            + f"{initial_snapshot.available_gib:.2f}"
            + " GiB, reserve="
            + f"{self.policy.minimum_available_gib:.2f}"
            + " GiB, estimated worker peak="
            + f"{self.policy.estimated_worker_peak_gib:.2f}"
            + " GiB, initial worker limit="
            + str(self.current_worker_limit),
            flush=True,
        )

        telemetry = MemoryTelemetryWriter(self.telemetry_path)
        try:
            self._write_telemetry(
                telemetry,
                initial_snapshot,
                "scheduler_start",
                active,
                pending,
                note=(
                    "memory guard enabled"
                    if self.policy.enabled
                    else "memory guard disabled"
                ),
            )
            while pending or active:
                completed_results = self._collect_finished_workers(
                    active,
                    pending,
                    telemetry,
                )
                for result in completed_results:
                    yield result

                snapshot = self.monitor.snapshot()
                active_rss = self._active_rss_bytes(active)
                self._update_statistics(snapshot, active_rss, active)
                now = time.monotonic()

                if (
                    now - last_telemetry
                    >= self.policy.telemetry_interval_seconds
                ):
                    self._write_telemetry(
                        telemetry,
                        snapshot,
                        "sample",
                        active,
                        pending,
                        active_rss_bytes=active_rss,
                    )
                    last_telemetry = now

                if (
                    self.policy.enabled
                    and active
                    and snapshot.available_bytes
                    < self.policy.minimum_available_bytes
                ):
                    pressure_result = self._relieve_memory_pressure(
                        snapshot,
                        active,
                        pending,
                        telemetry,
                    )
                    if pressure_result is not None:
                        yield pressure_result
                    continue

                launched = False
                while (
                    pending
                    and len(active) < self.current_worker_limit
                ):
                    snapshot = self.monitor.snapshot()
                    active_rss = self._active_rss_bytes(active)
                    if not self._has_launch_headroom(
                        snapshot.available_bytes,
                        active_rss,
                        len(active),
                    ):
                        if (
                            now - last_waiting_log
                            >= self.policy.waiting_log_interval_seconds
                        ):
                            print(
                                "[memory guard] waiting: available="
                                + f"{snapshot.available_gib:.2f}"
                                + " GiB, active="
                                + str(len(active))
                                + ", worker limit="
                                + str(self.current_worker_limit)
                                + ", pending="
                                + str(len(pending)),
                                flush=True,
                            )
                            self._write_telemetry(
                                telemetry,
                                snapshot,
                                "launch_throttled",
                                active,
                                pending,
                                active_rss_bytes=active_rss,
                                note="insufficient projected headroom",
                            )
                            last_waiting_log = now
                        break

                    pending_task = pending.popleft()
                    handle = self._launch_worker(pending_task)
                    active[handle.process.pid] = handle
                    launched = True
                    self.statistics.maximum_active_workers = max(
                        self.statistics.maximum_active_workers,
                        len(active),
                    )
                    self._write_telemetry(
                        telemetry,
                        snapshot,
                        "worker_started",
                        active,
                        pending,
                        active_rss_bytes=active_rss,
                        note=self._dataset_slug(pending_task.task),
                    )

                if not launched and (pending or active):
                    time.sleep(self.policy.poll_interval_seconds)
        finally:
            self._terminate_all(active)
            final_snapshot = self.monitor.snapshot()
            self._write_telemetry(
                telemetry,
                final_snapshot,
                "scheduler_stop",
                active,
                pending,
            )
            telemetry.close()
            self.statistics.final_worker_limit = self.current_worker_limit

    def _collect_finished_workers(
        self,
        active,
        pending,
        telemetry,
    ):
        results = []
        for process_id, handle in list(active.items()):
            result = None
            received = False
            try:
                pipe_ready = handle.receive_connection.poll()
            except (BrokenPipeError, EOFError, OSError):
                pipe_ready = False
            if pipe_ready:
                try:
                    result = handle.receive_connection.recv()
                    received = True
                except (BrokenPipeError, EOFError, OSError):
                    received = False

            if not received and handle.process.is_alive():
                continue

            if not received:
                handle.process.join(timeout=0.2)
                try:
                    pipe_ready = handle.receive_connection.poll(0.2)
                except (BrokenPipeError, EOFError, OSError):
                    pipe_ready = False
                if pipe_ready:
                    try:
                        result = handle.receive_connection.recv()
                        received = True
                    except (BrokenPipeError, EOFError, OSError):
                        received = False

            if received:
                self._finish_process(handle)
                del active[process_id]
                self.statistics.completed_process_count += 1
                snapshot = self.monitor.snapshot()
                if (
                    isinstance(result, dict)
                    and not result.get("ok", False)
                    and result.get("error_type") == "MemoryError"
                ):
                    self.statistics.memory_pressure_event_count += 1
                    self._decrease_worker_limit()
                    replacement_failure = self._retry_or_failure(
                        pending_task=handle.pending_task,
                        pending=pending,
                        error_type="MemoryError",
                        error_message=str(
                            result.get(
                                "error_message",
                                "worker触发Python MemoryError。",
                            )
                        ),
                    )
                    self._write_telemetry(
                        telemetry,
                        snapshot,
                        "worker_memory_error",
                        active,
                        pending,
                        note=self._dataset_slug(
                            handle.pending_task.task
                        ),
                    )
                    if replacement_failure is not None:
                        results.append(replacement_failure)
                    continue
                self._write_telemetry(
                    telemetry,
                    snapshot,
                    "worker_finished",
                    active,
                    pending,
                    note=self._dataset_slug(handle.pending_task.task),
                )
                results.append(result)
                continue

            exit_code = handle.process.exitcode
            self._finish_process(handle)
            del active[process_id]
            self.statistics.abrupt_exit_event_count += 1
            self._decrease_worker_limit()
            failure = self._retry_or_failure(
                pending_task=handle.pending_task,
                pending=pending,
                error_type="AbruptWorkerExit",
                error_message=(
                    "worker进程未返回结果便退出，exit code="
                    + str(exit_code)
                ),
            )
            snapshot = self.monitor.snapshot()
            self._write_telemetry(
                telemetry,
                snapshot,
                "worker_abrupt_exit",
                active,
                pending,
                note=(
                    self._dataset_slug(handle.pending_task.task)
                    + "; exit_code="
                    + str(exit_code)
                ),
            )
            if failure is not None:
                results.append(failure)
        return results

    def _relieve_memory_pressure(
        self,
        snapshot,
        active,
        pending,
        telemetry,
    ):
        newest = max(
            active.values(),
            key=lambda handle: handle.started_monotonic,
        )
        process_id = newest.process.pid
        dataset_slug = self._dataset_slug(newest.pending_task.task)
        print(
            "[memory guard] pressure detected: available="
            + f"{snapshot.available_gib:.2f}"
            + " GiB < reserve="
            + f"{self.policy.minimum_available_gib:.2f}"
            + " GiB; stop "
            + dataset_slug,
            flush=True,
        )
        self._terminate_process(newest)
        del active[process_id]
        self.statistics.memory_pressure_event_count += 1
        self._decrease_worker_limit()
        failure = self._retry_or_failure(
            pending_task=newest.pending_task,
            pending=pending,
            error_type="MemoryGuardTerminated",
            error_message=(
                "可用内存低于保护线，任务被主动终止并降低并发。"
            ),
        )
        self._write_telemetry(
            telemetry,
            snapshot,
            "memory_pressure_termination",
            active,
            pending,
            note=dataset_slug,
        )
        return failure

    def _retry_or_failure(
        self,
        pending_task,
        pending,
        error_type,
        error_message,
    ):
        if (
            pending_task.abrupt_attempts
            < self.policy.maximum_abrupt_retries
        ):
            pending_task.abrupt_attempts += 1
            pending.append(pending_task)
            self.statistics.retried_task_count += 1
            print(
                "[memory guard] requeue "
                + self._dataset_slug(pending_task.task)
                + ", retry "
                + str(pending_task.abrupt_attempts)
                + "/"
                + str(self.policy.maximum_abrupt_retries)
                + ", new worker limit="
                + str(self.current_worker_limit),
                flush=True,
            )
            return None

        metadata = pending_task.task.get("metadata", {})
        return {
            "ok": False,
            "mode": pending_task.task.get("mode", "unknown"),
            "dataset_slug": metadata.get("dataset_slug", "unknown"),
            "source_path": metadata.get("source_path"),
            "error_type": error_type,
            "error_message": error_message,
            "traceback": "",
        }

    def _launch_worker(self, pending_task):
        receive_connection, send_connection = self.context.Pipe(
            duplex=False
        )
        process = self.context.Process(
            target=_isolated_process_entry,
            args=(
                self.worker_function,
                pending_task.task,
                send_connection,
            ),
            name=(
                "SOE1.2-"
                + self._dataset_slug(pending_task.task)[:48]
            ),
        )
        process.daemon = False
        process.start()
        send_connection.close()
        return _ActiveWorker(
            process=process,
            receive_connection=receive_connection,
            pending_task=pending_task,
            started_monotonic=time.monotonic(),
        )

    def _has_launch_headroom(
        self,
        available_bytes,
        active_rss_bytes,
        active_count,
    ) -> bool:
        if not self.policy.enabled:
            return True
        expected_existing_peak = (
            active_count * self.policy.estimated_worker_peak_bytes
        )
        unmaterialized_existing_peak = max(
            0,
            expected_existing_peak - active_rss_bytes,
        )
        projected_available = (
            available_bytes
            - unmaterialized_existing_peak
            - self.policy.estimated_worker_peak_bytes
        )
        return (
            projected_available
            >= self.policy.minimum_available_bytes
        )

    def _active_rss_bytes(self, active) -> int:
        total = 0
        unknown = 0
        for process_id in active:
            value = self.monitor.process_rss_bytes(process_id)
            if value is None:
                unknown += 1
            else:
                total += int(value)
        total += (
            unknown * self.policy.estimated_worker_peak_bytes
        )
        return total

    def _update_statistics(self, snapshot, active_rss, active) -> None:
        self.statistics.minimum_available_gib = min(
            self.statistics.minimum_available_gib,
            snapshot.available_gib,
        )
        self.statistics.peak_active_worker_rss_gib = max(
            self.statistics.peak_active_worker_rss_gib,
            active_rss / GIB,
        )
        self.statistics.maximum_active_workers = max(
            self.statistics.maximum_active_workers,
            len(active),
        )

    def _decrease_worker_limit(self) -> None:
        self.current_worker_limit = max(
            self.policy.minimum_worker_limit,
            self.current_worker_limit - 1,
        )
        self.statistics.final_worker_limit = self.current_worker_limit

    def _write_telemetry(
        self,
        telemetry,
        snapshot,
        event,
        active,
        pending,
        active_rss_bytes=None,
        note="",
    ) -> None:
        if active_rss_bytes is None:
            active_rss_bytes = self._active_rss_bytes(active)
        telemetry.write(
            snapshot=snapshot,
            event=event,
            active_workers=len(active),
            worker_limit=self.current_worker_limit,
            pending_tasks=len(pending),
            active_worker_rss_bytes=active_rss_bytes,
            note=note,
        )

    @staticmethod
    def _finish_process(handle) -> None:
        handle.process.join(timeout=2.0)
        if handle.process.is_alive():
            handle.process.terminate()
            handle.process.join(timeout=2.0)
        handle.receive_connection.close()
        try:
            handle.process.close()
        except (AttributeError, ValueError):
            pass

    @staticmethod
    def _terminate_process(handle) -> None:
        if handle.process.is_alive():
            handle.process.terminate()
            handle.process.join(timeout=3.0)
        if handle.process.is_alive() and hasattr(handle.process, "kill"):
            handle.process.kill()
            handle.process.join(timeout=3.0)
        handle.receive_connection.close()
        try:
            handle.process.close()
        except (AttributeError, ValueError):
            pass

    def _terminate_all(self, active) -> None:
        for handle in list(active.values()):
            self._terminate_process(handle)
        active.clear()

    @staticmethod
    def _dataset_slug(task) -> str:
        return str(
            task.get("metadata", {}).get("dataset_slug", "unknown")
        )
