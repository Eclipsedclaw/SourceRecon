"""逐迭代数值、时间、内存和图像快照记录。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import time
from typing import Any, Mapping, Optional, Tuple

import numpy as np

from eiid.batch import SystemMemoryMonitor


class ProcessMemoryMonitor:
    """优先使用 psutil，精简 Linux 环境回退到 /proc/self/status。"""

    @staticmethod
    def resident_bytes() -> Optional[int]:
        try:
            import psutil

            return int(psutil.Process(os.getpid()).memory_info().rss)
        except (ImportError, OSError):
            pass
        status = Path("/proc/self/status")
        if status.is_file():
            try:
                for line in status.read_text(
                    encoding="ascii", errors="replace"
                ).splitlines():
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1]) * 1024
            except (OSError, ValueError, IndexError):
                return None
        return None


@dataclass(frozen=True)
class IterationMetrics:
    """一次 LM-MLEM 状态的完整轻量遥测。"""

    iteration: int
    log_likelihood: float
    relative_log_likelihood_change: Optional[float]
    total_intensity: float
    l1_relative_change: float
    l2_relative_change: float
    maximum_relative_change: float
    sky_marginal_l1_change: float
    energy_marginal_l1_change: float
    peak_joint_cell_index: int
    peak_sky_pixel_index: int
    peak_energy_bin_index: int
    valid_event_count: int
    zero_response_event_count: int
    invalid_denominator_count: int
    iteration_seconds: float
    elapsed_seconds: float
    events_per_second: float
    process_rss_bytes: Optional[int]
    system_available_memory_bytes: Optional[int]
    event_group_contributions: Mapping[str, int] = field(default_factory=dict)
    sky_centroid_direction: Optional[Tuple[float, float, float]] = None
    sky_r68_deg: Optional[float] = None
    energy_peak_mev: Optional[float] = None
    energy_weighted_mean_mev: Optional[float] = None

    def as_dict(self):
        payload = asdict(self)
        payload["event_group_contributions"] = dict(self.event_group_contributions)
        return payload


class IterationRecorder:
    """把每次迭代写入 JSONL，并按策略原子保存联合图像快照。"""

    def __init__(
        self,
        numerical_directory,
        checkpoint_directory,
        sky_pixel_count: int,
        energy_bin_count: int,
        snapshot_first_iterations: int = 3,
        snapshot_interval: int = 5,
    ):
        self.numerical_directory = Path(numerical_directory).resolve()
        self.checkpoint_directory = Path(checkpoint_directory).resolve()
        self.numerical_directory.mkdir(parents=True, exist_ok=True)
        self.checkpoint_directory.mkdir(parents=True, exist_ok=True)
        self.sky_pixel_count = int(sky_pixel_count)
        self.energy_bin_count = int(energy_bin_count)
        self.snapshot_first_iterations = int(snapshot_first_iterations)
        self.snapshot_interval = int(snapshot_interval)
        if self.sky_pixel_count <= 0 or self.energy_bin_count <= 0:
            raise ValueError("天空和能量网格大小必须为正。")
        if self.snapshot_first_iterations < 0 or self.snapshot_interval <= 0:
            raise ValueError("快照前置次数不能为负，快照间隔必须为正。")
        self.metrics_path = self.numerical_directory / "iteration_metrics.jsonl"
        self.summary_path = self.numerical_directory / "convergence_summary.json"
        self._record_count = 0

    def should_snapshot(self, iteration: int) -> bool:
        return (
            iteration <= self.snapshot_first_iterations
            or iteration % self.snapshot_interval == 0
        )

    @staticmethod
    def load_latest_checkpoint(checkpoint_directory):
        """读取最新完整 NPZ；用于在新 run 中从中断点恢复，不覆盖原 run。"""

        directory = Path(checkpoint_directory).resolve()
        candidates = sorted(directory.glob("iteration_*.npz"))
        if not candidates:
            raise FileNotFoundError("没有可用于恢复的 iteration checkpoint。")
        latest = candidates[-1]
        with np.load(str(latest), allow_pickle=False) as payload:
            image = np.asarray(payload["joint_image"], dtype=float)
            iteration = int(np.asarray(payload["iteration"]).reshape(-1)[0])
        if not np.all(np.isfinite(image)) or np.any(image < 0.0):
            raise ValueError("恢复 checkpoint 中的联合图像无效。")
        return iteration, image, latest

    def record(
        self,
        metrics: IterationMetrics,
        image,
        force_snapshot: bool = False,
    ) -> None:
        line = json.dumps(metrics.as_dict(), ensure_ascii=False, sort_keys=True)
        with self.metrics_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(line)
            stream.write("\n")
            stream.flush()
        self._record_count += 1
        if force_snapshot or self.should_snapshot(metrics.iteration):
            self._save_snapshot(metrics.iteration, image)

    def _save_snapshot(self, iteration: int, image) -> Path:
        joint = np.asarray(image, dtype=float).reshape(
            self.sky_pixel_count, self.energy_bin_count
        )
        destination = self.checkpoint_directory / (
            "iteration_{:06d}.npz".format(iteration)
        )
        temporary = destination.with_name(destination.name + ".tmp")
        with temporary.open("wb") as stream:
            np.savez_compressed(
                stream,
                joint_image=joint,
                sky_marginal=np.sum(joint, axis=1),
                energy_marginal=np.sum(joint, axis=0),
                iteration=np.asarray([iteration], dtype=np.int64),
            )
        os.replace(str(temporary), str(destination))
        return destination

    def finalize(
        self,
        stop_reason: str,
        completed_iterations: int,
        final_metrics: IterationMetrics,
        final_image,
    ) -> Path:
        self._save_snapshot(completed_iterations, final_image)
        payload = {
            "stop_reason": str(stop_reason),
            "completed_iterations": int(completed_iterations),
            "metric_record_count": self._record_count,
            "final_metrics": final_metrics.as_dict(),
            "final_snapshot": "iteration_{:06d}.npz".format(completed_iterations),
        }
        temporary = self.summary_path.with_name(self.summary_path.name + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(str(temporary), str(self.summary_path))
        return self.summary_path


def memory_snapshot():
    """返回进程 RSS 和系统可用内存；探测失败时不阻断重建。"""

    rss = ProcessMemoryMonitor.resident_bytes()
    try:
        available = SystemMemoryMonitor().snapshot().available_bytes
    except (OSError, RuntimeError, ValueError):
        available = None
    return rss, available
