from __future__ import annotations

from typing import Optional

import numpy as np


class ComptonKinematics:
    """集中实现所有康普顿公式，避免不同模块出现符号或单位不一致。"""

    ELECTRON_REST_ENERGY_MEV = 0.51099895

    @classmethod
    def first_scatter_angle(
        cls,
        incident_energy_mev: float,
        first_deposit_mev: float,
    ) -> Optional[float]:
        """
        已知入射能量和第一次沉积能量时计算第一次散射角。

        第一次散射后的光子能量为 E0-E1。返回 None 表示该能量假设与
        康普顿运动学不相容。
        """

        e0 = float(incident_energy_mev)
        e1 = float(first_deposit_mev)
        e_after = e0 - e1
        if e0 <= 0.0 or e1 <= 0.0 or e_after <= 0.0:
            return None

        cos_theta = 1.0 - cls.ELECTRON_REST_ENERGY_MEV * (
            1.0 / e_after - 1.0 / e0
        )
        if not np.isfinite(cos_theta) or cos_theta < -1.0 or cos_theta > 1.0:
            return None
        return float(np.arccos(np.clip(cos_theta, -1.0, 1.0)))

    @staticmethod
    def source_side_axis(first_position_mm, second_position_mm):
        """
        返回指向源一侧的圆锥轴 -normalize(r2-r1)。

        r2-r1 是第一次散射后光子的传播方向；天空图使用“探测器指向源”
        的方向定义，因此需要取负号。
        """

        propagation = np.asarray(second_position_mm) - np.asarray(
            first_position_mm
        )
        norm = float(np.linalg.norm(propagation))
        if norm <= 0.0:
            raise ValueError("前两个 hit 位置重合，无法定义康普顿圆锥轴。")
        return -propagation / norm

    @classmethod
    def recover_incident_energy_from_three_hits(
        cls,
        r1_mm,
        r2_mm,
        r3_mm,
        first_deposit_mev: float,
        second_deposit_mev: float,
    ) -> Optional[float]:
        """
        用第二次散射几何恢复 3-hit 事件的入射能量。

        设第二次散射前光子能量为 K，第二个 hit 沉积 E2，几何散射角
        为 theta2。由

            1/(K-E2) - 1/K = (1-cos(theta2))/m_ec^2

        解出 K，再加第一次沉积 E1 得到 E0。该推导不要求第三个 hit
        完全吸收，因此可以恢复部分 3-hit escape 事件。
        """

        incoming = np.asarray(r2_mm, dtype=float) - np.asarray(
            r1_mm, dtype=float
        )
        outgoing = np.asarray(r3_mm, dtype=float) - np.asarray(
            r2_mm, dtype=float
        )
        incoming_norm = float(np.linalg.norm(incoming))
        outgoing_norm = float(np.linalg.norm(outgoing))
        e1 = float(first_deposit_mev)
        e2 = float(second_deposit_mev)

        if incoming_norm <= 0.0 or outgoing_norm <= 0.0 or e1 <= 0.0 or e2 <= 0.0:
            return None

        cos_theta = float(
            np.dot(incoming, outgoing) / (incoming_norm * outgoing_norm)
        )
        cos_theta = float(np.clip(cos_theta, -1.0, 1.0))
        coefficient = (
            1.0 - cos_theta
        ) / cls.ELECTRON_REST_ENERGY_MEV

        # theta2 接近 0 时分母趋近 0，几何能量估计极不稳定。
        if coefficient <= 1e-12:
            return None

        discriminant = e2 * e2 + 4.0 * e2 / coefficient
        if discriminant <= 0.0 or not np.isfinite(discriminant):
            return None

        energy_before_second = 0.5 * (e2 + np.sqrt(discriminant))
        incident_energy = e1 + energy_before_second
        if not np.isfinite(incident_energy) or incident_energy <= e1:
            return None
        return float(incident_energy)

    @staticmethod
    def klein_nishina_relative_weight(
        incident_energy_mev: float,
        scatter_angle_rad: float,
    ) -> float:
        """
        未归一化 Klein-Nishina 微分截面，仅用作同一事件能量假设间的权重。

        绝对常数会在离散能量假设归一化时抵消，因此这里省略 r_e^2/2。
        """

        energy = float(incident_energy_mev)
        theta = float(scatter_angle_rad)
        if energy <= 0.0 or not np.isfinite(theta):
            return 0.0

        ratio = 1.0 / (
            1.0
            + energy
            / ComptonKinematics.ELECTRON_REST_ENERGY_MEV
            * (1.0 - np.cos(theta))
        )
        value = ratio * ratio * (
            ratio + 1.0 / ratio - np.sin(theta) ** 2
        )
        return float(max(value, 0.0))

