"""物理沉积到统一 digitized hit/event 的可替换数字化接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Iterable, Mapping, Optional, Tuple

from ..domain import (
    Channel,
    DetectorDeposit,
    DigitizedHit,
    EventTopology,
    MeasuredEvent,
    SequenceClass,
)
from .channel_map import ChannelMapping


class Digitizer(ABC):
    """数字化模型抽象接口；响应库必须记录具体实现及版本。"""

    version = "abstract"

    @abstractmethod
    def digitize(
        self,
        deposit: DetectorDeposit,
        channel: Channel,
        layer: int,
    ) -> Optional[DigitizedHit]:
        """把一个物理沉积转换为 hit；不可见时可返回 None。"""

        raise NotImplementedError


class TruthDigitizer(Digitizer):
    """无展宽、无噪声的物理检查数字化器。

    它保留所有正沉积，不能用于宣称真实飞行触发效率。真实阈值仍由独立的
    `TriggerPolicy` 应用。
    """

    version = "truth_digitizer_v1"

    def digitize(
        self,
        deposit: DetectorDeposit,
        channel: Channel,
        layer: int,
    ) -> DigitizedHit:
        return DigitizedHit(
            hit_id=(
                deposit.event_id
                + ":"
                + channel.value
                + ":pixel:"
                + deposit.pixel_id
            ),
            channel=channel,
            layer=layer,
            pixel_id=deposit.pixel_id,
            position_mm=deposit.energy_weighted_position_mm,
            energy_mev=deposit.total_edep_mev,
            time_ns=deposit.earliest_time_ns,
            is_valid_readout=True,
            metadata={
                "digitizer_version": self.version,
                "chamber_id": deposit.chamber_id,
                "step_count": deposit.step_count,
                "earliest_step_order": deposit.earliest_step_order,
            },
        )


class DigitizedEventBuilder:
    """按 eventID 聚合 deposit，并使用指定数字化器生成统一事件。"""

    def __init__(self, mapping: ChannelMapping, digitizer: Digitizer):
        self.mapping = mapping
        self.digitizer = digitizer

    def build(self, deposits: Iterable[DetectorDeposit]) -> Tuple[MeasuredEvent, ...]:
        by_event = defaultdict(list)
        for deposit in deposits:
            channel = self.mapping.channel_for_chamber(deposit.chamber_id)
            layer = self.mapping.layer_for_channel(channel)
            hit = self.digitizer.digitize(deposit, channel, layer)
            if hit is not None:
                by_event[deposit.event_id].append(hit)

        events = []
        for event_id, hits in by_event.items():
            # 保留原始像素 hit，只按可用的 step/time 辅助量提供稳定输入顺序。
            ordered = sorted(
                hits,
                key=lambda hit: (
                    float("inf")
                    if hit.time_ns is None
                    else float(hit.time_ns),
                    hit.layer,
                    hit.hit_id,
                ),
            )
            topology = (
                EventTopology.TWO_HIT
                if len(ordered) == 2
                else EventTopology.THREE_OR_MORE_HIT
                if len(ordered) >= 3
                else EventTopology.UNKNOWN
            )
            events.append(
                MeasuredEvent(
                    event_id=event_id,
                    hits=tuple(ordered),
                    sequence_class=SequenceClass.UNKNOWN,
                    topology=topology,
                    metadata={"digitizer_version": self.digitizer.version},
                )
            )
        events.sort(key=lambda event: event.event_id)
        return tuple(events)

