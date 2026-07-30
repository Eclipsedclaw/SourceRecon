# ThreeHitEvent.py

import numpy as np


class ThreeHitEvent:
    """
    单个 3-hit 康普顿候选事件。

    相比旧版本的核心变化：
        打分不再使用固定宽度 sigma_delta_cos=0.15 的裸 delta，
        而是用逐事件误差传播得到的 sigma_delta，
        把 delta 归一化成有统计含义的 pull：

            pull = delta_cos_second / sigma_delta(该事件)

        真事件（组合正确 + 全吸收）的 pull 应服从标准正态分布；
        假组合的 pull 是宽平台。

        分数：
            score = layer_score * exp(-0.5 * pull^2)

    物理逻辑说明（天基约束下的设计决策）：
        3-hit 事件在第二个作用点恰好有一条冗余约束
        （能量算的散射角 vs 几何算的散射角）。
        我们把这条约束全部花在"真伪鉴别"上：
        通过检验的事件同时意味着组合正确且全吸收，
        因此它的 E_total 就是真实入射能量，
        第一散射角（锥角）直接用 E_total 计算即可，
        不依赖任何已知源能量 E0。
    """

    MEC2_MEV = 0.51099895

    def __init__(
        self,
        event_id,
        hit1,
        hit2,
        hit3,
        sigma_delta_cos=0.15,
        resolution_model=None,
    ):
        """
        参数：
            sigma_delta_cos:
                兼容旧接口的固定宽度。
                仅当 resolution_model 为 None 时作为 sigma_delta 使用。

            resolution_model:
                DetectorResolutionModel 对象。
                提供后启用逐事件误差传播（推荐）。
        """

        self.event_id = event_id

        self.hit1 = hit1
        self.hit2 = hit2
        self.hit3 = hit3

        self.n_hits = 3
        self.event_type = "3hit"

        self.sigma_delta_cos_fallback = sigma_delta_cos
        self.resolution_model = resolution_model

        self.hit_ids = [hit1["hit_id"], hit2["hit_id"], hit3["hit_id"]]
        self.channels = [hit1["channel"], hit2["channel"], hit3["channel"]]
        self.layers = [hit1["layer"], hit2["layer"], hit3["layer"]]
        self.pixelids = [hit1["pixelid"], hit2["pixelid"], hit3["pixelid"]]

        self.r1 = hit1["pos"]
        self.r2 = hit2["pos"]
        self.r3 = hit3["pos"]

        self.E1 = hit1["energy"]
        self.E2 = hit2["energy"]
        self.E3 = hit3["energy"]
        self.E_total = self.E1 + self.E2 + self.E3

        # 能量份额特征（能量尺度无关，适合未知能谱场景）
        if self.E_total > 0:
            self.E1_fraction = self.E1 / self.E_total
        else:
            self.E1_fraction = 0.0

        self.distance_12 = self._distance(self.r1, self.r2)
        self.distance_23 = self._distance(self.r2, self.r3)

        # 第一次散射角：生成 Compton cone 用。
        # 使用 E_total 计算——对通过 pull 筛选的事件（隐含全吸收），
        # E_total 就是真实入射能量，此角度正确。
        self.cos_theta_c_first = self._calculate_first_compton_cos()
        self.theta_c_first = self._calculate_theta_from_cos(
            self.cos_theta_c_first
        )

        # 第二次散射角：能量法 vs 几何法
        self.cos_theta_c_second = self._calculate_second_compton_cos()
        self.cos_theta_g_second = self._calculate_second_geometry_cos()
        self.delta_cos_second = self._calculate_delta_cos_second()

        # ===== 新增：逐事件不确定度 + pull =====
        self.sigma_delta_second = self._calculate_sigma_delta_second()
        self.pull_second = self._calculate_pull_second()

        self.is_physical = self._check_physical_validity()

        self.score = self._calculate_score()

    # ============================================================
    # 基础几何 / 运动学
    # ============================================================

    def _distance(self, r_a, r_b):
        return float(np.linalg.norm(r_b - r_a))

    def _calculate_theta_from_cos(self, cos_value):
        if np.isnan(cos_value):
            return np.nan

        if cos_value < -1.0 or cos_value > 1.0:
            return np.nan

        return float(np.arccos(cos_value))

    def _calculate_first_compton_cos(self):
        """
        第一次散射角。

        h1 -> h2 -> h3

        E_before = E1 + E2 + E3
        E_after  = E2 + E3
        """

        e_before = self.E_total
        e_after = self.E2 + self.E3

        if e_before <= 0 or e_after <= 0:
            return np.nan

        cos_theta = 1.0 - self.MEC2_MEV * (
            1.0 / e_after - 1.0 / e_before
        )

        return float(cos_theta)

    def _calculate_second_compton_cos(self):
        """
        第二次散射角，由能量计算。

        E_before = E2 + E3
        E_after  = E3
        """

        e_before = self.E2 + self.E3
        e_after = self.E3

        if e_before <= 0 or e_after <= 0:
            return np.nan

        cos_theta = 1.0 - self.MEC2_MEV * (
            1.0 / e_after - 1.0 / e_before
        )

        return float(cos_theta)

    def _calculate_second_geometry_cos(self):
        """
        第二次散射角，由几何计算。

        在 h2 处：
            入射方向：r2 - r1
            出射方向：r3 - r2
        """

        v_in = self.r2 - self.r1
        v_out = self.r3 - self.r2

        norm_in = np.linalg.norm(v_in)
        norm_out = np.linalg.norm(v_out)

        if norm_in == 0 or norm_out == 0:
            return np.nan

        cos_theta = np.dot(v_in, v_out) / (norm_in * norm_out)

        return float(cos_theta)

    def _calculate_delta_cos_second(self):
        """
        delta_cos_second = cos(theta_C_second) - cos(theta_G_second)

        越接近 0 越自洽。
        """

        if np.isnan(self.cos_theta_c_second):
            return np.nan

        if np.isnan(self.cos_theta_g_second):
            return np.nan

        return float(self.cos_theta_c_second - self.cos_theta_g_second)

    # ============================================================
    # 新增：逐事件误差传播
    # ============================================================

    def _calculate_sigma_delta_second(self):
        """
        计算 delta_cos_second 的逐事件不确定度。

        sigma_delta^2 = sigma_C^2 + sigma_G^2 + floor^2

        能量侧（cos_C = 1 - mec2 * (1/E3 - 1/(E2+E3))）：

            d(cos_C)/dE2 = - mec2 / (E2+E3)^2
            d(cos_C)/dE3 =   mec2 / E3^2 - mec2 / (E2+E3)^2

            sigma_C^2 = (d/dE2 * sigma_E2)^2 + (d/dE3 * sigma_E3)^2

        几何侧：
            单段方向不确定度 ~ sqrt(2) * sigma_pos / L
            （两个端点各贡献一份，忽略 r2 共享带来的关联，第一版足够）

            sigma_theta^2 = 2*(sigma_pos/L12)^2 + 2*(sigma_pos/L23)^2
            sigma_G = |sin(theta_G)| * sigma_theta

            sin 接近 0 时该式会低估误差，
            所以对 sin 设下限，另外整体再加 floor。

        没有 resolution_model 时退回固定宽度（旧行为）。
        """

        if self.resolution_model is None:
            return float(self.sigma_delta_cos_fallback)

        if self.E2 <= 0 or self.E3 <= 0:
            return np.nan

        if self.distance_12 <= 0 or self.distance_23 <= 0:
            return np.nan

        # ---------- 能量侧 ----------
        e23 = self.E2 + self.E3

        sigma_e2 = self.resolution_model.sigma_energy(self.E2)
        sigma_e3 = self.resolution_model.sigma_energy(self.E3)

        dcos_de2 = -self.MEC2_MEV / (e23 ** 2)
        dcos_de3 = (
            self.MEC2_MEV / (self.E3 ** 2)
            - self.MEC2_MEV / (e23 ** 2)
        )

        sigma_c_sq = (
            (dcos_de2 * sigma_e2) ** 2
            + (dcos_de3 * sigma_e3) ** 2
        )

        # ---------- 几何侧 ----------
        sigma_pos = self.resolution_model.sigma_position()

        sigma_theta_sq = (
            2.0 * (sigma_pos / self.distance_12) ** 2
            + 2.0 * (sigma_pos / self.distance_23) ** 2
        )

        cos_g = self.cos_theta_g_second

        if np.isnan(cos_g):
            sin_theta = 1.0
        else:
            sin_theta = np.sqrt(max(0.0, 1.0 - cos_g ** 2))

        # sin 下限：防止 theta 接近 0 或 180 度时低估几何误差
        sin_eff = max(sin_theta, 0.1)

        sigma_g_sq = (sin_eff ** 2) * sigma_theta_sq

        # ---------- 合成 ----------
        floor = self.resolution_model.sigma_delta_floor

        sigma_delta = np.sqrt(sigma_c_sq + sigma_g_sq + floor ** 2)

        return float(sigma_delta)

    def _calculate_pull_second(self):
        """
        pull = delta / sigma_delta

        真事件（组合正确 + 全吸收）：pull ~ N(0, 1)
        假组合 / 逃逸事件：|pull| 系统性偏大
        """

        if np.isnan(self.delta_cos_second):
            return np.nan

        sigma = self.sigma_delta_second

        if sigma is None or np.isnan(sigma) or sigma <= 0:
            return np.nan

        return float(self.delta_cos_second / sigma)

    # ============================================================
    # 物理合法性与打分
    # ============================================================

    def _valid_cos(self, value):
        if np.isnan(value):
            return False

        return -1.0 <= value <= 1.0

    def _check_physical_validity(self):
        valid_first = self._valid_cos(self.cos_theta_c_first)
        valid_second_c = self._valid_cos(self.cos_theta_c_second)
        valid_second_g = self._valid_cos(self.cos_theta_g_second)

        return valid_first and valid_second_c and valid_second_g

    def _calculate_score(self):
        """
        基于 pull 的解析分数。

        score = layer_score * exp(-0.5 * pull^2)

        pull 的含义使得阈值可以直接按 sigma 说话：
            score >= 0.61  等价于  |pull| <= 1
            score >= 0.14  等价于  |pull| <= 2
            score >= 0.011 等价于  |pull| <= 3
        """

        if not self.is_physical:
            return 0.0

        if np.isnan(self.pull_second):
            return 0.0

        if self.layers == sorted(self.layers):
            layer_score = 1.0
        else:
            layer_score = 0.2

        # 限幅防止 exp 下溢告警
        pull_clipped = min(abs(self.pull_second), 30.0)

        consistency_score = np.exp(-0.5 * pull_clipped ** 2)

        return float(layer_score * consistency_score)

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "n_hits": self.n_hits,

            "hit_ids": self.hit_ids,
            "channels": self.channels,
            "layers": self.layers,
            "pixelids": self.pixelids,

            "E1": self.E1,
            "E2": self.E2,
            "E3": self.E3,
            "E_total": self.E_total,
            "E1_fraction": self.E1_fraction,

            "r1": self.r1,
            "r2": self.r2,
            "r3": self.r3,

            "distance_12": self.distance_12,
            "distance_23": self.distance_23,

            "cos_theta_c_first": self.cos_theta_c_first,
            "theta_c_first": self.theta_c_first,

            "cos_theta_c_second": self.cos_theta_c_second,
            "cos_theta_g_second": self.cos_theta_g_second,
            "delta_cos_second": self.delta_cos_second,

            "sigma_delta_second": self.sigma_delta_second,
            "pull_second": self.pull_second,

            "is_physical": self.is_physical,
            "score": self.score,
        }