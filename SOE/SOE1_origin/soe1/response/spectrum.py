from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import numpy as np

from ..domain import MeasuredEvent


@dataclass(frozen=True)
class DiscreteSpectrumPrior:
    """
    全局离散入射能谱先验。

    probabilities 表示每个能量 bin 的概率质量，而不是概率密度。
    """

    energies_mev: np.ndarray
    probabilities: np.ndarray

    def __post_init__(self) -> None:
        energies = np.asarray(self.energies_mev, dtype=float)
        probabilities = np.asarray(self.probabilities, dtype=float)
        if energies.ndim != 1 or probabilities.ndim != 1:
            raise ValueError("能谱 energies/probabilities 必须是一维数组。")
        if len(energies) != len(probabilities) or len(energies) == 0:
            raise ValueError("能谱 energies/probabilities 长度必须相等且非空。")
        if np.any(~np.isfinite(energies)) or np.any(energies <= 0.0):
            raise ValueError("能谱能量必须为正有限值。")
        if np.any(~np.isfinite(probabilities)) or np.any(probabilities < 0.0):
            raise ValueError("能谱概率必须为非负有限值。")

        order = np.argsort(energies)
        energies = energies[order]
        probabilities = probabilities[order]
        total = float(probabilities.sum())
        if total <= 0.0:
            raise ValueError("能谱概率总和必须大于 0。")

        object.__setattr__(self, "energies_mev", energies)
        object.__setattr__(self, "probabilities", probabilities / total)

    def probability_at(self, energy_mev: float) -> float:
        """线性插值概率质量，用于诊断或连续能量点近似。"""

        return float(
            np.interp(
                float(energy_mev),
                self.energies_mev,
                self.probabilities,
                left=0.0,
                right=0.0,
            )
        )


class SpectrumPriorFactory:
    """
    根据配置构造能谱先验。

    configured：
        用户给出谱线或离散能量概率，适合已有外部谱学信息时。
    ch0_observed：
        用 ch0-only 沉积能谱做高斯核平滑，作为第一版经验先验。该模式
        不是严格的响应反卷积，README 中会明确其适用边界。
    """

    def __init__(self, config: Dict[str, object]):
        self.config = config

    def build(
        self,
        spectroscopy_events: Iterable[MeasuredEvent],
    ) -> DiscreteSpectrumPrior:
        mode = str(self.config.get("mode", "configured"))
        grid = self._energy_grid()

        if mode == "configured":
            probabilities = self._configured_probabilities(grid)
        elif mode == "ch0_observed":
            probabilities = self._observed_probabilities(
                grid,
                list(spectroscopy_events),
            )
        else:
            raise ValueError("未知 spectrum.mode：" + mode)

        floor = float(self.config.get("probability_floor", 1e-12))
        probabilities = np.maximum(probabilities, floor)
        return DiscreteSpectrumPrior(grid, probabilities)

    def _energy_grid(self) -> np.ndarray:
        minimum = float(self.config["minimum_energy_mev"])
        maximum = float(self.config["maximum_energy_mev"])
        step = float(self.config["energy_step_mev"])
        if minimum <= 0.0 or maximum <= minimum or step <= 0.0:
            raise ValueError("能量网格配置不合法。")
        count = int(np.floor((maximum - minimum) / step)) + 1
        return minimum + np.arange(count, dtype=float) * step

    def _configured_probabilities(self, grid: np.ndarray) -> np.ndarray:
        components = self.config.get("components", [])
        if not components:
            raise ValueError("configured 能谱至少需要一个 components 元素。")

        default_sigma = float(
            self.config.get("configured_component_sigma_mev", 0.02)
        )
        result = np.zeros_like(grid)
        for component in components:
            center = float(component["energy_mev"])
            weight = float(component.get("weight", 1.0))
            sigma = float(component.get("sigma_mev", default_sigma))
            if sigma <= 0.0 or weight < 0.0:
                raise ValueError("configured spectrum component 参数不合法。")
            result += weight * np.exp(
                -0.5 * ((grid - center) / sigma) ** 2
            )
        return result

    def _observed_probabilities(
        self,
        grid: np.ndarray,
        events: List[MeasuredEvent],
    ) -> np.ndarray:
        energies = np.asarray(
            [event.total_deposited_energy_mev for event in events],
            dtype=float,
        )
        if energies.size == 0:
            raise ValueError(
                "spectrum.mode=ch0_observed，但输入中没有 ch0-only 事件。"
            )

        bandwidth = float(self.config.get("kde_bandwidth_mev", 0.03))
        if bandwidth <= 0.0:
            raise ValueError("kde_bandwidth_mev 必须大于 0。")

        # 分块计算，避免服务器上 ch0-only 事件很多时构造巨大二维矩阵。
        result = np.zeros_like(grid)
        chunk_size = 20000
        for start in range(0, len(energies), chunk_size):
            chunk = energies[start : start + chunk_size]
            residual = (grid[:, None] - chunk[None, :]) / bandwidth
            result += np.exp(-0.5 * residual * residual).sum(axis=1)
        return result

