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
        requested = self._validate_tree(tree)
        arrays = tree.arrays(sorted(requested), library="np", how=dict)
        return self._arrays_to_step_frame(arrays)

    def _validate_tree(self, tree):
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
        return requested

    def _arrays_to_step_frame(self, arrays) -> pd.DataFrame:
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

        for group_key, group in frame.groupby(group_columns, sort=False):
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
                    hit_id=(
                        str(event_id)
                        + "_chamber_"
                        + str(chamber_id)
                        + "_pixel_"
                        + str(pixel_id)
                    ),
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


class _ReservoirSampler:
    """
    对未知长度事件流执行等概率蓄水池抽样。

    这样每个文件即使包含千万级 EventID，也只在内存中保留配置指定数量
    的事件；被保留的每个事件拥有相同概率，不偏向 ROOT 文件开头。
    """

    def __init__(self, maximum_count, random_generator):
        self.maximum_count = (
            None if maximum_count is None else int(maximum_count)
        )
        if self.maximum_count is not None and self.maximum_count <= 0:
            raise ValueError("事件抽样上限必须为正整数或 null。")
        self.random_generator = random_generator
        self.items = []
        self.total_seen = 0

    def add(self, item) -> None:
        self.total_seen += 1
        if self.maximum_count is None:
            self.items.append(item)
            return
        if len(self.items) < self.maximum_count:
            self.items.append(item)
            return

        candidate = int(self.random_generator.integers(0, self.total_seen))
        if candidate < self.maximum_count:
            self.items[candidate] = item


