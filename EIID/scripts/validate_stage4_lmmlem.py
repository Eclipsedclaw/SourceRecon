#!/usr/bin/env python3
"""阶段 4 统一运行身份、LM-MLEM、遥测和 checkpoint 闭环验证。"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eiid.application import RunContext
from eiid.configuration import load_config
from eiid.convergence import IterationRecorder
from eiid.reconstruction import LmMlemConfig, ListModeMlemSolver
from eiid.response import SensitivityKind, SensitivityMap, SparseEventResponse


def _synthetic_problem(config):
    """构造两个联合单元、两类观测的可解析稀疏 list-mode 问题。"""

    sky_count = 12 * config.sky_grid.nside * config.sky_grid.nside
    if config.energy_grid.bin_width_mev is None:
        energy_count = len(config.energy_grid.edges_mev) - 1
    else:
        energy_count = int(
            round(
                (config.energy_grid.maximum_mev - config.energy_grid.minimum_mev)
                / config.energy_grid.bin_width_mev
            )
        )
    cell_count = sky_count * energy_count
    source_a = 0 * energy_count + 5
    source_b = 1 * energy_count + 10

    responses = []
    for index in range(24):
        responses.append(
            SparseEventResponse(
                event_id="class_a:{:03d}".format(index),
                cell_count=cell_count,
                cell_indices=np.asarray([source_a, source_b]),
                values=np.asarray([0.8, 0.1]),
                model_id="stage4_synthetic_matrix",
                diagnostics={"event_group": "class_a"},
            )
        )
    for index in range(10):
        responses.append(
            SparseEventResponse(
                event_id="class_b:{:03d}".format(index),
                cell_count=cell_count,
                cell_indices=np.asarray([source_a, source_b]),
                values=np.asarray([0.2, 0.9]),
                model_id="stage4_synthetic_matrix",
                diagnostics={"event_group": "class_b"},
            )
        )

    values = np.zeros((sky_count, energy_count), dtype=float)
    # 灵敏度是两个离散可接受观测类别上的响应积分。
    values.reshape(-1)[source_a] = 0.8 + 0.2
    values.reshape(-1)[source_b] = 0.1 + 0.9
    sensitivity = SensitivityMap(
        kind=SensitivityKind.CONDITIONAL_ACCEPTANCE_PROBABILITY,
        values=values,
        standard_error=np.zeros_like(values),
        unit="1",
        definition=(
            "stage4 synthetic discrete accepted-data space; "
            "not a Geant4 physical response"
        ),
        metadata={"physical_use_allowed": False},
    )
    return responses, sensitivity, source_a, source_b


def validate(config_path: str, run_id=None, log_path=None):
    config = load_config(config_path)
    if config.reconstruction is None:
        raise RuntimeError("阶段 4 配置必须包含 reconstruction。")
    context = RunContext.start(
        config,
        run_kind="stage4_lmmlem",
        run_id=run_id,
        log_path=log_path,
    )
    try:
        result = _validate(config, context)
        context.mark_success(result, stop_reason=result["stop_reason"])
        return result
    except BaseException as error:
        if context.status == "running":
            reason = "user_interrupt" if isinstance(error, KeyboardInterrupt) else "exception"
            context.mark_failure(error, stop_reason=reason)
        raise


def _validate(config, context):
    reconstruction = config.reconstruction
    responses, sensitivity, source_a, source_b = _synthetic_problem(config)
    if reconstruction.sensitivity_kind != sensitivity.kind.value:
        raise RuntimeError("配置选择的灵敏度物理定义与响应不一致。")
    solver = ListModeMlemSolver(
        LmMlemConfig(
            maximum_iterations=reconstruction.maximum_iterations,
            minimum_iterations=reconstruction.minimum_iterations,
            denominator_floor=reconstruction.denominator_floor,
            sensitivity_floor=reconstruction.sensitivity_floor,
            likelihood_relative_tolerance=(
                reconstruction.likelihood_relative_tolerance
            ),
            image_relative_tolerance=reconstruction.image_relative_tolerance,
            convergence_patience=reconstruction.convergence_patience,
        )
    )
    recorder = IterationRecorder(
        numerical_directory=context.paths.numerical_directory,
        checkpoint_directory=context.paths.checkpoint_directory,
        sky_pixel_count=sensitivity.shape[0],
        energy_bin_count=sensitivity.shape[1],
        snapshot_first_iterations=reconstruction.snapshot_first_iterations,
        snapshot_interval=reconstruction.snapshot_interval,
    )

    def observe(metrics, image, is_final):
        recorder.record(metrics, image, force_snapshot=is_final)

    reconstruction_result = solver.run(
        responses=responses,
        sensitivity_map=sensitivity,
        observer=observe,
    )
    final_metrics = reconstruction_result.telemetry[-1]
    recorder.finalize(
        stop_reason=reconstruction_result.stop_reason.value,
        completed_iterations=reconstruction_result.completed_iterations,
        final_metrics=final_metrics,
        final_image=reconstruction_result.image,
    )

    likelihood = np.asarray(
        [item.log_likelihood for item in reconstruction_result.telemetry]
    )
    if np.any(np.diff(likelihood) < -1e-9):
        raise RuntimeError("无正则 LM-MLEM 的 Poisson 对数似然出现显著下降。")
    if int(np.argmax(reconstruction_result.image)) != source_a:
        raise RuntimeError("stage4 synthetic 主源联合单元未被正确恢复。")
    if reconstruction_result.image[source_a] <= reconstruction_result.image[source_b]:
        raise RuntimeError("stage4 synthetic 主源强度应大于次源。")

    run_files = {
        "manifest": str(context.paths.manifest_path),
        "configuration_snapshot": str(context.paths.configuration_snapshot_path),
        "iteration_metrics": str(recorder.metrics_path),
        "convergence_summary": str(recorder.summary_path),
        "checkpoint_directory": str(context.paths.checkpoint_directory),
        "log": str(context.paths.log_path),
    }
    return {
        "status": "ok",
        "stage": 4,
        "run_id": context.run_id,
        "run_directory": str(context.paths.run_directory),
        "stop_reason": reconstruction_result.stop_reason.value,
        "completed_iterations": reconstruction_result.completed_iterations,
        "iteration_metric_count": len(reconstruction_result.telemetry),
        "initial_log_likelihood": float(likelihood[0]),
        "final_log_likelihood": float(likelihood[-1]),
        "likelihood_monotonic": True,
        "main_source_cell_index": source_a,
        "secondary_source_cell_index": source_b,
        "main_source_intensity": float(reconstruction_result.image[source_a]),
        "secondary_source_intensity": float(reconstruction_result.image[source_b]),
        "zero_sensitivity_cell_count": int(
            np.count_nonzero(
                sensitivity.values.reshape(-1)
                <= reconstruction.sensitivity_floor
            )
        ),
        "run_files": run_files,
        "formal_physical_response_used": False,
    }


def main():
    parser = argparse.ArgumentParser(description="验证阶段 4 LM-MLEM 与运行生命周期。")
    parser.add_argument("--config", required=True)
    arguments = parser.parse_args()
    print(
        json.dumps(
            validate(
                arguments.config,
                run_id=os.environ.get("EIID_RUN_ID") or None,
                log_path=os.environ.get("EIID_LOG_PATH") or None,
            ),
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
