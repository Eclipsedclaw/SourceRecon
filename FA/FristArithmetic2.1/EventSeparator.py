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

    输入：
        final_df

    输出：
        EventList 对象

    注意：
        EventSeparator 本身不保存复杂 event 信息；
        复杂信息都交给 TwoHitEvent / ThreeHitEvent 保存。
    """

    def __init__(
        self,
        final_df,
        channels=("ch2", "ch1", "ch0"),
        channel_to_layer=None,
        min_energy=0.0,
        allow_backscatter=False,
        sigma_delta_cos=0.15,
    ):
        self.final_df = final_df
        self.channels = list(channels)
        self.channel_to_layer = channel_to_layer or {
            "ch2": 0,
            "ch1": 1,
            "ch0": 2,
        }

        self.min_energy = min_energy
        self.allow_backscatter = allow_backscatter
        self.sigma_delta_cos = sigma_delta_cos

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
            hits = self._extract_hits_from_row(row)

            if len(hits) < 2:
                continue

            self._add_two_hit_events(event_list, row["EventID"], hits)

            if len(hits) >= 3:
                self._add_three_hit_events(event_list, row["EventID"], hits)

        return event_list

    def _extract_hits_from_row(self, row):
        """
        从 final_df 的一行里提取 ch0/ch1/ch2 hit。

        返回：
            hits: list[dict]
        """

        hits = []

        for channel in self.channels:
            if not self._channel_has_hit(row, channel):
                continue

            if channel not in self.channel_to_layer:
                raise ValueError("缺少 channel_to_layer 映射：" + str(channel))

            layer_id = int(self.channel_to_layer[channel])

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
                "material": "LYSO" if channel == "ch0" else "YSO",
            }

            hit["hit_id"] = (
                f"{hit['event_id']}_"
                f"{hit['channel']}_"
                f"{hit['pixelid']}"
            )

            hits.append(hit)

        return hits

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
            )

            event_list.add_event(event)
