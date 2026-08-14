"""康普顿运动学的最小回归测试；本文件由服务器端 pytest 执行。"""

import numpy as np

from soe1.physics import ComptonKinematics


def test_first_scatter_angle_rejects_impossible_energy():
    assert ComptonKinematics.first_scatter_angle(0.2, 0.3) is None


def test_three_hit_energy_recovery_matches_constructed_geometry():
    """
    构造 90 degree 第二次散射。

    先选第二次散射前能量 K，再由康普顿公式计算第二次沉积 E2，验证反解
    能够恢复 E0=E1+K。
    """

    electron_rest = ComptonKinematics.ELECTRON_REST_ENERGY_MEV
    energy_before_second = 0.45
    energy_after_second = 1.0 / (
        1.0 / energy_before_second + 1.0 / electron_rest
    )
    second_deposit = energy_before_second - energy_after_second
    first_deposit = 0.12

    recovered = ComptonKinematics.recover_incident_energy_from_three_hits(
        r1_mm=np.array([0.0, 0.0, 0.0]),
        r2_mm=np.array([0.0, 0.0, 1.0]),
        r3_mm=np.array([1.0, 0.0, 1.0]),
        first_deposit_mev=first_deposit,
        second_deposit_mev=second_deposit,
    )
    assert np.isclose(
        recovered,
        first_deposit + energy_before_second,
        rtol=1e-10,
    )

