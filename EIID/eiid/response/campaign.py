"""把离线 Geant4 节点统计汇总为版本化响应库。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Optional

import numpy as np

from eiid.domain import EnergyGrid

from .library import ResponseLibrary, ResponseLibraryMetadata
from .sensitivity import SensitivityBundle, SensitivityEstimator


@dataclass(frozen=True)
class ResponseNodeTable:
    """完整天空×能量节点的蒙特卡洛统计。

    行索引必须显式给出，防止依赖文件行顺序。各拓扑计数允许缺失；缺失表示
    没有生产该标定量，而不是零概率。
    """

    sky_pixel_index: np.ndarray
    energy_bin_index: np.ndarray
    generated_count: np.ndarray
    accepted_count: np.ndarray
    arm_sigma_deg: np.ndarray
    topology_counts: Mapping[str, np.ndarray]

    @classmethod
    def from_npz(cls, path_value) -> "ResponseNodeTable":
        with np.load(str(path_value), allow_pickle=False) as loaded:
            required = {
                "sky_pixel_index", "energy_bin_index", "generated_count",
                "accepted_count", "arm_sigma_deg",
            }
            missing = required.difference(loaded.files)
            if missing:
                raise ValueError("节点统计 NPZ 缺少：" + ", ".join(sorted(missing)))
            topology = {
                name[len("topology_count__"):]: np.asarray(loaded[name], dtype=float)
                for name in loaded.files
                if name.startswith("topology_count__")
            }
            return cls(
                sky_pixel_index=np.asarray(loaded["sky_pixel_index"], dtype=np.int64),
                energy_bin_index=np.asarray(loaded["energy_bin_index"], dtype=np.int64),
                generated_count=np.asarray(loaded["generated_count"], dtype=float),
                accepted_count=np.asarray(loaded["accepted_count"], dtype=float),
                arm_sigma_deg=np.asarray(loaded["arm_sigma_deg"], dtype=float),
                topology_counts=topology,
            )

    def dense(self, sky_count: int, energy_count: int):
        arrays = (
            self.sky_pixel_index, self.energy_bin_index, self.generated_count,
            self.accepted_count, self.arm_sigma_deg,
        )
        lengths = {np.asarray(item).reshape(-1).size for item in arrays}
        lengths.update(np.asarray(item).reshape(-1).size for item in self.topology_counts.values())
        if len(lengths) != 1:
            raise ValueError("节点统计全部列必须等长。")
        expected = int(sky_count) * int(energy_count)
        if next(iter(lengths)) != expected:
            raise ValueError("正式响应节点必须完整覆盖天空×能量网格。")
        sky = np.asarray(self.sky_pixel_index).reshape(-1)
        energy = np.asarray(self.energy_bin_index).reshape(-1)
        flat = sky * int(energy_count) + energy
        if np.any(sky < 0) or np.any(sky >= sky_count):
            raise ValueError("sky_pixel_index 越界。")
        if np.any(energy < 0) or np.any(energy >= energy_count):
            raise ValueError("energy_bin_index 越界。")
        if np.unique(flat).size != expected:
            raise ValueError("节点统计存在重复或缺失的天空—能量单元。")

        def arrange(values):
            result = np.empty(expected, dtype=float)
            result[flat] = np.asarray(values, dtype=float).reshape(-1)
            return result.reshape(sky_count, energy_count)

        generated = arrange(self.generated_count)
        accepted = arrange(self.accepted_count)
        arm = arrange(self.arm_sigma_deg)
        if np.any(~np.isfinite(generated)) or np.any(generated <= 0.0):
            raise ValueError("generated_count 必须全部为正有限数。")
        if np.any(~np.isfinite(accepted)) or np.any(accepted < 0.0) or np.any(accepted > generated):
            raise ValueError("accepted_count 必须满足 0<=accepted<=generated。")
        if np.any(~np.isfinite(arm)) or np.any(arm <= 0.0):
            raise ValueError("arm_sigma_deg 必须全部为正有限数。")
        topology = {}
        for name, values in self.topology_counts.items():
            counts = arrange(values)
            if np.any(~np.isfinite(counts)) or np.any(counts < 0.0) or np.any(counts > accepted):
                raise ValueError("拓扑计数必须位于 [0, accepted_count]：" + name)
            topology[str(name)] = counts
        return generated, accepted, arm, topology


class ResponseCampaignBuilder:
    """由完整节点统计生成响应库，不运行 Geant4。"""

    def build(
        self,
        node_table: ResponseNodeTable,
        energy_grid: EnergyGrid,
        sky_grid: Mapping,
        metadata: ResponseLibraryMetadata,
        normalization: Mapping,
    ) -> ResponseLibrary:
        sky_count = int(sky_grid["pixel_count"])
        generated, accepted, arm, topology = node_table.dense(
            sky_count, energy_grid.bin_count
        )
        conditional = SensitivityEstimator.conditional_acceptance(
            accepted,
            generated,
            definition=(
                "数字化后 ch1+ch2 有效 hit 且通过配置质量筛选的条件接受概率"
            ),
            metadata={
                "trigger": "valid_hit(ch1) AND valid_hit(ch2)",
                "generated_count_included_zero_deposit_events": bool(
                    normalization.get("generated_count_included_zero_deposit_events", False)
                ),
            },
        )
        if conditional.metadata["generated_count_included_zero_deposit_events"] is not True:
            raise ValueError("正式响应分母必须包含零沉积/未触发 primary。")
        source_mode = str(normalization.get("source_mode", ""))
        effective = None
        emitted = None
        if source_mode == "far_field_parallel_beam":
            effective = SensitivityEstimator.effective_area(
                conditional, float(normalization["generation_area_cm2"])
            )
        elif source_mode == "finite_distance_restricted_solid_angle":
            emitted = SensitivityEstimator.finite_distance_emitted_probability(
                conditional,
                float(normalization["restricted_solid_angle_sr"]),
                float(normalization["source_distance_mm"]),
            )
        else:
            raise ValueError("normalization.source_mode 必须明确选择远场或有限距离。")

        calibration = {"arm_sigma_deg": arm}
        safe_accepted = np.maximum(accepted, 1.0)
        for name, counts in topology.items():
            calibration["topology_probability__" + name] = counts / safe_accepted
        return ResponseLibrary(
            metadata=metadata,
            energy_grid=energy_grid,
            sky_grid=dict(sky_grid),
            sensitivities=SensitivityBundle(
                conditional=conditional,
                effective_area=effective,
                finite_distance_emitted=emitted,
            ),
            calibration_arrays=calibration,
        )


def utc_now() -> str:
    """供构建脚本记录统一 UTC 时间。"""

    return datetime.now(timezone.utc).isoformat()
