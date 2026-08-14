from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from ..domain import EventKernel, EventState
from ..geometry import HealpixPixelizer
from .kernel import IndependentEventProposal


@dataclass
class ReconstructionResult:
    """一次 SOE 链的全部可交付结果。"""

    posterior_mean_map: np.ndarray
    posterior_variance_map: np.ndarray
    final_counts: np.ndarray
    final_states: List[EventState]
    hypothesis_visit_counts: List[np.ndarray]
    saved_sample_count: int
    attempted_moves: int
    accepted_moves: int
    acceptance_rate: float
    random_seed: int


class SphericalSoeSampler:
    """
    球面 Stochastic Origin Ensemble 采样器。

    每个事件始终只在天空上放置一个当前 origin。2-hit 的不确定性由
    proposal 同时抽取能量分支和相应圆锥体现；3-hit 的几何恢复使其
    proposal 更窄，因此自然成为高质量锚点。
    """

    def __init__(
        self,
        kernels: List[EventKernel],
        proposal: IndependentEventProposal,
        pixelizer: HealpixPixelizer,
        sweeps: int,
        burn_in_sweeps: int,
        thinning_sweeps: int,
        random_seed: int,
    ):
        if not kernels:
            raise ValueError("没有可用于 SOE 的 EventKernel。")
        if sweeps <= 0 or burn_in_sweeps < 0 or thinning_sweeps <= 0:
            raise ValueError("SOE sweeps/burn-in/thinning 配置不合法。")
        if burn_in_sweeps >= sweeps:
            raise ValueError("burn_in_sweeps 必须小于 sweeps。")

        self.kernels = kernels
        self.proposal = proposal
        self.pixelizer = pixelizer
        self.sweeps = int(sweeps)
        self.burn_in_sweeps = int(burn_in_sweeps)
        self.thinning_sweeps = int(thinning_sweeps)
        self.random_seed = int(random_seed)

        # proposal 与 sampler 必须共享同一个 Generator，保证一个 seed
        # 完整复现实验。这里直接取 proposal 的 generator。
        self.rng = proposal.rng

    def run(self) -> ReconstructionResult:
        states = [
            self.proposal.propose(event_index)
            for event_index in range(len(self.kernels))
        ]
        counts = np.zeros(self.pixelizer.pixel_count, dtype=np.int64)
        for state in states:
            counts[state.pixel_index] += 1

        map_sum = np.zeros(self.pixelizer.pixel_count, dtype=float)
        map_square_sum = np.zeros(self.pixelizer.pixel_count, dtype=float)
        hypothesis_visits = [
            np.zeros(len(kernel.hypotheses), dtype=np.int64)
            for kernel in self.kernels
        ]
        saved_samples = 0
        attempted = 0
        accepted = 0

        for sweep in range(self.sweeps):
            for event_index in self.rng.permutation(len(self.kernels)):
                event_index = int(event_index)
                old_state = states[event_index]
                new_state = self.proposal.propose(event_index)
                attempted += 1

                if new_state.pixel_index == old_state.pixel_index:
                    # 像素占据数未变化，SOE 比为 1；事件 kernel 与 proposal
                    # 已抵消，因此能量/圆内位置的新状态可以直接接受。
                    states[event_index] = new_state
                    accepted += 1
                    continue

                old_pixel = old_state.pixel_index
                new_pixel = new_state.pixel_index
                log_ratio = self._log_soe_count_ratio(
                    old_count=int(counts[old_pixel]),
                    new_count=int(counts[new_pixel]),
                )
                if np.log(self.rng.uniform(0.0, 1.0)) < min(0.0, log_ratio):
                    counts[old_pixel] -= 1
                    counts[new_pixel] += 1
                    states[event_index] = new_state
                    accepted += 1

            if self._should_save(sweep):
                float_counts = counts.astype(float)
                map_sum += float_counts
                map_square_sum += float_counts * float_counts
                for event_index, state in enumerate(states):
                    hypothesis_visits[event_index][
                        state.hypothesis_index
                    ] += 1
                saved_samples += 1

        if saved_samples == 0:
            raise RuntimeError("SOE 没有保存任何后验样本，请检查采样配置。")

        mean_map = map_sum / saved_samples
        variance_map = (
            map_square_sum / saved_samples - mean_map * mean_map
        )
        variance_map = np.maximum(variance_map, 0.0)
        return ReconstructionResult(
            posterior_mean_map=mean_map,
            posterior_variance_map=variance_map,
            final_counts=counts.copy(),
            final_states=states,
            hypothesis_visit_counts=hypothesis_visits,
            saved_sample_count=saved_samples,
            attempted_moves=attempted,
            accepted_moves=accepted,
            acceptance_rate=accepted / attempted if attempted else 0.0,
            random_seed=self.random_seed,
        )

    def _should_save(self, sweep: int) -> bool:
        if sweep < self.burn_in_sweeps:
            return False
        return (sweep - self.burn_in_sweeps) % self.thinning_sweeps == 0

    @staticmethod
    def _g(count: int) -> float:
        if count <= 0:
            return 0.0
        return float(count * np.log(count))

    @classmethod
    def _log_soe_count_ratio(
        cls,
        old_count: int,
        new_count: int,
    ) -> float:
        """
        原始 SOE 风格的像素占据数比，使用对数避免 d^d 溢出。

        old_count 包含当前事件，所以必须至少为 1。
        """

        if old_count < 1 or new_count < 0:
            raise ValueError("SOE 像素计数状态不合法。")
        return (
            cls._g(new_count + 1)
            + cls._g(old_count - 1)
            - cls._g(new_count)
            - cls._g(old_count)
        )

