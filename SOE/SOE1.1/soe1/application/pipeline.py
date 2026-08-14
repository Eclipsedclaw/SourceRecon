from __future__ import annotations

from collections import Counter
from typing import Dict

import numpy as np

from ..analysis import DatasetQualityReporter
from ..configuration import Configuration
from ..diagnostics import OutputWriter
from ..geometry import (
    CsvQuaternionAttitudeProvider,
    HealpixPixelizer,
    IdentityAttitudeProvider,
)
from ..io import (
    ExperimentalTsvEventSource,
    Geant4RootEventSource,
    StreamingGeant4RootEventSource,
)
from ..reconstruction import IndependentEventProposal, SphericalSoeSampler
from ..response import EventKernelFactory, SpectrumPriorFactory


class EventSourceFactory:
    """根据 input.type 构造实验或 Geant4 输入对象。"""

    def __init__(self, configuration: Configuration):
        self.configuration = configuration

    def create(self):
        config = self.configuration.section("input")
        source_type = str(config["type"])
        if source_type == "experiment_tsv":
            return self._create_experiment_source(config)
        if source_type == "geant4_root":
            return self._create_geant4_source(config)
        raise ValueError("未知 input.type：" + source_type)

    def _create_experiment_source(self, config):
        paths = config["paths"]
        calibrations = config["calibration_paths"]
        channel_names = ("ch0", "ch1", "ch2")
        channel_paths = {
            channel: self.configuration.resolve_path(paths[channel])
            for channel in channel_names
        }
        calibration_paths = {
            channel: self.configuration.resolve_path(calibrations[channel])
            for channel in channel_names
        }
        return ExperimentalTsvEventSource(
            channel_paths=channel_paths,
            calibration_paths=calibration_paths,
            channel_to_layer={
                str(key): int(value)
                for key, value in config["channel_to_layer"].items()
            },
            columns=config["columns"],
            calibration_columns=config["calibration_columns"],
            separator=str(config.get("separator", "\t")),
            order_mode=str(config.get("order_mode", "layer")),
            spectroscopy_channel=str(
                config.get("spectroscopy_channel", "ch0")
            ),
            minimum_hit_energy_mev=float(
                config.get("minimum_hit_energy_mev", 0.0)
            ),
        )

    def _create_geant4_source(self, config):
        source_class = (
            StreamingGeant4RootEventSource
            if bool(config.get("streaming", False))
            else Geant4RootEventSource
        )
        common_arguments = dict(
            root_path=self.configuration.resolve_path(config["root_path"]),
            tree_name=config.get("tree_name"),
            branches=config["branches"],
            chamber_to_layer={
                int(key): int(value)
                for key, value in config["chamber_to_layer"].items()
            },
            layer_to_channel={
                int(key): str(value)
                for key, value in config["layer_to_channel"].items()
            },
            dataset_id=str(config.get("dataset_id", "geant4")),
            order_mode=str(config.get("order_mode", "layer")),
            spectroscopy_channel=str(
                config.get("spectroscopy_channel", "ch0")
            ),
            minimum_hit_energy_mev=float(
                config.get("minimum_hit_energy_mev", 0.0)
            ),
        )
        if source_class is StreamingGeant4RootEventSource:
            common_arguments.update(
                {
                    "uproot_step_size": config.get(
                        "uproot_step_size", "250 MB"
                    ),
                    "maximum_imaging_events": config.get(
                        "maximum_imaging_events"
                    ),
                    "maximum_spectroscopy_events": config.get(
                        "maximum_spectroscopy_events"
                    ),
                    "sampling_seed": int(
                        config.get("sampling_seed", 20260730)
                    ),
                }
            )
        return source_class(**common_arguments)


