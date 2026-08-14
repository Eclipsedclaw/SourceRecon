from __future__ import annotations

from typing import List

import numpy as np

from ..domain import EventKernel, EventState
from ..geometry import AttitudeProvider, ConeDirectionSampler, HealpixPixelizer


class IndependentEventProposal:
    """
    从单事件物理 kernel 独立提出 (energy, class, direction)。

    proposal 恰好等于每个事件在不考虑 SOE 聚集项时的归一化分布。于是
    Metropolis-Hastings 中事件响应的 new/old 比与 proposal reverse/forward
    比严格抵消，采样器只需计算 SOE 像素占据数变化。这不是忽略响应；
    响应已经完整进入 proposal 的可达范围和抽样频率。
    """

    def __init__(
        self,
        kernels: List[EventKernel],
        attitude_provider: AttitudeProvider,
        pixelizer: HealpixPixelizer,
        random_generator: np.random.Generator,
    ):
        self.kernels = kernels
        self.attitude_provider = attitude_provider
        self.pixelizer = pixelizer
        self.rng = random_generator
        self.direction_sampler = ConeDirectionSampler(random_generator)
        self._hypothesis_probabilities = [
            self._normalize_weights(kernel) for kernel in kernels
        ]

    def propose(self, event_index: int) -> EventState:
        kernel = self.kernels[event_index]
        probabilities = self._hypothesis_probabilities[event_index]
        hypothesis_index = int(
            self.rng.choice(len(kernel.hypotheses), p=probabilities)
        )
        hypothesis = kernel.hypotheses[hypothesis_index]
        direction_detector = self.direction_sampler.sample(
            axis=kernel.axis_detector,
            scatter_angle_rad=hypothesis.scatter_angle_rad,
            arm_sigma_rad=hypothesis.arm_sigma_rad,
        )
        direction_sky = self.attitude_provider.detector_to_sky(
            kernel.event,
            direction_detector,
        )
        pixel = self.pixelizer.direction_to_pixel(direction_sky)
        return EventState(
            event_index=event_index,
            hypothesis_index=hypothesis_index,
            direction_detector=direction_detector,
            direction_sky=direction_sky,
            pixel_index=pixel,
        )

    @staticmethod
    def _normalize_weights(kernel: EventKernel) -> np.ndarray:
        weights = np.asarray(
            [hypothesis.weight for hypothesis in kernel.hypotheses],
            dtype=float,
        )
        total = float(weights.sum())
        if total <= 0.0 or not np.isfinite(total):
            raise ValueError(
                "event " + kernel.event.event_id + " 的 hypothesis 权重无效。"
            )
        return weights / total

