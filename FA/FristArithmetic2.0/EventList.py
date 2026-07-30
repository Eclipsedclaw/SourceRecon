# EventList.py

import pandas as pd

from TwoHitEvent import TwoHitEvent
from ThreeHitEvent import ThreeHitEvent


class EventList:
    """
    EventList 用来存放所有候选 event 对象。

    里面每一个元素都是：
        TwoHitEvent 对象
        或 ThreeHitEvent 对象

    它提供：
        1. 添加 event
        2. 通过 index 取 event
        3. 查看所有 event index
        4. 转成 DataFrame 方便检查
        5. 按分数排序
    """

    def __init__(self):
        self.events = []
        self.indexes = []

    def add_event(self, event):
        """
        添加一个 TwoHitEvent 或 ThreeHitEvent。
        """

        if not isinstance(event, (TwoHitEvent, ThreeHitEvent)):
            raise TypeError(
                "EventList 只能添加 TwoHitEvent 或 ThreeHitEvent 对象"
            )

        event_index = len(self.events)

        self.events.append(event)
        self.indexes.append(event_index)

        return event_index

    def __len__(self):
        return len(self.events)

    def __getitem__(self, index):
        return self.events[index]

    def get_event(self, index):
        return self.events[index]

    def get_indexes(self):
        return self.indexes

    def to_dataframe(self):
        """
        把所有 event 转成 DataFrame，方便 print、筛选、保存。
        """

        records = []

        for index, event in enumerate(self.events):
            record = event.to_dict()
            record["event_index"] = index
            records.append(record)

        return pd.DataFrame(records)

    def sort_by_score(self, descending=True):
        """
        返回按 score 排序后的 event index。
        注意：这里只返回 index，不改变 self.events 的原始顺序。
        """

        sorted_indexes = sorted(
            self.indexes,
            key=lambda idx: self.events[idx].score,
            reverse=descending,
        )

        return sorted_indexes

    def get_two_hit_events(self):
        return [
            event for event in self.events
            if isinstance(event, TwoHitEvent)
        ]

    def get_three_hit_events(self):
        return [
            event for event in self.events
            if isinstance(event, ThreeHitEvent)
        ]