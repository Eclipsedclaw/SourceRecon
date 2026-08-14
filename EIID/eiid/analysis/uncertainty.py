"""重建结果的轻量不确定度诊断。"""

from __future__ import annotations

import numpy as np


class DiagonalFisherUncertainty:
    """计算 list-mode Poisson 观测 Fisher 信息的对角近似。

    该近似忽略联合单元间协方差，适合快速诊断和能谱误差条展示，不等同于
    完整置信区间。输出元数据必须保留这一限制。
    """

    METHOD = "observed_fisher_diagonal_covariance_ignored"

    @staticmethod
    def estimate(
        image, responses, denominator_floor: float = 1e-12,
        background_event_density=None,
    ):
        estimate = np.asarray(image, dtype=float).reshape(-1)
        response_items = tuple(responses)
        backgrounds = (
            np.zeros(len(response_items), dtype=float)
            if background_event_density is None
            else np.asarray(background_event_density, dtype=float).reshape(-1)
        )
        if backgrounds.size != len(response_items):
            raise ValueError("不确定度背景密度数量与事件数不一致。")
        information = np.zeros_like(estimate)
        invalid = 0
        for index, response in enumerate(response_items):
            denominator = response.dot(estimate) + backgrounds[index]
            if denominator <= float(denominator_floor):
                invalid += 1
                continue
            contribution = (response.values / denominator) ** 2
            np.add.at(information, response.cell_indices, contribution)
        standard_error = np.full_like(estimate, np.nan)
        active = information > 0.0
        standard_error[active] = 1.0 / np.sqrt(information[active])
        return standard_error, {
            "method": DiagonalFisherUncertainty.METHOD,
            "invalid_denominator_event_count": invalid,
            "finite_standard_error_cell_count": int(np.sum(active)),
        }
