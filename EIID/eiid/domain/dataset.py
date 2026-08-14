"""事件集合和数据集级元数据。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

from .event import MeasuredEvent


@dataclass(frozen=True)
class DatasetMetadata:
    """不依赖文件名猜测的通用数据集元数据。"""

    dataset_id: str
    source_type: str
    schema_version: str
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.dataset_id or not self.source_type or not self.schema_version:
            raise ValueError("dataset_id/source_type/schema_version 不能为空。")
        object.__setattr__(self, "attributes", dict(self.attributes))


@dataclass(frozen=True)
class EventDataset:
    """模拟和实验输入接口共同返回的领域对象。"""

    events: Tuple[MeasuredEvent, ...]
    metadata: DatasetMetadata
    summary: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        events = tuple(self.events)
        if any(not isinstance(event, MeasuredEvent) for event in events):
            raise TypeError("EventDataset.events 必须全部是 MeasuredEvent。")
        ids = [event.event_id for event in events]
        if len(ids) != len(set(ids)):
            raise ValueError("EventDataset 中 event_id 必须唯一。")
        object.__setattr__(self, "events", events)
        object.__setattr__(self, "summary", dict(self.summary))

    def observable_copy(self) -> "EventDataset":
        """移除全部事件真值，作为重建输入边界。"""

        return EventDataset(
            events=tuple(event.observable_copy() for event in self.events),
            metadata=self.metadata,
            summary=self.summary,
        )