class AttitudeProviderFactory:
    """构造单位姿态或 CSV 四元数姿态接口。"""

    def __init__(self, configuration: Configuration):
        self.configuration = configuration

    def create(self):
        config = self.configuration.optional_section("attitude")
        mode = str(config.get("mode", "identity"))
        if mode == "identity":
            return IdentityAttitudeProvider()
        if mode == "csv_quaternion":
            return CsvQuaternionAttitudeProvider(
                path=self.configuration.resolve_path(config["path"]),
                columns=config["columns"],
                separator=str(config.get("separator", ",")),
                time_scale_to_ns=float(
                    config.get("time_scale_to_ns", 1.0)
                ),
                maximum_time_difference_ns=config.get(
                    "maximum_time_difference_ns"
                ),
                conjugate=bool(config.get("conjugate", False)),
            )
        raise ValueError("未知 attitude.mode：" + mode)


class SoeApplication:
    """
    SOE1 的唯一高层编排类。

    入口脚本只负责读取命令行参数。本类依次完成 IO、能谱、事件 kernel、
    SOE 链与输出；各步骤依赖抽象接口而不是具体文件格式。
    """

    def __init__(self, configuration: Configuration):
        self.configuration = configuration

    def run(self, dataset_metadata=None, analysis_directory=None):
        event_source = EventSourceFactory(self.configuration).create()
        dataset = event_source.read()

        spectrum = SpectrumPriorFactory(
            self.configuration.section("spectrum")
        ).build(dataset.spectroscopy_events)

        kernel_factory = EventKernelFactory(
            spectrum=spectrum,
            response_config=self.configuration.section("response"),
        )
        kernels, kernel_rejected = kernel_factory.build_many(
            dataset.imaging_events
        )
        if not kernels:
            raise RuntimeError("所有 imaging event 都未能生成物理合法 kernel。")

        reconstruction_config = self.configuration.section("reconstruction")
        pixelizer = HealpixPixelizer(
            nside=int(reconstruction_config["healpix_nside"]),
            nested=bool(reconstruction_config.get("healpix_nested", False)),
        )
        attitude_provider = AttitudeProviderFactory(
            self.configuration
        ).create()
        random_seed = int(reconstruction_config.get("random_seed", 20260730))
        random_generator = np.random.default_rng(random_seed)
        proposal = IndependentEventProposal(
            kernels=kernels,
            attitude_provider=attitude_provider,
            pixelizer=pixelizer,
            random_generator=random_generator,
        )
        sampler = SphericalSoeSampler(
            kernels=kernels,
            proposal=proposal,
            pixelizer=pixelizer,
            sweeps=int(reconstruction_config["sweeps"]),
            burn_in_sweeps=int(
                reconstruction_config["burn_in_sweeps"]
            ),
            thinning_sweeps=int(
                reconstruction_config["thinning_sweeps"]
            ),
            random_seed=random_seed,
        )
        result = sampler.run()

        output_config = self.configuration.section("output")
        output_directory = self.configuration.resolve_path(
            output_config["directory"]
        )
        writer = OutputWriter(
            output_directory=output_directory,
            pixelizer=pixelizer,
        )
        run_summary = self._build_run_summary(
            dataset.summary,
            kernels,
            len(kernel_rejected),
            result,
        )
        output_paths = writer.write_all(
            result=result,
            kernels=kernels,
            spectrum=spectrum,
            run_summary=run_summary,
            configuration=self.configuration.as_dict(),
        )
        if analysis_directory is not None:
            reporter = DatasetQualityReporter(
                numerical_directory=output_directory,
                report_directory=analysis_directory,
                metadata=dataset_metadata,
                analysis_config=self.configuration.optional_section(
                    "analysis"
                ),
            )
            output_paths.update(reporter.write_all())
        return output_paths

    @staticmethod
    def _build_run_summary(
        input_summary: Dict[str, object],
        kernels,
        kernel_rejected_count: int,
        result,
    ) -> Dict[str, object]:
        hit_counts = Counter(
            "3_or_more_hit" if kernel.event.n_hits >= 3 else "2_hit"
            for kernel in kernels
        )
        return {
            "input": input_summary,
            "kernel_count": len(kernels),
            "kernel_rejected_count": int(kernel_rejected_count),
            "kernel_count_by_type": dict(hit_counts),
            "saved_sample_count": result.saved_sample_count,
            "attempted_moves": result.attempted_moves,
            "accepted_moves": result.accepted_moves,
            "acceptance_rate": result.acceptance_rate,
            "random_seed": result.random_seed,
        }
