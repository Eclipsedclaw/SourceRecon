from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from ..domain import (
    DepositionClass,
    EnergyHypothesis,
    EventKernel,
    MeasuredEvent,
)
from ..physics import ComptonKinematics
from .spectrum import DiscreteSpectrumPrior


class EnergyResolutionModel:
    """简单但可配置的能量分辨率模型。"""

    def __init__(self, fractional_sigma: float, noise_sigma_mev: float):
        self.fractional_sigma = float(fractional_sigma)
        self.noise_sigma_mev = float(noise_sigma_mev)
        if self.fractional_sigma < 0.0 or self.noise_sigma_mev < 0.0:
            raise ValueError("能量分辨率 sigma 参数不能为负。")

    def sigma(self, energy_mev: float) -> float:
        fractional = self.fractional_sigma * float(energy_mev)
        return float(np.sqrt(fractional * fractional + self.noise_sigma_mev**2))

    def gaussian_likelihood(self, measured: float, expected: float) -> float:
        sigma = max(self.sigma(expected), 1e-9)
        residual = (float(measured) - float(expected)) / sigma
        return float(np.exp(-0.5 * residual * residual) / sigma)


class TerminalAbsorptionModel:
    """
    根据末端 channel 给出全吸收先验概率。

    ch0 较厚的事实只通过该概率进入模型，不会把 ch0 hit 硬编码为全吸收。
    后续拿到多能源 Geant4 标定后，可以用新的响应类替换本类。
    """

    def __init__(
        self,
        probability_by_channel: Dict[str, float],
        default_probability: float,
    ):
        self.probability_by_channel = {
            str(key): float(value)
            for key, value in probability_by_channel.items()
        }
        self.default_probability = float(default_probability)

    def full_probability(self, event: MeasuredEvent) -> float:
        value = self.probability_by_channel.get(
            event.terminal_channel,
            self.default_probability,
        )
        return float(np.clip(value, 1e-6, 1.0 - 1e-6))


class ArmResolutionModel:
    """按 hit 数给出高斯 ARM sigma。配置单位为 degree。"""

    def __init__(self, sigma_deg_by_hit_count: Dict[str, float]):
        self.sigma_deg_by_hit_count = {
            str(key): float(value)
            for key, value in sigma_deg_by_hit_count.items()
        }

    def sigma_rad(self, event: MeasuredEvent) -> float:
        key = str(min(event.n_hits, 3))
        sigma_deg = self.sigma_deg_by_hit_count.get(
            key,
            self.sigma_deg_by_hit_count.get("default", 5.0),
        )
        if sigma_deg <= 0.0:
            raise ValueError("ARM sigma 必须大于 0。")
        return float(np.deg2rad(sigma_deg))


