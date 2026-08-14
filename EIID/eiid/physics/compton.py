"""康普顿运动学基础公式。"""

from __future__ import annotations

from typing import Optional

import numpy as np


class ComptonKinematics:
    """康普顿候选能量、散射角和来源侧圆锥轴。

    本类只判断解析运动学可行性。真实核宽度、逃逸概率、Doppler 展宽和拓扑
    概率属于 `DetectorResponse`，不得在此写成固定 5 度高斯。
    """

    ELECTRON_REST_ENERGY_MEV = 0.51099895

    @classmethod
    def scatter_cosine(cls, incident_energy_mev: float, first_deposit_mev: float) -> Optional[float]:
        """计算第一散射角余弦。

        采用设计基线公式：

            cos(theta) = 1 - m_e c^2 * [1/(E-e1) - 1/E]

        若候选入射能量不能解释第一沉积，或结果越出物理范围，则返回 None。
        """

        incident = float(incident_energy_mev)
        deposit = float(first_deposit_mev)
        if (
            not np.isfinite(incident)
            or not np.isfinite(deposit)
            or incident <= 0.0
            or deposit < 0.0
            or incident <= deposit
        ):
            return None
        remaining = incident - deposit
        cosine = 1.0 - cls.ELECTRON_REST_ENERGY_MEV * (
            1.0 / remaining - 1.0 / incident
        )
        tolerance = 1e-12
        if cosine < -1.0 - tolerance or cosine > 1.0 + tolerance:
            return None
        return float(np.clip(cosine, -1.0, 1.0))

    @classmethod
    def scatter_angle_rad(cls, incident_energy_mev: float, first_deposit_mev: float) -> Optional[float]:
        """返回候选第一散射角（弧度），不可行时返回 None。"""

        cosine = cls.scatter_cosine(incident_energy_mev, first_deposit_mev)
        return None if cosine is None else float(np.arccos(cosine))

    @staticmethod
    def source_side_axis(first_position_mm, second_position_mm) -> np.ndarray:
        """由前两个交互位置构造指向来源一侧的康普顿圆锥轴。

        gamma 在两次交互之间沿 `(r2-r1)` 传播，因此来源侧轴为其反方向：
        `-normalize(r2-r1)`。对当前正常中心事件，该轴约为全局 `-Z`。
        """

        first = np.asarray(first_position_mm, dtype=float)
        second = np.asarray(second_position_mm, dtype=float)
        if first.shape != (3,) or second.shape != (3,):
            raise ValueError("交互位置必须是三维向量。")
        delta = second - first
        norm = float(np.linalg.norm(delta))
        if not np.all(np.isfinite(delta)) or norm <= 0.0:
            raise ValueError("两次交互位置必须有限且不能重合。")
        return -delta / norm

