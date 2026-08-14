"""输入源抽象接口及触发后的数据集视图。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Mapping, Tuple

from ..detector import TriggerDecision
from ..domain import EventDataset, MeasuredEvent


class EventSource(ABC):
    """所有输入源都返回统一 `EventDataset`。"""

    @abstractmethod
    def read(self) -> EventDataset:
        raise NotImplementedError


@dataclass(frozen=True)
class IngestedDataset:
    """保留全部输入事件，同时提供触发接受/拒绝视图和逐事件决定。"""

    dataset: EventDataset
    accepted_events: Tuple[MeasuredEvent, ...]
    rejected_events: Tuple[MeasuredEvent, ...]
    decisions: Mapping[str, TriggerDecision]

    def __post_init__(self) -> None:
        object.__setattr__(self, "accepted_events", tuple(self.accepted_events))
        object.__setattr__(self, "rejected_events", tuple(self.rejected_events))
        object.__setattr__(self, "decisions", dict(self.decisions))

