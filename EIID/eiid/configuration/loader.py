"""JSON/YAML 配置读取器。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

from .models import (
    BatchConfig,
    BackgroundConfig,
    CoordinateConfig,
    EiidConfig,
    EnergyGridConfig,
    EventResponseConfig,
    MemoryGuardConfig,
    OutputConfig,
    ProjectPathsConfig,
    ReconstructionConfig,
    ResponseConfig,
    RuntimeConfig,
    SkyGridConfig,
    TriggerConfig,
    VisualizationConfig,
)
from .validation import (
    require_keys,
    require_mapping,
    validate_coordinate_pair,
    validate_first_version_energy_range,
    validate_mapping,
    validate_trigger,
    vector3,
)


class ConfigurationError(ValueError):
    """配置文件格式正确但内容不满足 EIID 约束。"""


def _read_payload(path: Path) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    try:
        with path.open("r", encoding="utf-8") as stream:
            if suffix == ".json":
                payload = json.load(stream)
            elif suffix in (".yaml", ".yml"):
                try:
                    import yaml
                except ImportError as error:
                    raise ImportError(
                        "读取 YAML 配置需要 PyYAML；也可以直接使用 JSON 配置。"
                    ) from error
                payload = yaml.safe_load(stream)
            else:
                raise ConfigurationError("配置扩展名必须是 .json/.yaml/.yml。")
    except json.JSONDecodeError as error:
        raise ConfigurationError("JSON 配置解析失败：" + str(error)) from error
    if not isinstance(payload, dict):
        raise ConfigurationError("配置顶层必须是 object。")
    return payload


def load_config(path_value: str) -> EiidConfig:
    """读取、类型化并验证 EIID 配置。"""

    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError("找不到 EIID 配置文件：" + str(path))
    payload = _read_payload(path)
    try:
        require_keys(
            payload,
            (
                "schema_version",
                "profile_purpose",
                "paths",
                "coordinates",
                "channel_mapping",
                "energy_grid",
                "sky_grid",
                "trigger",
                "runtime",
                "batch",
            ),
            "配置顶层",
        )
        if str(payload["schema_version"]) != "0.1.0":
            raise ValueError("阶段 1 只支持 schema_version=0.1.0。")

        paths = require_mapping(payload["paths"], "paths")
        require_keys(
            paths,
            ("project_root", "input_root", "response_root", "output_root", "log_root"),
            "paths",
        )
        def resolve_config_path(value):
            candidate = Path(str(value)).expanduser()
            if candidate.is_absolute():
                return candidate.resolve()
            return (path.parent / candidate).resolve()

        project_root = resolve_config_path(paths["project_root"])
        resolved_roots = {
            name: resolve_config_path(paths[name])
            for name in ("input_root", "response_root", "output_root", "log_root")
        }
        for name, candidate in resolved_roots.items():
            try:
                candidate.relative_to(project_root)
            except ValueError as error:
                raise ValueError(
                    "paths." + name + " 必须位于 paths.project_root 下。"
                ) from error

        coordinates = require_mapping(payload["coordinates"], "coordinates")
        require_keys(
            coordinates,
            ("detector_stack_direction", "camera_boresight_source_direction"),
            "coordinates",
        )
        stack = vector3(coordinates["detector_stack_direction"], "堆叠方向")
        boresight = vector3(
            coordinates["camera_boresight_source_direction"], "相机正前方来源方向"
        )
        validate_coordinate_pair(stack, boresight)

        mapping = require_mapping(payload["channel_mapping"], "channel_mapping")
        require_keys(mapping, ("chamber_to_channel", "channel_to_layer"), "channel_mapping")
        chamber_to_channel = {
            int(key): str(value)
            for key, value in require_mapping(
                mapping["chamber_to_channel"], "chamber_to_channel"
            ).items()
        }
        channel_to_layer = {
            str(key): int(value)
            for key, value in require_mapping(
                mapping["channel_to_layer"], "channel_to_layer"
            ).items()
        }
        validate_mapping(chamber_to_channel, channel_to_layer)

        energy = require_mapping(payload["energy_grid"], "energy_grid")
        require_keys(energy, ("minimum_mev", "maximum_mev"), "energy_grid")
        minimum = float(energy["minimum_mev"])
        maximum = float(energy["maximum_mev"])
        validate_first_version_energy_range(minimum, maximum)
        has_width = energy.get("bin_width_mev") is not None
        has_edges = energy.get("edges_mev") is not None
        if has_width == has_edges:
            raise ValueError("energy_grid 必须且只能配置 bin_width_mev 或 edges_mev。")
        bin_width = float(energy["bin_width_mev"]) if has_width else None
        edges = (
            tuple(float(item) for item in energy["edges_mev"])
            if has_edges
            else None
        )

        sky = require_mapping(payload["sky_grid"], "sky_grid")
        require_keys(sky, ("type", "nside", "nested"), "sky_grid")
        if str(sky["type"]) != "healpix":
            raise ValueError("第一版 sky_grid.type 必须是 healpix。")

        trigger = require_mapping(payload["trigger"], "trigger")
        require_keys(trigger, ("required_channels", "minimum_hit_energy_mev"), "trigger")
        required_channels = tuple(str(item) for item in trigger["required_channels"])
        thresholds = {
            str(key): float(value)
            for key, value in require_mapping(
                trigger["minimum_hit_energy_mev"], "minimum_hit_energy_mev"
            ).items()
        }
        validate_trigger(required_channels, thresholds)
        coincidence = trigger.get("coincidence_window_ns")
        coincidence = None if coincidence is None else float(coincidence)
        if coincidence is not None and coincidence <= 0.0:
            raise ValueError("coincidence_window_ns 必须为正数或 null。")

        runtime = require_mapping(payload["runtime"], "runtime")
        require_keys(runtime, ("numerical_threads_per_worker",), "runtime")
        thread_count = int(runtime["numerical_threads_per_worker"])
        if thread_count <= 0:
            raise ValueError("numerical_threads_per_worker 必须大于 0。")

        batch = require_mapping(payload["batch"], "batch")
        require_keys(batch, ("maximum_workers", "memory_guard"), "batch")
        maximum_workers = int(batch["maximum_workers"])
        if maximum_workers <= 0:
            raise ValueError("batch.maximum_workers 必须大于 0。")
        memory = require_mapping(batch["memory_guard"], "batch.memory_guard")
        require_keys(
            memory,
            ("enabled", "minimum_available_gib", "estimated_worker_peak_gib"),
            "batch.memory_guard",
        )
        minimum_available_gib = float(memory["minimum_available_gib"])
        estimated_worker_peak_gib = float(memory["estimated_worker_peak_gib"])
        poll_interval = float(memory.get("poll_interval_seconds", 2.0))
        maximum_retries = int(memory.get("maximum_retries", 2))
        if minimum_available_gib <= 0.0 or estimated_worker_peak_gib <= 0.0:
            raise ValueError("内存保留量和 worker 峰值估计必须大于 0。")
        if poll_interval <= 0.0 or maximum_retries < 0:
            raise ValueError("内存轮询间隔必须为正，重试次数不能为负。")

        response_config = None
        response_payload = payload.get("response")
        if response_payload is not None:
            response = require_mapping(response_payload, "response")
            require_keys(
                response,
                ("adapter", "library_path", "library_status"),
                "response",
            )
            adapter = str(response["adapter"]).strip()
            library_status = str(response["library_status"]).strip()
            if not adapter or not library_status:
                raise ValueError("response.adapter/library_status 不能为空。")
            if adapter not in {
                "prototype_npz_json", "prototype_npz_json_v1", "portable_npz_json_v1"
            }:
                raise ValueError("response.adapter 不是已注册适配器。")
            if library_status not in {
                "prototype_not_formal", "candidate_unvalidated", "validated_physical"
            }:
                raise ValueError("response.library_status 不是受支持状态。")
            library_path = resolve_config_path(response["library_path"])
            try:
                library_path.relative_to(resolved_roots["response_root"])
            except ValueError as error:
                raise ValueError(
                    "response.library_path 必须位于 paths.response_root 下。"
                ) from error
            overwrite_existing = response.get("overwrite_existing", False)
            if not isinstance(overwrite_existing, bool):
                raise ValueError("response.overwrite_existing 必须是布尔值。")
            parameters = require_mapping(
                response.get("parameters", {}), "response.parameters"
            )
            response_config = ResponseConfig(
                adapter=adapter,
                library_path=library_path,
                library_status=library_status,
                overwrite_existing=overwrite_existing,
                parameters=dict(parameters),
            )

        reconstruction_config = None
        reconstruction_payload = payload.get("reconstruction")
        if reconstruction_payload is not None:
            reconstruction = require_mapping(
                reconstruction_payload, "reconstruction"
            )
            require_keys(
                reconstruction,
                (
                    "sensitivity_kind",
                    "maximum_iterations",
                    "minimum_iterations",
                    "denominator_floor",
                    "sensitivity_floor",
                    "convergence_patience",
                    "snapshot_first_iterations",
                    "snapshot_interval",
                ),
                "reconstruction",
            )
            sensitivity_kind = str(reconstruction["sensitivity_kind"]).strip()
            allowed_sensitivity = {
                "conditional_acceptance_probability",
                "effective_area_cm2",
                "finite_distance_emitted_probability",
            }
            if sensitivity_kind not in allowed_sensitivity:
                raise ValueError("reconstruction.sensitivity_kind 未明确选择物理定义。")
            maximum_iterations = int(reconstruction["maximum_iterations"])
            minimum_iterations = int(reconstruction["minimum_iterations"])
            denominator_floor = float(reconstruction["denominator_floor"])
            sensitivity_floor = float(reconstruction["sensitivity_floor"])
            patience = int(reconstruction["convergence_patience"])
            snapshot_first = int(reconstruction["snapshot_first_iterations"])
            snapshot_interval = int(reconstruction["snapshot_interval"])
            likelihood_value = reconstruction.get("likelihood_relative_tolerance")
            image_value = reconstruction.get("image_relative_tolerance")
            likelihood_tolerance = (
                None if likelihood_value is None else float(likelihood_value)
            )
            image_tolerance = None if image_value is None else float(image_value)
            if maximum_iterations <= 0:
                raise ValueError("reconstruction.maximum_iterations 必须大于 0。")
            if minimum_iterations < 0 or minimum_iterations > maximum_iterations:
                raise ValueError("reconstruction.minimum_iterations 范围无效。")
            if denominator_floor <= 0.0 or sensitivity_floor < 0.0:
                raise ValueError("reconstruction 数值下限无效。")
            if patience <= 0 or snapshot_first < 0 or snapshot_interval <= 0:
                raise ValueError("reconstruction 早停或快照参数无效。")
            for label, value in (
                ("likelihood_relative_tolerance", likelihood_tolerance),
                ("image_relative_tolerance", image_tolerance),
            ):
                if value is not None and value <= 0.0:
                    raise ValueError("reconstruction." + label + " 必须为正或 null。")
            reconstruction_config = ReconstructionConfig(
                sensitivity_kind=sensitivity_kind,
                maximum_iterations=maximum_iterations,
                minimum_iterations=minimum_iterations,
                denominator_floor=denominator_floor,
                sensitivity_floor=sensitivity_floor,
                likelihood_relative_tolerance=likelihood_tolerance,
                image_relative_tolerance=image_tolerance,
                convergence_patience=patience,
                snapshot_first_iterations=snapshot_first,
                snapshot_interval=snapshot_interval,
            )

        event_response_config = None
        event_response_payload = payload.get("event_response")
        if event_response_payload is not None:
            event_response = require_mapping(
                event_response_payload, "event_response"
            )
            require_keys(event_response, ("model_id", "parameters"), "event_response")
            model_id = str(event_response["model_id"]).strip()
            if not model_id:
                raise ValueError("event_response.model_id 不能为空。")
            parameters = dict(
                require_mapping(event_response["parameters"], "event_response.parameters")
            )
            if model_id == "analytic_compton_gaussian_arm_v1":
                if float(parameters.get("arm_sigma_deg", 0.0)) <= 0.0:
                    raise ValueError("解析响应必须显式配置正 arm_sigma_deg。")
                if parameters.get("allow_nonphysical_response_for_smoke") is not True:
                    raise ValueError("解析响应只允许显式的非物理 smoke。")
            elif model_id == "hybrid_monte_carlo_arm_v1":
                weight = float(parameters.get("minimum_relative_weight", -1.0))
                if weight < 0.0 or weight >= 1.0:
                    raise ValueError("混合响应 minimum_relative_weight 必须位于 [0,1)。")
                allow = parameters.get("allow_unvalidated_response", False)
                if not isinstance(allow, bool):
                    raise ValueError("allow_unvalidated_response 必须是布尔值。")
            else:
                raise ValueError("第一版不支持 event_response.model_id=" + model_id)
            event_response_config = EventResponseConfig(
                model_id=model_id,
                parameters=parameters,
            )

        background_config = None
        background_payload = payload.get("background")
        if background_payload is not None:
            background = require_mapping(background_payload, "background")
            require_keys(background, ("mode", "event_density", "expected_count"), "background")
            mode = str(background["mode"])
            if mode not in {"none", "fixed_uniform_event_density"}:
                raise ValueError("background.mode 第一版只支持 none 或 fixed_uniform_event_density。")
            event_density = float(background["event_density"])
            expected_count = float(background["expected_count"])
            if event_density < 0.0 or expected_count < 0.0:
                raise ValueError("背景密度和期望计数不能为负。")
            if mode == "none" and (event_density != 0.0 or expected_count != 0.0):
                raise ValueError("background.mode=none 时两个数值必须为 0。")
            if mode == "fixed_uniform_event_density" and event_density <= 0.0:
                raise ValueError("固定背景的 event_density 必须大于 0。")
            background_config = BackgroundConfig(mode, event_density, expected_count)

        visualization_config = None
        visualization_payload = payload.get("visualization")
        if visualization_payload is not None:
            visualization = require_mapping(
                visualization_payload, "visualization"
            )
            require_keys(
                visualization,
                (
                    "enabled",
                    "display_up_direction",
                    "smoothing_sigma_deg",
                    "smoothing_chunk_size",
                    "maximum_numpy_smoothing_pixels",
                    "raster_width",
                    "raster_height",
                    "dpi",
                    "energy_bands_mev",
                    "file_names",
                ),
                "visualization",
            )
            if not isinstance(visualization["enabled"], bool):
                raise ValueError("visualization.enabled 必须是布尔值。")
            up_direction = vector3(
                visualization["display_up_direction"],
                "visualization.display_up_direction",
            )
            if abs(sum(a * b for a, b in zip(up_direction, boresight))) > 0.999:
                raise ValueError("显示向上方向不能与相机正前方平行。")
            smoothing_sigma = float(visualization["smoothing_sigma_deg"])
            smoothing_chunk_size = int(visualization["smoothing_chunk_size"])
            maximum_smoothing_pixels = int(
                visualization["maximum_numpy_smoothing_pixels"]
            )
            raster_width = int(visualization["raster_width"])
            raster_height = int(visualization["raster_height"])
            dpi = int(visualization["dpi"])
            energy_bands = tuple(
                (float(item[0]), float(item[1]))
                for item in visualization["energy_bands_mev"]
            )
            if smoothing_sigma <= 0.0:
                raise ValueError("visualization.smoothing_sigma_deg 必须为正。")
            if smoothing_chunk_size <= 0 or maximum_smoothing_pixels <= 0:
                raise ValueError("visualization 平滑分块和像素上限必须为正。")
            if raster_width < 64 or raster_height < 32 or dpi < 50:
                raise ValueError("visualization 栅格尺寸或 dpi 过小。")
            if not energy_bands or any(
                len(item) != 2 or item[0] < minimum or item[1] > maximum or item[0] >= item[1]
                for item in energy_bands
            ):
                raise ValueError("visualization.energy_bands_mev 必须位于 0.1--3.0 MeV。")
            figure_names = {
                str(key): str(value)
                for key, value in require_mapping(
                    visualization["file_names"],
                    "visualization.file_names",
                ).items()
            }
            required_figures = {
                "full_sky_raw",
                "front_raw",
                "front_smoothed",
                "energy_spectrum",
                "joint_distribution",
                "convergence",
                "dashboard",
                "front_centered",
                "planar_projection",
                "source_zoom",
                "energy_band_skymaps",
                "iteration_snapshots",
                "event_diagnostics",
            }
            if set(figure_names) != required_figures:
                raise ValueError("visualization.file_names 必须完整配置十三类图。")
            for value in figure_names.values():
                if Path(value).name != value or not value.lower().endswith(".png"):
                    raise ValueError("可视化文件名必须是无目录的 .png 文件名。")
            if len(set(figure_names.values())) != len(figure_names):
                raise ValueError("可视化文件名不能重复。")
            visualization_config = VisualizationConfig(
                enabled=visualization["enabled"],
                display_up_direction=up_direction,
                smoothing_sigma_deg=smoothing_sigma,
                smoothing_chunk_size=smoothing_chunk_size,
                maximum_numpy_smoothing_pixels=maximum_smoothing_pixels,
                raster_width=raster_width,
                raster_height=raster_height,
                dpi=dpi,
                energy_bands_mev=energy_bands,
                file_names=figure_names,
            )

        output_config = None
        output_payload = payload.get("output")
        if output_payload is not None:
            output = require_mapping(output_payload, "output")
            require_keys(output, ("file_names",), "output")
            output_names = {
                str(key): str(value)
                for key, value in require_mapping(
                    output["file_names"], "output.file_names"
                ).items()
            }
            required_outputs = {
                "final_joint_image",
                "event_summary",
                "reconstruction_summary",
                "dataset_metadata",
            }
            if set(output_names) != required_outputs:
                raise ValueError("output.file_names 必须完整配置四类数值输出。")
            for value in output_names.values():
                if Path(value).name != value:
                    raise ValueError("数值输出文件名不能包含目录。")
            if len(set(output_names.values())) != len(output_names):
                raise ValueError("数值输出文件名不能重复。")
            output_config = OutputConfig(file_names=output_names)
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, ConfigurationError):
            raise
        raise ConfigurationError(str(error)) from error

    return EiidConfig(
        schema_version=str(payload["schema_version"]),
        profile_purpose=str(payload["profile_purpose"]),
        paths=ProjectPathsConfig(
            project_root=project_root,
            input_root=resolved_roots["input_root"],
            response_root=resolved_roots["response_root"],
            output_root=resolved_roots["output_root"],
            log_root=resolved_roots["log_root"],
        ),
        coordinates=CoordinateConfig(stack, boresight),
        chamber_to_channel=chamber_to_channel,
        channel_to_layer=channel_to_layer,
        energy_grid=EnergyGridConfig(minimum, maximum, bin_width, edges),
        sky_grid=SkyGridConfig("healpix", int(sky["nside"]), bool(sky["nested"])),
        trigger=TriggerConfig(required_channels, thresholds, coincidence),
        runtime=RuntimeConfig(thread_count),
        batch=BatchConfig(
            maximum_workers,
            MemoryGuardConfig(
                bool(memory["enabled"]),
                minimum_available_gib,
                estimated_worker_peak_gib,
                poll_interval,
                maximum_retries,
            ),
        ),
        source_path=path,
        response=response_config,
        reconstruction=reconstruction_config,
        event_response=event_response_config,
        background=background_config,
        visualization=visualization_config,
        output=output_config,
        raw_payload=payload,
    )
