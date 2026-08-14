from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from ..domain import Hit, InputDataset, MeasuredEvent
from .base import EventSource


class Geant4RootEventSource(EventSource):
    """
    从 Geant4 ROOT step 表构造 pixel 级 hit 与同 gamma 事件。

    聚合键为 eventID + chamberID + pixelID；位置取沉积能量加权平均，
    能量取 step 的 eDep 求和。primary energy 不会进入重建对象，避免把
    模拟真值泄漏到未知能源算法。
    """

    def __init__(
        self,
        root_path: Path,
        tree_name: Optional[str],
        branches: Dict[str, Optional[str]],
        chamber_to_layer: Dict[int, int],
        layer_to_channel: Dict[int, str],
        dataset_id: str = "geant4",
        order_mode: str = "layer",
        spectroscopy_channel: str = "ch0",
        minimum_hit_energy_mev: float = 0.0,
    ):
        self.root_path = root_path
        self.tree_name = tree_name
        self.branches = branches
        self.chamber_to_layer = chamber_to_layer
        self.layer_to_channel = layer_to_channel
        self.dataset_id = dataset_id
        self.order_mode = order_mode
        self.spectroscopy_channel = spectroscopy_channel
        self.minimum_hit_energy_mev = float(minimum_hit_energy_mev)

    def read(self) -> InputDataset:
        if not self.root_path.exists():
            raise FileNotFoundError("找不到 Geant4 ROOT：" + str(self.root_path))

        try:
            import uproot
        except ImportError as exc:
            raise ImportError(
                "读取 Geant4 ROOT 需要 uproot：pip install uproot awkward"
            ) from exc

        with uproot.open(self.root_path) as root_file:
            tree_name = self.tree_name or self._find_first_tree(root_file)
            tree = root_file[tree_name]
            frame = self._read_step_frame(tree)
        hits = self._aggregate_steps(frame)
        events = self._group_events(hits)
        imaging, spectroscopy, rejected = self._classify_events(events)

        deposited_before = float(frame["energy_mev"].sum())
        deposited_after = float(sum(hit.energy_mev for hit in hits))
        tolerance = max(1e-10, abs(deposited_before) * 1e-10)
        if abs(deposited_before - deposited_after) > tolerance:
            raise RuntimeError(
                "Geant4 step-to-hit 聚合前后能量不守恒："
                + str(deposited_before)
                + " vs "
                + str(deposited_after)
            )

        return InputDataset(
            imaging_events=imaging,
            spectroscopy_events=spectroscopy,
            rejected_events=rejected,
            summary={
                "source_type": "geant4_root",
                "root_path": str(self.root_path),
                "tree_name": tree_name,
                "positive_energy_step_count": len(frame),
                "hit_count": len(hits),
                "event_count": len(events),
                "imaging_event_count": len(imaging),
                "spectroscopy_event_count": len(spectroscopy),
                "rejected_event_count": len(rejected),
                "order_mode": self.order_mode,
            },
        )

    def _read_step_frame(self, tree) -> pd.DataFrame:
        required_keys = [
            "event_id",
            "chamber_id",
            "pixel_id",
            "energy_mev",
            "x_mm",
            "y_mm",
            "z_mm",
        ]
        missing_config = [
            key for key in required_keys if not self.branches.get(key)
        ]
        if missing_config:
            raise KeyError(
                "Geant4 branches 配置缺少：" + ", ".join(missing_config)
            )

        requested = {
            branch_name
            for branch_name in self.branches.values()
            if branch_name is not None
        }
        available = {str(name).split(";")[0] for name in tree.keys()}
        missing_branches = sorted(requested - available)
        if missing_branches:
            raise KeyError(
                "ROOT tree 缺少 branches：" + ", ".join(missing_branches)
            )

        arrays = tree.arrays(sorted(requested), library="np", how=dict)
        frame = pd.DataFrame(
            {
                "event_id_raw": np.asarray(
                    arrays[self.branches["event_id"]]
                ),
                "chamber_id": np.asarray(
                    arrays[self.branches["chamber_id"]], dtype=int
                ),
                "pixel_id": np.asarray(arrays[self.branches["pixel_id"]]),
                "energy_mev": np.asarray(
                    arrays[self.branches["energy_mev"]], dtype=float
                ),
                "x_mm": np.asarray(
                    arrays[self.branches["x_mm"]], dtype=float
                ),
                "y_mm": np.asarray(
                    arrays[self.branches["y_mm"]], dtype=float
                ),
                "z_mm": np.asarray(
                    arrays[self.branches["z_mm"]], dtype=float
                ),
            }
        )

        frame["step_order"] = self._optional_array(
            arrays,
            self.branches.get("step_id"),
            len(frame),
        )
        frame["time_ns"] = self._optional_array(
            arrays,
            self.branches.get("time_ns"),
            len(frame),
        )
        frame = frame.loc[
            np.isfinite(frame["energy_mev"])
            & (frame["energy_mev"] > self.minimum_hit_energy_mev)
        ].copy()

        unknown_chambers = sorted(
            set(frame["chamber_id"].unique()) - set(self.chamber_to_layer)
        )
        if unknown_chambers:
            raise ValueError(
                "chamber_to_layer 未覆盖 chamberID："
                + ", ".join(map(str, unknown_chambers))
            )

        frame["event_id"] = frame["event_id_raw"].map(
            lambda value: self.dataset_id + ":" + str(value)
        )
        frame["layer"] = frame["chamber_id"].map(self.chamber_to_layer)
        frame["channel"] = frame["layer"].map(self.layer_to_channel)
        if frame["channel"].isna().any():
            raise ValueError("layer_to_channel 没有覆盖全部 layer。")
        return frame

    def _aggregate_steps(self, frame: pd.DataFrame) -> List[Hit]:
        hits: List[Hit] = []
        group_columns = ["event_id", "chamber_id", "pixel_id"]

        for hit_index, (group_key, group) in enumerate(
            frame.groupby(group_columns, sort=False)
        ):
            event_id, chamber_id, pixel_id = group_key
            energies = group["energy_mev"].to_numpy(dtype=float)
            total_energy = float(energies.sum())
            position = np.average(
                group[["x_mm", "y_mm", "z_mm"]].to_numpy(dtype=float),
                axis=0,
                weights=energies,
            )
            order_values = group["step_order"].to_numpy(dtype=float)
            finite_orders = order_values[np.isfinite(order_values)]
            time_values = group["time_ns"].to_numpy(dtype=float)
            finite_times = time_values[np.isfinite(time_values)]
            layer = int(self.chamber_to_layer[int(chamber_id)])

            hits.append(
                Hit(
                    hit_id=self.dataset_id + "_hit_" + str(hit_index),
                    event_id=str(event_id),
                    channel=self.layer_to_channel[layer],
                    layer=layer,
                    pixel_id=str(pixel_id),
                    position_mm=position,
                    energy_mev=total_energy,
                    time_ns=(
                        float(finite_times.min())
                        if finite_times.size
                        else None
                    ),
                    truth_order=(
                        float(finite_orders.min())
                        if finite_orders.size
                        else None
                    ),
                    true_event_id=str(event_id),
                    metadata={
                        "chamber_id": int(chamber_id),
                        "step_count": int(len(group)),
                    },
                )
            )
        return hits

    def _group_events(self, hits: List[Hit]) -> List[MeasuredEvent]:
        grouped: Dict[str, List[Hit]] = {}
        for hit in hits:
            grouped.setdefault(hit.event_id, []).append(hit)

        events = []
        for event_id, event_hits in grouped.items():
            finite_times = [
                float(hit.time_ns)
                for hit in event_hits
                if hit.time_ns is not None and np.isfinite(hit.time_ns)
            ]
            event = MeasuredEvent(
                event_id=event_id,
                hits=event_hits,
                attitude_time_ns=min(finite_times) if finite_times else None,
            ).collapsed_by_layer().ordered(self.order_mode)
            events.append(event)
        events.sort(key=lambda event: event.event_id)
        return events

    def _classify_events(self, events):
        imaging = []
        spectroscopy = []
        rejected = []
        for event in events:
            if all(
                hit.channel == self.spectroscopy_channel
                for hit in event.hits
            ):
                spectroscopy.append(event)
            elif event.n_hits >= 2 and self._is_cross_layer(event):
                imaging.append(event)
            else:
                rejected.append(event)
        return imaging, spectroscopy, rejected

    @staticmethod
    def _is_cross_layer(event: MeasuredEvent) -> bool:
        if len({hit.layer for hit in event.hits}) < 2:
            return False
        first = event.hits[0].position_mm
        return any(
            np.linalg.norm(hit.position_mm - first) > 0.0
            for hit in event.hits[1:]
        )

    @staticmethod
    def _optional_array(arrays, branch_name, length):
        if branch_name is None:
            return np.full(length, np.nan, dtype=float)
        return np.asarray(arrays[branch_name], dtype=float)

    @staticmethod
    def _find_first_tree(root_file) -> str:
        for name, obj in root_file.items():
            if hasattr(obj, "arrays") and hasattr(obj, "num_entries"):
                return str(name).split(";")[0]
        raise RuntimeError("ROOT 文件中没有找到可读取的 TTree。")
