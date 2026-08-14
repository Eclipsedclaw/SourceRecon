"""可配置实验长表输入及逐像素线性能量标定。"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, Mapping, Optional, Tuple

import numpy as np

from ..domain import (
    Channel,
    DatasetMetadata,
    DigitizedHit,
    EventDataset,
    EventTopology,
    MeasuredEvent,
    SequenceClass,
)
from .base import EventSource


class LinearCalibrationTable:
    """逐像素线性标定：E_keV = slope * ADC + intercept。"""

    def __init__(self, coefficients: Mapping[str, Tuple[float, float]]):
        parsed = {
            str(pixel): (float(values[0]), float(values[1]))
            for pixel, values in coefficients.items()
        }
        if not parsed:
            raise ValueError("线性标定表不能为空。")
        for pixel, (slope, intercept) in parsed.items():
            if not np.isfinite(slope) or not np.isfinite(intercept):
                raise ValueError("像素 " + pixel + " 的标定系数必须有限。")
        self.coefficients = parsed

    @classmethod
    def from_file(
        cls,
        path: Path,
        delimiter: str,
        columns: Mapping[str, str],
    ) -> "LinearCalibrationTable":
        required = ("pixel_id", "slope_kev_per_adc", "intercept_kev")
        missing = [key for key in required if not columns.get(key)]
        if missing:
            raise ValueError("calibration_columns 缺少：" + ", ".join(missing))
        coefficients = {}
        with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, delimiter=delimiter)
            if reader.fieldnames is None:
                raise ValueError("标定文件没有表头：" + str(path))
            absent = [columns[key] for key in required if columns[key] not in reader.fieldnames]
            if absent:
                raise KeyError(str(path) + " 缺少列：" + ", ".join(absent))
            for row in reader:
                pixel = str(row[columns["pixel_id"]])
                if pixel in coefficients:
                    raise ValueError("标定表 PixelID 重复：" + pixel)
                coefficients[pixel] = (
                    float(row[columns["slope_kev_per_adc"]]),
                    float(row[columns["intercept_kev"]]),
                )
        return cls(coefficients)

    def energy_mev(self, pixel_id: str, adc: float) -> float:
        """把 ADC 转换为 MeV；缺少像素标定时明确失败。"""

        pixel = str(pixel_id)
        try:
            slope, intercept = self.coefficients[pixel]
        except KeyError as error:
            raise KeyError("标定表缺少 PixelID：" + pixel) from error
        return float((slope * float(adc) + intercept) / 1000.0)


class ExperimentalDelimitedEventSource(EventSource):
    """读取每通道一份的 CSV/TSV 长表，保留同 EventID 的多个像素 hit。

    `energy_mode=direct_mev` 时输入直接包含 MeV；`calibrated_adc` 时使用逐像素
    线性标定。实验输入从不构造 `SimulationTruth`。
    """

    def __init__(
        self,
        channel_paths: Mapping[Channel, Path],
        channel_to_layer: Mapping[Channel, int],
        columns: Mapping[str, Optional[str]],
        dataset_id: str,
        delimiter: str = "\t",
        energy_mode: str = "direct_mev",
        calibration_tables: Optional[Mapping[Channel, LinearCalibrationTable]] = None,
    ):
        self.channel_paths = {
            key if isinstance(key, Channel) else Channel(key): Path(value)
            for key, value in channel_paths.items()
        }
        self.channel_to_layer = {
            key if isinstance(key, Channel) else Channel(key): int(value)
            for key, value in channel_to_layer.items()
        }
        self.columns = dict(columns)
        self.dataset_id = str(dataset_id)
        self.delimiter = str(delimiter)
        self.energy_mode = str(energy_mode)
        self.calibration_tables = {
            key if isinstance(key, Channel) else Channel(key): value
            for key, value in (calibration_tables or {}).items()
        }
        if set(self.channel_paths) != set(Channel):
            raise ValueError("实验输入必须显式提供 ch0/ch1/ch2 三个路径。")
        if set(self.channel_to_layer) != set(Channel):
            raise ValueError("channel_to_layer 必须覆盖 ch0/ch1/ch2。")
        if self.energy_mode not in ("direct_mev", "calibrated_adc"):
            raise ValueError("energy_mode 必须是 direct_mev 或 calibrated_adc。")
        required = ["event_id", "pixel_id", "x_mm", "y_mm", "z_mm"]
        required.append("energy_mev" if self.energy_mode == "direct_mev" else "adc")
        missing = [key for key in required if not self.columns.get(key)]
        if missing:
            raise ValueError("实验 columns 缺少：" + ", ".join(missing))
        if self.energy_mode == "calibrated_adc" and set(self.calibration_tables) != set(Channel):
            raise ValueError("calibrated_adc 模式必须提供 ch0/ch1/ch2 标定表。")

    def _energy(self, channel: Channel, row: Mapping[str, str], pixel: str) -> float:
        if self.energy_mode == "direct_mev":
            return float(row[self.columns["energy_mev"]])
        return self.calibration_tables[channel].energy_mev(
            pixel, float(row[self.columns["adc"]])
        )

    def read(self) -> EventDataset:
        by_event = defaultdict(list)
        raw_row_count = 0
        for channel in sorted(Channel, key=lambda item: item.value):
            path = self.channel_paths[channel]
            if not path.is_file():
                raise FileNotFoundError("找不到实验输入：" + str(path))
            with path.open("r", encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream, delimiter=self.delimiter)
                if reader.fieldnames is None:
                    raise ValueError("实验文件没有表头：" + str(path))
                active_keys = [
                    "event_id",
                    "pixel_id",
                    "x_mm",
                    "y_mm",
                    "z_mm",
                    "energy_mev" if self.energy_mode == "direct_mev" else "adc",
                ]
                if self.columns.get("time_ns") is not None:
                    active_keys.append("time_ns")
                required_names = [self.columns[key] for key in active_keys]
                absent = [name for name in required_names if name not in reader.fieldnames]
                if absent:
                    raise KeyError(str(path) + " 缺少列：" + ", ".join(absent))
                for row_index, row in enumerate(reader, start=2):
                    raw_row_count += 1
                    raw_event_id = str(row[self.columns["event_id"]])
                    pixel = str(row[self.columns["pixel_id"]])
                    energy = self._energy(channel, row, pixel)
                    if not np.isfinite(energy) or energy < 0.0:
                        raise ValueError(
                            str(path)
                            + " 第 "
                            + str(row_index)
                            + " 行能量不是非负有限值。"
                        )
                    time_column = self.columns.get("time_ns")
                    raw_time = row.get(time_column, "") if time_column else ""
                    time_ns = None if raw_time in (None, "") else float(raw_time)
                    event_id = self.dataset_id + ":" + raw_event_id
                    by_event[event_id].append(
                        DigitizedHit(
                            hit_id=(
                                event_id
                                + ":"
                                + channel.value
                                + ":row:"
                                + str(row_index)
                            ),
                            channel=channel,
                            layer=self.channel_to_layer[channel],
                            pixel_id=pixel,
                            position_mm=[
                                float(row[self.columns["x_mm"]]),
                                float(row[self.columns["y_mm"]]),
                                float(row[self.columns["z_mm"]]),
                            ],
                            energy_mev=energy,
                            time_ns=time_ns,
                            is_valid_readout=True,
                            metadata={
                                "source_file": str(path),
                                "source_row": row_index,
                                "energy_mode": self.energy_mode,
                            },
                        )
                    )

        events = []
        for event_id, hits in by_event.items():
            ordered = tuple(
                sorted(
                    hits,
                    key=lambda hit: (
                        float("inf") if hit.time_ns is None else hit.time_ns,
                        hit.layer,
                        hit.hit_id,
                    ),
                )
            )
            topology = (
                EventTopology.TWO_HIT
                if len(ordered) == 2
                else EventTopology.THREE_OR_MORE_HIT
                if len(ordered) >= 3
                else EventTopology.UNKNOWN
            )
            events.append(
                MeasuredEvent(
                    event_id=event_id,
                    hits=ordered,
                    sequence_class=SequenceClass.UNKNOWN,
                    topology=topology,
                    truth=None,
                    metadata={"energy_mode": self.energy_mode},
                )
            )
        events.sort(key=lambda event: event.event_id)
        return EventDataset(
            events=tuple(events),
            metadata=DatasetMetadata(
                dataset_id=self.dataset_id,
                source_type="experiment_delimited",
                schema_version="experiment_delimited_v1",
                attributes={
                    "paths": {
                        channel.value: str(path)
                        for channel, path in self.channel_paths.items()
                    },
                    "energy_mode": self.energy_mode,
                },
            ),
            summary={
                "raw_row_count": raw_row_count,
                "event_count": len(events),
                "truth_available": False,
            },
        )
