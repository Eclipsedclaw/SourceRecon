"""实验输入到联合图像、遥测和图片的阶段 5 端到端应用。"""

from __future__ import annotations

import time

import numpy as np

from eiid.analysis import DiagonalFisherUncertainty, ReconstructionResultWriter
from eiid.convergence import IterationRecorder
from eiid.coordinates import HealpixSkyGrid
from eiid.detector import TriggerPolicy
from eiid.domain import EnergyGrid
from eiid.io import EventIngestionPipeline, EventSourceFactory
from eiid.reconstruction import LmMlemConfig, ListModeMlemSolver
from eiid.response import (
    AnalyticComptonResponse,
    EventKernelBuilder,
    HybridMonteCarloResponse,
    ResponseStoreFactory,
    SensitivityKind,
    SensitivityMap,
)
from eiid.visualization import EiidFigureSuite


class ExperimentReconstructionApplication:
    """编排输入、响应、重建和输出；各数值模块仍保持独立可测试。"""

    def __init__(
        self,
        config,
        run_context,
        initial_image=None,
        resumed_from_run_id=None,
    ):
        self.config = config
        self.context = run_context
        self.initial_image = initial_image
        self.resumed_from_run_id = resumed_from_run_id

    def _energy_grid(self):
        energy = self.config.energy_grid
        if energy.edges_mev is not None:
            return EnergyGrid.nonuniform(energy.edges_mev)
        return EnergyGrid.uniform(
            energy.minimum_mev, energy.maximum_mev, energy.bin_width_mev
        )

    def _prepare_response(self, sky_grid, energy_grid):
        """构造事件核与同源灵敏度，并返回明确的物理使用状态。"""

        response = self.config.event_response
        if response is None:
            raise RuntimeError("端到端重建缺少 event_response 配置。")
        parameters = response.parameters
        if response.model_id == "analytic_compton_gaussian_arm_v1":
            if parameters.get("allow_nonphysical_response_for_smoke") is not True:
                raise RuntimeError(
                    "解析相对似然不是正式物理响应；smoke 必须显式允许非物理响应。"
                )
            model = AnalyticComptonResponse(
                arm_sigma_rad=np.deg2rad(float(parameters["arm_sigma_deg"])),
                minimum_relative_weight=float(parameters["minimum_relative_weight"]),
            )
            return model, None, False, {
                "library_id": None,
                "library_status": "prototype_not_physical",
                "response_semantics": model.response_semantics,
            }
        if response.model_id != "hybrid_monte_carlo_arm_v1":
            raise RuntimeError("不支持的 event_response.model_id：" + response.model_id)
        library_config = self.config.response
        if library_config is None:
            raise RuntimeError("混合响应必须配置 response 响应库。")
        library = ResponseStoreFactory.create(library_config.adapter).load(
            library_config.library_path
        )
        if library.metadata.library_status != library_config.library_status:
            raise RuntimeError("配置声明的响应库状态与 manifest 不一致。")
        if not np.allclose(
            library.energy_grid.edges_mev,
            energy_grid.edges_mev,
            rtol=0.0,
            atol=1e-12,
        ):
            raise RuntimeError("响应库能量网格与重建网格不同；禁止隐式插值。")
        library_sky = library.sky_grid
        if (
            int(library_sky.get("pixel_count", -1)) != sky_grid.pixel_count
            or int(library_sky.get("nside", -1)) != sky_grid.nside
            or bool(library_sky.get("nested", False)) != sky_grid.nested
        ):
            raise RuntimeError("响应库 HEALPix 网格与重建网格不同；禁止隐式重排。")
        kind = SensitivityKind(self.config.reconstruction.sensitivity_kind)
        sensitivity = library.sensitivities.by_kind(kind)
        if sensitivity is None:
            raise RuntimeError("响应库不包含所选物理灵敏度：" + kind.value)
        if "arm_sigma_deg" not in library.calibration_arrays:
            raise RuntimeError("混合响应库缺少 arm_sigma_deg 标定数组。")
        physical = library.metadata.library_status == "validated_physical"
        if not physical and parameters.get("allow_unvalidated_response") is not True:
            raise RuntimeError(
                "响应库尚未 validated_physical；验证运行必须显式允许未验证响应。"
            )
        model = HybridMonteCarloResponse(
            library.calibration_arrays["arm_sigma_deg"],
            sensitivity.values,
            minimum_relative_weight=float(parameters["minimum_relative_weight"]),
            modeled_topology_probability=library.calibration_arrays.get(
                "topology_probability__normal_forward"
            ),
        )
        return model, sensitivity, physical, {
            "library_id": library.metadata.library_id,
            "library_status": library.metadata.library_status,
            "geometry_version": library.metadata.geometry_version,
            "physics_list": library.metadata.physics_list,
            "digitizer_version": library.metadata.digitizer_version,
            "response_semantics": model.response_semantics,
            "sensitivity_kind": sensitivity.kind.value,
            "sensitivity_unit": sensitivity.unit,
            "sensitivity_definition": sensitivity.definition,
        }

    @staticmethod
    def _prototype_sensitivity(kernel_batch, sky_count, energy_count):
        """仅在事件核联合支撑上置 1；明确禁止用于物理归一化。"""

        values = np.zeros(sky_count * energy_count, dtype=float)
        for response in kernel_batch.responses:
            values[response.cell_indices] = 1.0
        if not np.any(values > 0.0):
            raise RuntimeError("全部接受事件都没有解析响应支撑。")
        values = values.reshape(sky_count, energy_count)
        return SensitivityMap(
            kind=SensitivityKind.CONDITIONAL_ACCEPTANCE_PROBABILITY,
            values=values,
            standard_error=np.zeros_like(values),
            unit="1",
            definition=(
                "stage5 prototype union-support unit sensitivity; "
                "not a physical detector sensitivity"
            ),
            metadata={"physical_use_allowed": False},
        )

    def run(self):
        reconstruction = self.config.reconstruction
        visualization = self.config.visualization
        output = self.config.output
        if reconstruction is None or visualization is None or output is None:
            raise RuntimeError("阶段 5 必须配置 reconstruction/visualization/output。")
        started = time.perf_counter()
        source = EventSourceFactory(self.config).create()
        trigger = TriggerPolicy(
            self.config.trigger.minimum_hit_energy_mev,
            self.config.trigger.coincidence_window_ns,
        )
        ingested = EventIngestionPipeline(source, trigger).run()
        events = tuple(event.observable_copy() for event in ingested.accepted_events)
        if not events:
            raise RuntimeError("触发后没有可重建事件。")

        energy_grid = self._energy_grid()
        sky_grid = HealpixSkyGrid(
            self.config.sky_grid.nside, self.config.sky_grid.nested
        )
        response_model, sensitivity, physical_use_allowed, response_provenance = (
            self._prepare_response(sky_grid, energy_grid)
        )
        kernel_batch = EventKernelBuilder(
            response_model, sky_grid, energy_grid
        ).build(events)
        if sensitivity is None:
            sensitivity = self._prototype_sensitivity(
                kernel_batch, sky_grid.pixel_count, energy_grid.bin_count
            )
        if reconstruction.sensitivity_kind != sensitivity.kind.value:
            raise RuntimeError("重建配置的灵敏度类型与事件响应不一致。")

        recorder = IterationRecorder(
            self.context.paths.numerical_directory,
            self.context.paths.checkpoint_directory,
            sky_grid.pixel_count,
            energy_grid.bin_count,
            reconstruction.snapshot_first_iterations,
            reconstruction.snapshot_interval,
        )
        solver = ListModeMlemSolver(
            LmMlemConfig(
                maximum_iterations=reconstruction.maximum_iterations,
                minimum_iterations=reconstruction.minimum_iterations,
                denominator_floor=reconstruction.denominator_floor,
                sensitivity_floor=reconstruction.sensitivity_floor,
                likelihood_relative_tolerance=(
                    reconstruction.likelihood_relative_tolerance
                ),
                image_relative_tolerance=(
                    reconstruction.image_relative_tolerance
                ),
                convergence_patience=reconstruction.convergence_patience,
            )
        )

        def observe(metrics, image, is_final):
            recorder.record(metrics, image, force_snapshot=is_final)

        background = self.config.background
        background_density = None
        background_expected_count = 0.0
        background_mode = "none"
        if background is not None:
            background_mode = background.mode
            background_expected_count = background.expected_count
            if background.mode == "fixed_uniform_event_density":
                background_density = np.full(
                    len(kernel_batch.responses), background.event_density, dtype=float
                )
        if (
            response_model.model_id == "hybrid_monte_carlo_arm_v1"
            and kernel_batch.unsupported_event_ids
            and background_density is None
        ):
            raise RuntimeError(
                "混合响应存在不可解释事件；必须配置非零 background/outlier 分量。"
            )

        result = solver.run(
            kernel_batch.responses,
            sensitivity,
            background_event_density=background_density,
            background_expected_count=background_expected_count,
            initial_image=self.initial_image,
            sky_directions=sky_grid.all_pixel_directions(),
            energy_centers_mev=energy_grid.centers_mev,
            observer=observe,
        )
        recorder.finalize(
            result.stop_reason.value,
            result.completed_iterations,
            result.telemetry[-1],
            result.image,
        )

        writer = ReconstructionResultWriter(self.context, output)
        joint_standard_error, uncertainty_metadata = (
            DiagonalFisherUncertainty.estimate(
                result.image,
                kernel_batch.responses,
                reconstruction.denominator_floor,
                background_event_density=background_density,
            )
        )
        joint_error = joint_standard_error.reshape(
            sky_grid.pixel_count, energy_grid.bin_count
        )
        energy_standard_error = np.sqrt(np.nansum(joint_error ** 2, axis=0))
        joint_path = writer.write_joint_image(
            result.image,
            energy_grid,
            sky_grid,
            joint_standard_error=joint_error,
            uncertainty_metadata=uncertainty_metadata,
        )
        event_path = writer.write_event_summary(events, kernel_batch.responses)
        ingestion_summary = {
            "accepted_event_count": len(ingested.accepted_events),
            "rejected_event_count": len(ingested.rejected_events),
            "rejected_event_ids": [
                event.event_id for event in ingested.rejected_events
            ],
        }
        dataset_path = writer.write_dataset_metadata(
            ingested.dataset, ingestion_summary
        )
        figure_paths = {}
        if visualization.enabled:
            figure_paths = EiidFigureSuite(
                self.context.paths.figure_directory,
                visualization,
                self.config.coordinates.camera_boresight_source_direction,
                physical_use_allowed=physical_use_allowed,
                response_label=response_provenance["response_semantics"],
            ).render(
                result.image,
                energy_grid,
                sky_grid,
                result.telemetry,
                energy_standard_error=energy_standard_error,
                event_responses=kernel_batch.responses,
            )

        joint = result.image.reshape(
            sky_grid.pixel_count, energy_grid.bin_count
        )
        peak = int(np.argmax(result.image))
        summary = {
            "status": "ok",
            "stage": "production_end_to_end",
            "run_id": self.context.run_id,
            "dataset_id": ingested.dataset.metadata.dataset_id,
            "accepted_event_count": len(events),
            "rejected_event_count": len(ingested.rejected_events),
            "supported_event_count": len(kernel_batch.supported_event_ids),
            "unsupported_event_count": len(kernel_batch.unsupported_event_ids),
            "kernel_summary": dict(kernel_batch.summary),
            "stop_reason": result.stop_reason.value,
            "completed_iterations": result.completed_iterations,
            "initial_log_likelihood": result.telemetry[0].log_likelihood,
            "final_log_likelihood": result.telemetry[-1].log_likelihood,
            "sky_centroid_direction": result.telemetry[-1].sky_centroid_direction,
            "sky_r68_deg": result.telemetry[-1].sky_r68_deg,
            "energy_weighted_mean_mev": result.telemetry[-1].energy_weighted_mean_mev,
            "peak_sky_pixel_index": peak // energy_grid.bin_count,
            "peak_energy_bin_index": peak % energy_grid.bin_count,
            "peak_energy_mev": float(
                energy_grid.centers_mev[peak % energy_grid.bin_count]
            ),
            "total_reconstructed_intensity": float(np.sum(joint)),
            "elapsed_seconds": time.perf_counter() - started,
            "physical_use_allowed": physical_use_allowed,
            "response_provenance": response_provenance,
            "response_semantics": response_provenance["response_semantics"],
            "background": {
                "mode": background_mode,
                "event_density": 0.0 if background is None else background.event_density,
                "expected_count": background_expected_count,
            },
            "uncertainty": uncertainty_metadata,
            "resumed_from_run_id": self.resumed_from_run_id,
            "numerical_outputs": {
                "joint_image": str(joint_path),
                "event_summary": str(event_path),
                "dataset_metadata": str(dataset_path),
            },
            "figure_outputs": dict(figure_paths),
        }
        summary_path = writer.write_reconstruction_summary(summary)
        summary["numerical_outputs"]["reconstruction_summary"] = str(
            summary_path
        )
        return summary
