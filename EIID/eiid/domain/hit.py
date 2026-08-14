"""数字化 hit 领域对象。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

import numpy as np

from .enums import Channel


@dataclass(frozen=True)
class DigitizedHit:
    """一个已经完成沉积聚合和数字化的可观测 hit。

    本对象既可由 Geant4 数字化器产生，也可由实验输入适配器产生。模拟特有
    真值不得放入本对象的必需字段。
    """

    hit_id: str
    channel: Channel
    layer: int
    pixel_id: str
    position_mm: np.ndarray
    energy_mev: float
    time_ns: Optional[float] = None
    energy_sigma_mev: Optional[float] = None
    position_sigma_mm: Optional[float] = None
    is_valid_readout: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.hit_id:
            raise ValueError("DigitizedHit.hit_id 不能为空。")
        channel = self.channel if isinstance(self.channel, Channel) else Channel(self.channel)
        if int(self.layer) < 0:
            raise ValueError("DigitizedHit.layer 不能为负。")
        position = np.asarray(self.position_mm, dtype=float).copy()
        if position.shape != (3,) or not np.all(np.isfinite(position)):
            raise ValueError("DigitizedHit.position_mm 必须是三个有限数字。")
        energy = float(self.energy_mev)
        if not np.isfinite(energy) or energy < 0.0:
            raise ValueError("DigitizedHit.energy_mev 必须是非负有限值。")
        for label, value in (
            ("time_ns", self.time_ns),
            ("energy_sigma_mev", self.energy_sigma_mev),
            ("position_sigma_mm", self.position_sigma_mm),
        ):
            if value is not None and not np.isfinite(float(value)):
                raise ValueError(label + " 必须为有限值或 None。")
        if self.energy_sigma_mev is not None and self.energy_sigma_mev < 0.0:
            raise ValueError("energy_sigma_mev 不能为负。")
        if self.position_sigma_mm is not None and self.position_sigma_mm < 0.0:
            raise ValueError("position_sigma_mm 不能为负。")
        position.setflags(write=False)
        object.__setattr__(self, "channel", channel)
        object.__setattr__(self, "layer", int(self.layer))
        object.__setattr__(self, "pixel_id", str(self.pixel_id))
        object.__setattr__(self, "position_mm", position)
        object.__setattr__(self, "energy_mev", energy)
        object.__setattr__(self, "metadata", dict(self.metadata))

