"""无强制第三方依赖的系统内存探测和 worker 容量估算。"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Dict


GIB = 1024 ** 3


@dataclass(frozen=True)
class MemorySnapshot:
    """某一时刻的系统物理内存状态。"""

    total_bytes: int
    available_bytes: int
    timestamp_utc: str

    @property
    def total_gib(self) -> float:
        return self.total_bytes / GIB

    @property
    def available_gib(self) -> float:
        return self.available_bytes / GIB


@dataclass(frozen=True)
class MemoryGuardPolicy:
    """根据保留线和单 worker 峰值估计动态限制数据集并发。"""

    enabled: bool = True
    minimum_available_gib: float = 5.0
    estimated_worker_peak_gib: float = 4.0

    def __post_init__(self) -> None:
        if self.minimum_available_gib <= 0.0:
            raise ValueError("minimum_available_gib 必须大于 0。")
        if self.estimated_worker_peak_gib <= 0.0:
            raise ValueError("estimated_worker_peak_gib 必须大于 0。")

    @property
    def minimum_available_bytes(self) -> int:
        return int(self.minimum_available_gib * GIB)

    @property
    def estimated_worker_peak_bytes(self) -> int:
        return int(self.estimated_worker_peak_gib * GIB)

    def safe_worker_capacity(self, available_bytes: int, configured_maximum: int) -> int:
        """给出当前可安全容纳的 worker 总数，结果不超过用户上限。"""

        maximum = int(configured_maximum)
        if maximum <= 0:
            raise ValueError("configured_maximum 必须大于 0。")
        if not self.enabled:
            return maximum
        usable = int(available_bytes) - self.minimum_available_bytes
        if usable <= 0:
            return 0
        capacity = usable // self.estimated_worker_peak_bytes
        return max(0, min(maximum, int(capacity)))


class SystemMemoryMonitor:
    """优先读取 Linux `/proc/meminfo`，同时支持 Windows 开发机。"""

    PROC_MEMINFO = Path("/proc/meminfo")

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def parse_proc_meminfo(text: str) -> Dict[str, int]:
        """解析 `/proc/meminfo`，统一转换为字节。"""

        result = {}
        for line in text.splitlines():
            if ":" not in line:
                continue
            key, raw = line.split(":", 1)
            fields = raw.strip().split()
            if not fields:
                continue
            multiplier = 1024 if len(fields) > 1 and fields[1] == "kB" else 1
            result[key] = int(fields[0]) * multiplier
        if "MemTotal" not in result:
            raise RuntimeError("/proc/meminfo 缺少 MemTotal。")
        return result

    def snapshot(self) -> MemorySnapshot:
        if self.PROC_MEMINFO.is_file():
            values = self.parse_proc_meminfo(
                self.PROC_MEMINFO.read_text(encoding="ascii", errors="replace")
            )
            available = values.get(
                "MemAvailable",
                values.get("MemFree", 0)
                + values.get("Buffers", 0)
                + values.get("Cached", 0),
            )
            return MemorySnapshot(
                total_bytes=int(values["MemTotal"]),
                available_bytes=int(available),
                timestamp_utc=self._timestamp(),
            )
        if os.name == "nt":
            return self._windows_snapshot()
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        return MemorySnapshot(
            total_bytes=page_size * int(os.sysconf("SC_PHYS_PAGES")),
            available_bytes=page_size * int(os.sysconf("SC_AVPHYS_PAGES")),
            timestamp_utc=self._timestamp(),
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
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise OSError("Windows GlobalMemoryStatusEx 调用失败。")
        return MemorySnapshot(
            total_bytes=int(status.total_physical),
            available_bytes=int(status.available_physical),
            timestamp_utc=self._timestamp(),
        )
