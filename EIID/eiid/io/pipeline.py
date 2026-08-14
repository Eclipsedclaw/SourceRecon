"""输入与触发的高层边界，不涉及重建算法。"""

from __future__ import annotations

from ..detector import TriggerPolicy
from .base import EventSource, IngestedDataset


class EventIngestionPipeline:
    """读取全部事件后应用独立 TriggerPolicy，且不删除拒绝事件。"""

    def __init__(self, source: EventSource, trigger_policy: TriggerPolicy):
        self.source = source
        self.trigger_policy = trigger_policy

    def run(self) -> IngestedDataset:
        dataset = self.source.read()
        accepted = []
        rejected = []
        decisions = {}
        for event in dataset.events:
            decision = self.trigger_policy.evaluate(event)
            decisions[event.event_id] = decision
            (accepted if decision.accepted else rejected).append(event)
        return IngestedDataset(
            dataset=dataset,
            accepted_events=tuple(accepted),
            rejected_events=tuple(rejected),
            decisions=decisions,
        )

