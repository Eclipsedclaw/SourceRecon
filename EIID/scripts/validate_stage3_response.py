#!/usr/bin/env python3
"""阶段 3 响应抽象、三类灵敏度和原型响应库往返验证。"""

from __future__ import annotations

import argparse
import os
import json
from pathlib import Path
import sys

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eiid.configuration import load_config
from eiid.application import RunContext
from eiid.detector import TriggerPolicy
from eiid.domain import Channel, EnergyGrid
from eiid.io import EventIngestionPipeline, EventSourceFactory
from eiid.physics import ComptonKinematics
from eiid.response import (
    AnalyticComptonResponse,
    PrototypeNpzJsonResponseStore,
    ResponseLibrary,
    ResponseLibraryMetadata,
    SensitivityBundle,
    SensitivityEstimator,
)


def _energy_grid(config):
    if config.energy_grid.edges_mev is not None:
        return EnergyGrid.nonuniform(config.energy_grid.edges_mev)
    return EnergyGrid.uniform(
        config.energy_grid.minimum_mev,
        config.energy_grid.maximum_mev,
        config.energy_grid.bin_width_mev,
    )


def _cone_directions(event, energy_grid):
    """为若干候选能量构造精确落在圆锥上的测试方向。"""

    ch2_hits = event.hits_in_channel(Channel.CH2)
    ch1_hits = event.hits_in_channel(Channel.CH1)
    first_energy = float(sum(hit.energy_mev for hit in ch2_hits))
    second_energy = float(sum(hit.energy_mev for hit in ch1_hits))
    first_position = np.average(
        np.asarray([hit.position_mm for hit in ch2_hits]),
        axis=0,
        weights=np.asarray([hit.energy_mev for hit in ch2_hits]),
    )
    second_position = np.average(
        np.asarray([hit.position_mm for hit in ch1_hits]),
        axis=0,
        weights=np.asarray([hit.energy_mev for hit in ch1_hits]),
    )
    axis = ComptonKinematics.source_side_axis(first_position, second_position)
    reference = np.asarray([1.0, 0.0, 0.0])
    if abs(float(np.dot(axis, reference))) > 0.9:
        reference = np.asarray([0.0, 1.0, 0.0])
    perpendicular = reference - np.dot(reference, axis) * axis
    perpendicular /= np.linalg.norm(perpendicular)

    directions = []
    selected_energies = []
    for energy in energy_grid.centers_mev:
        if energy - first_energy + 1e-12 < second_energy:
            continue
        angle = ComptonKinematics.scatter_angle_rad(float(energy), first_energy)
        if angle is None:
            continue
        directions.append(np.cos(angle) * axis + np.sin(angle) * perpendicular)
        selected_energies.append(float(energy))
        if len(directions) == 3:
            break
    if len(directions) < 2:
        raise RuntimeError("阶段 3 smoke 未找到至少两个可行候选入射能量。")
    return np.asarray(directions), selected_energies


def validate(config_path: str, run_id=None, log_path=None):
    config = load_config(config_path)
    context = RunContext.start(
        config,
        run_kind="stage3_response",
        run_id=run_id,
        log_path=log_path,
    )
    try:
        result = _validate(config, context)
        context.mark_success(
            result, stop_reason="stage3_response_validation_completed"
        )
        return result
    except BaseException as error:
        if context.status == "running":
            reason = "user_interrupt" if isinstance(error, KeyboardInterrupt) else "exception"
            context.mark_failure(error, stop_reason=reason)
        raise


