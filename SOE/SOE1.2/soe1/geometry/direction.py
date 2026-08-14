from __future__ import annotations

from typing import Tuple

import numpy as np


class ConeDirectionSampler:
    """
    在 ARM 加宽的球面事件圆上抽取方向。

    beta 的目标测度为

        p(beta) ∝ Normal(beta | theta, sigma) * sin(beta)

    其中 sin(beta) 是均匀球面立体角 dOmega 的雅可比。phi 均匀分布于
    [0, 2pi)。这样 proposal 与 README 中定义的事件方向 kernel 一致。
    """

    def __init__(self, random_generator: np.random.Generator):
        self.rng = random_generator

    def sample(
        self,
        axis: np.ndarray,
        scatter_angle_rad: float,
        arm_sigma_rad: float,
    ) -> np.ndarray:
        axis = self._normalize(axis)
        e1, e2 = self._orthonormal_basis(axis)
        beta = self._sample_beta(scatter_angle_rad, arm_sigma_rad)
        phi = float(self.rng.uniform(0.0, 2.0 * np.pi))

        direction = (
            np.cos(beta) * axis
            + np.sin(beta)
            * (np.cos(phi) * e1 + np.sin(phi) * e2)
        )
        return self._normalize(direction)

    def _sample_beta(self, theta: float, sigma: float) -> float:
        if sigma <= 0.0:
            raise ValueError("ARM sigma 必须大于 0。")

        # 从截断高斯提出，再用 sin(beta) 接受，得到相对于 dOmega 正确的
        # 环带分布。拒绝法失败时宁可报错，也不静默改变目标分布。
        for _ in range(10000):
            beta = float(self.rng.normal(theta, sigma))
            if beta < 0.0 or beta > np.pi:
                continue
            if self.rng.uniform(0.0, 1.0) <= np.sin(beta):
                return beta
        raise RuntimeError("ARM beta 拒绝采样 10000 次仍未成功。")

    @staticmethod
    def _orthonormal_basis(axis: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        # 选择与 axis 最不平行的笛卡尔基向量，提高叉乘数值稳定性。
        candidates = np.eye(3)
        reference = candidates[np.argmin(np.abs(candidates @ axis))]
        e1 = np.cross(reference, axis)
        e1 = e1 / np.linalg.norm(e1)
        e2 = np.cross(axis, e1)
        e2 = e2 / np.linalg.norm(e2)
        return e1, e2

    @staticmethod
    def _normalize(vector: np.ndarray) -> np.ndarray:
        value = np.asarray(vector, dtype=float)
        norm = float(np.linalg.norm(value))
        if value.shape != (3,) or norm <= 0.0:
            raise ValueError("方向必须是非零三维向量。")
        return value / norm

