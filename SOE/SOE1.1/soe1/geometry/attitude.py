from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

from ..domain import MeasuredEvent


class AttitudeProvider(ABC):
    """探测器坐标到天空惯性坐标的旋转接口。"""

    @abstractmethod
    def detector_to_sky(
        self,
        event: MeasuredEvent,
        direction_detector: np.ndarray,
    ) -> np.ndarray:
        raise NotImplementedError


class IdentityAttitudeProvider(AttitudeProvider):
    """地面固定坐标或几何单元测试使用的单位姿态。"""

    def detector_to_sky(self, event, direction_detector):
        direction = np.asarray(direction_detector, dtype=float)
        return direction / np.linalg.norm(direction)


class CsvQuaternionAttitudeProvider(AttitudeProvider):
    """
    从 CSV/TSV 姿态表按最近时刻读取四元数。

    四元数约定为 (x, y, z, w)，表示把 detector frame 主动旋转到 sky
    frame。若上游姿态系统使用相反约定，必须在配置中设置 conjugate=true。
    """

    def __init__(
        self,
        path: Path,
        columns: Dict[str, str],
        separator: str = ",",
        time_scale_to_ns: float = 1.0,
        maximum_time_difference_ns: Optional[float] = None,
        conjugate: bool = False,
    ):
        if not path.exists():
            raise FileNotFoundError("找不到姿态文件：" + str(path))
        self.path = path
        self.columns = columns
        self.separator = separator
        self.time_scale_to_ns = float(time_scale_to_ns)
        self.maximum_time_difference_ns = maximum_time_difference_ns
        self.conjugate = bool(conjugate)

        frame = pd.read_csv(path, sep=separator)
        required = [
            columns["time"],
            columns["qx"],
            columns["qy"],
            columns["qz"],
            columns["qw"],
        ]
        missing = [name for name in required if name not in frame.columns]
        if missing:
            raise KeyError("姿态文件缺少列：" + ", ".join(missing))

        times = (
            frame[columns["time"]].to_numpy(dtype=float)
            * self.time_scale_to_ns
        )
        quaternions = frame[
            [columns["qx"], columns["qy"], columns["qz"], columns["qw"]]
        ].to_numpy(dtype=float)
        order = np.argsort(times)
        self.times_ns = times[order]
        self.quaternions = quaternions[order]
        if len(self.times_ns) == 0:
            raise ValueError("姿态文件没有数据行。")
        if not np.all(np.isfinite(self.times_ns)):
            raise ValueError("姿态时间列含非有限值。")
        if not np.all(np.isfinite(self.quaternions)):
            raise ValueError("姿态四元数列含非有限值。")

    def detector_to_sky(self, event, direction_detector):
        if event.attitude_time_ns is None:
            raise ValueError(
                "事件 "
                + event.event_id
                + " 没有时间，无法从姿态表选择四元数。"
            )
        index = self._nearest_index(float(event.attitude_time_ns))
        difference = abs(
            float(self.times_ns[index]) - float(event.attitude_time_ns)
        )
        if (
            self.maximum_time_difference_ns is not None
            and difference > float(self.maximum_time_difference_ns)
        ):
            raise ValueError(
                "事件 "
                + event.event_id
                + " 与最近姿态的时间差超过限制："
                + str(difference)
                + " ns"
            )

        quaternion = self.quaternions[index].astype(float)
        if self.conjugate:
            quaternion[:3] *= -1.0
        rotation = self._quaternion_to_matrix(quaternion)
        direction = rotation @ np.asarray(direction_detector, dtype=float)
        return direction / np.linalg.norm(direction)

    def _nearest_index(self, time_ns: float) -> int:
        insertion = int(np.searchsorted(self.times_ns, time_ns))
        if insertion <= 0:
            return 0
        if insertion >= len(self.times_ns):
            return len(self.times_ns) - 1
        before = insertion - 1
        after = insertion
        if abs(self.times_ns[before] - time_ns) <= abs(
            self.times_ns[after] - time_ns
        ):
            return before
        return after

    @staticmethod
    def _quaternion_to_matrix(quaternion: np.ndarray) -> np.ndarray:
        qx, qy, qz, qw = quaternion
        norm = float(np.linalg.norm(quaternion))
        if norm <= 0.0:
            raise ValueError("姿态四元数范数为 0。")
        qx, qy, qz, qw = quaternion / norm
        return np.array(
            [
                [
                    1.0 - 2.0 * (qy * qy + qz * qz),
                    2.0 * (qx * qy - qz * qw),
                    2.0 * (qx * qz + qy * qw),
                ],
                [
                    2.0 * (qx * qy + qz * qw),
                    1.0 - 2.0 * (qx * qx + qz * qz),
                    2.0 * (qy * qz - qx * qw),
                ],
                [
                    2.0 * (qx * qz - qy * qw),
                    2.0 * (qy * qz + qx * qw),
                    1.0 - 2.0 * (qx * qx + qy * qy),
                ],
            ],
            dtype=float,
        )