class EventKernelFactory:
    """
    把可成像事件转换为多圆锥概率 kernel。

    2-hit：
        对每个全局能量 bin 同时计算 full 与 escape 分支。
    >=3-hit：
        用前三个 hit 的第二散射几何恢复 E0，再用全局能量网格表达测量
        不确定性；后续 hit 的能量仍计入总沉积能量。
    """

    def __init__(
        self,
        spectrum: DiscreteSpectrumPrior,
        response_config: Dict[str, object],
    ):
        self.spectrum = spectrum
        energy_resolution = response_config.get("energy_resolution", {})
        self.energy_resolution = EnergyResolutionModel(
            fractional_sigma=float(
                energy_resolution.get("fractional_sigma", 0.04)
            ),
            noise_sigma_mev=float(
                energy_resolution.get("noise_sigma_mev", 0.005)
            ),
        )
        self.absorption_model = TerminalAbsorptionModel(
            probability_by_channel=response_config.get(
                "full_absorption_probability_by_terminal_channel",
                {},
            ),
            default_probability=float(
                response_config.get(
                    "default_full_absorption_probability",
                    0.2,
                )
            ),
        )
        self.arm_model = ArmResolutionModel(
            response_config.get(
                "arm_sigma_deg_by_hit_count",
                {"2": 5.0, "3": 4.0},
            )
        )
        self.escape_energy_scale_mev = float(
            response_config.get("escape_energy_scale_mev", 0.25)
        )
        self.three_hit_geometry_fractional_sigma = float(
            response_config.get(
                "three_hit_geometry_fractional_sigma",
                0.10,
            )
        )
        self.minimum_hypothesis_weight = float(
            response_config.get("minimum_hypothesis_weight", 1e-15)
        )
        if self.escape_energy_scale_mev <= 0.0:
            raise ValueError("escape_energy_scale_mev 必须大于 0。")
        if self.three_hit_geometry_fractional_sigma <= 0.0:
            raise ValueError(
                "three_hit_geometry_fractional_sigma 必须大于 0。"
            )
        if self.minimum_hypothesis_weight < 0.0:
            raise ValueError("minimum_hypothesis_weight 不能为负。")

    def build(self, event: MeasuredEvent) -> Optional[EventKernel]:
        if event.n_hits < 2:
            return None

        axis = ComptonKinematics.source_side_axis(
            event.hits[0].position_mm,
            event.hits[1].position_mm,
        )
        if event.n_hits == 2:
            hypotheses = self._build_two_hit_hypotheses(event)
        else:
            hypotheses = self._build_three_hit_hypotheses(event)

        hypotheses = [
            hypothesis
            for hypothesis in hypotheses
            if np.isfinite(hypothesis.weight)
            and hypothesis.weight >= self.minimum_hypothesis_weight
        ]
        if not hypotheses:
            return None
        return EventKernel(
            event=event,
            axis_detector=axis,
            hypotheses=hypotheses,
        )

    def build_many(self, events: List[MeasuredEvent]):
        kernels = []
        rejected = []
        for event in events:
            kernel = self.build(event)
            if kernel is None:
                rejected.append(event)
            else:
                kernels.append(kernel)
        return kernels, rejected

    def _build_two_hit_hypotheses(
        self,
        event: MeasuredEvent,
    ) -> List[EnergyHypothesis]:
        first_deposit = event.hits[0].energy_mev
        total_deposit = event.total_deposited_energy_mev
        full_probability = self.absorption_model.full_probability(event)
        arm_sigma = self.arm_model.sigma_rad(event)
        hypotheses: List[EnergyHypothesis] = []

        for energy, spectral_probability in zip(
            self.spectrum.energies_mev,
            self.spectrum.probabilities,
        ):
            theta = ComptonKinematics.first_scatter_angle(
                energy,
                first_deposit,
            )
            if theta is None:
                continue

            cross_section = ComptonKinematics.klein_nishina_relative_weight(
                energy,
                theta,
            )
            if cross_section <= 0.0:
                continue

            full_likelihood = self.energy_resolution.gaussian_likelihood(
                measured=total_deposit,
                expected=energy,
            )
            full_weight = (
                spectral_probability
                * full_probability
                * full_likelihood
                * cross_section
            )
            hypotheses.append(
                EnergyHypothesis(
                    incident_energy_mev=float(energy),
                    deposition_class=DepositionClass.FULL,
                    scatter_angle_rad=theta,
                    arm_sigma_rad=arm_sigma,
                    weight=float(full_weight),
                    diagnostics={
                        "full_probability": full_probability,
                        "missing_energy_mev": float(energy - total_deposit),
                    },
                )
            )

            missing_energy = float(energy - total_deposit)
            if missing_energy < 0.0:
                continue
            scale = self.escape_energy_scale_mev
            escape_likelihood = np.exp(-missing_energy / scale) / scale
            escape_weight = (
                spectral_probability
                * (1.0 - full_probability)
                * escape_likelihood
                * cross_section
            )
            hypotheses.append(
                EnergyHypothesis(
                    incident_energy_mev=float(energy),
                    deposition_class=DepositionClass.ESCAPE,
                    scatter_angle_rad=theta,
                    arm_sigma_rad=arm_sigma,
                    weight=float(escape_weight),
                    diagnostics={
                        "full_probability": full_probability,
                        "missing_energy_mev": missing_energy,
                    },
                )
            )
        return hypotheses

    def _build_three_hit_hypotheses(
        self,
        event: MeasuredEvent,
    ) -> List[EnergyHypothesis]:
        h1, h2, h3 = event.hits[:3]
        recovered_energy = (
            ComptonKinematics.recover_incident_energy_from_three_hits(
                h1.position_mm,
                h2.position_mm,
                h3.position_mm,
                h1.energy_mev,
                h2.energy_mev,
            )
        )
        if recovered_energy is None:
            return []

        sigma = max(
            recovered_energy * self.three_hit_geometry_fractional_sigma,
            self.energy_resolution.sigma(recovered_energy),
        )
        total_deposit = event.total_deposited_energy_mev
        if total_deposit > recovered_energy + 3.0 * sigma:
            # 可见沉积能量显著大于几何恢复的入射能量，说明顺序、位置或
            # 能量至少有一项不相容，不能把它当作高质量 3-hit 锚点。
            return []

        arm_sigma = self.arm_model.sigma_rad(event)
        hypotheses = []
        for energy, spectral_probability in zip(
            self.spectrum.energies_mev,
            self.spectrum.probabilities,
        ):
            energy_sigma = self.energy_resolution.sigma(energy)
            if energy < total_deposit - 3.0 * energy_sigma:
                continue
            theta = ComptonKinematics.first_scatter_angle(
                energy,
                h1.energy_mev,
            )
            if theta is None:
                continue
            residual = (energy - recovered_energy) / sigma
            geometry_likelihood = np.exp(-0.5 * residual * residual) / sigma
            cross_section = ComptonKinematics.klein_nishina_relative_weight(
                energy,
                theta,
            )
            weight = (
                spectral_probability
                * geometry_likelihood
                * cross_section
            )
            hypotheses.append(
                EnergyHypothesis(
                    incident_energy_mev=float(energy),
                    deposition_class=DepositionClass.GEOMETRY_RECOVERED,
                    scatter_angle_rad=theta,
                    arm_sigma_rad=arm_sigma,
                    weight=float(weight),
                    diagnostics={
                        "recovered_energy_mev": recovered_energy,
                        "geometry_sigma_mev": sigma,
                        "missing_energy_mev": float(
                            energy - total_deposit
                        ),
                    },
                )
            )
        return hypotheses
