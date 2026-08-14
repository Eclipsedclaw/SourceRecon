from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from ..domain import Hit, InputDataset, MeasuredEvent
from .base import EventSource


class ExperimentalTsvEventSource(EventSource):
    """
    读取 FristArithmetic 风格的三通道实验 TSV 与三份刻度表。

    与旧版 outer-merge 宽表不同，本类始终保持“每行一个 hit”的长表，
    因而同一 EventID 在同一 channel 中出现多个 pixel hit 时不会产生
    笛卡尔积，也不会丢失信息。
    """

    def __init__(
        self,
        channel_paths: Dict[str, Path],
        calibration_paths: Dict[str, Path],
        channel_to_layer: Dict[str, int],
        columns: Dict[str, str],
        calibration_columns: Dict[str, str],
        separator: str = "\t",
        order_mode: str = "layer",
        spectroscopy_channel: str = "ch0",
        minimum_hit_energy_mev: float = 0.0,
    ):
        self.channel_paths = channel_paths
        self.calibration_paths = calibration_paths
        self.channel_to_layer = channel_to_layer
        self.columns = columns
        self.calibration_columns = calibration_columns
        self.separator = separator
        self.order_mode = order_mode
        self.spectroscopy_channel = spectroscopy_channel
        self.minimum_hit_energy_mev = float(minimum_hit_energy_mev)

    def read(self) -> InputDataset:
        hits_by_event: Dict[str, List[Hit]] = {}
        raw_row_count = 0

        for channel in sorted(self.channel_paths):
            channel_hits, channel_rows = self._read_channel(channel)
            raw_row_count += channel_rows
            for hit in channel_hits:
                hits_by_event.setdefault(hit.event_id, []).append(hit)

        all_events = []
        for event_id, hits in hits_by_event.items():
            event_time = self._minimum_finite_time(hits)
            event = MeasuredEvent(
                event_id=event_id,
                hits=hits,
                attitude_time_ns=event_time,
            ).collapsed_by_layer().ordered(self.order_mode)
            all_events.append(event)

        all_events.sort(key=lambda event: event.event_id)
        imaging, spectroscopy, rejected = self._classify_events(all_events)

        return InputDataset(
            imaging_events=imaging,
            spectroscopy_events=spectroscopy,
            rejected_events=rejected,
            summary={
                "source_type": "experimental_tsv",
                "raw_rows": raw_row_count,
                "event_count": len(all_events),
                "imaging_event_count": len(imaging),
                "spectroscopy_event_count": len(spectroscopy),
                "rejected_event_count": len(rejected),
                "order_mode": self.order_mode,
            },
        )

    def _read_channel(self, channel: str):
        if channel not in self.channel_to_layer:
            raise KeyError("channel_to_layer 缺少：" + channel)

        data_path = self.channel_paths[channel]
        calibration_path = self.calibration_paths[channel]
        self._require_file(data_path)
        self._require_file(calibration_path)

        raw = pd.read_csv(data_path, sep=self.separator)
        calibration = pd.read_csv(calibration_path, sep=self.separator)
        self._require_columns(raw, self.columns.values(), str(data_path))
        self._require_columns(
            calibration,
            self.calibration_columns.values(),
            str(calibration_path),
        )

        pixel_column = self.columns["pixel_id"]
        calibration_pixel = self.calibration_columns["pixel_id"]
        slope_column = self.calibration_columns["slope_kev_per_adc"]
        intercept_column = self.calibration_columns["intercept_kev"]

        calibration_view = calibration[
            [calibration_pixel, slope_column, intercept_column]
        ].rename(columns={calibration_pixel: pixel_column})
        merged = raw.merge(
            calibration_view,
            on=pixel_column,
            how="left",
            validate="many_to_one",
        )

        if merged[[slope_column, intercept_column]].isna().any().any():
            missing_pixels = merged.loc[
                merged[slope_column].isna() | merged[intercept_column].isna(),
                pixel_column,
            ].drop_duplicates()
            raise ValueError(
                channel
                + " 存在没有刻度参数的 PixelID："
                + ", ".join(map(str, missing_pixels.tolist()[:20]))
            )

        energy_mev = (
            merged[self.columns["adc"]] * merged[slope_column]
            + merged[intercept_column]
        ) / 1000.0

        hits: List[Hit] = []
        for row_index, (_, row) in enumerate(merged.iterrows()):
            energy = float(energy_mev.iloc[row_index])
            if not np.isfinite(energy) or energy <= self.minimum_hit_energy_mev:
                continue

            event_id = str(row[self.columns["event_id"]])
            time_ns = self._optional_float(row, self.columns.get("time_ns"))
            hit = Hit(
                hit_id=channel + "_" + event_id + "_" + str(row_index),
                event_id=event_id,
                channel=channel,
                layer=int(self.channel_to_layer[channel]),
                pixel_id=str(row[pixel_column]),
                position_mm=np.array(
                    [
                        float(row[self.columns["x_mm"]]),
                        float(row[self.columns["y_mm"]]),
                        float(row[self.columns["z_mm"]]),
                    ],
                    dtype=float,
                ),
                energy_mev=energy,
                time_ns=time_ns,
                truth_order=None,
                true_event_id=None,
            )
            hits.append(hit)

        return hits, len(raw)

    def _classify_events(self, events):
        imaging = []
        spectroscopy = []
        rejected = []

        for event in events:
            if all(
                hit.channel == self.spectroscopy_channel
                for hit in event.hits
            ):
                # 同一 gamma 在厚 ch0 的多个 pixel 留下能量时，总沉积能量
                # 对谱学仍有用，但没有跨层基线，不能生成可靠方向圆锥。
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
    def _minimum_finite_time(hits: List[Hit]):
        values = [
            float(hit.time_ns)
            for hit in hits
            if hit.time_ns is not None and np.isfinite(hit.time_ns)
        ]
        return min(values) if values else None

    @staticmethod
    def _optional_float(row, column_name):
        if column_name is None or column_name not in row.index:
            return None
        value = row[column_name]
        return float(value) if pd.notna(value) else None

    @staticmethod
    def _require_file(path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError("找不到实验输入文件：" + str(path))

    @staticmethod
    def _require_columns(frame, columns, file_name) -> None:
        missing = [column for column in columns if column not in frame.columns]
        if missing:
            raise KeyError(
                file_name + " 缺少列：" + ", ".join(map(str, missing))
            )
