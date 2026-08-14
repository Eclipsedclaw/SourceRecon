"""把统一事件集合批量转换为稀疏联合响应。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence, Tuple

from eiid.domain import EnergyGrid, MeasuredEvent

from .base import EventResponseModel
from .sparse import SparseEventResponse


@dataclass(frozen=True)
class EventKernelBatch:
    """一批事件响应及不可解释事件的显式统计。"""

    responses: Tuple[SparseEventResponse, ...]
    supported_event_ids: Tuple[str, ...]
    unsupported_event_ids: Tuple[str, ...]
    summary: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "responses", tuple(self.responses))
        object.__setattr__(
            self, "supported_event_ids", tuple(self.supported_event_ids)
        )
        object.__setattr__(
            self, "unsupported_event_ids", tuple(self.unsupported_event_ids)
        )
        object.__setattr__(self, "summary", dict(self.summary))


class EventKernelBuilder:
    """应用同一响应模型构建事件核，不读取文件也不执行 MLEM。"""

    def __init__(self, response_model: EventResponseModel, sky_grid, energy_grid: EnergyGrid):
        self.response_model = response_model
        self.sky_grid = sky_grid
        self.energy_grid = energy_grid

    def build(self, events: Sequence[MeasuredEvent]) -> EventKernelBatch:
        items = tuple(events)
        directions = self.sky_grid.all_pixel_directions()
        responses = tuple(
            self.response_model.evaluate(event, directions, self.energy_grid)
            for event in items
        )
        supported = tuple(
            response.event_id
            for response in responses
            if response.nonzero_count > 0
        )
        unsupported = tuple(
            response.event_id
            for response in responses
            if response.nonzero_count == 0
        )
        nonzero_counts = [response.nonzero_count for response in responses]
        return EventKernelBatch(
            responses=responses,
            supported_event_ids=supported,
            unsupported_event_ids=unsupported,
            summary={
                "event_count": len(items),
                "supported_event_count": len(supported),
                "unsupported_event_count": len(unsupported),
                "total_sparse_cell_count": int(sum(nonzero_counts)),
                "maximum_event_sparse_cell_count": int(
                    max(nonzero_counts) if nonzero_counts else 0
                ),
                "response_model_id": self.response_model.model_id,
                "response_semantics": self.response_model.response_semantics,
            },
        )
