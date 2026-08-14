"""从全局配置构造模拟或实验输入源。"""

from __future__ import annotations

from pathlib import Path

from ..configuration import EiidConfig
from ..detector import ChannelMapping, TruthDigitizer
from ..domain import Channel
from .experiment import ExperimentalDelimitedEventSource, LinearCalibrationTable
from .geant4_legacy import LegacyGeant4RootEventSource
from .geant4_formal import FormalGeant4RootEventSource


class EventSourceFactory:
    """输入类型工厂；重建应用不需要知道 ROOT/CSV/TSV 细节。"""

    def __init__(self, config: EiidConfig):
        self.config = config
        self.mapping = ChannelMapping(
            config.chamber_to_channel,
            config.channel_to_layer,
        )

    def create(self):
        raw = self.config.raw_payload.get("input")
        if not isinstance(raw, dict):
            raise ValueError("配置缺少 input object。")
        source_type = str(raw.get("type", ""))
        if source_type == "geant4_legacy_root":
            return self._geant4_legacy(raw)
        if source_type == "geant4_formal_root":
            return self._geant4_formal(raw)
        if source_type == "experiment_delimited":
            return self._experiment(raw)
        raise ValueError("未知 input.type：" + source_type)

    def _geant4_legacy(self, raw):
        digitizer = raw.get("digitizer", {})
        if digitizer.get("mode") != "truth":
            raise ValueError("阶段 2 legacy Geant4 只实现显式 mode=truth 数字化器。")
        return LegacyGeant4RootEventSource(
            root_path=self.config.resolve_path(raw["root_path"]),
            tree_name=str(raw["tree_name"]),
            branches=raw["branches"],
            mapping=self.mapping,
            digitizer=TruthDigitizer(),
            dataset_id=str(raw["dataset_id"]),
            uproot_step_size=str(raw.get("uproot_step_size", "100 MB")),
            minimum_positive_step_energy_mev=float(
                raw.get("minimum_positive_step_energy_mev", 0.0)
            ),
        )

    def _experiment(self, raw):
        channel_paths = {
            Channel(channel): self.config.resolve_path(path)
            for channel, path in raw["paths"].items()
        }
        energy_mode = str(raw["energy_mode"])
        calibration_tables = None
        if energy_mode == "calibrated_adc":
            calibration_tables = {
                Channel(channel): LinearCalibrationTable.from_file(
                    self.config.resolve_path(path),
                    delimiter=str(raw.get("delimiter", "\t")),
                    columns=raw["calibration_columns"],
                )
                for channel, path in raw["calibration_paths"].items()
            }
        return ExperimentalDelimitedEventSource(
            channel_paths=channel_paths,
            channel_to_layer={
                Channel(channel): layer
                for channel, layer in self.config.channel_to_layer.items()
            },
            columns=raw["columns"],
            dataset_id=str(raw["dataset_id"]),
            delimiter=str(raw.get("delimiter", "\t")),
            energy_mode=energy_mode,
            calibration_tables=calibration_tables,
        )

    def _geant4_formal(self, raw):
        digitizer = raw.get("digitizer", {})
        if digitizer.get("mode") != "truth":
            raise ValueError("formal ROOT 第一版只接入显式 mode=truth；realistic 需版本化标定。")
        return FormalGeant4RootEventSource(
            root_path=self.config.resolve_path(raw["root_path"]),
            primary_tree=str(raw["trees"]["primary"]),
            deposit_tree=str(raw["trees"]["deposit"]),
            primary_branches=raw["branches"]["primary"],
            deposit_branches=raw["branches"]["deposit"],
            mapping=self.mapping,
            dataset_id=str(raw["dataset_id"]),
            digitizer=TruthDigitizer(),
        )
