from __future__ import annotations

import csv
import ctypes
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Dict, Optional


GIB = 1024 ** 3


@dataclass(frozen=True)
class MemorySnapshot:
    """操作系统在某一时刻报告的物理内存与交换分区状态。"""

    total_bytes: int
    available_bytes: int
    swap_free_bytes: int
    timestamp_utc: str

    @property
    def total_gib(self) -> float:
        return self.total_bytes / GIB

    @property
    def available_gib(self) -> float:
        return self.available_bytes / GIB

    @property
    def swap_free_gib(self) -> float:
        return self.swap_free_bytes / GIB


@dataclass(frozen=True)
class MemoryGuardPolicy:
    """
    批处理内存保护策略。

    parallel_workers 仍表示用户允许的最大并发数；本策略只负责在内存不足时
    降低实际并发，不会修改单组数据的物理模型或 SOE 参数。
    """

    enabled: bool = True
    minimum_available_gib: float = 5.0
    estimated_worker_peak_gib: float = 4.0
    poll_interval_seconds: float = 2.0
    telemetry_interval_seconds: float = 10.0
    waiting_log_interval_seconds: float = 30.0
    maximum_abrupt_retries: int = 2
    minimum_worker_limit: int = 1

    @classmethod
    def from_batch_config(cls, batch_config: Dict[str, object]):
        raw = batch_config.get("memory_guard", {})
        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            raise TypeError("batch.memory_guard 必须是 JSON 对象。")
        policy = cls(
            enabled=bool(raw.get("enabled", True)),
            minimum_available_gib=float(
                raw.get("minimum_available_gib", 5.0)
            ),
            estimated_worker_peak_gib=float(
                raw.get("estimated_worker_peak_gib", 4.0)
            ),
            poll_interval_seconds=float(
                raw.get("poll_interval_seconds", 2.0)
            ),
            telemetry_interval_seconds=float(
                raw.get("telemetry_interval_seconds", 10.0)
            ),
            waiting_log_interval_seconds=float(
                raw.get("waiting_log_interval_seconds", 30.0)
            ),
            maximum_abrupt_retries=int(
                raw.get("maximum_abrupt_retries", 2)
            ),
            minimum_worker_limit=int(
                raw.get("minimum_worker_limit", 1)
            ),
        )
        policy.validate()
        return policy

    def validate(self) -> None:
        if self.minimum_available_gib <= 0.0:
            raise ValueError(
                "batch.memory_guard.minimum_available_gib 必须大于 0。"
            )
        if self.estimated_worker_peak_gib <= 0.0:
            raise ValueError(
                "batch.memory_guard.estimated_worker_peak_gib 必须大于 0。"
            )
        if self.poll_interval_seconds <= 0.0:
            raise ValueError(
                "batch.memory_guard.poll_interval_seconds 必须大于 0。"
            )
        if self.telemetry_interval_seconds <= 0.0:
            raise ValueError(
                "batch.memory_guard.telemetry_interval_seconds 必须大于 0。"
            )
        if self.waiting_log_interval_seconds <= 0.0:
            raise ValueError(
                "batch.memory_guard.waiting_log_interval_seconds 必须大于 0。"
            )
        if self.maximum_abrupt_retries < 0:
            raise ValueError(
                "batch.memory_guard.maximum_abrupt_retries 不能小于 0。"
            )
        if self.minimum_worker_limit <= 0:
            raise ValueError(
                "batch.memory_guard.minimum_worker_limit 必须大于 0。"
            )

    @property
    def minimum_available_bytes(self) -> int:
        return int(self.minimum_available_gib * GIB)

    @property
    def estimated_worker_peak_bytes(self) -> int:
        return int(self.estimated_worker_peak_gib * GIB)

    def safe_worker_capacity(
        self,
        available_bytes: int,
        configured_maximum: int,
    ) -> int:
        """根据当前可用内存估算还能安全容纳的总worker数量。"""

        if not self.enabled:
            return int(configured_maximum)
        usable = int(available_bytes) - self.minimum_available_bytes
        if usable <= 0:
            return 0
        capacity = usable // self.estimated_worker_peak_bytes
        return max(0, min(int(configured_maximum), int(capacity)))