def _validate(config, context):
    if config.response is None:
        raise RuntimeError("阶段 3 配置必须包含 response。")
    if config.response.adapter != "prototype_npz_json":
        raise RuntimeError("本验证入口只支持明确标注为原型的 NPZ+JSON 适配器。")
    parameters = config.response.parameters
    energy_grid = _energy_grid(config)
    sky_pixel_count = 12 * config.sky_grid.nside * config.sky_grid.nside
    shape = (sky_pixel_count, energy_grid.bin_count)

    accepted = np.full(shape, float(parameters["accepted_count_per_node"]))
    generated = np.full(shape, float(parameters["generated_count_per_node"]))
    conditional = SensitivityEstimator.conditional_acceptance(
        accepted,
        generated,
        definition=str(parameters["acceptance_definition"]),
        metadata={"campaign": "stage3_synthetic_smoke"},
    )
    effective_area = SensitivityEstimator.effective_area(
        conditional, float(parameters["generation_area_cm2"])
    )
    emitted = SensitivityEstimator.finite_distance_emitted_probability(
        conditional,
        float(parameters["restricted_solid_angle_sr"]),
        float(parameters["source_distance_mm"]),
    )
    bundle = SensitivityBundle(
        conditional=conditional,
        effective_area=effective_area,
        finite_distance_emitted=emitted,
    )

    arm_sigma_rad = np.deg2rad(float(parameters["arm_sigma_deg"]))
    library = ResponseLibrary(
        metadata=ResponseLibraryMetadata(
            library_id="stage3_synthetic_smoke",
            schema_version="0.1.0",
            library_status=config.response.library_status,
            response_model_kind="hybrid_interface_synthetic_calibration",
            geometry_version=str(parameters["geometry_version"]),
            physics_list=str(parameters["physics_list"]),
            digitizer_version=str(parameters["digitizer_version"]),
            trigger_definition=str(parameters["acceptance_definition"]),
            producer_run_id=context.run_id,
            created_utc=context.started_utc,
            attributes={"physical_use_allowed": False},
        ),
        energy_grid=energy_grid,
        sky_grid={
            "type": config.sky_grid.grid_type,
            "nside": config.sky_grid.nside,
            "nested": config.sky_grid.nested,
            "pixel_count": sky_pixel_count,
        },
        sensitivities=bundle,
        calibration_arrays={"arm_sigma_rad": np.full(shape, arm_sigma_rad)},
    )
    store = PrototypeNpzJsonResponseStore()
    response_run_directory = config.response.library_path / context.run_id
    manifest_path = store.save(
        library,
        response_run_directory,
        overwrite=config.response.overwrite_existing,
    )
    loaded = store.load(response_run_directory)
    if not store.is_complete(response_run_directory):
        raise RuntimeError("响应库完成标记或 SHA-256 检查失败。")
    if not np.array_equal(loaded.energy_grid.edges_mev, energy_grid.edges_mev):
        raise RuntimeError("响应库往返后能量边界发生变化。")
    if not np.allclose(
        loaded.sensitivities.finite_distance_emitted.values,
        conditional.values
        * float(parameters["restricted_solid_angle_sr"])
        / (4.0 * np.pi),
    ):
        raise RuntimeError("s_emitted 未正确计入 Omega/(4*pi)。")

    source = EventSourceFactory(config).create()
    trigger = TriggerPolicy(
        config.trigger.minimum_hit_energy_mev,
        config.trigger.coincidence_window_ns,
    )
    ingested = EventIngestionPipeline(source, trigger).run()
    # 选取没有 ch0 的接受事件，确保验证对象确实是未知入射能量的两层事件。
    event = next(
        item.observable_copy()
        for item in ingested.accepted_events
        if not item.hits_in_channel(Channel.CH0)
    )
    directions, candidate_energies = _cone_directions(event, energy_grid)
    analytic = AnalyticComptonResponse(
        arm_sigma_rad=arm_sigma_rad,
        minimum_relative_weight=float(parameters["minimum_relative_weight"]),
    )
    sparse = analytic.evaluate(event, directions, energy_grid)
    if sparse.nonzero_count == 0:
        raise RuntimeError("解析响应未给未知能量 2-hit 事件产生任何候选单元。")
    supported_energy_bins = np.unique(
        sparse.cell_indices % energy_grid.bin_count
    ).size
    if supported_energy_bins < 2:
        raise RuntimeError("未知入射能量事件必须保留多个可行能量候选。")

    return {
        "status": "ok",
        "stage": 3,
        "run_id": context.run_id,
        "run_directory": str(context.paths.run_directory),
        "log_path": str(context.paths.log_path),
        "response_library_directory": str(response_run_directory),
        "library_status": loaded.metadata.library_status,
        "format_status": store.FORMAT_ID + " (prototype_not_formal)",
        "manifest_path": str(manifest_path),
        "sky_energy_shape": list(shape),
        "conditional_acceptance_probability": float(conditional.values[0, 0]),
        "effective_area_cm2": float(effective_area.values[0, 0]),
        "finite_distance_s_emitted": float(emitted.values[0, 0]),
        "solid_angle_fraction_of_4pi": float(
            emitted.metadata["solid_angle_fraction_of_4pi"]
        ),
        "analytic_event_id": event.event_id,
        "analytic_nonzero_cell_count": sparse.nonzero_count,
        "analytic_supported_energy_bin_count": int(supported_energy_bins),
        "example_candidate_energies_mev": candidate_energies,
        "backscatter_removed_in_io": False,
        "formal_response_format_decided": False,
    }


def main():
    parser = argparse.ArgumentParser(description="验证 EIID 阶段 3 响应与灵敏度。")
    parser.add_argument("--config", required=True)
    arguments = parser.parse_args()
    run_id = os.environ.get("EIID_RUN_ID") or None
    log_path = os.environ.get("EIID_LOG_PATH") or None
    print(
        json.dumps(
            validate(arguments.config, run_id=run_id, log_path=log_path),
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
