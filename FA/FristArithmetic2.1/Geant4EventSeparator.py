# Geant4EventSeparator.py

import itertools
import numpy as np

from EventList import EventList
from TwoHitEvent import TwoHitEvent
from ThreeHitEvent import ThreeHitEvent


class Geant4EventSeparator:
    """
    从 Geant4 fake coincidence windows 中枚举 2-hit / 3-hit candidate。

    输入：
        windows

    输出：
        EventList

    关键点：
        同一个 window 中混合了多个 true_event_id。
        因此枚举出来的 candidate 有真有假。
    """

    def __init__(
        self,
        windows,
        min_energy=0.0,
        allow_backscatter=False,
        sigma_delta_cos=0.15,
        max_candidates_per_window=None,
    ):
        self.windows = windows
        self.min_energy = min_energy
        self.allow_backscatter = allow_backscatter
        self.sigma_delta_cos = sigma_delta_cos
        self.max_candidates_per_window = max_candidates_per_window

    def separate(self):
        event_list = EventList()

        for window in self.windows:
            window_id = window["window_id"]
            hit_df = window["hit_df"]

            hits = self._hits_from_df(hit_df)

            candidates = []

            candidates.extend(
                self._make_two_hit_events(window_id, hits)
            )

            candidates.extend(
                self._make_three_hit_events(window_id, hits)
            )

            if self.max_candidates_per_window is not None:
                candidates = candidates[:self.max_candidates_per_window]

            for event in candidates:
                event_list.add_event(event)

        return event_list

    def _hits_from_df(self, hit_df):
        hits = []

        for _, row in hit_df.iterrows():
            if float(row["energy"]) <= self.min_energy:
                continue

            hit = {
                "true_event_id": row["true_event_id"],
                "hit_id": row["hit_id"],
                "layer": int(row["layer"]),
                "channel": row["channel"],
                "pixelid": row["pixelid"],

                "x": float(row["x"]),
                "y": float(row["y"]),
                "z": float(row["z"]),
                "pos": np.array(
                    [float(row["x"]), float(row["y"]), float(row["z"])],
                    dtype=float,
                ),

                "energy": float(row["energy"]),
                "first_time_ns": row.get("first_time_ns", np.nan),
                "first_step_id": row.get("first_step_id", np.nan),
                "material": row.get("material", None),
                "chamberid": row.get("chamberid", np.nan),
            }

            hits.append(hit)

        return hits

    def _make_two_hit_events(self, window_id, hits):
        events = []

        if self.allow_backscatter:
            pairs = itertools.permutations(hits, 2)
        else:
            pairs = [
                (h1, h2)
                for h1, h2 in itertools.permutations(hits, 2)
                if h1["layer"] < h2["layer"]
            ]

        for h1, h2 in pairs:
            event = TwoHitEvent(
                event_id=f"window_{window_id}",
                hit1=h1,
                hit2=h2,
            )
            events.append(event)

        return events

    def _make_three_hit_events(self, window_id, hits):
        events = []

        if self.allow_backscatter:
            triplets = itertools.permutations(hits, 3)
        else:
            triplets = [
                (h1, h2, h3)
                for h1, h2, h3 in itertools.permutations(hits, 3)
                if h1["layer"] < h2["layer"] < h3["layer"]
            ]

        for h1, h2, h3 in triplets:
            event = ThreeHitEvent(
                event_id=f"window_{window_id}",
                hit1=h1,
                hit2=h2,
                hit3=h3,
                sigma_delta_cos=self.sigma_delta_cos,
            )
            events.append(event)

        return events
