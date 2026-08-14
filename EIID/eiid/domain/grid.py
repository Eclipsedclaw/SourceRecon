"""能量网格和联合网格。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class EnergyGrid:
    """由严格递增 bin 边界定义的能量网格。

    输出必须保存 `edges_mev`，不能只保存 bin 中心，否则无法可靠重采样。
    """

    edges_mev: np.ndarray

    def __post_init__(self) -> None:
        edges = np.asarray(self.edges_mev, dtype=float).copy()
        if edges.ndim != 1 or edges.size < 2:
            raise ValueError("EnergyGrid 至少需要两个一维边界。")
        if not np.all(np.isfinite(edges)) or np.any(np.diff(edges) <= 0.0):
            raise ValueError("EnergyGrid 边界必须有限且严格递增。")
        edges.setflags(write=False)
        object.__setattr__(self, "edges_mev", edges)

    @classmethod
    def uniform(cls, minimum_mev: float, maximum_mev: float, width_mev: float) -> "EnergyGrid":
        """构造能整除给定范围的均匀网格。"""

        minimum = float(minimum_mev)
        maximum = float(maximum_mev)
        width = float(width_mev)
        if width <= 0.0 or maximum <= minimum:
            raise ValueError("均匀能量网格要求正 bin 宽和递增范围。")
        raw_count = (maximum - minimum) / width
        count = int(round(raw_count))
        if count <= 0 or not np.isclose(raw_count, count, atol=1e-10, rtol=1e-10):
            raise ValueError("bin_width_mev 必须整除能量范围。")
        return cls(np.linspace(minimum, maximum, count + 1, dtype=float))

    @classmethod
    def nonuniform(cls, edges_mev: Sequence[float]) -> "EnergyGrid":
        """构造非均匀能量网格。"""

        return cls(np.asarray(edges_mev, dtype=float))

    @property
    def bin_count(self) -> int:
        return int(self.edges_mev.size - 1)

    @property
    def centers_mev(self) -> np.ndarray:
        return 0.5 * (self.edges_mev[:-1] + self.edges_mev[1:])

    def bin_index(self, energy_mev: float) -> int:
        """返回能量 bin；最大边界属于最后一个 bin。"""

        value = float(energy_mev)
        if value < self.edges_mev[0] or value > self.edges_mev[-1]:
            raise ValueError("能量超出网格范围。")
        if np.isclose(value, self.edges_mev[-1]):
            return self.bin_count - 1
        return int(np.searchsorted(self.edges_mev, value, side="right") - 1)


@dataclass(frozen=True)
class SkyEnergyGrid:
    """天空像素与能量 bin 的笛卡尔积，仅保存网格对象而不分配稠密响应。"""

    sky_grid: object
    energy_grid: EnergyGrid

    @property
    def cell_count(self) -> int:
        return int(self.sky_grid.pixel_count * self.energy_grid.bin_count)

