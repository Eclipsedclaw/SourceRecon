from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import numpy as np


class DepositionClass(str, Enum):
    """当前能量假设对事件末态的解释。"""

    FULL = "full"
    ESCAPE = "escape"
    GEOMETRY_RECOVERED = "geometry_recovered"


@dataclass(frozen=True)
class Hit:
    """
    一个已经完成 step-to-hit 聚合的可观测 hit。

    true_event_id 和 truth_order 只用于 Geant4 分组与开发期固定顺序，
    不能用于推断能量或全吸收类型。
    """

    hit_id: str
    event_id: str
    channel: str
    layer: int
    pixel_id: str
    position_mm: np.ndarray
    energy_mev: float
    time_ns: Optional[float] = None
    truth_order: Optional[float] = None
    true_event_id: Optional[str] = None
    metadata: Dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        position = np.asarray(self.position_mm, dtype=float)
        if position.shape != (3,):
            raise ValueError("Hit.position_mm 必须是长度为 3 的向量。")
        if not np.all(np.isfinite(position)):
            raise ValueError("Hit.position_mm 含非有限值。")
        if not np.isfinite(self.energy_mev) or self.energy_mev <= 0.0:
            raise ValueError("Hit.energy_mev 必须为正有限值。")
        object.__setattr__(self, "position_mm", position)


@dataclass(frozen=True)
class MeasuredEvent:
    """
    同一条 gamma 在同一瞬间留下的全部可见 hit。

    用户给出的实验条件保证同一时间至多一条 gamma，因此实验 EventID
    可以直接用于分组；Geant4 则使用 true eventID。这里不再进行旧程序的
    fake coincidence window 或多 gamma matching。
    """

    event_id: str
    hits: List[Hit]
    attitude_time_ns: Optional[float] = None

    @property
    def n_hits(self) -> int:
        return len(self.hits)

    @property
    def total_deposited_energy_mev(self) -> float:
        return float(sum(hit.energy_mev for hit in self.hits))

    @property
    def terminal_channel(self) -> str:
        return self.hits[-1].channel

    def ordered(self, mode: str) -> "MeasuredEvent":
        """
        返回按指定规则排序的新事件。

        layer：
            按 layer 递增，适合当前不考虑 backscatter 的实验基线。
        truth：
            按 Geant4 first step/order 排序，仅用于模拟开发。
        """

        if mode == "layer":
            key = lambda hit: (
                hit.layer,
                (
                    float(hit.truth_order)
                    if hit.truth_order is not None
                    and np.isfinite(hit.truth_order)
                    else 0.0
                ),
            )
        elif mode == "truth":
            if any(
                hit.truth_order is None
                or not np.isfinite(hit.truth_order)
                for hit in self.hits
            ):
                raise ValueError(
                    "event " + self.event_id + " 缺少 truth_order，不能按 truth 排序。"
                )
            key = lambda hit: float(hit.truth_order)
        else:
            raise ValueError("未知事件排序模式：" + str(mode))

        return MeasuredEvent(
            event_id=self.event_id,
            hits=sorted(self.hits, key=key),
            attitude_time_ns=self.attitude_time_ns,
        )

    def collapsed_by_layer(self) -> "MeasuredEvent":
        """
        把同一 detector layer 的多个 pixel hit 合成一个有效 layer hit。

        当前 SOE1 不重建同一层内部多个相互作用的先后顺序。直接把这些
        pixel 当成有序 Compton hit 会制造不存在的几何信息，因此保守地：

            能量求和；
            位置取沉积能量加权质心；
            时间/辅助顺序取最早值。

        该近似保持总沉积能量，并保证当前三层硬件至多生成 3-hit 事件。
        """

        by_layer: Dict[int, List[Hit]] = {}
        for hit in self.hits:
            by_layer.setdefault(hit.layer, []).append(hit)

        collapsed_hits: List[Hit] = []
        for layer, layer_hits in sorted(by_layer.items()):
            if len(layer_hits) == 1:
                collapsed_hits.append(layer_hits[0])
                continue

            energies = np.asarray(
                [hit.energy_mev for hit in layer_hits],
                dtype=float,
            )
            positions = np.asarray(
                [hit.position_mm for hit in layer_hits],
                dtype=float,
            )
            total_energy = float(energies.sum())
            finite_times = [
                float(hit.time_ns)
                for hit in layer_hits
                if hit.time_ns is not None and np.isfinite(hit.time_ns)
            ]
            finite_orders = [
                float(hit.truth_order)
                for hit in layer_hits
                if hit.truth_order is not None
                and np.isfinite(hit.truth_order)
            ]
            collapsed_hits.append(
                Hit(
                    hit_id=(
                        self.event_id
                        + "_layer_"
                        + str(layer)
                        + "_combined"
                    ),
                    event_id=self.event_id,
                    channel=layer_hits[0].channel,
                    layer=layer,
                    pixel_id="combined:" + ",".join(
                        hit.pixel_id for hit in layer_hits
                    ),
                    position_mm=np.average(
                        positions,
                        axis=0,
                        weights=energies,
                    ),
                    energy_mev=total_energy,
                    time_ns=min(finite_times) if finite_times else None,
                    truth_order=min(finite_orders) if finite_orders else None,
                    true_event_id=layer_hits[0].true_event_id,
                    metadata={
                        "combined_pixel_hit_count": len(layer_hits),
                        "combined_hit_ids": [
                            hit.hit_id for hit in layer_hits
                        ],
                    },
                )
            )

        return MeasuredEvent(
            event_id=self.event_id,
            hits=collapsed_hits,
            attitude_time_ns=self.attitude_time_ns,
        )


@dataclass(frozen=True)
class InputDataset:
    """所有 IO 实现向重建流程返回的统一数据对象。"""

    imaging_events: List[MeasuredEvent]
    spectroscopy_events: List[MeasuredEvent]
    rejected_events: List[MeasuredEvent]
    summary: Dict[str, object]


@dataclass(frozen=True)
class EnergyHypothesis:
    """
    某事件的一种入射能量/沉积类型解释。

    weight 是已经包含全局能谱、探测器响应和运动学合法性的未归一化权重。
    """

    incident_energy_mev: float
    deposition_class: DepositionClass
    scatter_angle_rad: float
    arm_sigma_rad: float
    weight: float
    diagnostics: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class EventKernel:
    """
    一个可成像事件的完整独立 proposal kernel。

    axis_detector 指向源一侧，即 -normalize(r2-r1)。每个能量假设对应
    不同的康普顿圆半顶角。
    """

    event: MeasuredEvent
    axis_detector: np.ndarray
    hypotheses: List[EnergyHypothesis]

    def __post_init__(self) -> None:
        axis = np.asarray(self.axis_detector, dtype=float)
        norm = np.linalg.norm(axis)
        if axis.shape != (3,) or norm <= 0.0:
            raise ValueError("EventKernel.axis_detector 必须是非零三维向量。")
        if not self.hypotheses:
            raise ValueError("EventKernel 至少需要一个能量假设。")
        object.__setattr__(self, "axis_detector", axis / norm)


@dataclass
class EventState:
    """马尔可夫链中一个事件当前占据的隐状态。"""

    event_index: int
    hypothesis_index: int
    direction_detector: np.ndarray
    direction_sky: np.ndarray
    pixel_index: int
