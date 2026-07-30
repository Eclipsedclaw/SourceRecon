# DetectorResolution.py

import numpy as np


class DetectorResolutionModel:
    """
    探测器分辨率模型。

    作用：
        为 ThreeHitEvent 的逐事件误差传播提供两个输入：
            1. 能量分辨率 sigma_E(E)
            2. 位置分辨率 sigma_pos

    能量分辨率模型：
        sigma_E(E) = energy_a * sqrt(E) + energy_b    (单位 MeV)

        这是最常用的经验形式：
            statistical 项 ~ sqrt(E)
            electronic noise 项 ~ 常数

    重要：
        默认参数只是占位值！
        必须用你自己的刻度数据拟合 energy_a / energy_b，
        否则 pull 的归一化没有意义。

        拟合方法：
            对刻度中每个已知峰，取峰位 E_i 和峰的 sigma_i，
            用 from_calibration_points() 做最小二乘。
    """

    def __init__(
        self,
        energy_a=0.010,        # TODO: 用刻度数据拟合
        energy_b=0.002,        # TODO: 用刻度数据拟合
        sigma_pos_mm=1.5,      # TODO: 约等于 像素间距 / sqrt(12)，z 方向取层厚 / sqrt(12)
        sigma_delta_floor=0.02,
    ):
        """
        参数：
            energy_a:
                能量分辨率 sqrt 项系数，单位 sqrt(MeV)。

            energy_b:
                能量分辨率常数项，单位 MeV。

            sigma_pos_mm:
                单个 hit 的有效位置不确定度，单位 mm。
                像素探测器一般取 pitch / sqrt(12)。

            sigma_delta_floor:
                sigma_delta 的下限。
                防止个别事件传播出的 sigma 过小，
                导致 pull 爆炸（比如 sin(theta) 接近 0 的病态几何）。
        """

        self.energy_a = float(energy_a)
        self.energy_b = float(energy_b)
        self.sigma_pos_mm = float(sigma_pos_mm)
        self.sigma_delta_floor = float(sigma_delta_floor)

    def sigma_energy(self, energy_mev):
        """
        返回给定能量下的能量不确定度 sigma_E，单位 MeV。
        """

        e = max(float(energy_mev), 1e-6)

        return self.energy_a * np.sqrt(e) + self.energy_b

    def sigma_position(self):
        """
        返回单个 hit 的位置不确定度，单位 mm。
        """

        return self.sigma_pos_mm

    @classmethod
    def from_calibration_points(
        cls,
        peak_energies_mev,
        peak_sigmas_mev,
        sigma_pos_mm=1.5,
        sigma_delta_floor=0.02,
    ):
        """
        用刻度峰数据拟合能量分辨率模型。

        参数：
            peak_energies_mev:
                各刻度峰的能量列表，单位 MeV。
                例如 [0.122, 0.511, 0.662, 1.275]

            peak_sigmas_mev:
                对应峰的高斯 sigma 列表，单位 MeV。
                注意是 sigma 不是 FWHM。
                FWHM 换算：sigma = FWHM / 2.355

        拟合：
            sigma = a * sqrt(E) + b
            对 (sqrt(E), 1) 做线性最小二乘。
        """

        energies = np.asarray(peak_energies_mev, dtype=float)
        sigmas = np.asarray(peak_sigmas_mev, dtype=float)

        if len(energies) < 2:
            raise ValueError("至少需要两个刻度峰才能拟合 a 和 b。")

        design = np.vstack([np.sqrt(energies), np.ones_like(energies)]).T

        coeffs, _, _, _ = np.linalg.lstsq(design, sigmas, rcond=None)

        a, b = float(coeffs[0]), float(coeffs[1])

        return cls(
            energy_a=a,
            energy_b=b,
            sigma_pos_mm=sigma_pos_mm,
            sigma_delta_floor=sigma_delta_floor,
        )

    def __repr__(self):
        return (
            f"DetectorResolutionModel("
            f"energy_a={self.energy_a:.5f}, "
            f"energy_b={self.energy_b:.5f}, "
            f"sigma_pos_mm={self.sigma_pos_mm:.2f}, "
            f"sigma_delta_floor={self.sigma_delta_floor:.3f})"
        )