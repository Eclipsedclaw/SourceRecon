# EventSeparator.py

import itertools
import numpy as np
import pandas as pd

from TwoHitEvent import TwoHitEvent
from ThreeHitEvent import ThreeHitEvent
from EventList import EventList


class EventSeparator:
    """
    从 final_df 中划分候选 2-hit / 3-hit event。

    相比旧版本的变化：
        1. 新增 resolution_model 参数，透传给 ThreeHitEvent，
           启用逐事件误差传播和 pull 打分；
        2. extract_hits_from_row 改为公开方法，
           供 MixedEventBackground 复用同一套 hit 提取逻辑；
        3. min_energy 建议设为真实噪声阈值（比如 0.02 MeV），
           低能噪声 hit 会污染 E_total 并制造假 3-hit。
    """

    def __init__(
        self,
        final_df,
        channels=("ch0", "ch1", "ch2"),
        min_energy=0.0,
        allow_backscatter=False,
        sigma_delta_cos=0.15,
        resolution_model=None,
    ):
        self.final_df = final_df
        self.channels = list(channels)

        self.min_energy = min_energy
        self.allow_backscatter = allow_backscatter
        self.sigma_delta_cos = sigma_delta_cos
        self.resolution_model = resolution_model

    def separate(self):
        """
        主函数。

        遍历 final_df 的每一行；
        从每一行里提取 hit；
        枚举 2-hit 和 3-hit event；
        返回 EventList。
        """

        event_list = EventList()

        for _, row in self.final_df.iterrows():
            hits = self.extract_hits_from_row(row)

            if len(hits) < 2:
                continue

            self._add_two_hit_events(event_list, row["EventID"], hits)

            if len(hits) >= 3:
                self._add_three_hit_events(event_list, row["EventID"], hits)

        return event_list

    def extract_hits_from_row(self, row):
        """
        从 final_df 的一行里提取 ch0/ch1/ch2 hit。

        公开方法：MixedEventBackground 也会调用它，
        保证真实事件和混合本底使用完全一致的 hit 定义。

        返回：
            hits: list[dict]
        """

        hits = []

        for layer_id, channel in enumerate(self.channels):
            if not self._channel_has_hit(row, channel):
                continue

            hit = {
                "event_id": row["EventID"],
                "channel": channel,
                "layer": layer_id,

                "pixelid": row[f"{channel}_pixelid"],

                "x": float(row[f"{channel}_x"]),
                "y": float(row[f"{channel}_y"]),
                "z": float(row[f"{channel}_z"]),
                "pos": np.array(
                    [
                        float(row[f"{channel}_x"]),
                        float(row[f"{channel}_y"]),
                        float(row[f"{channel}_z"]),
                    ],
                    dtype=float,
                ),

                "energy": float(row[f"{channel}_energy"]),
            }

            hit["hit_id"] = (
                f"{hit['event_id']}_"
                f"{hit['channel']}_"
                f"{hit['pixelid']}"
            )

            hits.append(hit)

        return hits

    # 兼容旧代码的私有名
    def _extract_hits_from_row(self, row):
        return self.extract_hits_from_row(row)

    def _channel_has_hit(self, row, channel):
        """
        判断某个 channel 在这一行中是否有有效 hit。
        """

        required_columns = [
            f"{channel}_pixelid",
            f"{channel}_x",
            f"{channel}_y",
            f"{channel}_z",
            f"{channel}_energy",
        ]

        for col in required_columns:
            if col not in row.index:
                return False

            if pd.isna(row[col]):
                return False

        if row[f"{channel}_energy"] <= self.min_energy:
            return False

        return True

    def _add_two_hit_events(self, event_list, event_id, hits):
        """
        枚举并添加 2-hit event。
        """

        if self.allow_backscatter:
            hit_pairs = itertools.permutations(hits, 2)
        else:
            hit_pairs = [
                (h1, h2)
                for h1, h2 in itertools.permutations(hits, 2)
                if h1["layer"] < h2["layer"]
            ]

        for hit1, hit2 in hit_pairs:
            event = TwoHitEvent(
                event_id=event_id,
                hit1=hit1,
                hit2=hit2,
                resolution_model=self.resolution_model,
            )

            event_list.add_event(event)

    def _add_three_hit_events(self, event_list, event_id, hits):
        """
        枚举并添加 3-hit event。
        """

        if self.allow_backscatter:
            hit_triplets = itertools.permutations(hits, 3)
        else:
            ordered_hits = sorted(hits, key=lambda h: h["layer"])
            hit_triplets = [tuple(ordered_hits)]

        for hit1, hit2, hit3 in hit_triplets:
            event = ThreeHitEvent(
                event_id=event_id,
                hit1=hit1,
                hit2=hit2,
                hit3=hit3,
                sigma_delta_cos=self.sigma_delta_cos,
                resolution_model=self.resolution_model,
            )

            event_list.add_event(event)