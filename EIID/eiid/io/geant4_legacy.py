"""当前 Geant4 `Tree1` 的兼容读取和 step-to-deposit 聚合。"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from ..detector import ChannelMapping, DigitizedEventBuilder, Digitizer
from ..domain import DatasetMetadata, DetectorDeposit, EventDataset
from .base import EventSource


@dataclass(frozen=True)
class LegacyStep:
    """从 legacy `Tree1` 读取的一条正沉积 Geant4 step。"""

    raw_event_id: str
    chamber_id: int
    pixel_id: str
    energy_mev: float
    position_mm: np.ndarray
    step_order: Optional[float] = None
    time_ns: Optional[float] = None

    def __post_init__(self) -> None:
        position = np.asarray(self.position_mm, dtype=float).copy()
        energy = float(self.energy_mev)
        if not self.raw_event_id:
            raise ValueError("LegacyStep.raw_event_id 不能为空。")
        if position.shape != (3,) or not np.all(np.isfinite(position)):
            raise ValueError("LegacyStep.position_mm 必须是三个有限数字。")
        if not np.isfinite(energy) or energy <= 0.0:
            raise ValueError("LegacyStep.energy_mev 必须为正有限值。")
        position.setflags(write=False)
        object.__setattr__(self, "position_mm", position)
        object.__setattr__(self, "energy_mev", energy)
        object.__setattr__(self, "chamber_id", int(self.chamber_id))
        object.__setattr__(self, "pixel_id", str(self.pixel_id))


class LegacyStepAggregator:
    """按 eventID + chamberID + pixelID 聚合 step，保证沉积能量守恒。"""

    def __init__(self, dataset_id: str):
        if not dataset_id:
            raise ValueError("dataset_id 不能为空。")
        self.dataset_id = dataset_id

    def aggregate(self, steps: Iterable[LegacyStep]) -> Tuple[DetectorDeposit, ...]:
        groups = defaultdict(list)
        total_before = 0.0
        for step in steps:
            groups[(step.raw_event_id, step.chamber_id, step.pixel_id)].append(step)
            total_before += step.energy_mev

        deposits = []
        for (raw_event_id, chamber_id, pixel_id), group in groups.items():
            energies = np.asarray([step.energy_mev for step in group], dtype=float)
            positions = np.asarray([step.position_mm for step in group], dtype=float)
            times = [
                float(step.time_ns)
                for step in group
                if step.time_ns is not None and np.isfinite(float(step.time_ns))
            ]
            orders = [
                float(step.step_order)
                for step in group
                if step.step_order is not None
                and np.isfinite(float(step.step_order))
            ]
            deposits.append(
                DetectorDeposit(
                    event_id=self.dataset_id + ":" + str(raw_event_id),
                    chamber_id=chamber_id,
                    pixel_id=pixel_id,
                    total_edep_mev=float(energies.sum()),
                    energy_weighted_position_mm=np.average(
                        positions, axis=0, weights=energies
                    ),
                    earliest_time_ns=min(times) if times else None,
                    earliest_step_order=min(orders) if orders else None,
                    step_count=len(group),
                )
            )
        deposits.sort(
            key=lambda item: (
                item.event_id,
                item.chamber_id,
                item.pixel_id,
            )
        )
        total_after = sum(item.total_edep_mev for item in deposits)
        tolerance = max(1e-12, abs(total_before) * 1e-12)
        if abs(total_before - total_after) > tolerance:
            raise RuntimeError("legacy step 聚合前后沉积能量不守恒。")
        return tuple(deposits)


class LegacyGeant4RootEventSource(EventSource):
    """流式读取当前 step 级 `Tree1` 并生成统一事件。

    当前 Tree1 不包含零 hit primary，因此本输入源永远在 summary 中标记
    `primary_denominator_complete=False`，禁止把观测 event 数当成生成分母。
    """

    REQUIRED_BRANCH_KEYS = (
        "event_id",
        "chamber_id",
        "pixel_id",
        "energy_mev",
        "x_mm",
        "y_mm",
        "z_mm",
    )

    def __init__(
        self,
        root_path: Path,
        tree_name: str,
        branches: Mapping[str, Optional[str]],
        mapping: ChannelMapping,
        digitizer: Digitizer,
        dataset_id: str,
        uproot_step_size: str = "100 MB",
        minimum_positive_step_energy_mev: float = 0.0,
    ):
        self.root_path = Path(root_path)
        self.tree_name = str(tree_name)
        self.branches = dict(branches)
        self.mapping = mapping
        self.digitizer = digitizer
        self.dataset_id = str(dataset_id)
        self.uproot_step_size = str(uproot_step_size)
        self.minimum_positive_step_energy_mev = float(
            minimum_positive_step_energy_mev
        )
        if not self.tree_name or not self.dataset_id:
            raise ValueError("tree_name 和 dataset_id 必须显式配置。")
        missing = [key for key in self.REQUIRED_BRANCH_KEYS if not self.branches.get(key)]
        if missing:
            raise ValueError("Geant4 branches 缺少：" + ", ".join(missing))
        if self.minimum_positive_step_energy_mev < 0.0:
            raise ValueError("minimum_positive_step_energy_mev 不能为负。")

    def _records_from_arrays(self, arrays: Mapping[str, np.ndarray]) -> Tuple[LegacyStep, ...]:
        event_ids = np.asarray(arrays[self.branches["event_id"]])
        length = len(event_ids)
        required_names = [
            self.branches[key] for key in self.REQUIRED_BRANCH_KEYS
        ]
        if any(len(np.asarray(arrays[name])) != length for name in required_names):
            raise ValueError("ROOT branch 长度不一致。")

        def optional(key):
            name = self.branches.get(key)
            if name is None:
                return np.full(length, np.nan, dtype=float)
            return np.asarray(arrays[name], dtype=float)

        chambers = np.asarray(arrays[self.branches["chamber_id"]], dtype=int)
        pixels = np.asarray(arrays[self.branches["pixel_id"]])
        energies = np.asarray(arrays[self.branches["energy_mev"]], dtype=float)
        x_values = np.asarray(arrays[self.branches["x_mm"]], dtype=float)
        y_values = np.asarray(arrays[self.branches["y_mm"]], dtype=float)
        z_values = np.asarray(arrays[self.branches["z_mm"]], dtype=float)
        orders = optional("step_id")
        times = optional("time_ns")

        records = []
        for index in range(length):
            energy = float(energies[index])
            if (
                not np.isfinite(energy)
                or energy <= self.minimum_positive_step_energy_mev
            ):
                continue
            records.append(
                LegacyStep(
                    raw_event_id=str(event_ids[index]),
                    chamber_id=int(chambers[index]),
                    pixel_id=str(pixels[index]),
                    energy_mev=energy,
                    position_mm=[x_values[index], y_values[index], z_values[index]],
                    step_order=(
                        None if not np.isfinite(orders[index]) else float(orders[index])
                    ),
                    time_ns=(
                        None if not np.isfinite(times[index]) else float(times[index])
                    ),
                )
            )
        return tuple(records)

    @staticmethod
    def _split_complete_records(
        records: Sequence[LegacyStep],
    ) -> Tuple[Tuple[LegacyStep, ...], Tuple[LegacyStep, ...]]:
        """暂存分块末尾 event，避免同一 event 跨块时被重复聚合。"""

        if not records:
            return (), ()
        raw_ids = [record.raw_event_id for record in records]
        last_id = raw_ids[-1]
        split = len(records)
        while split > 0 and raw_ids[split - 1] == last_id:
            split -= 1
        return tuple(records[:split]), tuple(records[split:])

    def read(self) -> EventDataset:
        if not self.root_path.is_file():
            raise FileNotFoundError("找不到 Geant4 ROOT：" + str(self.root_path))
        try:
            import uproot
        except ImportError as error:
            raise ImportError(
                "读取 Geant4 ROOT 需要 uproot/awkward；请安装项目 io 依赖。"
            ) from error

        requested = sorted(
            {name for name in self.branches.values() if name is not None}
        )
        aggregator = LegacyStepAggregator(self.dataset_id)
        all_deposits = []
        carry = ()
        positive_step_count = 0
        previous_numeric_or_text_id = None

        with uproot.open(self.root_path) as root_file:
            if self.tree_name not in root_file:
                raise KeyError("ROOT 文件缺少配置树：" + self.tree_name)
            tree = root_file[self.tree_name]
            available = {str(name).split(";")[0] for name in tree.keys()}
            missing = sorted(set(requested) - available)
            if missing:
                raise KeyError("ROOT tree 缺少 branches：" + ", ".join(missing))
            for arrays in tree.iterate(
                expressions=requested,
                step_size=self.uproot_step_size,
                library="np",
                how=dict,
            ):
                records = carry + self._records_from_arrays(arrays)
                if records:
                    ids = [record.raw_event_id for record in records]
                    # 标准 Geant4 输出 eventID 单调；字符串转数字失败时按原字符串比较。
                    try:
                        comparable = [int(value) for value in ids]
                    except ValueError:
                        comparable = ids
                    if any(right < left for left, right in zip(comparable, comparable[1:])):
                        raise RuntimeError("流式读取要求 ROOT eventID 单调不下降。")
                    if (
                        previous_numeric_or_text_id is not None
                        and comparable[0] < previous_numeric_or_text_id
                    ):
                        raise RuntimeError("ROOT 分块之间 eventID 倒序。")
                    previous_numeric_or_text_id = comparable[-1]
                complete, carry = self._split_complete_records(records)
                positive_step_count += len(complete)
                all_deposits.extend(aggregator.aggregate(complete))

        if carry:
            positive_step_count += len(carry)
            all_deposits.extend(aggregator.aggregate(carry))

        events = DigitizedEventBuilder(self.mapping, self.digitizer).build(all_deposits)
        return EventDataset(
            events=events,
            metadata=DatasetMetadata(
                dataset_id=self.dataset_id,
                source_type="geant4_legacy_tree1",
                schema_version="legacy_tree1",
                attributes={
                    "root_path": str(self.root_path),
                    "tree_name": self.tree_name,
                    "digitizer_version": self.digitizer.version,
                },
            ),
            summary={
                "positive_step_count": positive_step_count,
                "deposit_count": len(all_deposits),
                "observed_event_count": len(events),
                "primary_denominator_complete": False,
                "zero_hit_primaries_available": False,
                "warning": (
                    "legacy Tree1 不含零 hit primary，不能独立计算正式响应效率分母"
                ),
            },
        )
