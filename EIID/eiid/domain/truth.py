"""仅模拟数据可用的真值对象。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

import numpy as np


def _readonly_vector(value: np.ndarray, label: str) -> np.ndarray:
    array = np.asarray(value, dtype=float).copy()
    if array.shape != (3,) or not np.all(np.isfinite(array)):
        raise ValueError(label + " 必须是三个有限数字。")
    norm = float(np.linalg.norm(array))
    if norm <= 0.0:
        raise ValueError(label + " 不能是零向量。")
    array /= norm
    array.setflags(write=False)
    return array


@dataclass(frozen=True)
class SimulationTruth:
    """Geant4 primary 和物理过程真值。

    重建核心不得依赖本类。它只服务响应构建、闭环验证和污染率统计。
    """

    primary_energy_mev: float
    propagation_direction_detector: np.ndarray
    source_direction_detector: np.ndarray
    event_weight: float = 1.0
    is_full_absorption: Optional[bool] = None
    is_backscatter: Optional[bool] = None
    has_pair_production: Optional[bool] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        energy = float(self.primary_energy_mev)
        weight = float(self.event_weight)
        if not np.isfinite(energy) or energy <= 0.0:
            raise ValueError("primary_energy_mev 必须是正有限值。")
        if not np.isfinite(weight) or weight < 0.0:
            raise ValueError("event_weight 必须是非负有限值。")
        object.__setattr__(self, "primary_energy_mev", energy)
        object.__setattr__(self, "event_weight", weight)
        object.__setattr__(
            self,
            "propagation_direction_detector",
            _readonly_vector(
                self.propagation_direction_detector,
                "propagation_direction_detector",
            ),
        )
        object.__setattr__(
            self,
            "source_direction_detector",
            _readonly_vector(self.source_direction_detector, "source_direction_detector"),
        )
        object.__setattr__(self, "metadata", dict(self.metadata))

