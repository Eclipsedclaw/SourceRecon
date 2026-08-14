"""统一事件领域对象。"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Optional, Sequence, Tuple

from .enums import Channel, EventTopology, SequenceClass
from .hit import DigitizedHit
from .truth import SimulationTruth


@dataclass(frozen=True)
class MeasuredEvent:
    """同一 gamma/符合窗口内的全部数字化 hit。

    `hits` 保留输入顺序和全部像素，不在此处按 layer 合并或删除 backscatter。
    零 hit 模拟 primary 也允许存在，以便响应效率分母完整。
    """

    event_id: str
    hits: Tuple[DigitizedHit, ...]
    sequence_class: SequenceClass = SequenceClass.UNKNOWN
    topology: EventTopology = EventTopology.UNKNOWN
    truth: Optional[SimulationTruth] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("MeasuredEvent.event_id 不能为空。")
        hits = tuple(self.hits)
        if any(not isinstance(hit, DigitizedHit) for hit in hits):
            raise TypeError("MeasuredEvent.hits 必须全部是 DigitizedHit。")
        sequence = (
            self.sequence_class
            if isinstance(self.sequence_class, SequenceClass)
            else SequenceClass(self.sequence_class)
        )
        topology = (
            self.topology
            if isinstance(self.topology, EventTopology)
            else EventTopology(self.topology)
        )
        object.__setattr__(self, "hits", hits)
        object.__setattr__(self, "sequence_class", sequence)
        object.__setattr__(self, "topology", topology)
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def total_deposited_energy_mev(self) -> float:
        """全部数字化 hit 的观测能量和；不等同于入射能量。"""

        return float(sum(hit.energy_mev for hit in self.hits))

    @property
    def channels(self) -> Tuple[Channel, ...]:
        """按 hit 顺序返回通道，不去重。"""

        return tuple(hit.channel for hit in self.hits)

    def hits_in_channel(self, channel: Channel) -> Tuple[DigitizedHit, ...]:
        """返回指定通道的全部 hit，不丢失同层多像素信息。"""

        selected = channel if isinstance(channel, Channel) else Channel(channel)
        return tuple(hit for hit in self.hits if hit.channel == selected)

    def observable_copy(self) -> "MeasuredEvent":
        """移除模拟真值，生成可安全传入重建核心的事件。"""

        return replace(self, truth=None)

