#!/usr/bin/env python3
"""阶段 1 小规模验证入口，不读取 ROOT，也不产生重建结果文件。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eiid.batch import MemoryGuardPolicy, SystemMemoryMonitor
from eiid.configuration import load_config
from eiid.coordinates import CoordinateConvention, HealpixSkyGrid
from eiid.detector import ChannelMapping, TriggerPolicy
from eiid.domain import Channel, DigitizedHit, EnergyGrid, MeasuredEvent
from eiid.physics import ComptonKinematics


def _hit(hit_id, channel, layer, z_mm, energy_mev, time_ns):
    return DigitizedHit(
        hit_id=hit_id,
        channel=channel,
        layer=layer,
        pixel_id="0",
        position_mm=[0.0, 0.0, z_mm],
        energy_mev=energy_mev,
        time_ns=time_ns,
    )


def validate(config_path: str):
    """执行配置、坐标、触发、网格、运动学和内存策略闭环。"""

    config = load_config(config_path)
    convention = CoordinateConvention(
        config.coordinates.detector_stack_direction,
        config.coordinates.camera_boresight_source_direction,
    )
    mapping = ChannelMapping(
        config.chamber_to_channel,
        config.channel_to_layer,
    )
    energy_config = config.energy_grid
    if energy_config.bin_width_mev is not None:
        energy_grid = EnergyGrid.uniform(
            energy_config.minimum_mev,
            energy_config.maximum_mev,
            energy_config.bin_width_mev,
        )
    else:
        energy_grid = EnergyGrid.nonuniform(energy_config.edges_mev)
    sky_grid = HealpixSkyGrid(config.sky_grid.nside, config.sky_grid.nested)
    trigger = TriggerPolicy(
        config.trigger.minimum_hit_energy_mev,
        config.trigger.coincidence_window_ns,
    )

    event = MeasuredEvent(
        event_id="foundation:center_forward",
        hits=(
            _hit("h_ch2", Channel.CH2, 0, -30.0, 0.15, 10.0),
            _hit("h_ch1", Channel.CH1, 1, -0.399, 0.20, 10.0),
            _hit("h_ch0", Channel.CH0, 2, 40.702, 0.10, 10.0),
        ),
    )
    decision = trigger.evaluate(event)
    if not decision.accepted:
        raise RuntimeError("基础事件未通过已确定的 ch1+ch2 触发。")

    source_axis = ComptonKinematics.source_side_axis(
        event.hits[0].position_mm,
        event.hits[1].position_mm,
    )
    if not convention.is_camera_front(source_axis):
        raise RuntimeError("来源侧圆锥轴未落在相机前半球，坐标符号可能反转。")
    angle = ComptonKinematics.scatter_angle_rad(0.662, 0.15)
    if angle is None:
        raise RuntimeError("构造的康普顿候选能量不应被判为无效。")

    snapshot = SystemMemoryMonitor().snapshot()
    memory_config = config.batch.memory_guard
    memory_policy = MemoryGuardPolicy(
        enabled=memory_config.enabled,
        minimum_available_gib=memory_config.minimum_available_gib,
        estimated_worker_peak_gib=memory_config.estimated_worker_peak_gib,
    )
    safe_workers = memory_policy.safe_worker_capacity(
        snapshot.available_bytes,
        config.batch.maximum_workers,
    )

    return {
        "status": "ok",
        "schema_version": config.schema_version,
        "profile_purpose": config.profile_purpose,
        "coordinate": {
            "detector_stack_direction": list(
                convention.detector_stack_direction
            ),
            "camera_boresight_source_direction": list(
                convention.camera_boresight_source_direction
            ),
            "center_source_axis": source_axis.tolist(),
        },
        "mapping": {
            "chamber_0": mapping.channel_for_chamber(0).value,
            "chamber_1": mapping.channel_for_chamber(1).value,
            "chamber_2": mapping.channel_for_chamber(2).value,
        },
        "trigger": {
            "accepted": decision.accepted,
            "valid_hit_ids": list(decision.valid_hit_ids),
        },
        "energy_grid": {
            "minimum_mev": float(energy_grid.edges_mev[0]),
            "maximum_mev": float(energy_grid.edges_mev[-1]),
            "bin_count": energy_grid.bin_count,
        },
        "sky_grid": {
            "type": "healpix",
            "nside": sky_grid.nside,
            "pixel_count": sky_grid.pixel_count,
        },
        "memory": {
            "total_gib": round(snapshot.total_gib, 3),
            "available_gib": round(snapshot.available_gib, 3),
            "configured_worker_upper_bound": config.batch.maximum_workers,
            "safe_worker_capacity_now": safe_workers,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="验证 EIID 阶段 1 基础约定。")
    parser.add_argument("--config", required=True, help="JSON/YAML 配置文件路径。")
    arguments = parser.parse_args()
    result = validate(arguments.config)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()

