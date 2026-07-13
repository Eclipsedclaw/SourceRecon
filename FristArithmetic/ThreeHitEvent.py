# ThreeHitEvent.py

import numpy as np


class ThreeHitEvent:
    """
    单个 3-hit 康普顿候选事件。

    一个 ThreeHitEvent 对象只表示一个候选 event，例如：
        ch0 -> ch1 -> ch2

    这个类内部保存：
        1. EventID
        2. 三个 hit 的通道、层号、像素号
        3. 三个 hit 的位置
        4. 三个 hit 的能量
        5. 第一次散射角，用于生成 Compton cone
        6. 第二次散射的能量角和几何角，用于内部一致性打分
        7. 分数 score
    """

    MEC2_MEV = 0.51099895

    def __init__(self, event_id, hit1, hit2, hit3, sigma_delta_cos=0.15):
        self.event_id = event_id

        self.hit1 = hit1
        self.hit2 = hit2
        self.hit3 = hit3

        self.n_hits = 3
        self.event_type = "3hit"

        self.sigma_delta_cos = sigma_delta_cos

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

        self.distance_12 = self._distance(self.r1, self.r2)
        self.distance_23 = self._distance(self.r2, self.r3)

        # 第一次散射角：后面生成 Compton cone 用
        self.cos_theta_c_first = self._calculate_first_compton_cos()
        self.theta_c_first = self._calculate_theta_from_cos(
            self.cos_theta_c_first
        )

        # 第二次散射角：3-hit 内部自洽性检查用
        self.cos_theta_c_second = self._calculate_second_compton_cos()
        self.cos_theta_g_second = self._calculate_second_geometry_cos()
        self.delta_cos_second = self._calculate_delta_cos_second()

        self.is_physical = self._check_physical_validity()

        # 当前先用手写分数，后面可以替换成 ML score
        self.score = self._calculate_score()

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

        第一次散射前：
            E_before = E1 + E2 + E3

        第一次散射后：
            E_after = E2 + E3
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

        第二次散射前：
            E_before = E2 + E3

        第二次散射后：
            E_after = E3
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
        三点事件最重要的打分依据之一：

            delta_cos_second
            = cos(theta_C_second) - cos(theta_G_second)

        越接近 0，说明这个 3-hit event 越自洽。
        """

        if np.isnan(self.cos_theta_c_second):
            return np.nan

        if np.isnan(self.cos_theta_g_second):
            return np.nan

        return float(self.cos_theta_c_second - self.cos_theta_g_second)

    def _valid_cos(self, value):
        if np.isnan(value):
            return False

        return -1.0 <= value <= 1.0

    def _check_physical_validity(self):
        """
        3-hit event 的基本物理检查。
        """

        valid_first = self._valid_cos(self.cos_theta_c_first)
        valid_second_c = self._valid_cos(self.cos_theta_c_second)
        valid_second_g = self._valid_cos(self.cos_theta_g_second)

        return valid_first and valid_second_c and valid_second_g

    def _calculate_score(self):
        """
        当前版本的 3-hit 初步分数。

        核心依据：
            delta_cos_second 越接近 0，分数越高。

        后期这里可以替换成：
            score = model.predict(features)
        """

        if not self.is_physical:
            return 0.0

        if np.isnan(self.delta_cos_second):
            return 0.0

        if self.layers == sorted(self.layers):
            layer_score = 1.0
        else:
            layer_score = 0.2

        compton_score = np.exp(
            -0.5 * (self.delta_cos_second / self.sigma_delta_cos) ** 2
        )

        return float(layer_score * compton_score)

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

            "is_physical": self.is_physical,
            "score": self.score,
        }