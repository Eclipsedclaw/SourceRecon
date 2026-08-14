"""用于早期联调的解析康普顿相对响应。"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

from eiid.domain import Channel, EnergyGrid, MeasuredEvent, SequenceClass
from eiid.physics import ComptonKinematics

from .base import EventResponseModel
from .sparse import SparseEventResponse


class AnalyticComptonResponse(EventResponseModel):
    """康普顿运动学 × 显式 ARM 高斯的简化响应。

    该模型只输出用于接口和算法联调的相对似然，不冒充正式归一化的
    R(d|Omega,E)。ARM 宽度必须由调用者显式给出，避免把待确认参数写成
    隐藏的固定 5 度。正式目标是用 Geant4 标定参数替换本模型。
    """

    model_id = "analytic_compton_gaussian_arm_v1"
    response_semantics = "prototype_relative_likelihood_not_normalized"

    def __init__(self, arm_sigma_rad: float, minimum_relative_weight: float = 1e-8):
        sigma = float(arm_sigma_rad)
        threshold = float(minimum_relative_weight)
        if not np.isfinite(sigma) or sigma <= 0.0:
            raise ValueError("arm_sigma_rad 必须是正有限数，并由配置或标定显式提供。")
        if not np.isfinite(threshold) or threshold < 0.0 or threshold >= 1.0:
            raise ValueError("minimum_relative_weight 必须位于 [0,1)。")
        self.arm_sigma_rad = sigma
        self.minimum_relative_weight = threshold

    @staticmethod
    def _aggregate_channel(
        event: MeasuredEvent, channel: Channel
    ) -> Optional[Tuple[float, np.ndarray]]:
        """在响应层按通道形成能量和质心，不修改或丢弃原始多像素 hit。"""

        hits = tuple(
            hit
            for hit in event.hits_in_channel(channel)
            if hit.is_valid_readout and hit.energy_mev > 0.0
        )
        if not hits:
            return None
        energies = np.asarray([hit.energy_mev for hit in hits], dtype=float)
        positions = np.asarray([hit.position_mm for hit in hits], dtype=float)
        total = float(np.sum(energies))
        centroid = np.average(positions, axis=0, weights=energies)
        return total, np.asarray(centroid, dtype=float)

    @staticmethod
    def _normalized_directions(sky_directions: np.ndarray) -> np.ndarray:
        directions = np.asarray(sky_directions, dtype=float)
        if directions.ndim != 2 or directions.shape[1] != 3 or directions.shape[0] == 0:
            raise ValueError("sky_directions 必须是非空的 (N_sky,3) 数组。")
        if not np.all(np.isfinite(directions)):
            raise ValueError("sky_directions 必须全部有限。")
        norms = np.linalg.norm(directions, axis=1)
        if np.any(norms <= 0.0):
            raise ValueError("sky_directions 不能包含零向量。")
        return directions / norms[:, np.newaxis]

    def evaluate(
        self,
        event: MeasuredEvent,
        sky_directions: np.ndarray,
        energy_grid: EnergyGrid,
    ) -> SparseEventResponse:
        directions = self._normalized_directions(sky_directions)
        energy_count = energy_grid.bin_count
        cell_count = int(directions.shape[0] * energy_count)

        if event.sequence_class == SequenceClass.BACKSCATTER:
            return SparseEventResponse.empty(
                event.event_id,
                cell_count,
                self.model_id,
                "backscatter_component_not_enabled",
            )
        first = self._aggregate_channel(event, Channel.CH2)
        second = self._aggregate_channel(event, Channel.CH1)
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
                event.event_id,
                cell_count,
                self.model_id,
                "coincident_representative_positions",
            )

        polar_angles = np.arccos(np.clip(directions @ axis, -1.0, 1.0))
        indices = []
        values = []
        feasible_energy_bins = 0
        for energy_index, incident_energy in enumerate(energy_grid.centers_mev):
            # 第二 hit 的沉积不能超过第一散射后的候选光子能量；这里允许末端逃逸。
            if incident_energy - first_energy + 1e-12 < second_energy:
                continue
            scatter_angle = ComptonKinematics.scatter_angle_rad(
                float(incident_energy), first_energy
            )
            if scatter_angle is None:
                continue
            feasible_energy_bins += 1
            residual = polar_angles - scatter_angle
            weights = np.exp(-0.5 * (residual / self.arm_sigma_rad) ** 2)
            selected = np.flatnonzero(weights >= self.minimum_relative_weight)
            indices.extend((selected * energy_count + energy_index).tolist())
            values.extend(weights[selected].tolist())

        if not indices:
            return SparseEventResponse.empty(
                event.event_id,
                cell_count,
                self.model_id,
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
                "arm_sigma_rad": self.arm_sigma_rad,
                "feasible_energy_bin_count": feasible_energy_bins,
                "input_hit_count": len(event.hits),
            },
        )
