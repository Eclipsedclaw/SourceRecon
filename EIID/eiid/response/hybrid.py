"""解析康普顿运动学与离线蒙特卡洛标定量组合的混合响应。"""

from __future__ import annotations

import numpy as np

from eiid.domain import Channel, SequenceClass
from eiid.physics import ComptonKinematics

from .analytic import AnalyticComptonResponse
from .base import EventResponseModel
from .sparse import SparseEventResponse


class HybridMonteCarloResponse(EventResponseModel):
    """使用逐方向、逐能量 ARM 和效率的第一版混合事件核。

    `arm_sigma_deg` 与所选物理灵敏度必须来自同一响应库。核中包含灵敏度，
    因而对观测数据空间积分后与 LM-MLEM 分母中的 s(Ω,E) 定义一致。
    """

    model_id = "hybrid_monte_carlo_arm_v1"
    response_semantics = "hybrid_calibrated_event_density"

    def __init__(
        self,
        arm_sigma_deg,
        sensitivity_values,
        minimum_relative_weight=1e-8,
        modeled_topology_probability=None,
    ):
        sigma = np.deg2rad(np.asarray(arm_sigma_deg, dtype=float))
        sensitivity = np.asarray(sensitivity_values, dtype=float)
        if sigma.ndim != 2 or sigma.shape != sensitivity.shape:
            raise ValueError("arm_sigma_deg 与灵敏度必须是同形状二维数组。")
        if np.any(~np.isfinite(sigma)) or np.any(sigma <= 0.0):
            raise ValueError("arm_sigma_deg 必须全部为正有限数。")
        if np.any(~np.isfinite(sensitivity)) or np.any(sensitivity < 0.0):
            raise ValueError("混合响应灵敏度必须为非负有限数。")
        threshold = float(minimum_relative_weight)
        if threshold < 0.0 or threshold >= 1.0:
            raise ValueError("minimum_relative_weight 必须位于 [0,1)。")
        self.arm_sigma_rad = sigma
        self.sensitivity = sensitivity
        topology = (
            np.ones_like(sensitivity)
            if modeled_topology_probability is None
            else np.asarray(modeled_topology_probability, dtype=float)
        )
        if topology.shape != sensitivity.shape or np.any(~np.isfinite(topology)) or np.any(topology < 0.0) or np.any(topology > 1.0):
            raise ValueError("modeled_topology_probability 必须是同形状的 [0,1] 数组。")
        self.modeled_topology_probability = topology
        self.minimum_relative_weight = threshold

    def evaluate(self, event, sky_directions, energy_grid):
        directions = AnalyticComptonResponse._normalized_directions(sky_directions)
        expected = (directions.shape[0], energy_grid.bin_count)
        if self.arm_sigma_rad.shape != expected:
            raise ValueError("重建网格与响应库网格不一致；必须显式重采样后再重建。")
        cell_count = expected[0] * expected[1]
        if event.sequence_class == SequenceClass.BACKSCATTER:
            return SparseEventResponse.empty(
                event.event_id, cell_count, self.model_id,
                "backscatter_component_not_enabled_preserved_as_outlier",
            )
        first = AnalyticComptonResponse._aggregate_channel(event, Channel.CH2)
        second = AnalyticComptonResponse._aggregate_channel(event, Channel.CH1)
        if first is None or second is None:
            return SparseEventResponse.empty(
                event.event_id, cell_count, self.model_id, "missing_ch1_or_ch2"
            )
        first_energy, first_position = first
        second_energy, second_position = second
        try:
            axis = ComptonKinematics.source_side_axis(first_position, second_position)
        except ValueError:
            return SparseEventResponse.empty(
                event.event_id, cell_count, self.model_id,
                "coincident_representative_positions",
            )
        polar = np.arccos(np.clip(directions @ axis, -1.0, 1.0))
        indices = []
        values = []
        for energy_index, incident_energy in enumerate(energy_grid.centers_mev):
            if incident_energy - first_energy + 1e-12 < second_energy:
                continue
            scatter = ComptonKinematics.scatter_angle_rad(float(incident_energy), first_energy)
            if scatter is None:
                continue
            sigma = self.arm_sigma_rad[:, energy_index]
            relative = np.exp(-0.5 * ((polar - scatter) / sigma) ** 2)
            # ARM 残差按一维高斯密度归一化，使不同 sigma 的能量节点可比较。
            density = relative / (np.sqrt(2.0 * np.pi) * sigma)
            weights = (
                density
                * self.sensitivity[:, energy_index]
                * self.modeled_topology_probability[:, energy_index]
            )
            scale = float(np.max(relative))
            selected = np.flatnonzero(
                (relative >= self.minimum_relative_weight * max(scale, 1e-300))
                & (weights > 0.0)
            )
            indices.extend((selected * energy_grid.bin_count + energy_index).tolist())
            values.extend(weights[selected].tolist())
        if not indices:
            return SparseEventResponse.empty(
                event.event_id, cell_count, self.model_id,
                "no_supported_sky_energy_cell",
            )
        return SparseEventResponse(
            event_id=event.event_id,
            cell_count=cell_count,
            cell_indices=np.asarray(indices, dtype=np.int64),
            values=np.asarray(values, dtype=float),
            model_id=self.model_id,
            diagnostics={
                "response_semantics": self.response_semantics,
                "event_group": event.sequence_class.value,
                "input_hit_count": len(event.hits),
            },
        )