class SystemMemoryMonitor:
    """
    无第三方依赖的系统内存读取器。

    服务器优先读取 /proc/meminfo；Windows回退只用于本地测试和开发。
    """

    PROC_MEMINFO = Path("/proc/meminfo")

    def snapshot(self) -> MemorySnapshot:
        if self.PROC_MEMINFO.is_file():
            values = self._parse_proc_meminfo_text(
                self.PROC_MEMINFO.read_text(encoding="ascii")
            )
            total = values["MemTotal"]
            available = values.get(
                "MemAvailable",
                values.get("MemFree", 0)
                + values.get("Buffers", 0)
                + values.get("Cached", 0),
            )
            swap_free = values.get("SwapFree", 0)
            return self._build_snapshot(total, available, swap_free)

        if os.name == "nt":
            return self._windows_snapshot()
        return self._posix_sysconf_snapshot()

    def process_rss_bytes(self, process_id: int) -> Optional[int]:
        status_path = Path("/proc") / str(int(process_id)) / "status"
        if not status_path.is_file():
            return None
        try:
            for line in status_path.read_text(
                encoding="ascii", errors="replace"
            ).splitlines():
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
        except (OSError, ValueError, IndexError):
            return None
        return None

    @staticmethod
    def _parse_proc_meminfo_text(text: str) -> Dict[str, int]:
        values = {}
        for line in text.splitlines():
            if ":" not in line:
                continue
            key, raw_value = line.split(":", 1)
            fields = raw_value.strip().split()
            if not fields:
                continue
            multiplier = 1024 if len(fields) > 1 and fields[1] == "kB" else 1
            values[key] = int(fields[0]) * multiplier
        if "MemTotal" not in values:
            raise RuntimeError("/proc/meminfo 缺少 MemTotal。")
        return values

    @staticmethod
    def _build_snapshot(total, available, swap_free) -> MemorySnapshot:
        return MemorySnapshot(
            total_bytes=int(total),
            available_bytes=int(available),
            swap_free_bytes=int(swap_free),
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
        )

    def _windows_snapshot(self) -> MemorySnapshot:
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("available_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(MemoryStatus)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(
            ctypes.byref(status)
        ):
            raise OSError("Windows GlobalMemoryStatusEx 调用失败。")
        return self._build_snapshot(
            status.total_physical,
            status.available_physical,
            status.available_page_file,
        )

    def _posix_sysconf_snapshot(self) -> MemorySnapshot:
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        total = page_size * int(os.sysconf("SC_PHYS_PAGES"))
        available = page_size * int(os.sysconf("SC_AVPHYS_PAGES"))
        return self._build_snapshot(total, available, 0)


class MemoryTelemetryWriter:
    """把调度过程写成可直接用表格软件查看的CSV。"""

    FIELD_NAMES = [
        "run_id",
        "timestamp_utc",
        "event",
        "total_memory_gib",
        "available_memory_gib",
        "swap_free_gib",
        "active_workers",
        "worker_limit",
        "pending_tasks",
        "active_worker_rss_gib",
        "note",
    ]

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%S.%fZ"
        )
        write_header = not self.path.exists() or self.path.stat().st_size == 0
        self._file = self.path.open("a", encoding="utf-8", newline="")
        self._writer = csv.DictWriter(
            self._file,
            fieldnames=self.FIELD_NAMES,
        )
        if write_header:
            self._writer.writeheader()
            self._file.flush()

    def write(
        self,
        snapshot: MemorySnapshot,
        event: str,
        active_workers: int,
        worker_limit: int,
        pending_tasks: int,
        active_worker_rss_bytes: int,
        note: str = "",
    ) -> None:
        self._writer.writerow(
            {
                "run_id": self.run_id,
                "timestamp_utc": snapshot.timestamp_utc,
                "event": event,
                "total_memory_gib": f"{snapshot.total_gib:.6f}",
                "available_memory_gib": f"{snapshot.available_gib:.6f}",
                "swap_free_gib": f"{snapshot.swap_free_gib:.6f}",
                "active_workers": int(active_workers),
                "worker_limit": int(worker_limit),
                "pending_tasks": int(pending_tasks),
                "active_worker_rss_gib": (
                    f"{active_worker_rss_bytes / GIB:.6f}"
                ),
                "note": str(note),
            }
        )
        self._file.flush()

    def close(self) -> None:
        if not self._file.closed:
            self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback_value):
        self.close()