class StreamingGeant4RootEventSource(Geant4RootEventSource):
    """
    面向大型 Geant4 ROOT 的流式事件源。

    ROOT 按 step 分块读取。由于同一个 EventID 可能跨越两个分块，程序会
    暂存每块末尾的 EventID，并在下一块到来后再聚合。为保证这个边界逻辑
    正确，输入中的 eventID 必须单调不下降（标准 Geant4 输出通常如此）。
    """

    def __init__(
        self,
        *args,
        uproot_step_size="250 MB",
        maximum_imaging_events=None,
        maximum_spectroscopy_events=None,
        sampling_seed=20260730,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.uproot_step_size = uproot_step_size
        self.maximum_imaging_events = maximum_imaging_events
        self.maximum_spectroscopy_events = maximum_spectroscopy_events
        self.sampling_seed = int(sampling_seed)

    def read(self) -> InputDataset:
        if not self.root_path.exists():
            raise FileNotFoundError("找不到 Geant4 ROOT：" + str(self.root_path))

        try:
            import uproot
        except ImportError as exc:
            raise ImportError(
                "读取 Geant4 ROOT 需要 uproot：pip install uproot awkward"
            ) from exc

        random_generator = np.random.default_rng(self.sampling_seed)
        imaging_sampler = _ReservoirSampler(
            self.maximum_imaging_events,
            random_generator,
        )
        spectroscopy_sampler = _ReservoirSampler(
            self.maximum_spectroscopy_events,
            random_generator,
        )
        rejected_count = 0
        positive_step_count = 0
        hit_count = 0
        deposited_before = 0.0
        deposited_after = 0.0
        carry = None
        previous_raw_event_id = None

        with uproot.open(self.root_path) as root_file:
            tree_name = self.tree_name or self._find_first_tree(root_file)
            tree = root_file[tree_name]
            requested = self._validate_tree(tree)

            for arrays in tree.iterate(
                expressions=sorted(requested),
                step_size=self.uproot_step_size,
                library="np",
                how=dict,
            ):
                frame = self._arrays_to_step_frame(arrays)
                if frame.empty:
                    continue
                if carry is not None:
                    frame = pd.concat([carry, frame], ignore_index=True)
                    carry = None

                raw_ids = frame["event_id_raw"].to_numpy()
                if np.any(raw_ids[1:] < raw_ids[:-1]):
                    raise RuntimeError(
                        "流式读取要求 ROOT 中 eventID 单调不下降；"
                        "当前文件不满足，请先排序或关闭 input.streaming。"
                    )
                if (
                    previous_raw_event_id is not None
                    and raw_ids[0] < previous_raw_event_id
                ):
                    raise RuntimeError(
                        "ROOT 分块之间检测到 eventID 倒序，无法安全流式聚合。"
                    )

                last_id = raw_ids[-1]
                carry_mask = frame["event_id_raw"] == last_id
                complete = frame.loc[~carry_mask].copy()
                carry = frame.loc[carry_mask].copy()
                previous_raw_event_id = last_id

                counts = self._consume_complete_frame(
                    complete,
                    imaging_sampler,
                    spectroscopy_sampler,
                )
                positive_step_count += counts["step_count"]
                hit_count += counts["hit_count"]
                rejected_count += counts["rejected_count"]
                deposited_before += counts["deposited_before"]
                deposited_after += counts["deposited_after"]

        if carry is not None and not carry.empty:
            counts = self._consume_complete_frame(
                carry,
                imaging_sampler,
                spectroscopy_sampler,
            )
            positive_step_count += counts["step_count"]
            hit_count += counts["hit_count"]
            rejected_count += counts["rejected_count"]
            deposited_before += counts["deposited_before"]
            deposited_after += counts["deposited_after"]

        tolerance = max(1e-10, abs(deposited_before) * 1e-10)
        if abs(deposited_before - deposited_after) > tolerance:
            raise RuntimeError(
                "Geant4 流式 step-to-hit 聚合前后能量不守恒："
                + str(deposited_before)
                + " vs "
                + str(deposited_after)
            )

        imaging = sorted(
            imaging_sampler.items,
            key=lambda event: event.event_id,
        )
        spectroscopy = sorted(
            spectroscopy_sampler.items,
            key=lambda event: event.event_id,
        )
        total_event_count = (
            imaging_sampler.total_seen
            + spectroscopy_sampler.total_seen
            + rejected_count
        )
        return InputDataset(
            imaging_events=imaging,
            spectroscopy_events=spectroscopy,
            rejected_events=[],
            summary={
                "source_type": "geant4_root_streaming",
                "root_path": str(self.root_path),
                "tree_name": tree_name,
                "positive_energy_step_count": positive_step_count,
                "hit_count": hit_count,
                "event_count": total_event_count,
                "imaging_event_count": imaging_sampler.total_seen,
                "spectroscopy_event_count": spectroscopy_sampler.total_seen,
                "rejected_event_count": rejected_count,
                "imaging_event_count_used": len(imaging),
                "spectroscopy_event_count_used": len(spectroscopy),
                "maximum_imaging_events": self.maximum_imaging_events,
                "maximum_spectroscopy_events": (
                    self.maximum_spectroscopy_events
                ),
                "sampling_seed": self.sampling_seed,
                "uproot_step_size": str(self.uproot_step_size),
                "order_mode": self.order_mode,
            },
        )

    def _consume_complete_frame(
        self,
        frame,
        imaging_sampler,
        spectroscopy_sampler,
    ):
        if frame.empty:
            return {
                "step_count": 0,
                "hit_count": 0,
                "rejected_count": 0,
                "deposited_before": 0.0,
                "deposited_after": 0.0,
            }

        hits = self._aggregate_steps(frame)
        events = self._group_events(hits)
        imaging, spectroscopy, rejected = self._classify_events(events)
        for event in imaging:
            imaging_sampler.add(event)
        for event in spectroscopy:
            spectroscopy_sampler.add(event)

        return {
            "step_count": int(len(frame)),
            "hit_count": int(len(hits)),
            "rejected_count": int(len(rejected)),
            "deposited_before": float(frame["energy_mev"].sum()),
            "deposited_after": float(
                sum(hit.energy_mev for hit in hits)
            ),
        }
