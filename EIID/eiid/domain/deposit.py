"""Geant4 step 聚合后的物理沉积对象。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

import numpy as np


@dataclass(frozen=True)
class DetectorDeposit:
    """同一 event、chamber、pixel 内全部正沉积 step 的聚合结果。

    它还不是实验 hit：能量展宽、噪声、阈值和坏道等数字化处理尚未应用。
    """

    event_id: str
    chamber_id: int
    pixel_id: str
    total_edep_mev: float
    energy_weighted_position_mm: np.ndarray
    earliest_time_ns: Optional[float] = None
    earliest_step_order: Optional[float] = None
    step_count: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("DetectorDeposit.event_id 不能为空。")
        energy = float(self.total_edep_mev)
        if not np.isfinite(energy) or energy <= 0.0:
            raise ValueError("DetectorDeposit.total_edep_mev 必须为正有限值。")
        position = np.asarray(self.energy_weighted_position_mm, dtype=float).copy()
        if position.shape != (3,) or not np.all(np.isfinite(position)):
            raise ValueError("energy_weighted_position_mm 必须是三个有限数字。")
        if int(self.step_count) <= 0:
            raise ValueError("DetectorDeposit.step_count 必须大于 0。")
        for label, value in (
            ("earliest_time_ns", self.earliest_time_ns),
            ("earliest_step_order", self.earliest_step_order),
        ):
            if value is not None and not np.isfinite(float(value)):
                raise ValueError(label + " 必须为有限值或 None。")
        position.setflags(write=False)
        object.__setattr__(self, "chamber_id", int(self.chamber_id))
        object.__setattr__(self, "pixel_id", str(self.pixel_id))
        object.__setattr__(self, "total_edep_mev", energy)
        object.__setattr__(self, "energy_weighted_position_mm", position)
        object.__setattr__(self, "step_count", int(self.step_count))
        object.__setattr__(self, "metadata", dict(self.metadata))

