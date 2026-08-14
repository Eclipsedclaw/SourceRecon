"""具有完整 primary 分母的正式 Geant4 ROOT 输入适配器。"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from eiid.detector import ChannelMapping, DigitizedEventBuilder, TruthDigitizer
from eiid.domain import DatasetMetadata, DetectorDeposit, EventDataset, MeasuredEvent, SequenceClass, SimulationTruth

from .base import EventSource


class FormalGeant4RootEventSource(EventSource):
    """读取 PrimaryTruth 和聚合后的 DetectorDeposit。

    每个 primary 必须出现一次，即使没有沉积。第一版 formal adapter 只允许
    truth digitizer；真实数字化通过同一 Digitizer 接口后续接入。
    """

    def __init__(self, root_path, primary_tree, deposit_tree, primary_branches,
                 deposit_branches, mapping: ChannelMapping, dataset_id, digitizer=None):
        self.root_path = Path(root_path).expanduser().resolve()
        self.primary_tree = str(primary_tree)
        self.deposit_tree = str(deposit_tree)
        self.primary_branches = dict(primary_branches)
        self.deposit_branches = dict(deposit_branches)
        self.mapping = mapping
        self.dataset_id = str(dataset_id)
        self.digitizer = digitizer or TruthDigitizer()
        required_primary = {"event_id", "energy_mev", "propagation_x", "propagation_y", "propagation_z"}
        required_deposit = {"event_id", "chamber_id", "pixel_id", "energy_mev", "x_mm", "y_mm", "z_mm"}
        if required_primary.difference(self.primary_branches):
            raise ValueError("primary_branches 缺少必需逻辑字段。")
        if required_deposit.difference(self.deposit_branches):
            raise ValueError("deposit_branches 缺少必需逻辑字段。")

    @staticmethod
    def _optional(array_map, branches, name, index, default=None):
        branch = branches.get(name)
        return default if branch in (None, "") else array_map[branch][index]

    def read(self) -> EventDataset:
        if not self.root_path.is_file():
            raise FileNotFoundError("找不到正式 Geant4 ROOT：" + str(self.root_path))
        try:
            import uproot
        except ImportError as error:
            raise ImportError("读取正式 Geant4 ROOT 需要安装 uproot。") from error
        with uproot.open(str(self.root_path)) as root:
            if self.primary_tree not in root or self.deposit_tree not in root:
                raise KeyError("ROOT 缺少配置的 PrimaryTruth/DetectorDeposit 树。")
            primary_names = tuple(value for value in self.primary_branches.values() if value)
            deposit_names = tuple(value for value in self.deposit_branches.values() if value)
            primary = root[self.primary_tree].arrays(primary_names, library="np")
            deposits_raw = root[self.deposit_tree].arrays(deposit_names, library="np")

        event_branch = self.primary_branches["event_id"]
        primary_count = len(primary[event_branch])
        truth_by_id = {}
        for index in range(primary_count):
            raw_id = str(primary[event_branch][index])
            event_id = self.dataset_id + ":" + raw_id
            if event_id in truth_by_id:
                raise ValueError("PrimaryTruth eventID 重复：" + raw_id)
            propagation = np.asarray([
                primary[self.primary_branches["propagation_x"]][index],
                primary[self.primary_branches["propagation_y"]][index],
                primary[self.primary_branches["propagation_z"]][index],
            ], dtype=float)
            source_names = tuple(self.primary_branches.get(name) for name in ("source_x", "source_y", "source_z"))
            source = -propagation if any(name in (None, "") for name in source_names) else np.asarray([primary[name][index] for name in source_names], dtype=float)
            truth_by_id[event_id] = SimulationTruth(
                primary_energy_mev=float(primary[self.primary_branches["energy_mev"]][index]),
                propagation_direction_detector=propagation,
                source_direction_detector=source,
                event_weight=float(self._optional(primary, self.primary_branches, "event_weight", index, 1.0)),
                is_full_absorption=(None if self.primary_branches.get("is_full_absorption") in (None, "") else bool(self._optional(primary, self.primary_branches, "is_full_absorption", index))),
                is_backscatter=(None if self.primary_branches.get("is_backscatter") in (None, "") else bool(self._optional(primary, self.primary_branches, "is_backscatter", index))),
                has_pair_production=(None if self.primary_branches.get("has_pair_production") in (None, "") else bool(self._optional(primary, self.primary_branches, "has_pair_production", index))),
                metadata={"primary_truth_tree": self.primary_tree},
            )

        deposits = []
        deposit_event = self.deposit_branches["event_id"]
        for index in range(len(deposits_raw[deposit_event])):
            event_id = self.dataset_id + ":" + str(deposits_raw[deposit_event][index])
            if event_id not in truth_by_id:
                raise ValueError("DetectorDeposit 引用了不存在的 primary：" + event_id)
            time_value = self._optional(deposits_raw, self.deposit_branches, "time_ns", index, None)
            deposits.append(DetectorDeposit(
                event_id=event_id,
                chamber_id=int(deposits_raw[self.deposit_branches["chamber_id"]][index]),
                pixel_id=str(deposits_raw[self.deposit_branches["pixel_id"]][index]),
                total_edep_mev=float(deposits_raw[self.deposit_branches["energy_mev"]][index]),
                energy_weighted_position_mm=np.asarray([
                    deposits_raw[self.deposit_branches["x_mm"]][index],
                    deposits_raw[self.deposit_branches["y_mm"]][index],
                    deposits_raw[self.deposit_branches["z_mm"]][index],
                ], dtype=float),
                earliest_time_ns=None if time_value is None else float(time_value),
                step_count=int(self._optional(deposits_raw, self.deposit_branches, "step_count", index, 1)),
                metadata={"deposit_tree": self.deposit_tree},
            ))

        measured = {event.event_id: event for event in DigitizedEventBuilder(self.mapping, self.digitizer).build(deposits)}
        events = []
        for event_id in sorted(truth_by_id):
            truth = truth_by_id[event_id]
            base = measured.get(event_id, MeasuredEvent(event_id=event_id, hits=()))
            sequence = SequenceClass.BACKSCATTER if truth.is_backscatter is True else SequenceClass.NORMAL_FORWARD if truth.is_backscatter is False else SequenceClass.UNKNOWN
            events.append(replace(base, truth=truth, sequence_class=sequence))
        return EventDataset(
            events=tuple(events),
            metadata=DatasetMetadata(
                dataset_id=self.dataset_id,
                source_type="geant4_formal_root",
                schema_version="geant4_primary_deposit_v1",
                attributes={"root_path": str(self.root_path), "primary_tree": self.primary_tree,
                            "deposit_tree": self.deposit_tree, "digitizer_version": self.digitizer.version},
            ),
            summary={
                "generated_primary_count": primary_count,
                "deposit_row_count": len(deposits),
                "zero_digitized_hit_primary_count": sum(not event.hits for event in events),
                "truth_available": True,
                "complete_primary_denominator": True,
            },
        )
